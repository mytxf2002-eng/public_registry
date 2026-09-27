"""JSON Schemas for resource and translation files, generated from the vocabularies.

schema/*.schema.json in the repository are written by `python -m registry_kit schema`, and
`schema --check` (part of CI) fails when they are out of date. Validation always uses the schema
generated in memory, so it can never drift from vocab/. Rules the schema cannot express (real calendar
dates, URL uniqueness, placeholders, the rules for new files) are in validate.py.
"""
import difflib
import json
import os

import jsonschema

from . import vocab as V

URL = {'type': 'string', 'maxLength': 500, 'pattern': r'^https?://[^\s/?#.][^\s]*$'}
DATE = {'type': 'string', 'pattern': r'^\d{4}-\d{2}-\d{2}$'}
PARTIAL_DATE = {'type': ['string', 'null'], 'pattern': r'^\d{4}(-\d{2}(-\d{2})?)?$'}
TRIMMED = r'^\S(.*\S)?$'
ID_PATTERN = r'^[a-z0-9][a-z0-9-]{1,63}$'
TAG_PATTERN = r'^[a-z0-9][a-z0-9+.-]{0,29}$'
SPATIAL_PATTERN = r'^(' + '|'.join(V.REGIONS) + r'|[A-Z]{2}(-[A-Z0-9]{1,3})?)$'

PATTERN_HINTS = {
    'id': 'lowercase letters, digits and hyphens, 2-64 characters, same as the file name',
    'tags': 'lowercase letters, digits and - + . (for example "air-quality")',
    'spatial': '"global", a continent id such as "europe", or an ISO 3166 code such as "US" or "US-NY"',
    'added': 'a date written YYYY-MM-DD',
    'reviewed': 'a date written YYYY-MM-DD',
    'date': 'a date written YYYY-MM-DD',
    'start': '"YYYY", "YYYY-MM" or "YYYY-MM-DD" (quoted) or null',
    'end': '"YYYY", "YYYY-MM" or "YYYY-MM-DD" (quoted) or null',
    'url': 'an http(s) URL without spaces',
    'license_url': 'an http(s) URL without spaces',
    'docs': 'an http(s) URL without spaces',
    'spec': 'an http(s) URL without spaces',
    'name': 'text without leading or trailing spaces',
    'description': 'text without leading or trailing spaces',
}


def _kind_rule(kind, block):
    has = {'properties': {'kind': {'contains': {'const': kind}}}, 'required': ['kind']}
    return {'if': has, 'then': {'required': [block]}, 'else': {'not': {'required': [block]}}}


