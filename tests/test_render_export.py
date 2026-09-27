import json
import os
import shutil
import sqlite3
import tempfile
import unittest
from unittest import mock

from registry_kit import export, render, vocab as V
from registry_kit.build import build
from registry_kit.lifecycle import archive, restore
from registry_kit.validate import validate
from tests.helpers import ROOT, TempRepo, resource

class ExportTest(unittest.TestCase):
    def test_exports(self):
        t = TempRepo()
        out = tempfile.mkdtemp(prefix='registry-export-')
        try:
            v = t.repo.vocab
            items = [export.enrich(r.data, v, {'alpha-base-0': {'id': 'alpha-base-0', 'description': '说明'}},
                                   {'alpha-base-0': {'state': 'verified', 'checked': '2026-01-01', 'last_ok': '2026-01-01'}})
                     for r in t.repo.load_resources()]
            meta = {'generated': '2026-01-01', 'source_sha': 'abc'}
            export.export_all(out, items, v, meta, {'resources': len(items)})
            con = sqlite3.connect(os.path.join(out, 'export', 'registry.sqlite'))
            self.assertEqual(con.execute('select count(*) from resources').fetchone()[0], 10)
            self.assertEqual(con.execute("select description_zh from resources where id='alpha-base-0'").fetchone()[0], '说明')
            con.close()
            with open(os.path.join(out, 'api', 'v1', 'index.json'), encoding='utf-8') as f:
                index = json.load(f)
            self.assertEqual((index['count'], index['source_sha']), (10, 'abc'))
            with open(os.path.join(out, 'api', 'v1', 'resources', 'alpha-base-0.json'), encoding='utf-8') as f:
                one = json.load(f)
            self.assertEqual(one['health']['state'], 'verified')
            with open(os.path.join(out, 'export', 'resources.csv'), encoding='utf-8-sig') as f:
                header = f.readline().strip()
            self.assertEqual(header.split(','), export.CSV_COLUMNS)
        finally:
            t.cleanup()
            shutil.rmtree(out, ignore_errors=True)


class LifecycleTest(unittest.TestCase):
    def test_archive_and_restore_keep_everything(self):
        t = TempRepo(per_domain=6)
        try:
            t.write_raw('i18n/zh-CN/alpha-base-5.yml', 'id: alpha-base-5\ndescription: 中文说明\n')
            before = t.repo.load_resources()
            path = archive(t.repo, 'alpha-base-5', 'Shut down in 2026', date='2026-02-01')
            self.assertEqual(path, 'data/_archive/alpha-base-5.yml')
            self.assertTrue(os.path.exists(t.repo.abs('i18n/zh-CN/alpha-base-5.yml')))
            self.assertEqual([str(p) for p in validate(t.repo) if p.level == 'error'], [])
            restore(t.repo, 'alpha-base-5')
            self.assertEqual([r.data for r in t.repo.load_resources()], [r.data for r in before])
            self.assertEqual([str(p) for p in validate(t.repo) if p.level == 'error'], [])
        finally:
            t.cleanup()


class BuildTest(unittest.TestCase):
    @mock.patch.dict(os.environ, {'GITHUB_REPOSITORY': ''})    # as outside GitHub Actions
    def test_build_without_link_state(self):
        t = TempRepo()
        try:
            summary = build(t.repo, source_sha='abc')
            self.assertIn('built 10 resources', summary)
            with open(t.repo.abs('build/site/api/v1/index.json'), encoding='utf-8') as f:
                self.assertEqual(json.load(f)['source_sha'], 'abc')
            con = sqlite3.connect(t.repo.abs('build/site/export/registry.sqlite'))
            try:
                self.assertIsNone(con.execute("select value from meta where key='source'").fetchone()[0])
            finally:
                con.close()
            build(t.repo, source_sha='def')                          # an earlier build is replaced
        finally:
            t.cleanup()

    def test_build_never_writes_over_the_repository(self):
        t = TempRepo()
        try:
            with self.assertRaises(SystemExit):
                build(t.repo, out=t.root)
            t.write_raw('notes/keep.md', 'mine\n')
            with self.assertRaises(SystemExit):
                build(t.repo, out='notes')
            self.assertTrue(os.path.exists(t.repo.abs('notes/keep.md')))
        finally:
            t.cleanup()


class PagesTest(unittest.TestCase):
    def test_domain_page_lists_kinds_separately(self):
        v = V.load(ROOT)
        items = [resource('api-one', 'weather-climate'),
                 dict(resource('data-one', 'weather-climate', kind=['dataset'],
                               dataset={'formats': ['csv'], 'access': 'public'}), api=None)]
        items[1].pop('api')
        page = render.domain_page('weather-climate', items, 'en', v, {}, {'api-one': {'state': 'verified'}}, '2026-01-01')
        self.assertIn('## APIs (including those that also offer downloads) (1)', page)
        self.assertIn('## Datasets (1)', page)
        self.assertIn('| OK |', page)
        zh = render.domain_page('weather-climate', items, 'zh-CN', v, {'data-one': {'description': '中文说明'}}, {}, '2026-01-01')
        self.assertIn('中文说明', zh)
        self.assertIn('未检测', zh)


if __name__ == '__main__':
    unittest.main()
