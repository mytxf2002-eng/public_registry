"""Strict YAML loading and canonical YAML writing.

Loading is stricter than yaml.safe_load:
- a duplicated key is an error instead of silently keeping the last value;
- only true/false are booleans (YAML 1.2), so `no`, `yes`, `on`, `off` stay strings;
- dates stay strings ("2026-09-27"), so files round-trip unchanged and match the JSON Schema.

Writing produces one canonical layout, so `registry_kit format --check` can require it.
"""
import re

import yaml


class DuplicateKeyError(yaml.constructor.ConstructorError):
    pass


class StrictLoader(yaml.SafeLoader):
    """SafeLoader with YAML 1.2 booleans, string timestamps and duplicate-key detection."""


# rebuild the implicit resolvers: drop bool and timestamp, then add a YAML 1.2 bool
StrictLoader.yaml_implicit_resolvers = {
    first: [(tag, regexp) for tag, regexp in resolvers
            if tag not in ('tag:yaml.org,2002:bool', 'tag:yaml.org,2002:timestamp')]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
StrictLoader.add_implicit_resolver('tag:yaml.org,2002:bool', re.compile(r'^(?:true|True|TRUE|false|False|FALSE)$'),
                                   list('tTfF'))


def _construct_mapping(loader, node, deep=False):
    loader.flatten_mapping(node)
    seen = {}
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            hash(key)
        except TypeError:
            raise yaml.constructor.ConstructorError('while constructing a mapping', node.start_mark,
                                                    'found a list or mapping used as a key', key_node.start_mark)
        if key in seen:
            raise DuplicateKeyError('while constructing a mapping', node.start_mark,
                                    f'found duplicate key "{key}"', key_node.start_mark)
        seen[key] = True
    return loader.construct_mapping(node, deep=deep)


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def load(text):
    return yaml.load(text, Loader=StrictLoader)  # noqa: S506 - StrictLoader is a SafeLoader


def load_file(path):
    with open(path, encoding='utf-8') as f:
        return load(f.read())


# ---------------------------------------------------------------- writing

class _Dumper(yaml.SafeDumper):
    pass


# quote strings a YAML 1.1 reader would take for something else (yes/no/on/off, dates, numbers)
def _scalar(value):
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float)):
        return repr(value)
    text = yaml.dump(value, Dumper=_Dumper, allow_unicode=True, width=10 ** 6, default_flow_style=True)
    if text.endswith('\n...\n'):
        text = text[:-5]
    text = text.rstrip('\n')
    if isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return value                        # keep dates plain; the loader reads them as strings
    return text


def _flow_list(values):
    return '[' + ', '.join(_scalar(v) for v in values) + ']'


def _is_flat_list(value):
    return isinstance(value, list) and all(not isinstance(v, (dict, list)) for v in value)


def _emit(data, order, indent, out):
    pad = '  ' * indent
    for key in _ordered_keys(data, order):
        value = data[key]
        sub_order = order.get(key, {}) if isinstance(order.get(key), dict) else {}
        if isinstance(value, dict) and not value:
            out.append(f'{pad}{key}: {{}}')             # "key:" alone would read back as null
        elif isinstance(value, dict):
            out.append(f'{pad}{key}:')
            _emit(value, sub_order, indent + 1, out)
        elif isinstance(value, list) and not _is_flat_list(value):
            out.append(f'{pad}{key}:')
            item_order = sub_order.get('[]', {}) if isinstance(sub_order, dict) else {}
            for item in value:
                if not isinstance(item, dict) or not item:
                    # an item that is not a block (malformed files are formatted too; validate reports them)
                    text = _flow_list(item) if isinstance(item, list) else '{}' if item == {} else _scalar(item)
                    out.append(f'{pad}  - {text}')
                    continue
                lines = []
                _emit(item, item_order, 0, lines)
                out.append(f'{pad}  - {lines[0]}')
                out.extend(f'{pad}    {line}' for line in lines[1:])
        elif isinstance(value, list):
            out.append(f'{pad}{key}: {_flow_list(value)}')
        else:
            out.append(f'{pad}{key}: {_scalar(value)}')


def _ordered_keys(data, order):
    known = [k for k in order if k in data and k != '[]']
    return known + sorted(k for k in data if k not in order)


def dump(data, order):
    """Canonical YAML: keys in `order` (a nested dict of key -> sub-order), unknown keys last, sorted."""
    lines = []
    _emit(data, order, 0, lines)
    return '\n'.join(lines) + '\n'
