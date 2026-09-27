"""Machine-readable outputs: JSON, CSV and SQLite exports, and the static read-only API (api/v1)."""
import csv
import io
import json
import os
import sqlite3

from .vocab import KINDS

API_VERSION = 'v1'
CSV_COLUMNS = [
    'id', 'name', 'kind', 'domain', 'url', 'description', 'description_zh', 'tags', 'license', 'license_family',
    'license_url', 'publisher_name', 'publisher_kind', 'added', 'origin', 'reviewed', 'sponsored',
    'api_auth', 'api_https', 'api_cors', 'api_docs', 'api_spec', 'mcp_auth', 'mcp_transport', 'mcp_install',
    'dataset_formats', 'dataset_access',
    'dataset_url', 'temporal_start', 'temporal_end', 'spatial', 'update_frequency', 'size',
    'health_state', 'health_checked', 'health_last_ok',
]


def enrich(d, v, zh, health):
    """A resource as published: its file's fields plus translation, licence family and health."""
    out = dict(d)
    out['license_family'] = v.license_family(d.get('license', 'unknown'))
    if d['id'] in zh:
        out['i18n'] = {'zh-CN': {k: val for k, val in zh[d['id']].items() if k != 'id'}}
    h = health.get(d['id'])
    out['health'] = ({k: h.get(k) for k in ('state', 'checked', 'last_ok', 'result', 'status', 'failures')}
                     if h else {'state': 'unchecked'})
    return out


def flat(r):
    api, ds, mcp = r.get('api') or {}, r.get('dataset') or {}, r.get('mcp') or {}
    pub, prov, h = r.get('publisher') or {}, r.get('provenance') or {}, r.get('health') or {}
    temporal = ds.get('temporal') or {}
    zh = (r.get('i18n') or {}).get('zh-CN') or {}
    return {
        'id': r['id'], 'name': r['name'], 'kind': '|'.join(r['kind']), 'domain': r['domain'], 'url': r['url'],
        'description': r['description'], 'description_zh': zh.get('description', ''),
        'tags': '|'.join(r.get('tags', [])), 'license': r.get('license', 'unknown'),
        'license_family': r['license_family'], 'license_url': r.get('license_url', ''),
        'publisher_name': pub.get('name', ''), 'publisher_kind': pub.get('kind', ''),
        'added': prov.get('added', ''), 'origin': prov.get('origin', ''), 'reviewed': prov.get('reviewed', ''),
        'sponsored': 'yes' if prov.get('sponsored') else '',
        'api_auth': api.get('auth', ''), 'api_https': '' if not api else ('yes' if api.get('https') else 'no'),
        'api_cors': api.get('cors', ''), 'api_docs': api.get('docs', ''), 'api_spec': api.get('spec', ''),
        'mcp_auth': mcp.get('auth', ''), 'mcp_transport': '|'.join(mcp.get('transport', [])),
        'mcp_install': '|'.join(i['url'] for i in mcp.get('install', [])),
        'dataset_formats': '|'.join(ds.get('formats', [])), 'dataset_access': ds.get('access', ''),
        'dataset_url': ds.get('url', ''), 'temporal_start': temporal.get('start') or '',
        'temporal_end': temporal.get('end') or '', 'spatial': '|'.join(ds.get('spatial', [])),
        'update_frequency': ds.get('update_frequency', ''), 'size': ds.get('size', ''),
        'health_state': h.get('state', ''), 'health_checked': h.get('checked') or '',
        'health_last_ok': h.get('last_ok') or '',
    }


