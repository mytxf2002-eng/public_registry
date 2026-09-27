"""Loading the repository: resource files, translations and health state."""
import json
import os
import re
from dataclasses import dataclass, field

import yaml

from . import vocab as vocab_mod
from . import yamlio

ID_RE = re.compile(r'^[a-z0-9][a-z0-9-]{1,63}$')
ARCHIVE_DIR = '_archive'
LANGUAGES = ('zh-CN',)

# canonical key order of a resource file (nested dicts give the order inside a block)
RESOURCE_ORDER = {
    'id': 0, 'kind': 0, 'name': 0, 'url': 0, 'description': 0, 'domain': 0, 'tags': 0,
    'license': 0, 'license_url': 0,
    'publisher': {'name': 0, 'kind': 0},
    'provenance': {'added': 0, 'origin': 0, 'reviewed': 0, 'sponsored': 0},
    'api': {'auth': 0, 'https': 0, 'cors': 0, 'docs': 0, 'spec': 0},
    'mcp': {'auth': 0, 'transport': 0, 'install': {'[]': {'name': 0, 'url': 0}}},
    'dataset': {'formats': 0, 'access': 0, 'url': 0, 'temporal': {'start': 0, 'end': 0}, 'spatial': 0,
                'update_frequency': 0, 'size': 0},
    'archived': {'date': 0, 'reason': 0},
}
I18N_ORDER = {'id': 0, 'name': 0, 'description': 0, 'group': 0}


@dataclass
class Problem:
    level: str          # "error" or "warning"
    path: str           # repository-relative path, forward slashes
    message: str

    def __str__(self):
        return f'{self.level.upper()}: {self.path}: {self.message}'


@dataclass
class Resource:
    data: dict
    path: str           # repository-relative path, forward slashes
    archived: bool = False

    @property
    def id(self):
        return self.data.get('id')


@dataclass
class Translation:
    data: dict
    path: str
    lang: str


@dataclass
class Repo:
    root: str
    _vocab: object = field(default=None, repr=False)

    @property
    def vocab(self):
        if self._vocab is None:
            self._vocab = vocab_mod.load(self.root)
        return self._vocab

    def abs(self, rel):
        return os.path.join(self.root, *rel.split('/'))

    def rel(self, path):
        return os.path.relpath(path, self.root).replace(os.sep, '/')

    # ------------------------------------------------------------ files

    def data_files(self):
        """Every file below data/, as repository-relative paths, sorted."""
        out = []
        base = os.path.join(self.root, 'data')
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames.sort()
            for name in sorted(filenames):
                out.append(self.rel(os.path.join(dirpath, name)))
        return out

    def i18n_files(self, lang):
        base = os.path.join(self.root, 'i18n', lang)
        if not os.path.isdir(base):
            return []
        out = []
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames.sort()
            out.extend(self.rel(os.path.join(dirpath, n)) for n in sorted(filenames))
        return out

    @staticmethod
    def resource_path(domain, resource_id):
        return f'data/{domain}/{resource_id}.yml'

    @staticmethod
    def archive_path(resource_id):
        return f'data/{ARCHIVE_DIR}/{resource_id}.yml'

    @staticmethod
    def i18n_path(lang, resource_id):
        return f'i18n/{lang}/{resource_id}.yml'

    # ------------------------------------------------------------ loading

    def _load(self, rel, problems):
        try:
            data = yamlio.load_file(self.abs(rel))
        except yaml.YAMLError as e:
            detail = getattr(e, 'problem', None) or (str(e).splitlines()[0] if str(e) else repr(e))
            problems.append(Problem('error', rel, f'invalid YAML: {detail}{_yaml_where(e)}'))
            return None
        except UnicodeDecodeError:
            problems.append(Problem('error', rel, 'file is not UTF-8'))
            return None
        if not isinstance(data, dict):
            problems.append(Problem('error', rel, 'file must contain a mapping of fields'))
            return None
        return data

    def load_resources(self, problems=None):
        """Resources from data/ (active) and data/_archive/ (archived). Layout problems are reported."""
        problems = [] if problems is None else problems
        resources = []
        for rel in self.data_files():
            parts = rel.split('/')
            if len(parts) != 3 or not parts[2].endswith('.yml'):
                hint = ' (use the .yml extension)' if rel.endswith('.yaml') else ''
                problems.append(Problem('error', rel, 'unexpected file: resources live at data/<domain>/<id>.yml '
                                        f'or data/{ARCHIVE_DIR}/<id>.yml{hint}'))
                continue
            data = self._load(rel, problems)
            if data is not None:
                resources.append(Resource(data, rel, archived=parts[1] == ARCHIVE_DIR))
        return resources

    def load_translations(self, lang, problems=None):
        problems = [] if problems is None else problems
        out = []
        for rel in self.i18n_files(lang):
            parts = rel.split('/')
            if len(parts) != 3 or not parts[2].endswith('.yml'):
                problems.append(Problem('error', rel, f'unexpected file: translations live at i18n/{lang}/<id>.yml'))
                continue
            data = self._load(rel, problems)
            if data is not None:
                out.append(Translation(data, rel, lang))
        return out

    def load_health(self):
        path = os.path.join(self.root, 'health', 'status.json')
        if not os.path.exists(path):
            return {'generated': None, 'resources': {}}
        with open(path, encoding='utf-8') as f:
            return json.load(f)

    def save_health(self, health):
        path = os.path.join(self.root, 'health', 'status.json')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        text = json.dumps(health, ensure_ascii=False, indent=1, sort_keys=True) + '\n'
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)

    # ------------------------------------------------------------ writing

    def write_resource(self, data, archived=False):
        rel = self.archive_path(data['id']) if archived else self.resource_path(data['domain'], data['id'])
        write_text(self.abs(rel), yamlio.dump(data, RESOURCE_ORDER))
        return rel

    def write_translation(self, lang, data):
        rel = self.i18n_path(lang, data['id'])
        write_text(self.abs(rel), yamlio.dump(data, I18N_ORDER))
        return rel


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)


def _yaml_where(error):
    mark = getattr(error, 'problem_mark', None)
    return f' (line {mark.line + 1}, column {mark.column + 1})' if mark else ''


def find_root(start=None):
    """The repository root: the nearest parent directory that has vocab/domains.yml."""
    path = os.path.abspath(start or os.getcwd())
    while True:
        if os.path.exists(os.path.join(path, 'vocab', 'domains.yml')):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            raise SystemExit('registry_kit: run this inside the registry repository (vocab/domains.yml not found)')
        path = parent
