"""Counts and quality metrics, shared by `stats`, the site dashboard and the README summary."""
import datetime as dt
from collections import Counter

from .vocab import KINDS

STALE_AFTER_DAYS = 180


def pct(part, whole):
    return round(100.0 * part / whole, 1) if whole else 0.0


def compute(repo, today=None):
    today = today or dt.datetime.now(dt.timezone.utc).date().isoformat()
    v = repo.vocab
    resources = [r.data for r in repo.load_resources() if not r.archived]
    archived = [r.data for r in repo.load_resources() if r.archived]
    zh = {t.data['id'] for t in repo.load_translations('zh-CN')}
    health = repo.load_health().get('resources', {})
    n = len(resources)
    apis = [d for d in resources if 'api' in d['kind']]
    datasets = [d for d in resources if 'dataset' in d['kind']]

    def known_license(items):
        return sum(1 for d in items if d.get('license', 'unknown') != 'unknown')

    domains = {}
    for dom in v.domain_ids:
        items = [d for d in resources if d['domain'] == dom]
        c = Counter(k for d in items for k in d['kind'])
        domains[dom] = {'total': len(items), **{k: c[k] for k in KINDS}}

    states = Counter(health.get(d['id'], {}).get('state', 'unchecked') for d in resources)
    checked = n - states.get('unchecked', 0)
    reviewed = [d.get('provenance', {}).get('reviewed') for d in resources]
    fresh = sum(1 for r in reviewed if r and (dt.date.fromisoformat(today) - dt.date.fromisoformat(r)).days
                <= STALE_AFTER_DAYS)
    families = Counter(v.license_family(d.get('license', 'unknown')) for d in resources)
    return {
        'generated': today,
        'resources': n,
        'archived': len(archived),
        'kinds': {k: sum(1 for d in resources if k in d['kind']) for k in KINDS},
        'api_and_dataset': sum(1 for d in resources if 'api' in d['kind'] and 'dataset' in d['kind']),
        'origins': dict(Counter(d['provenance']['origin'] for d in resources)),
        'domains': domains,
        'completeness': {
            'description': 100.0,
            'license_known': pct(known_license(resources), n),
            'license_known_api': pct(known_license(apis), len(apis)),
            'license_known_dataset': pct(known_license(datasets), len(datasets)),
            'license_url_when_known': pct(sum(1 for d in resources if d.get('license', 'unknown') != 'unknown'
                                              and d.get('license_url')), known_license(resources)),
            'publisher': pct(sum(1 for d in resources if d.get('publisher')), n),
            'publisher_dataset': pct(sum(1 for d in datasets if d.get('publisher')), len(datasets)),
            'cors_known': pct(sum(1 for d in apis if d['api']['cors'] != 'unknown'), len(apis)),
            'temporal': pct(sum(1 for d in datasets if d['dataset'].get('temporal')), len(datasets)),
            'spatial': pct(sum(1 for d in datasets if d['dataset'].get('spatial')), len(datasets)),
            'update_frequency': pct(sum(1 for d in datasets if d['dataset'].get('update_frequency')), len(datasets)),
            'translation_zh': pct(sum(1 for d in resources if d['id'] in zh), n),
        },
        'license_families': dict(families),
        'licenses': dict(Counter(d.get('license', 'unknown') for d in resources).most_common()),
        'access': dict(Counter(d['dataset']['access'] for d in datasets)),
        'formats': dict(Counter(f for d in datasets for f in d['dataset']['formats']).most_common()),
        'auth': dict(Counter(d['api']['auth'] for d in apis)),
        'publisher_kinds': dict(Counter(d['publisher']['kind'] for d in resources if d.get('publisher'))),
        'health': {'states': dict(states), 'checked': checked,
                   'availability': pct(states.get('verified', 0) + states.get('suspicious', 0), checked)},
        'freshness': pct(fresh, n),
        'sponsored': sum(1 for d in resources if d.get('provenance', {}).get('sponsored')),
    }


def format_text(s):
    c = s['completeness']
    lines = [
        f'resources: {s["resources"]} (archived {s["archived"]})',
        '  ' + ', '.join(f'{k}: {s["kinds"][k]}' for k in KINDS) + f', api+dataset: {s["api_and_dataset"]}',
        '  origins: ' + ', '.join(f'{k} {v}' for k, v in sorted(s['origins'].items())),
        f'completeness: licence {c["license_known"]}% (APIs {c["license_known_api"]}%, datasets '
        f'{c["license_known_dataset"]}%), licence URL {c["license_url_when_known"]}% of known, publisher '
        f'{c["publisher"]}%, CORS known {c["cors_known"]}% of APIs, zh-CN {c["translation_zh"]}%',
        f'datasets: temporal {c["temporal"]}%, spatial {c["spatial"]}%, update frequency {c["update_frequency"]}%',
        'health: ' + ', '.join(f'{k} {v}' for k, v in sorted(s['health']['states'].items()))
        + f'; availability {s["health"]["availability"]}% of checked',
        f'freshness (reviewed within 180 days): {s["freshness"]}%; sponsored: {s["sponsored"]}',
        'smallest domains: ' + ', '.join(f'{k} {v["total"]}' for k, v in
                                         sorted(s['domains'].items(), key=lambda x: x[1]['total'])[:6]),
    ]
    return '\n'.join(lines)
