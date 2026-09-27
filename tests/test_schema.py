import unittest

from registry_kit import vocab as V
from registry_kit.schema import Validator, write_schemas
from tests.helpers import ROOT, resource


class VocabTest(unittest.TestCase):
    def setUp(self):
        self.v = V.load(ROOT)

    def test_counts_and_shapes(self):
        self.assertEqual(len(self.v.domains), 45)
        self.assertGreater(len(self.v.formats), 50)
        for lid, lic in self.v.licenses.items():
            if lic['spdx']:
                self.assertRegex(lid, r'^[A-Za-z0-9.+-]+$')
            else:
                self.assertTrue(lid.startswith('LicenseRef-'))

    def test_aliases(self):
        self.assertEqual(self.v.canonical_license('CC BY 4.0'), 'CC-BY-4.0')
        self.assertEqual(self.v.canonical_license('Open Government Licence v3.0'), 'OGL-UK-3.0')
        self.assertEqual(self.v.canonical_license('public domain'), 'LicenseRef-Public-Domain')
        self.assertEqual(self.v.canonical_format('ndjson'), 'jsonl')
        self.assertEqual(self.v.canonical_format('SHP'), 'shapefile')
        self.assertEqual(self.v.canonical_format('off'), 'model-3d')      # YAML 1.1 would have read a boolean

    def test_committed_schemas_are_current(self):
        self.assertEqual(write_schemas(ROOT, self.v, check=True), [],
                         'schema/*.json are stale: run python -m registry_kit schema')


class ResourceSchemaTest(unittest.TestCase):
    def setUp(self):
        self.val = Validator(V.load(ROOT))

    def errors(self, data):
        return self.val.resource_errors(data)

    def test_valid_resource(self):
        self.assertEqual(self.errors(resource('good-one', 'weather-climate')), [])

    def test_unknown_field(self):
        self.assertIn('file: unknown field "status"', self.errors(resource('a-b', 'weather-climate', status='ok')))

    def test_kind_blocks_must_match(self):
        data = resource('a-b', 'weather-climate', kind=['api', 'dataset'])
        self.assertIn('kind includes "dataset", so the "dataset" block is required', self.errors(data))
        data = resource('a-b', 'weather-climate', dataset={'formats': ['csv'], 'access': 'public'})
        self.assertIn('"dataset" block is present but kind does not include "dataset"', self.errors(data))

    def test_license_alias_gets_a_hint(self):
        msgs = self.errors(resource('a-b', 'weather-climate', license='CC BY 4.0'))
        self.assertTrue(any('use "CC-BY-4.0"' in m for m in msgs), msgs)

    def test_custom_licence_needs_its_source(self):
        msgs = self.errors(resource('a-b', 'weather-climate', license='LicenseRef-Custom-Open'))
        self.assertTrue(any('needs license_url' in m for m in msgs), msgs)

    def test_patterns(self):
        msgs = self.errors(resource('A_B', 'weather-climate', tags=['Air Quality']))
        self.assertTrue(any(m.startswith('id:') for m in msgs), msgs)
        self.assertTrue(any(m.startswith('tags.0:') for m in msgs), msgs)
        data = resource('a-b', 'weather-climate', kind=['dataset'],
                        dataset={'formats': ['csv'], 'access': 'public', 'spatial': ['usa'], 'temporal': {'start': 2015}})
        data.pop('api')
        msgs = self.errors(data)
        self.assertTrue(any(m.startswith('dataset.spatial.0:') for m in msgs), msgs)
        self.assertTrue(any(m.startswith('dataset.temporal.start:') for m in msgs), msgs)

    def test_archived_files_keep_their_original_text(self):
        short = resource('old-one', 'weather-climate', description='Weather')
        self.assertIn('description: 7 characters, must be at least 10', self.errors(short))
        short['archived'] = {'date': '2026-09-27', 'reason': 'Shut down'}
        self.assertEqual(self.errors(short), [])

    def test_format_and_domain_suggestions(self):
        data = resource('a-b', 'wether-climate', kind=['dataset'], dataset={'formats': ['zip'], 'access': 'public'})
        data.pop('api')
        msgs = ' '.join(self.errors(data))
        self.assertIn('did you mean "weather-climate"', msgs)
        self.assertIn('use "archive"', msgs)


if __name__ == '__main__':
    unittest.main()
