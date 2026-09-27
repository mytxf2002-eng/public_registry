import unittest

from registry_kit import vocab as V
from registry_kit.normalize import format_repo, normalize_resource
from registry_kit.validate import validate
from tests.helpers import ROOT, TempRepo, resource


class NormalizeTest(unittest.TestCase):
    def setUp(self):
        self.v = V.load(ROOT)

    def test_mechanical_fixes(self):
        d = resource('x-y', url='https://x.example.net/?utm_source=a&page=2', license='CC BY 4.0',
                     kind=['dataset', 'api'], tags=['Air Quality', 'air-quality', 'PM2_5'],
                     description='Two  spaces   inside the text',
                     dataset={'formats': ['CSV', 'zip', 'csv'], 'access': 'public', 'spatial': ['us', 'Global'],
                              'temporal': {'start': 2015}})
        n = normalize_resource(d, self.v)
        self.assertEqual(n['url'], 'https://x.example.net/?page=2')
        self.assertEqual(n['license'], 'CC-BY-4.0')
        self.assertEqual(n['kind'], ['api', 'dataset'])
        self.assertEqual(n['tags'], ['air-quality', 'pm2-5'])
        self.assertEqual(n['description'], 'Two spaces inside the text')
        self.assertEqual(n['dataset']['formats'], ['csv', 'archive'])
        self.assertEqual(n['dataset']['spatial'], ['US', 'global'])
        self.assertEqual(n['dataset']['temporal'], {'start': '2015'})

    def test_format_is_idempotent_and_fixes_validation(self):
        t = TempRepo()
        try:
            t.write_raw('data/alpha/messy.yml', 'url: https://messy.example.net/?utm_medium=x\nid: messy\nkind: [api]\n'
                        'name: Messy\ndescription: A messy but otherwise valid resource file\ndomain: alpha\n'
                        'license: cc0\nprovenance: {origin: contribution, added: 2026-09-27}\n'
                        'api: {auth: none, https: true, cors: no}\n')
            self.assertTrue([p for p in validate(t.repo) if p.level == 'error'])
            self.assertEqual(format_repo(t.repo, check=True), ['data/alpha/messy.yml'])
            format_repo(t.repo)
            self.assertEqual(format_repo(t.repo, check=True), [])
            self.assertEqual([str(p) for p in validate(t.repo) if p.level == 'error'], [])
            with open(t.repo.abs('data/alpha/messy.yml'), encoding='utf-8') as f:
                text = f.read()
            t.write_raw('data/alpha/empty-block.yml', text.replace('id: messy', 'id: empty-block')
                        .replace('messy.example.net', 'empty.example.net') + 'dataset: {}\n')
            format_repo(t.repo)
            self.assertEqual(format_repo(t.repo, check=True), [])             # an empty block stays {}
            self.assertTrue(text.startswith('id: messy\nkind: [api]\nname: Messy\nurl: https://messy.example.net/\n'))
            self.assertIn("license: CC0-1.0", text)
            self.assertIn("cors: 'no'", text)
        finally:
            t.cleanup()


if __name__ == '__main__':
    unittest.main()