def write_json(path, data, compact=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        if compact:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        else:
            json.dump(data, f, ensure_ascii=False, indent=1)
            f.write('\n')


def csv_text(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, lineterminator='\n')
    w.writeheader()
    for row in rows:
        w.writerow(row)
    return buf.getvalue()


def write_sqlite(path, resources, v, meta):
    if os.path.exists(path):
        os.remove(path)
    con = sqlite3.connect(path)
    try:
        cols = ', '.join(f'"{c}" TEXT' for c in CSV_COLUMNS[1:])
        con.execute(f'CREATE TABLE resources ("id" TEXT PRIMARY KEY, {cols})')
        con.execute('CREATE TABLE resource_kinds (id TEXT, kind TEXT)')
        con.execute('CREATE TABLE resource_tags (id TEXT, tag TEXT)')
        con.execute('CREATE TABLE resource_formats (id TEXT, format TEXT)')
        con.execute('CREATE TABLE domains (id TEXT PRIMARY KEY, name TEXT, name_zh TEXT, scope TEXT, scope_zh TEXT)')
        con.execute('CREATE TABLE licenses (id TEXT PRIMARY KEY, family TEXT, spdx INTEGER, description TEXT)')
        con.execute('CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)')
        placeholders = ', '.join('?' for _ in CSV_COLUMNS)
        for r in resources:
            row = flat(r)
            con.execute(f'INSERT INTO resources VALUES ({placeholders})', [row[c] for c in CSV_COLUMNS])
            con.executemany('INSERT INTO resource_kinds VALUES (?, ?)', [(r['id'], k) for k in r['kind']])
            con.executemany('INSERT INTO resource_tags VALUES (?, ?)', [(r['id'], t) for t in r.get('tags', [])])
            con.executemany('INSERT INTO resource_formats VALUES (?, ?)',
                            [(r['id'], f) for f in (r.get('dataset') or {}).get('formats', [])])
        con.executemany('INSERT INTO domains VALUES (?, ?, ?, ?, ?)',
                        [(d['id'], d['name'], d['name_zh'], d['scope'], d['scope_zh']) for d in v.domains])
        con.executemany('INSERT INTO licenses VALUES (?, ?, ?, ?)',
                        [(l['id'], l['family'], int(l['spdx']), l['description']) for l in v.licenses.values()])
        con.executemany('INSERT INTO meta VALUES (?, ?)',
                        [(k, None if val is None else str(val)) for k, val in meta.items()])
        con.execute('CREATE INDEX idx_domain ON resources(domain)')
        con.execute('CREATE INDEX idx_kind ON resource_kinds(kind)')
        con.commit()
    finally:
        con.close()


def export_all(out, resources, v, meta, stats):
    """Write build/export/* and build/api/v1/*. `resources` are enriched records sorted by id."""
    exp = os.path.join(out, 'export')
    write_json(os.path.join(exp, 'resources.json'), {**meta, 'count': len(resources), 'resources': resources})
    os.makedirs(exp, exist_ok=True)
    with open(os.path.join(exp, 'resources.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        f.write(csv_text(flat(r) for r in resources))
    write_sqlite(os.path.join(exp, 'registry.sqlite'), resources, v, meta)

    api = os.path.join(out, 'api', API_VERSION)
    summary = [{'id': r['id'], 'name': r['name'], 'kind': r['kind'], 'domain': r['domain'], 'url': r['url'],
                'license': r.get('license'), 'state': r['health']['state']} for r in resources]
    write_json(os.path.join(api, 'resources.json'), {**meta, 'count': len(summary), 'resources': summary}, compact=True)
    for r in resources:
        write_json(os.path.join(api, 'resources', f'{r["id"]}.json'), r)
    domains = []
    for d in v.domains:
        items = [s for s in summary if s['domain'] == d['id']]
        domains.append({**d, 'count': len(items), 'href': f'domains/{d["id"]}.json'})
        write_json(os.path.join(api, 'domains', f'{d["id"]}.json'), {**d, 'count': len(items), 'resources': items},
                   compact=True)
    write_json(os.path.join(api, 'domains.json'), {**meta, 'domains': domains})
    for kind in KINDS:
        items = [s for s in summary if kind in s['kind']]
        write_json(os.path.join(api, 'kinds', f'{kind}.json'), {'kind': kind, 'count': len(items), 'resources': items},
                   compact=True)
    write_json(os.path.join(api, 'stats.json'), stats)
    write_json(os.path.join(api, 'index.json'), {
        **meta, 'version': API_VERSION, 'count': len(resources),
        'endpoints': {
            'resources': 'resources.json', 'resource': 'resources/{id}.json', 'domains': 'domains.json',
            'domain': 'domains/{domain}.json', 'kind': 'kinds/{kind}.json', 'stats': 'stats.json',
        },
        'exports': {'json': '../../export/resources.json', 'csv': '../../export/resources.csv',
                    'sqlite': '../../export/registry.sqlite'},
    })
