import unittest
from unittest import mock

import requests

from registry_kit import health
from registry_kit.health import next_state, run_health
from tests.helpers import TempRepo, resource

OK = {'result': 'ok', 'status': 200, 'final_url': 'https://a.example.net/'}
DOWN = {'result': 'timeout', 'status': None, 'detail': 'read timed out'}


class ClassifyTest(unittest.TestCase):
    def test_status_codes(self):
        self.assertEqual(health.classify_status(200), 'ok')
        for code in (401, 403, 405, 406, 429):
            self.assertEqual(health.classify_status(code), 'restricted')
        self.assertEqual(health.classify_status(503, '<title>Just a moment...</title>'), 'restricted')
        self.assertEqual(health.classify_status(503), 'server_error')
        self.assertEqual(health.classify_status(404), 'not_found')
        self.assertEqual(health.classify_status(410), 'not_found')
        self.assertEqual(health.classify_status(400), 'client_error')

    def test_exceptions(self):
        self.assertEqual(health.classify_exception(requests.exceptions.ConnectTimeout('x')), 'timeout')
        self.assertEqual(health.classify_exception(requests.exceptions.SSLError('x')), 'ssl_error')
        self.assertEqual(health.classify_exception(requests.exceptions.ConnectionError('NameResolutionError: x')),
                         'dns_error')
        self.assertEqual(health.classify_exception(requests.exceptions.ConnectionError('[Errno 111] Connection refused')),
                         'refused')

    def test_unknown_charset_falls_back_to_utf8(self):
        self.assertEqual(health.decode('café'.encode('utf-8'), 'x-user-defined-nonsense'), 'café')
        self.assertEqual(health.decode('café'.encode('latin-1'), 'latin-1'), 'café')

    def test_report_stays_within_the_issue_size_limit(self):
        records = {f'r{i:04d}': {'state': 'unconfirmed', 'result': 'timeout', 'url': f'https://r{i}.example.net/',
                                 'failing_since': '2026-01-01', 'detail': 'x' * 150} for i in range(2000)}
        text = health.report(records, '2026-01-02')
        self.assertLess(len(text), 65_536)
        self.assertIn('more; the full state is status.json on the health-data branch', text)

    def test_content_signals(self):
        self.assertEqual(health.content_signals('https://api.example.net/x', 'https://www.example.net/y', ''), [])
        self.assertEqual(health.content_signals('https://example.net/', 'https://other.org/', ''), ['cross-site-redirect'])
        self.assertEqual(health.content_signals('https://example.net/', 'https://example.net/',
                                                '<h1>This domain is for sale</h1>'), ['parked-or-gambling'])
        self.assertEqual(health.content_signals('https://a.github.io/x', 'https://b.github.io/x', ''),
                         ['cross-site-redirect'])


class HysteresisTest(unittest.TestCase):
    def test_single_failure_does_not_flip_a_verified_resource(self):
        rec = next_state(None, OK, '2026-01-01')
        self.assertEqual(rec['state'], 'verified')
        rec = next_state(rec, DOWN, '2026-01-02')
        self.assertEqual((rec['state'], rec['failures'], rec['failing_since']), ('verified', 1, '2026-01-02'))

    def test_failing_needs_three_checks_and_seven_days(self):
        rec = next_state(None, OK, '2026-01-01')
        for day in ('2026-01-02', '2026-01-03', '2026-01-04'):
            rec = next_state(rec, DOWN, day)
        self.assertEqual((rec['state'], rec['failures']), ('verified', 3))       # 3 failures but only 3 days
        rec = next_state(rec, DOWN, '2026-01-08')
        self.assertEqual(rec['state'], 'verified')                               # 6 days after the first failure
        rec = next_state(rec, DOWN, '2026-01-09')
        self.assertEqual(rec['state'], 'failing')
        rec = next_state(rec, OK, '2026-01-10')
        self.assertEqual((rec['state'], rec['failures'], rec['failing_since']), ('verified', 0, None))

    def test_a_gap_in_the_checks_does_not_shorten_the_seven_days(self):
        rec = next_state(None, OK, '2026-01-01')
        for day in ('2026-01-20', '2026-01-21', '2026-01-22'):                   # no checks for 18 days
            rec = next_state(rec, DOWN, day)
        self.assertEqual(rec['state'], 'verified')

    def test_a_failure_drops_the_signals_of_a_working_page(self):
        sig = dict(OK, signals=['cross-site-redirect'], final_url='https://moved.example.org/')
        rec = next_state(None, sig, '2026-01-01')
        rec = next_state(rec, DOWN, '2026-01-02')
        self.assertEqual((rec['state'], rec['signals']), ('suspicious', ['cross-site-redirect']))
        for day in ('2026-01-03', '2026-01-09'):
            rec = next_state(rec, DOWN, day)
        self.assertEqual(rec['state'], 'failing')
        self.assertNotIn('signals', rec)

    def test_new_resource_that_never_worked_is_unconfirmed(self):
        rec = next_state(None, DOWN, '2026-01-01')
        self.assertEqual(rec['state'], 'unconfirmed')
        rec = next_state(rec, DOWN, '2026-01-02')
        rec = next_state(rec, DOWN, '2026-01-09')
        self.assertEqual(rec['state'], 'failing')

    def test_signals_and_acknowledgements(self):
        sig = dict(OK, signals=['cross-site-redirect'], final_url='https://moved.example.org/')
        self.assertEqual(next_state(None, sig, '2026-01-01')['state'], 'suspicious')
        self.assertEqual(next_state(None, sig, '2026-01-01', acknowledged={'cross-site-redirect'})['state'], 'verified')


