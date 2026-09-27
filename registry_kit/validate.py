"""Full validation of the repository. Every problem is collected; nothing stops at the first error.

Every problem is an error that must be fixed before merging. Files passed with --strict (the files a
pull request adds) are also held to the rules for new resources: complete metadata and the
`contribution` origin.
"""
import datetime as dt
import os
import re
from collections import Counter, defaultdict

from . import urls, yamlio
from .health import FAILED_RESULTS, SIGNALS
from .repo import ID_RE, LANGUAGES, Problem
from .schema import Validator

MIN_DOMAIN_SIZE = 5

# text left over from a template: TODO markers, <angle-bracket> slots, the template's own sample text.
# (Words such as "placeholder" or "lorem ipsum" are not flagged: some APIs generate exactly that.)
PLACEHOLDER_RE = re.compile(r'\b(TODO|TBD|FIXME|XXX)\b|<[a-z][a-z _-]*>|\bYOUR_API_KEY\b|'
                            r'(?i:describe the (resource|dataset|api) here)')
PLACEHOLDER_URL_HOSTS = {'example.com', 'example.org', 'example.net', 'localhost', '127.0.0.1'}
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
PARTIAL_DATE_RE = re.compile(r'^\d{4}(-\d{2}(-\d{2})?)?$')


def validate(repo, strict_paths=(), today=None):
    """Validate everything. `strict_paths`: files held to the rules for new files (repository-relative,
    `./`-prefixed, backslashed or absolute paths are all accepted). `today`: YYYY-MM-DD, for tests."""
    problems = []
    today = dt.date.fromisoformat(today) if today else dt.datetime.now(dt.timezone.utc).date()
    strict = {_repo_path(repo, p) for p in strict_paths}
    for path in sorted(strict):
        if not os.path.exists(repo.abs(path)):
            problems.append(Problem('error', path, 'no such file (given with --strict)'))
    v = repo.vocab
    validator = Validator(v)

    resources = repo.load_resources(problems)
    by_id = defaultdict(list)
    by_key = defaultdict(list)
    names = defaultdict(list)
    domain_sizes = Counter()

    for r in resources:
        d = r.data
        add = _adder(problems, r.path)
        for message in validator.resource_errors(d):
            add('error', message)
        rid = d.get('id')
        stem = os.path.basename(r.path)[:-4]
        if isinstance(rid, str):
            by_id[rid].append(r)
            if rid != stem:
                add('error', f'id "{rid}" must equal the file name ("{stem}")')
        elif ID_RE.match(stem) is None:
            add('error', 'file name must be a valid id (lowercase letters, digits and hyphens)')
        domain = d.get('domain')
        folder = r.path.split('/')[1]
        if r.archived:
            if 'archived' not in d:
                add('error', 'archived resources need an "archived" block with date and reason')
        else:
            if 'archived' in d:
                add('error', 'has an "archived" block but is not in data/_archive/')
            if isinstance(domain, str) and folder != domain:
                add('error', f'domain is "{domain}" but the file is in data/{folder}/')
            if domain in v.domain_ids:
                domain_sizes[domain] += 1
        _check_urls(d, add, by_key, r)
        _check_dates(d, add, today)
        if r.archived:
            continue            # archived files are a frozen record: only structure and uniqueness apply
        if isinstance(d.get('name'), str) and isinstance(domain, str):
            names[(domain, d['name'].casefold())].append(r)
        _check_text(d, add)
        if r.path in strict:
            _check_new(d, add)

    for rid, group in by_id.items():
        if len(group) > 1:
            paths = ', '.join(g.path for g in group)
            for g in group:
                problems.append(Problem('error', g.path, f'id "{rid}" is used by more than one file ({paths})'))
    for key, group in by_key.items():
        if len(group) > 1:
            for g in group:
                others = [o for o in group if o is not g]
                what = ', '.join(('archived ' if o.archived else '') + o.path for o in others)
                reason = next((o.data.get('archived', {}).get('reason') for o in others if o.archived), None)
                problems.append(Problem('error', g.path, f'same URL as {what}'
                                        + (f' (archived because: {reason})' if reason else '')))
    for (domain, _), group in names.items():
        if len(group) > 1:
            for g in group:
                problems.append(Problem('error', g.path, f'another resource in {domain} has the same name: '
                                        + ', '.join(o.path for o in group if o is not g)))
    for domain in v.domain_ids:
        if domain_sizes[domain] < MIN_DOMAIN_SIZE:
            problems.append(Problem('error', f'data/{domain}/',
                                    f'domain has {domain_sizes[domain]} resources; the minimum is {MIN_DOMAIN_SIZE}'))
    for folder in _data_folders(repo):
        if folder not in v.domain_ids and folder != '_archive':
            problems.append(Problem('error', f'data/{folder}/', 'folder is not a domain from vocab/domains.yml'))

    # a translation may belong to an archived resource: it is kept so that restoring brings it back
    known_ids = {r.data.get('id') for r in resources}
    for lang in LANGUAGES:
        for t in repo.load_translations(lang, problems):
            add = _adder(problems, t.path)
            for message in validator.translation_errors(t.data):
                add('error', message)
            tid = t.data.get('id')
            stem = os.path.basename(t.path)[:-4]
            if tid != stem:
                add('error', f'id "{tid}" must equal the file name ("{stem}")')
            if tid not in known_ids:
                add('error', f'no resource with id "{tid}" (orphaned translation)')
            for field in ('name', 'description', 'group'):
                value = t.data.get(field)
                if isinstance(value, str) and PLACEHOLDER_RE.search(value):
                    add('error', f'{field} looks like a placeholder')

    _check_acknowledged(repo, known_ids, problems)
    return problems


