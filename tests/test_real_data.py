"""Regression tests on the real registry data: the rules must hold for every file in the repository."""
import re
import unittest

from registry_kit.normalize import format_repo
from registry_kit.repo import Repo
from registry_kit.validate import MIN_DOMAIN_SIZE, validate
from tests.helpers import ROOT


class RealDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = Repo(ROOT)
        cls.problems = validate(cls.repo)
        cls.active = [r.data for r in cls.repo.load_resources() if not r.archived]

    def test_no_validation_errors(self):
        errors = [str(p) for p in self.problems if p.level == 'error']
        self.assertEqual(errors[:20], [], f'{len(errors)} validation errors')

    def test_files_are_canonical(self):
        self.assertEqual(format_repo(self.repo, check=True), [], 'run python -m registry_kit format')

    def test_every_domain_is_populated(self):
        sizes = {d: 0 for d in self.repo.vocab.domain_ids}
        for d in self.active:
            sizes[d['domain']] += 1
        self.assertEqual({d: n for d, n in sizes.items() if n < MIN_DOMAIN_SIZE}, {})

    def test_no_tracking_parameters_anywhere_in_data(self):
        hits = []
        for rel in self.repo.data_files():
            with open(self.repo.abs(rel), encoding='utf-8') as f:
                if re.search(r'[?&](utm_[a-z]+|gclid|fbclid)=', f.read()):
                    hits.append(rel)
        self.assertEqual(hits, [])

    def test_imported_dates_are_plausible(self):
        # the imported resources were dated from the history of the lists they came from; validate checks
        # the general date rules (real dates, not in the future, reviewed not before added) for every file
        for d in self.active:
            if d['provenance']['origin'] != 'contribution':
                self.assertGreaterEqual(d['provenance']['added'], '2016-03-01', d['id'])


if __name__ == '__main__':
    unittest.main()
