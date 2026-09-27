"""`registry_kit build`: every generated output, into build/ (never committed).

build/
  site/               the static site (GitHub Pages root): index.html, app.js, data.js,
    export/           resources.json, resources.csv, registry.sqlite
    api/v1/           static read-only API
  docs/en/, docs/zh-CN/   Markdown pages per domain, plus an index
  build-info.json     source commit, date and counts
"""
import datetime as dt
import json
import os
import shutil
import subprocess
from collections import defaultdict

from . import export, render, site, stats as stats_mod


def git_head(root):
    try:
        out = subprocess.run(['git', '-C', root, 'rev-parse', 'HEAD'], capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or None if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def _check_out_dir(repo, out):
    """The output directory is emptied of earlier outputs, so it must never be the repository itself or a
    folder with other content: it has to be new, empty, or a previous build (it has build-info.json)."""
    root = os.path.abspath(repo.root)
    target = os.path.abspath(out)
    if target == root or root.startswith(target.rstrip(os.sep) + os.sep):
        raise SystemExit(f'registry_kit build: --out {out} would overwrite the repository; use a separate folder')
    if os.path.isdir(target) and os.listdir(target) and not os.path.exists(os.path.join(target, 'build-info.json')):
        raise SystemExit(f'registry_kit build: {out} is not empty and holds no earlier build; use a new folder')


def build(repo, out='build', source_sha=None, today=None):
    today = today or dt.datetime.now(dt.timezone.utc).date().isoformat()
    out = out if os.path.isabs(out) else os.path.join(repo.root, out)
    _check_out_dir(repo, out)
    v = repo.vocab
    active = sorted((r.data for r in repo.load_resources() if not r.archived), key=lambda d: d['id'])
    zh = {t.data['id']: t.data for t in repo.load_translations('zh-CN')}
    health = repo.load_health().get('resources', {})
    stats = stats_mod.compute(repo, today=today)
    sha = source_sha or os.environ.get('GITHUB_SHA') or git_head(repo.root)
    repository = os.environ.get('GITHUB_REPOSITORY')          # owner/name, set by GitHub Actions
    meta = {'generated': today, 'source_sha': sha, 'license': 'CC-BY-4.0',
            'source': f'https://github.com/{repository}' if repository else None}
    enriched = [export.enrich(d, v, zh, health) for d in active]

    for sub in ('site', 'docs'):
        shutil.rmtree(os.path.join(out, sub), ignore_errors=True)
    site_dir = os.path.join(out, 'site')
    site.write_site(site_dir, enriched, v, stats, meta)
    export.export_all(site_dir, enriched, v, meta, stats)

    by_domain = defaultdict(list)
    for d in active:
        by_domain[d['domain']].append(d)
    totals = {'resources': len(active)}
    for lang in ('en', 'zh-CN'):
        docs = os.path.join(out, 'docs', lang)
        os.makedirs(docs, exist_ok=True)
        translations = zh if lang == 'zh-CN' else {}
        for dom in v.domain_ids:
            text = render.domain_page(dom, list(by_domain.get(dom, [])), lang, v, translations, health, today)
            _write(os.path.join(docs, f'{dom}.md'), text)
        _write(os.path.join(docs, 'README.md'), render.index_page(by_domain, lang, v, today, totals))

    info = {'source_sha': sha, 'generated': today, 'resources': len(active), 'kinds': stats['kinds']}
    _write(os.path.join(out, 'build-info.json'), json.dumps(info, indent=1) + '\n')
    return (f'built {len(active)} resources into {out}: site (+export, api/v1), docs en/zh-CN '
            f'({len(v.domain_ids)} domains each); source {sha or "unknown"}')


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text if text.endswith('\n') else text + '\n')
