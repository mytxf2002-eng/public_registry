import unittest

from registry_kit.validate import validate
from tests.helpers import TempRepo, resource


class ValidateTest(unittest.TestCase):
    def setUp(self):
        self.t = TempRepo()

    def tearDown(self):
        self.t.cleanup()

    def problems(self, **kw):
        return [p for p in validate(self.t.repo, **kw) if p.level == 'error']

    def messages(self, **kw):
        return [f'{p.path}: {p.message}' for p in self.problems(**kw)]

    def test_baseline_is_clean(self):
        self.assertEqual(self.messages(), [])

    def test_all_errors_are_reported_at_once(self):
        self.t.write_raw('data/alpha/broken.yml', 'id: broken\nkind: [api\n')
        self.t.write_raw('data/alpha/stray.yaml', 'id: stray\n')
        self.t.write(resource('bad-desc', description='ends with a period.'))
        msgs = ' | '.join(self.messages())
        self.assertIn('invalid YAML', msgs)
        self.assertIn('use the .yml extension', msgs)
        self.assertIn('must not end with a period', msgs)

    def test_duplicate_key(self):
        self.t.write_raw('data/alpha/dupe.yml', 'id: dupe\nid: dupe\n')
        self.assertTrue(any('duplicate key' in m for m in self.messages()))

    def test_id_and_folder_must_match(self):
        with open(self.t.repo.abs(self.t.write(resource("some-id"))), encoding="utf-8") as f:
            self.t.write_raw("data/alpha/other-name.yml", f.read())
        self.t.write(resource('wrong-folder', domain='beta'))
        import os
        os.replace(self.t.repo.abs('data/beta/wrong-folder.yml'), self.t.repo.abs('data/alpha/wrong-folder.yml'))
        msgs = ' | '.join(self.messages())
        self.assertIn('id "some-id" must equal the file name ("other-name")', msgs)
        self.assertIn('domain is "beta" but the file is in data/alpha/', msgs)

    def test_url_uniqueness_ignores_scheme_www_slash_and_tracking(self):
        self.t.write(resource('first', url='https://www.dup.example.net/api/'))
        self.t.write(resource('second', url='http://dup.example.net/api?utm_source=list'))
        msgs = ' | '.join(self.messages())
        self.assertIn('same URL as data/alpha/first.yml', msgs)
        self.assertIn('tracking parameters (utm_source)', msgs)

    def test_archived_urls_stay_reserved(self):
        self.t.write(resource('gone', url='https://gone.example.net/', archived={'date': '2026-01-01', 'reason': 'Shut down'}),
                     archived=True)
        self.t.write(resource('again', url='https://gone.example.net'))
        self.assertTrue(any('archived data/_archive/gone.yml (archived because: Shut down)' in m for m in self.messages()))

    def test_archived_block_required_in_archive(self):
        self.t.write(resource('no-reason'), archived=True)
        self.assertTrue(any('need an "archived" block' in m for m in self.messages()))

    def test_same_name_in_a_domain(self):
        self.t.write(resource('one', name='Same Name'))
        self.t.write(resource('two', name='same name'))
        self.assertEqual(sum('same name' in m for m in self.messages()), 2)

    def test_text_rules(self):
        self.t.write(resource('a-1', name='Weather API'))
        self.t.write(resource('a-2', description='lowercase start of the description text'))
        self.t.write(resource('a-3', description='Visit https://example.org for more'))
        self.t.write(resource('a-4', description='TODO write the description later'))
        self.t.write(resource('a-5', description='<describe the resource> in a sentence'))
        msgs = ' | '.join(self.messages())
        for text in ('must not end with " API"', 'must start with a capital', 'must not contain URLs',
                     'looks like a placeholder'):
            self.assertIn(text, msgs)

    def test_placeholder_words_used_by_real_apis_are_fine(self):
        self.t.write(resource('placebear', description='Placeholder bear pictures'))
        self.t.write(resource('ipsum', description='A meatier lorem ipsum generator'))
        self.assertEqual(self.messages(), [])

    def test_domain_minimum_size(self):
        import os
        for i in range(3):
            os.remove(self.t.repo.abs(f'data/beta/beta-base-{i}.yml'))
        self.assertIn('data/beta/: domain has 2 resources; the minimum is 5', self.messages())

    def test_translations(self):
        self.t.write_raw('i18n/zh-CN/nobody.yml', 'id: nobody\ndescription: 没有对应的资源\n')
        self.t.write_raw('i18n/zh-CN/alpha-base-0.yml', 'id: alpha-base-0\ndescription: 正常的中文说明\nextra: x\n')
        msgs = ' | '.join(self.messages())
        self.assertIn('orphaned translation', msgs)
        self.assertIn('unknown field "extra"', msgs)

    def test_strict_files_need_complete_metadata(self):
        path = self.t.write(resource('new-one'))
        self.assertEqual(self.messages(), [])
        msgs = ' | '.join(self.messages(strict_paths=[path]))
        self.assertIn('license is "unknown"', msgs)
        self.assertIn('publisher is missing', msgs)
        path = self.t.write(resource('complete', license='CC0-1.0', license_url='https://complete.example.net/terms',
                                     publisher={'name': 'Example Org', 'kind': 'nonprofit'}))
        self.assertEqual([m for m in self.messages(strict_paths=[path]) if 'complete' in m], [])

    def test_strict_paths_in_any_spelling(self):
        path = self.t.write(resource('spelled', provenance={'added': '2026-09-27', 'origin': 'public-apis'}))
        for given in (path, './' + path, path.replace('/', '\\'), self.t.repo.abs(path)):
            msgs = ' | '.join(self.messages(strict_paths=[given]))
            self.assertIn('new resources use "contribution"', msgs, given)
        self.assertIn('data/alpha/typo.yml: no such file (given with --strict)',
                      self.messages(strict_paths=['data/alpha/typo.yml']))

    def test_dates_must_be_real_and_in_order(self):
        self.t.write(resource('bad-day', provenance={'added': '2026-02-30', 'origin': 'contribution'}))
        self.t.write(resource('future', provenance={'added': '2030-01-01', 'origin': 'contribution'}))
        self.t.write(resource('reversed', provenance={'added': '2026-09-27', 'origin': 'contribution',
                                                      'reviewed': '2026-01-01'}))
        self.t.write(resource('span', kind=['dataset'], api=None,
                              dataset={'formats': ['csv'], 'access': 'public',
                                       'temporal': {'start': '2020-13', 'end': '2019'}}))
        self.t.write(resource('order', kind=['dataset'], api=None,
                              dataset={'formats': ['csv'], 'access': 'public',
                                       'temporal': {'start': '2021-05', 'end': '2020'}}))
        msgs = ' | '.join(self.messages(today='2026-09-27'))
        self.assertIn('provenance.added is not a real date (2026-02-30)', msgs)
        self.assertIn('provenance.added is in the future (2030-01-01)', msgs)
        self.assertIn('provenance.reviewed is earlier than provenance.added', msgs)
        self.assertIn('dataset.temporal.start is not a real date (2020-13)', msgs)
        self.assertIn('dataset.temporal.start is later than dataset.temporal.end', msgs)

    def test_malformed_urls_are_reported_not_raised(self):
        self.t.write(resource('port', url='https://port.example.net:8o80/'))
        self.t.write(resource('ipv6', url='https://[x/'))
        msgs = ' | '.join(self.messages())
        self.assertIn('port.yml: url is not a usable URL', msgs)
        self.assertIn('ipv6.yml: url is not a usable URL', msgs)

    def test_a_list_as_a_key_is_invalid_yaml(self):
        self.t.write_raw('data/alpha/listkey.yml', 'id: listkey\n[api]: x\n')
        self.assertTrue(any('listkey.yml: invalid YAML' in m for m in self.messages()))

    def test_template_slots_anywhere_are_placeholders(self):
        self.t.write(resource('slot', publisher={'name': '<publisher name>', 'kind': 'company'}))
        self.assertTrue(any('publisher.name looks like a placeholder' in m for m in self.messages()))

    def test_tags_do_not_repeat_the_domain(self):
        self.t.write(resource('tagged', tags=['alpha', 'weather']))
        self.assertTrue(any('tags must not repeat the domain' in m for m in self.messages()))

    def test_a_translation_of_an_archived_resource_is_kept(self):
        self.t.write(resource('old', archived={'date': '2026-01-01', 'reason': 'Shut down'}), archived=True)
        self.t.write_raw('i18n/zh-CN/old.yml', 'id: old\ndescription: 已归档资源的中文说明\n')
        self.assertEqual(self.messages(), [])

    def test_acknowledgements_are_checked(self):
        self.t.write_raw('health/acknowledged.yml',
                         'alpha-base-0:\n  results: [client_error]\n  reason: bot block, checked 2026-09-27\n'
                         'alpha-base-1:\n  results: client_error\n  reason: x\n'
                         'alpha-base-2:\n  signals: [redirect]\n'
                         'nobody:\n  signals: [cross-site-redirect]\n  reason: x\n'
                         'alpha-base-3:\n')
        msgs = ' | '.join(self.messages())
        self.assertNotIn('alpha-base-0', msgs)
        self.assertIn('alpha-base-1: results must be a list', msgs)
        self.assertIn('alpha-base-2: signals: redirect is not one of', msgs)
        self.assertIn('alpha-base-2: needs a reason', msgs)
        self.assertIn('nobody: no resource with this id', msgs)
        self.assertIn('alpha-base-3: needs signals and/or results', msgs)


if __name__ == '__main__':
    unittest.main()