def resource_schema(v):
    text = {'type': 'string', 'minLength': 1}
    return {
        '$schema': 'https://json-schema.org/draft/2020-12/schema',
        '$id': 'resource.schema.json',
        'title': 'Registry resource',
        'description': 'One API, dataset or MCP server. Generated from vocab/ by registry_kit; do not edit.',
        'type': 'object',
        'additionalProperties': False,
        'required': ['id', 'kind', 'name', 'url', 'description', 'domain', 'license', 'provenance'],
        'properties': {
            'id': {'type': 'string', 'pattern': ID_PATTERN},
            'kind': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': {'enum': list(V.KINDS)}},
            'name': {'type': 'string', 'minLength': 1, 'maxLength': 80, 'pattern': TRIMMED},
            'url': URL,
            # at least 10 characters for active resources (see allOf); archived files keep the text they had
            'description': {'type': 'string', 'minLength': 1, 'maxLength': 200, 'pattern': TRIMMED},
            'domain': {'enum': v.domain_ids},
            'tags': {'type': 'array', 'maxItems': 8, 'uniqueItems': True,
                     'items': {'type': 'string', 'pattern': TAG_PATTERN}},
            'license': {'enum': sorted(v.licenses) + ['unknown']},
            'license_url': URL,
            'publisher': {
                'type': 'object', 'additionalProperties': False, 'required': ['name', 'kind'],
                'properties': {'name': {**text, 'maxLength': 120}, 'kind': {'enum': list(V.PUBLISHER_KINDS)}},
            },
            'provenance': {
                'type': 'object', 'additionalProperties': False, 'required': ['added', 'origin'],
                'properties': {'added': DATE, 'origin': {'enum': list(V.ORIGINS)}, 'reviewed': DATE,
                               'sponsored': {'type': 'boolean'}},
            },
            'api': {
                'type': 'object', 'additionalProperties': False, 'required': ['auth', 'https', 'cors'],
                'properties': {'auth': {'enum': list(V.AUTH)}, 'https': {'type': 'boolean'},
                               'cors': {'enum': list(V.CORS)}, 'docs': URL, 'spec': URL},
            },
            'mcp': {
                'type': 'object', 'additionalProperties': False, 'required': ['auth', 'transport'],
                'properties': {
                    'auth': {'enum': list(V.AUTH)},
                    'transport': {'type': 'array', 'minItems': 1, 'uniqueItems': True,
                                  'items': {'enum': list(V.TRANSPORTS)}},
                    'install': {'type': 'array', 'items': {
                        'type': 'object', 'additionalProperties': False, 'required': ['name', 'url'],
                        'properties': {'name': {**text, 'maxLength': 40}, 'url': URL}}},
                },
            },
            'dataset': {
                'type': 'object', 'additionalProperties': False, 'required': ['formats', 'access'],
                'properties': {
                    'formats': {'type': 'array', 'minItems': 1, 'uniqueItems': True,
                                'items': {'enum': sorted(v.formats)}},
                    'access': {'enum': list(V.ACCESS)},
                    'url': URL,
                    'temporal': {'type': 'object', 'additionalProperties': False,
                                 'properties': {'start': PARTIAL_DATE, 'end': PARTIAL_DATE}},
                    'spatial': {'type': 'array', 'minItems': 1, 'uniqueItems': True,
                                'items': {'type': 'string', 'pattern': SPATIAL_PATTERN}},
                    'update_frequency': {'enum': list(V.FREQUENCIES)},
                    'size': {**text, 'maxLength': 40},
                },
            },
            'archived': {
                'type': 'object', 'additionalProperties': False, 'required': ['date', 'reason'],
                'properties': {'date': DATE, 'reason': {**text, 'maxLength': 300}},
            },
        },
        'allOf': [
            {'if': {'not': {'required': ['archived']}},
             'then': {'properties': {'description': {'minLength': 10}}}},
            _kind_rule('api', 'api'),
            _kind_rule('dataset', 'dataset'),
            _kind_rule('mcp-server', 'mcp'),
            {'if': {'properties': {'license': {'enum': list(V.LICENSE_URL_REQUIRED)}}, 'required': ['license']},
             'then': {'required': ['license_url']}},
        ],
    }


def translation_schema(v):
    return {
        '$schema': 'https://json-schema.org/draft/2020-12/schema',
        '$id': 'translation.schema.json',
        'title': 'Registry translation',
        'description': 'Translated text for one resource, stored at i18n/<lang>/<id>.yml. Generated; do not edit.',
        'type': 'object',
        'additionalProperties': False,
        'required': ['id', 'description'],
        'properties': {
            'id': {'type': 'string', 'pattern': ID_PATTERN},
            'name': {'type': 'string', 'minLength': 1, 'maxLength': 80, 'pattern': TRIMMED},
            'description': {'type': 'string', 'minLength': 4, 'maxLength': 400, 'pattern': TRIMMED},
            'group': {'type': 'string', 'minLength': 1, 'maxLength': 40, 'pattern': TRIMMED},
        },
    }


SCHEMAS = {'resource.schema.json': resource_schema, 'translation.schema.json': translation_schema}


def render_schema(builder, v):
    return json.dumps(builder(v), ensure_ascii=False, indent=2) + '\n'


def write_schemas(root, v, check=False):
    """Write (or with check=True, compare) schema/*.json. Returns the names that differ."""
    stale = []
    for name, builder in SCHEMAS.items():
        path = os.path.join(root, 'schema', name)
        text = render_schema(builder, v)
        current = None
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                current = f.read()
        if current != text:
            stale.append(name)
            if not check:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(text)
    return stale


