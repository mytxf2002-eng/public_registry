"""Markdown outputs: an index page and one page per domain, in English and Chinese.

All outputs are generated into build/; nothing here is committed to the repository.
"""
import unicodedata
from collections import Counter

from .vocab import KINDS

KIND_LABELS = {
    'en': {'api': 'APIs', 'dataset': 'Datasets', 'mcp-server': 'MCP servers'},
    'zh-CN': {'api': 'API', 'dataset': '数据集', 'mcp-server': 'MCP 服务器'},
}
STATE_LABELS = {
    'en': {'verified': 'OK', 'failing': 'Failing', 'suspicious': 'Check', 'unconfirmed': 'Unconfirmed',
           'unchecked': 'Not checked'},
    'zh-CN': {'verified': '正常', 'failing': '失效', 'suspicious': '待核实', 'unconfirmed': '待确认', 'unchecked': '未检测'},
}
AUTH_LABELS = {
    'en': {'none': 'No', 'api-key': 'API key', 'oauth': 'OAuth', 'user-agent': 'User-Agent',
           'x-mashape-key': 'RapidAPI key'},
    'zh-CN': {'none': '免鉴权', 'api-key': 'API key', 'oauth': 'OAuth', 'user-agent': 'User-Agent',
              'x-mashape-key': 'RapidAPI key'},
}
ACCESS_LABELS = {
    'en': {'public': 'Open', 'registration': 'Free account', 'application': 'Application', 'paid-tier': 'Free tier'},
    'zh-CN': {'public': '直接下载', 'registration': '免费注册', 'application': '需申请', 'paid-tier': '有免费档'},
}


def sort_key(text):
    """Case- and accent-insensitive ordering."""
    decomposed = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def cell(text):
    return str(text).replace('|', '\\|').replace('\n', ' ')

def _text(d, lang, translations):
    if lang == 'en':
        return d['description']
    t = translations.get(d['id'])
    return t['description'] if t else d['description']


def _state(d, health, lang):
    state = (health.get(d['id']) or {}).get('state', 'unchecked')
    return STATE_LABELS[lang].get(state, state)


def domain_page(domain, resources, lang, v, translations, health, generated):
    zh = lang == 'zh-CN'
    info = v.domain(domain)
    title = info['name_zh'] if zh else info['name']
    scope = info['scope_zh'] if zh else info['scope']
    counts = Counter(k for d in resources for k in d['kind'])
    summary = ' · '.join(f'{counts[k]} {KIND_LABELS[lang][k]}' for k in KINDS if counts[k])
    lines = [f'# {title}' + (f'（{info["name"]}）' if zh else ''), '',
             f'> {summary} · ' + (f'生成于 {generated} · [返回目录](README.md)' if zh
                                  else f'generated {generated} · [back to index](README.md)'), '', scope, '']
    groups = [('api', [d for d in resources if 'api' in d['kind']]),
              ('dataset', [d for d in resources if 'dataset' in d['kind'] and 'api' not in d['kind']]),
              ('mcp-server', [d for d in resources if 'mcp-server' in d['kind']])]
    for kind, items in groups:
        if not items:
            continue
        items.sort(key=lambda d: sort_key(d['name']))
        if kind == 'api':
            heading = 'API（含同时提供数据下载的）' if zh else 'APIs (including those that also offer downloads)'
            head = ('| 名称 | 说明 | 鉴权 | 数据下载 | 许可 | 状态 |' if zh
                    else '| Name | Description | Auth | Download | Licence | Status |')
        elif kind == 'dataset':
            heading = '数据集' if zh else 'Datasets'
            head = ('| 名称 | 说明 | 获取方式 | 格式 | 许可 | 状态 |' if zh
                    else '| Name | Description | Access | Formats | Licence | Status |')
        else:
            heading = 'MCP 服务器' if zh else 'MCP servers'
            head = '| 名称 | 说明 | 鉴权 | 传输 | 状态 |' if zh else '| Name | Description | Auth | Transport | Status |'
        lines += [f'## {heading} ({len(items)})', '']
        sep = '|' + '---|' * head.count(' | ') + '---|'
        for label, bucket in _buckets(items, kind, zh, translations):
            if label:
                lines += [f'### {label}（{len(bucket)}）' if zh else f'### {label} ({len(bucket)})', '']
            lines += [head, sep]
            lines += [_row(d, kind, lang, translations, health) for d in bucket]
            lines.append('')
    if any(d.get('provenance', {}).get('sponsored') for d in resources):
        lines += ['☆ ' + ('赞助商的产品。' if zh else 'Product of a sponsor.'), '']
    return '\n'.join(lines)


def _buckets(items, kind, zh, translations):
    """Chinese API sections are split by the curated zh-CN group; everything else is one table."""
    if not (zh and kind == 'api'):
        return [(None, items)]
    groups = {}
    for d in items:
        groups.setdefault((translations.get(d['id']) or {}).get('group'), []).append(d)
    if list(groups) == [None]:
        return [(None, items)]
    named = sorted(((g, b) for g, b in groups.items() if g), key=lambda gb: (-len(gb[1]), sort_key(gb[0])))
    return named + ([('其他', groups[None])] if None in groups else [])


def _row(d, kind, lang, translations, health):
    zh = lang == 'zh-CN'
    name = f'[{cell(d["name"])}]({d["url"]})'
    if d.get('provenance', {}).get('sponsored'):
        name += ' ☆'
    text = cell(_text(d, lang, translations))
    lic = d.get('license', 'unknown')
    lic = ('未知' if zh else 'unknown') if lic == 'unknown' else lic.replace('LicenseRef-', '')
    state = _state(d, health, lang)
    if kind == 'api':
        dl = ', '.join(d['dataset']['formats']) if 'dataset' in d else '–'
        return f'| {name} | {text} | {AUTH_LABELS[lang][d["api"]["auth"]]} | {dl} | {lic} | {state} |'
    if kind == 'dataset':
        ds = d['dataset']
        return f'| {name} | {text} | {ACCESS_LABELS[lang][ds["access"]]} | {", ".join(ds["formats"])} | {lic} | {state} |'
    m = d['mcp']
    return f'| {name} | {text} | {AUTH_LABELS[lang][m["auth"]]} | {", ".join(m["transport"])} | {state} |'


def index_page(by_domain, lang, v, generated, totals):
    zh = lang == 'zh-CN'
    head = ('| 领域 | API | 数据集 | MCP | 合计 |' if zh else '| Domain | APIs | Datasets | MCP | Total |')
    lines = ['# ' + ('公共 API 与数据集目录' if zh else 'Public APIs and datasets'), '',
             (f'共 {totals["resources"]} 个资源，分布在 {len(by_domain)} 个领域 · 生成于 {generated}' if zh else
              f'{totals["resources"]} resources in {len(by_domain)} domains · generated {generated}'), '',
             head, '|---|---:|---:|---:|---:|']
    for dom in v.domain_ids:
        items = by_domain.get(dom, [])
        c = Counter(k for d in items for k in d['kind'])
        name = v.domain(dom)['name_zh' if zh else 'name']
        lines.append(f'| [{name}]({dom}.md) | {c["api"]} | {c["dataset"]} | {c["mcp-server"]} | {len(items)} |')
    lines.append('')
    return '\n'.join(lines)
