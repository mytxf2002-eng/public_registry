"""The static site: index.html (a full page, also works from file://), embed.html (the same page without the
document wrapper, for hosts that add their own), app.js and data.js (the catalogue as one script)."""
import json
import os

TEMPLATES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates', 'site')
FONTS = ('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Condensed:wght@600'
         '&family=IBM+Plex+Sans:wght@400;500;600&display=swap')
KIND_CODES = {'api': 'a', 'dataset': 'd', 'mcp-server': 'm'}
ORIGIN_CODES = {'public-apis': 0, 'apd-link': 1, 'contribution': 2}


def compact(resources, v):
    """Short-key records for data.js (about half the size of the full export)."""
    dom_index = {d: i for i, d in enumerate(v.domain_ids)}
    out = []
    for r in resources:
        x = {'i': r['id'], 'n': r['name'], 'k': ''.join(KIND_CODES[k] for k in r['kind']), 'd': dom_index[r['domain']],
             'u': r['url'], 'e': r['description'], 'l': r.get('license', 'unknown'),
             'a': r['provenance']['added'], 'o': ORIGIN_CODES[r['provenance']['origin']]}
        zh = (r.get('i18n') or {}).get('zh-CN')
        if zh:
            x['z'] = zh['description']
            if zh.get('group'):
                x['zg'] = zh['group']
        if r.get('tags'):
            x['g'] = r['tags']
        if r.get('publisher'):
            x['p'] = [r['publisher']['name'], r['publisher']['kind']]
        if r['provenance'].get('sponsored'):
            x['s'] = 1
        if 'api' in r:
            x['ap'] = [r['api']['auth'], 1 if r['api']['https'] else 0, r['api']['cors']]
        if 'mcp' in r:
            x['mc'] = [r['mcp']['auth'], r['mcp']['transport']]
        if 'dataset' in r:
            ds = r['dataset']
            x['ds'] = {'f': ds['formats'], 'x': ds['access']}
        h = r.get('health') or {}
        if h.get('state') and h['state'] != 'unchecked':
            x['h'] = [h['state'], h.get('checked'), h.get('last_ok')]
        out.append(x)
    return out


def _read(name):
    with open(os.path.join(TEMPLATES, name), encoding='utf-8') as f:
        return f.read()


def write_site(out, resources, v, stats, meta):
    os.makedirs(out, exist_ok=True)
    payload = {
        'generated': meta['generated'], 'sha': (meta.get('source_sha') or '')[:10] or None,
        'domains': [{'id': d['id'], 'name': d['name'], 'name_zh': d['name_zh']} for d in v.domains],
        'licenses': {lid: l['family'] for lid, l in v.licenses.items()},
        'stats': stats, 'r': compact(resources, v),
    }
    body, css, app = _read('page.html'), _read('style.css'), _read('app.js')
    title = 'Public Registry'
    for mode, name in (('site', 'data.js'), ('embed', 'data-embed.js')):
        with open(os.path.join(out, name), 'w', encoding='utf-8', newline='\n') as f:
            f.write('window.REGISTRY=' + json.dumps({**payload, 'mode': mode}, ensure_ascii=False,
                                                    separators=(',', ':')) + ';\n')
    with open(os.path.join(out, 'app.js'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(app)
    head = (f'<title>{title}</title>\n<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            f'<link rel="stylesheet" href="{FONTS}">\n<style>\n{css}</style>\n')
    page = (f'<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f'<meta name="description" content="Public APIs, datasets and MCP servers with licences and daily link checks">\n'
            f'{head}</head>\n<body>\n{body}<script src="data.js"></script>\n<script src="app.js"></script>\n</body>\n</html>\n')
    embed = f'{head}{body}<script src="data-embed.js"></script>\n<script src="app.js"></script>\n'
    for name, text in (('index.html', page), ('embed.html', embed)):
        with open(os.path.join(out, name), 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
    return len(payload['r'])
