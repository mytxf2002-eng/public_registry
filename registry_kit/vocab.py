"""Controlled vocabularies (vocab/*.yml) and the small enums that live in code."""
import os
import re
from dataclasses import dataclass, field

from . import yamlio

KINDS = ('api', 'dataset', 'mcp-server')
AUTH = ('none', 'api-key', 'oauth', 'user-agent', 'x-mashape-key')
CORS = ('yes', 'no', 'unknown')
ACCESS = ('public', 'registration', 'application', 'paid-tier')
FREQUENCIES = ('realtime', 'daily', 'weekly', 'monthly', 'quarterly', 'annual', 'irregular', 'static')
PUBLISHER_KINDS = ('government', 'intergovernmental', 'academic', 'nonprofit', 'company', 'community', 'individual')
ORIGINS = ('public-apis', 'apd-link', 'contribution')
TRANSPORTS = ('stdio', 'http', 'sse')
REGIONS = ('global', 'africa', 'asia', 'europe', 'north-america', 'south-america', 'oceania', 'antarctica', 'arctic')
LICENSE_URL_REQUIRED = ('LicenseRef-Open-Government', 'LicenseRef-Custom-Open', 'LicenseRef-Research-Only')


def alias_key(text):
    """Case-, space-, underscore- and hyphen-insensitive key used for alias lookups."""
    return re.sub(r'[\s_-]+', '-', str(text).strip().lower())


@dataclass
class Vocab:
    domains: list = field(default_factory=list)        # [{id, name, name_zh, scope, scope_zh}]
    licenses: dict = field(default_factory=dict)       # id -> {id, family, spdx: bool, description?}
    license_aliases: dict = field(default_factory=dict)
    formats: dict = field(default_factory=dict)        # id -> {id, name, group}
    format_aliases: dict = field(default_factory=dict)

    @property
    def domain_ids(self):
        return [d['id'] for d in self.domains]

    def domain(self, domain_id):
        return next((d for d in self.domains if d['id'] == domain_id), None)

    def license_family(self, license_id):
        if license_id == 'unknown':
            return 'unknown'
        return self.licenses.get(license_id, {}).get('family', 'unknown')

    def canonical_license(self, value):
        if value in self.licenses or value == 'unknown':
            return value
        return self.license_aliases.get(alias_key(value), value)

    def canonical_format(self, value):
        if value in self.formats:
            return value
        return self.format_aliases.get(alias_key(value), value)


class VocabError(ValueError):
    pass


def _check_keys(item, allowed, where):
    extra = set(item) - set(allowed)
    if extra:
        raise VocabError(f'{where}: unexpected keys {sorted(extra)} (a comma inside an unquoted flow value?)')


def load(root):
    v = Vocab()
    base = os.path.join(root, 'vocab')

    domains = yamlio.load_file(os.path.join(base, 'domains.yml'))
    for d in domains:
        _check_keys(d, ('id', 'name', 'name_zh', 'scope', 'scope_zh'), f'domains.yml {d.get("id")}')
        if not re.fullmatch(r'[a-z][a-z0-9-]*', d.get('id', '')):
            raise VocabError(f'domains.yml: bad id {d.get("id")!r}')
        for k in ('name', 'name_zh', 'scope', 'scope_zh'):
            if not isinstance(d.get(k), str) or not d[k].strip():
                raise VocabError(f'domains.yml {d["id"]}: {k} is required')
    ids = [d['id'] for d in domains]
    if len(set(ids)) != len(ids):
        raise VocabError('domains.yml: duplicate ids')
    v.domains = domains

    lic = yamlio.load_file(os.path.join(base, 'licenses.yml'))
    for section, is_spdx in (('spdx', True), ('extensions', False)):
        for item in lic[section]:
            _check_keys(item, ('id', 'family', 'aliases', 'description'), f'licenses.yml {item.get("id")}')
            lid = item['id']
            if is_spdx == lid.startswith('LicenseRef-'):
                raise VocabError(f'licenses.yml: {lid} is in the wrong section')
            if lid in v.licenses:
                raise VocabError(f'licenses.yml: duplicate id {lid}')
            if item.get('family') not in ('public-domain', 'permissive', 'share-alike', 'no-derivatives',
                                          'non-commercial', 'research-only', 'terms'):
                raise VocabError(f'licenses.yml {lid}: bad family {item.get("family")!r}')
            v.licenses[lid] = {'id': lid, 'family': item['family'], 'spdx': is_spdx,
                               'description': item.get('description', '')}
            for alias in [lid] + list(item.get('aliases', [])):
                if not isinstance(alias, str):
                    raise VocabError(f'licenses.yml {lid}: alias {alias!r} is not a string (quote it)')
                key = alias_key(alias)
                if v.license_aliases.get(key, lid) != lid:
                    raise VocabError(f'licenses.yml: alias {alias!r} is used by two licences')
                v.license_aliases[key] = lid

    fmt = yamlio.load_file(os.path.join(base, 'formats.yml'))
    for group, items in fmt.items():
        for item in items:
            _check_keys(item, ('id', 'name', 'aliases'), f'formats.yml {item.get("id")}')
            fid = item['id']
            if fid in v.formats:
                raise VocabError(f'formats.yml: duplicate id {fid}')
            v.formats[fid] = {'id': fid, 'name': item['name'], 'group': group}
            for alias in [fid] + list(item.get('aliases', [])):
                if not isinstance(alias, str):
                    raise VocabError(f'formats.yml {fid}: alias {alias!r} is not a string (quote it)')
                key = alias_key(alias)
                if v.format_aliases.get(key, fid) != fid:
                    raise VocabError(f'formats.yml: alias {alias!r} is used by two formats')
                v.format_aliases[key] = fid
    return v
