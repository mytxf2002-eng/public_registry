import unittest

import yaml

from registry_kit import yamlio
from registry_kit.repo import RESOURCE_ORDER


class LoadTest(unittest.TestCase):
    def test_duplicate_key_is_an_error(self):
        with self.assertRaises(yaml.YAMLError):
            yamlio.load('id: a\nname: x\nname: y\n')

    def test_yes_no_on_off_stay_strings(self):
        data = yamlio.load('cors: no\nb: yes\nc: on\nd: off\ne: true\nf: False\n')
        self.assertEqual(data, {'cors': 'no', 'b': 'yes', 'c': 'on', 'd': 'off', 'e': True, 'f': False})

    def test_dates_stay_strings(self):
        self.assertEqual(yamlio.load('added: 2026-09-27\n'), {'added': '2026-09-27'})

    def test_unsafe_tags_are_rejected(self):
        with self.assertRaises(yaml.YAMLError):
            yamlio.load('x: !!python/object/apply:os.system ["echo hi"]\n')


class DumpTest(unittest.TestCase):
    def test_canonical_order_and_round_trip(self):
        data = {'url': 'https://a.example.net', 'id': 'a-b', 'kind': ['api'], 'name': 'A: B',
                'provenance': {'origin': 'contribution', 'added': '2026-09-27'},
                'api': {'cors': 'no', 'https': True, 'auth': 'none'}, 'zzz': 1}
        text = yamlio.dump(data, RESOURCE_ORDER)
        self.assertTrue(text.startswith('id: a-b\nkind: [api]\nname: \'A: B\'\nurl: '))
        self.assertIn("cors: 'no'", text)            # quoted, so YAML 1.1 readers do not see a boolean
        self.assertIn('added: 2026-09-27\n  origin:', text)
        self.assertTrue(text.rstrip().endswith('zzz: 1'))
        self.assertEqual(yamlio.load(text), data)

    def test_nested_lists_of_mappings(self):
        data = {'mcp': {'auth': 'none', 'transport': ['stdio'], 'install': [{'name': 'Glama', 'url': 'https://g.example.net'}]}}
        text = yamlio.dump(data, RESOURCE_ORDER)
        self.assertIn('  install:\n    - name: Glama\n      url: https://g.example.net\n', text)
        self.assertEqual(yamlio.load(text), data)

    def test_unicode_is_written_as_is(self):
        text = yamlio.dump({'description': '中文说明：数据'}, {'description': 0})
        self.assertIn('中文说明', text)
        self.assertEqual(yamlio.load(text), {'description': '中文说明：数据'})


if __name__ == '__main__':
    unittest.main()