class Validator:
    def __init__(self, v):
        self.vocab = v
        self.resource = jsonschema.Draft202012Validator(resource_schema(v))
        self.translation = jsonschema.Draft202012Validator(translation_schema(v))

    def resource_errors(self, data):
        return self._messages(self.resource, data)

    def translation_errors(self, data):
        return self._messages(self.translation, data)

    def _messages(self, validator, data):
        out = []
        for error in sorted(validator.iter_errors(data), key=lambda e: (list(e.absolute_path), e.validator)):
            out.extend(self._explain(error, data))
        return list(dict.fromkeys(out))

    def _explain(self, error, data):
        """Readable messages for one jsonschema error (if/then errors are unfolded)."""
        path = '.'.join(str(p) for p in error.absolute_path)
        where = path or 'file'
        kind = error.validator
        if kind in ('allOf', 'anyOf', 'oneOf') and error.context:
            out = []
            for sub in error.context:
                out.extend(self._explain(sub, data))
            return out
        if kind == 'required':
            missing = error.message.split("'")[1] if "'" in error.message else error.message
            if missing in ('api', 'dataset', 'mcp'):
                block_kind = {'api': 'api', 'dataset': 'dataset', 'mcp': 'mcp-server'}[missing]
                return [f'kind includes "{block_kind}", so the "{missing}" block is required']
            if missing == 'license_url':
                return [f'license {data.get("license")} needs license_url (where the terms are stated)']
            return [f'{where}: missing required field "{missing}"']
        if kind == 'not':
            block = next(iter(error.validator_value.get('required', ['?'])))
            block_kind = {'api': 'api', 'dataset': 'dataset', 'mcp': 'mcp-server'}.get(block, block)
            return [f'"{block}" block is present but kind does not include "{block_kind}"']
        if kind == 'additionalProperties':
            extra = sorted(set(error.instance) - set(error.schema.get('properties', {})))
            return [f'{where}: unknown field "{name}"' for name in extra]
        if kind == 'enum':
            return [f'{where}: {error.instance!r} is not allowed' + self._suggest(path, error.instance, error.validator_value)]
        if kind == 'pattern':
            field = str(error.absolute_path[-1]) if error.absolute_path else ''
            if isinstance(field, str) and field.isdigit() and len(error.absolute_path) > 1:
                field = str(error.absolute_path[-2])
            hint = PATTERN_HINTS.get(field, 'the expected format')
            return [f'{where}: {error.instance!r} must be {hint}']
        if kind in ('maxLength', 'minLength'):
            return [f'{where}: {len(error.instance)} characters, must be '
                    f'{"at most" if kind == "maxLength" else "at least"} {error.validator_value}']
        if kind == 'type':
            expected = error.validator_value
            expected = ' or '.join(expected) if isinstance(expected, list) else expected
            return [f'{where}: must be {expected}, not {type(error.instance).__name__}']
        if kind in ('minItems', 'maxItems'):
            return [f'{where}: must have {"at least" if kind == "minItems" else "at most"} '
                    f'{error.validator_value} item(s)']
        if kind == 'uniqueItems':
            return [f'{where}: has duplicate items']
        return [f'{where}: {error.message}']

    def _suggest(self, path, value, allowed):
        text = str(value)
        if path == 'license':
            canonical = self.vocab.canonical_license(text)
            if canonical != text:
                return f' (use "{canonical}"; `registry_kit format` fixes this)'
        if path.startswith('dataset.formats'):
            canonical = self.vocab.canonical_format(text)
            if canonical != text:
                return f' (use "{canonical}"; `registry_kit format` fixes this)'
        close = difflib.get_close_matches(text, [str(a) for a in allowed if a is not None], n=1, cutoff=0.6)
        if close:
            return f' (did you mean "{close[0]}"?)'
        if len(allowed) <= 8:
            return ' (allowed: ' + ', '.join(str(a) for a in allowed) + ')'
        return ' (see vocab/)'
