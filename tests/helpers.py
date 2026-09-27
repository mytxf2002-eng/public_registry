"""Temporary registries for tests: the real licence and format vocabularies, a small domain list."""
import os
import shutil
import tempfile

from registry_kit import yamlio
from registry_kit.repo import Repo, write_text

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOMAINS = [
    {'id': 'alpha', 'name': 'Alpha', 'name_zh': '甲', 'scope': 'First test domain.', 'scope_zh': '第一个测试领域。'},
    {'id': 'beta', 'name': 'Beta', 'name_zh': '乙', 'scope': 'Second test domain.', 'scope_zh': '第二个测试领域。'},
]


def resource(rid, domain='alpha', **fields):
    """A valid API resource; keyword arguments override or add fields."""
    data = {
        'id': rid, 'kind': ['api'], 'name': rid.replace('-', ' ').title(), 'url': f'https://{rid}.example.net/docs',
        'description': f'Test resource {rid} with enough words to be valid', 'domain': domain, 'license': 'unknown',
        'provenance': {'added': '2026-09-27', 'origin': 'contribution'},
        'api': {'auth': 'none', 'https': True, 'cors': 'unknown'},
    }
    data.update(fields)
    return data


class TempRepo:
    """A registry in a temporary directory with 5 valid resources in each test domain."""

    def __init__(self, per_domain=5):
        self.root = tempfile.mkdtemp(prefix='registry-test-')
        os.makedirs(os.path.join(self.root, 'vocab'))
        for name in ('licenses.yml', 'formats.yml'):
            shutil.copy(os.path.join(ROOT, 'vocab', name), os.path.join(self.root, 'vocab', name))
        write_text(os.path.join(self.root, 'vocab', 'domains.yml'),
                   '\n'.join(yamlio.dump(d, {'id': 0, 'name': 0, 'name_zh': 0, 'scope': 0, 'scope_zh': 0})
                             .replace('\n', '\n  ').rstrip().join(['- ', '\n']) for d in DOMAINS))
        os.makedirs(os.path.join(self.root, 'data', '_archive'))
        self.repo = Repo(self.root)
        for dom in ('alpha', 'beta'):
            for i in range(per_domain):
                self.repo.write_resource(resource(f'{dom}-base-{i}', dom))

    def write(self, data, archived=False):
        return self.repo.write_resource(data, archived=archived)

    def write_raw(self, rel, text):
        write_text(self.repo.abs(rel), text)

    def cleanup(self):
        shutil.rmtree(self.root, ignore_errors=True)