class RunHealthTest(unittest.TestCase):
    def test_run_updates_status_and_drops_removed_resources(self):
        t = TempRepo()
        try:
            t.repo.save_health({'generated': None, 'resources': {'removed-one': {'state': 'verified', 'url': 'x'}}})
            t.write(resource('flaky', url='https://flaky.example.net/'))
            answers = {'https://flaky.example.net/': DOWN}
            out = run_health(t.repo, today='2026-01-01', checker=lambda url: answers.get(url, OK))
            recs = t.repo.load_health()['resources']
            self.assertNotIn('removed-one', recs)
            self.assertEqual(recs['flaky']['state'], 'unconfirmed')
            self.assertEqual(recs['alpha-base-0']['state'], 'verified')
            self.assertIn('unconfirmed 1', out['summary'])
            self.assertIn('flaky', out['markdown'])
            t.write(resource('flaky', url='https://flaky.example.net/v2'))     # a new URL starts a new history
            run_health(t.repo, ids=['flaky'], today='2026-01-02', checker=lambda url: OK)
            self.assertEqual(t.repo.load_health()['resources']['flaky']['failures'], 0)
        finally:
            t.cleanup()

    def test_acknowledged_results_count_as_working(self):
        t = TempRepo()
        try:
            t.write_raw('health/acknowledged.yml', 'alpha-base-0:\n  results: [client_error]\n  reason: bot block\n')
            blocked = {'result': 'client_error', 'status': 400}
            run_health(t.repo, ids=['alpha-base-0', 'alpha-base-1'], today='2026-01-01', checker=lambda url: blocked)
            recs = t.repo.load_health()['resources']
            self.assertEqual((recs['alpha-base-0']['state'], recs['alpha-base-0']['result']), ('verified', 'restricted'))
            self.assertEqual(recs['alpha-base-1']['state'], 'unconfirmed')
        finally:
            t.cleanup()

    def test_a_malformed_acknowledgement_does_not_stop_the_check(self):
        t = TempRepo()
        try:
            t.write_raw('health/acknowledged.yml', 'alpha-base-0:\nalpha-base-1:\n  results: client_error\n')
            self.assertEqual(health.load_acknowledged(t.repo)['alpha-base-1'], {'signals': set(), 'results': set()})
            run_health(t.repo, ids=['alpha-base-0'], today='2026-01-01', checker=lambda url: OK)
        finally:
            t.cleanup()


class CheckUrlsCommandTest(unittest.TestCase):
    def test_new_files_are_checked_with_their_acknowledgements(self):
        from registry_kit.__main__ import main
        t = TempRepo()
        try:
            t.write(resource('meta-dev', url='https://meta-dev.example.net/docs'))
            t.write_raw('health/acknowledged.yml', 'meta-dev:\n  results: [client_error]\n  reason: bot block\n')
            blocked = {'result': 'client_error', 'status': 400}
            with mock.patch('registry_kit.health.check_url', return_value=blocked):
                self.assertEqual(main(['--root', t.root, 'check-urls', '--files', 'data/alpha/meta-dev.yml']), 0)
                self.assertEqual(main(['--root', t.root, 'check-urls', '--files', './data/alpha/alpha-base-0.yml']), 1)
                self.assertEqual(main(['--root', t.root, 'check-urls', '--files', 'data/alpha/missing.yml']), 1)
        finally:
            t.cleanup()


if __name__ == '__main__':
    unittest.main()