def _repo_path(repo, path):
    """A path given on the command line (repository-relative or absolute, with / or \\) as a
    repository-relative path with forward slashes."""
    path = path.replace('\\', '/')
    if os.path.isabs(path):
        return repo.rel(path)
    return os.path.normpath(path).replace('\\', '/')


def _adder(problems, path):
    def add(level, message):
        problems.append(Problem(level, path, message))
    return add


def _data_folders(repo):
    base = os.path.join(repo.root, 'data')
    if not os.path.isdir(base):
        return []
    return sorted(n for n in os.listdir(base) if os.path.isdir(os.path.join(base, n)))


def _url_fields(d):
    """(field name, value) for every URL in a resource."""
    out = [('url', d.get('url')), ('license_url', d.get('license_url'))]
    api, ds, mcp = d.get('api'), d.get('dataset'), d.get('mcp')
    if isinstance(api, dict):
        out += [('api.docs', api.get('docs')), ('api.spec', api.get('spec'))]
    if isinstance(ds, dict):
        out.append(('dataset.url', ds.get('url')))
    if isinstance(mcp, dict) and isinstance(mcp.get('install'), list):
        out += [('mcp.install.url', i.get('url')) for i in mcp['install'] if isinstance(i, dict)]
    return [(name, value) for name, value in out if isinstance(value, str)]


def _check_urls(d, add, by_key, r):
    for field, value in _url_fields(d):
        problem = urls.problem(value)
        if problem:
            add('error', f'{field} is not a usable URL ({problem})')
            continue
        if urls.tracking_params(value):
            if field == 'url':
                add('error', f'url has tracking parameters ({", ".join(urls.tracking_params(value))}); '
                             '`registry_kit format` removes them')
            else:
                add('error', f'{field} has tracking parameters')
        if field == 'url':
            by_key[urls.unique_key(value)].append(r)
            if urls.host(value) in PLACEHOLDER_URL_HOSTS:
                add('error', 'url points to a placeholder host')


def _date(value, partial=False):
    """The date a field names, or None when it is not a real calendar date."""
    if not isinstance(value, str) or not (PARTIAL_DATE_RE if partial else DATE_RE).match(value):
        return None
    parts = [int(p) for p in value.split('-')]
    try:
        return dt.date(parts[0], parts[1] if len(parts) > 1 else 1, parts[2] if len(parts) > 2 else 1)
    except ValueError:
        return None


def _check_dates(d, add, today):
    prov = d.get('provenance') if isinstance(d.get('provenance'), dict) else {}
    archived = d.get('archived') if isinstance(d.get('archived'), dict) else {}
    latest = today + dt.timedelta(days=1)           # a contributor's local date may be a day ahead of UTC
    found = {}
    for field, value in (('provenance.added', prov.get('added')), ('provenance.reviewed', prov.get('reviewed')),
                         ('archived.date', archived.get('date'))):
        if value is None:
            continue
        date = _date(value)
        if date is None:
            if isinstance(value, str) and DATE_RE.match(value):      # the schema reports other formats
                add('error', f'{field} is not a real date ({value})')
            continue
        if date > latest:
            add('error', f'{field} is in the future ({value})')
        found[field] = date
    if 'provenance.reviewed' in found and 'provenance.added' in found \
            and found['provenance.reviewed'] < found['provenance.added']:
        add('error', 'provenance.reviewed is earlier than provenance.added')
    ds = d.get('dataset') if isinstance(d.get('dataset'), dict) else {}
    temporal = ds.get('temporal') if isinstance(ds.get('temporal'), dict) else {}
    bounds = {}
    for key in ('start', 'end'):
        value = temporal.get(key)
        if isinstance(value, str) and PARTIAL_DATE_RE.match(value):
            if _date(value, partial=True) is None:
                add('error', f'dataset.temporal.{key} is not a real date ({value})')
            else:
                bounds[key] = value
    if len(bounds) == 2:
        n = min(len(bounds['start']), len(bounds['end']))
        if bounds['start'][:n] > bounds['end'][:n]:
            add('error', 'dataset.temporal.start is later than dataset.temporal.end')


