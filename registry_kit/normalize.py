"""`registry_kit format`: rewrite files into their canonical form.

Fixes what can be fixed mechanically: key order and layout, tracking parameters in URLs, licence and
format aliases, tag spelling, kind order, stray whitespace. Everything else is left to `validate`.
"""
import re

from . import urls, vocab as V, yamlio
from .repo import I18N_ORDER, RESOURCE_ORDER, LANGUAGES

URL_FIELDS = (('url',), ('license_url',), ('api', 'docs'), ('api', 'spec'), ('dataset', 'url'))


def _strip(value):
    if isinstance(value, str):
        return re.sub(r'[ \t]+', ' ', value.strip())
    if isinstance(value, list):
        return [_strip(v) for v in value]
    if isinstance(value, dict):
        return {k: _strip(v) for k, v in value.items()}
    return value


def normalize_resource(data, vocab):
    d = _strip(data)
    for path in URL_FIELDS:
        holder = d
        for key in path[:-1]:
            holder = holder.get(key) if isinstance(holder, dict) else None
        if isinstance(holder, dict) and isinstance(holder.get(path[-1]), str):
            holder[path[-1]] = urls.strip_tracking(holder[path[-1]])
    if isinstance(d.get('mcp'), dict) and isinstance(d['mcp'].get('install'), list):
        for item in d['mcp']['install']:
            if isinstance(item, dict) and isinstance(item.get('url'), str):
                item['url'] = urls.strip_tracking(item['url'])
    if isinstance(d.get('kind'), list):
        known = [k for k in V.KINDS if k in d['kind']]
        d['kind'] = known + [k for k in d['kind'] if k not in V.KINDS]
    if isinstance(d.get('license'), str):
        d['license'] = vocab.canonical_license(d['license'])
    if isinstance(d.get('tags'), list):
        tags = []
        for t in d['tags']:
            t = re.sub(r'[\s_]+', '-', str(t).strip().lower())
            if t and t not in tags:
                tags.append(t)
        d['tags'] = tags
    ds = d.get('dataset')
    if isinstance(ds, dict):
        if isinstance(ds.get('formats'), list):
            fm = []
            for f in ds['formats']:
                f = vocab.canonical_format(str(f).strip())
                if f not in fm:
                    fm.append(f)
            ds['formats'] = fm
        if isinstance(ds.get('spatial'), list):
            ds['spatial'] = [s.lower() if s.lower() in V.REGIONS else s.upper() for s in ds['spatial']
                             if isinstance(s, str)]
        if isinstance(ds.get('temporal'), dict):
            for k in ('start', 'end'):
                if isinstance(ds['temporal'].get(k), int):
                    ds['temporal'][k] = str(ds['temporal'][k])
    return d


def normalize_translation(data):
    return _strip(data)


def format_repo(repo, check=False):
    """Returns the files that are (check=True) or were (check=False) not canonical."""
    changed = []
    v = repo.vocab
    for r in repo.load_resources():
        text = yamlio.dump(normalize_resource(r.data, v), RESOURCE_ORDER)
        if _differs(repo, r.path, text, check):
            changed.append(r.path)
    for lang in LANGUAGES:
        for t in repo.load_translations(lang):
            text = yamlio.dump(normalize_translation(t.data), I18N_ORDER)
            if _differs(repo, t.path, text, check):
                changed.append(t.path)
    return changed


def _differs(repo, rel, text, check):
    path = repo.abs(rel)
    with open(path, encoding='utf-8', newline='') as f:
        current = f.read()
    if current == text:
        return False
    if not check:
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
    return True