def _check_text(d, add):
    name, desc = d.get('name'), d.get('description')
    if isinstance(name, str):
        if name.lower().endswith(' api'):
            add('error', 'name must not end with " API"')
    if isinstance(desc, str):
        if desc.endswith('.'):
            add('error', 'description must not end with a period')
        if desc[:1].islower():
            add('error', 'description must start with a capital letter or a digit')
        if re.search(r'https?://|www\.', desc):
            add('error', 'description must not contain URLs')
        if '\n' in desc:
            add('error', 'description must be one line')
        if isinstance(name, str) and desc.strip().casefold() == name.strip().casefold():
            add('error', 'description must say more than the name')
    for field, value in _free_text(d):
        if PLACEHOLDER_RE.search(value):
            add('error', f'{field} looks like a placeholder')
    tags, domain = d.get('tags'), d.get('domain')
    if isinstance(tags, list) and isinstance(domain, str) and domain in tags:
        add('error', f'tags must not repeat the domain ("{domain}")')


def _free_text(d):
    """(field name, value) for every free-text field of a resource."""
    out = [('name', d.get('name')), ('description', d.get('description'))]
    pub, ds, mcp = d.get('publisher'), d.get('dataset'), d.get('mcp')
    if isinstance(pub, dict):
        out.append(('publisher.name', pub.get('name')))
    if isinstance(ds, dict):
        out.append(('dataset.size', ds.get('size')))
    if isinstance(mcp, dict) and isinstance(mcp.get('install'), list):
        out += [('mcp.install.name', i.get('name')) for i in mcp['install'] if isinstance(i, dict)]
    return [(name, value) for name, value in out if isinstance(value, str)]


def _check_new(d, add):
    """Rules for resources a pull request adds: fields old resources may lack must be filled."""
    gaps = []
    if d.get('license') == 'unknown':
        gaps.append('license is "unknown"')
    if 'publisher' not in d:
        gaps.append('publisher is missing')
    if d.get('license') not in (None, 'unknown') and 'license_url' not in d:
        gaps.append('license_url is missing (where are the terms stated?)')
    for gap in gaps:
        add('error', f'new resources need complete metadata: {gap}')
    origin = d['provenance'].get('origin') if isinstance(d.get('provenance'), dict) else None
    if origin not in (None, 'contribution'):
        add('error', f'provenance.origin is "{origin}"; new resources use "contribution"')


def _check_acknowledged(repo, known_ids, problems):
    """health/acknowledged.yml: what the maintainer accepted by hand, per resource."""
    rel = 'health/acknowledged.yml'
    path = repo.abs(rel)
    if not os.path.exists(path):
        return
    try:
        data = yamlio.load_file(path)
    except Exception as e:  # noqa: BLE001 - reported like any other invalid YAML
        problems.append(Problem('error', rel, f'invalid YAML: {getattr(e, "problem", None) or e}'))
        return
    if data is None:
        return
    if not isinstance(data, dict):
        problems.append(Problem('error', rel, 'must be a mapping of resource ids'))
        return
    for rid, item in data.items():
        add = _adder(problems, f'{rel}: {rid}')
        if rid not in known_ids:
            add('error', 'no resource with this id')
        if not isinstance(item, dict):
            add('error', 'needs signals and/or results, and a reason')
            continue
        unknown = sorted(set(item) - {'signals', 'results', 'reason'})
        if unknown:
            add('error', f'unknown field(s): {", ".join(unknown)}')
        for field, allowed in (('signals', SIGNALS), ('results', FAILED_RESULTS)):
            value = item.get(field, [])
            if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
                add('error', f'{field} must be a list such as [{allowed[0]}]')
            elif set(value) - set(allowed):
                add('error', f'{field}: {", ".join(sorted(set(value) - set(allowed)))} is not one of '
                             f'{", ".join(allowed)}')
        if not item.get('signals') and not item.get('results'):
            add('error', 'lists neither signals nor results')
        if not isinstance(item.get('reason'), str) or not item['reason'].strip():
            add('error', 'needs a reason: what was checked, and when')
