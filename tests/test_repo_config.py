"""Consistency of the GitHub configuration kept in the repository."""
import glob
import json
import os
import re
import subprocess
import unittest

import yaml

from tests.helpers import ROOT

WORKFLOWS = os.path.join(ROOT, '.github', 'workflows')


def load_workflow(name):
    with open(os.path.join(WORKFLOWS, name), encoding='utf-8') as f:
        return yaml.safe_load(f)


def tracked_files():
    """Files git would commit: tracked ones plus untracked ones that are not ignored."""
    try:
        out = subprocess.run(['git', '-C', ROOT, 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
                             capture_output=True, check=True, timeout=60).stdout
        return sorted({p for p in out.decode('utf-8').split('\0') if p and os.path.isfile(os.path.join(ROOT, p))})
    except (OSError, subprocess.SubprocessError):          # not a git checkout: every file except build outputs
        out = []
        for dirpath, dirnames, filenames in os.walk(ROOT):
            dirnames[:] = [d for d in dirnames if d not in ('.git', 'build', '__pycache__', '.venv', 'venv')]
            out += [os.path.relpath(os.path.join(dirpath, n), ROOT) for n in filenames]
        return sorted(out)


class RepoConfigTest(unittest.TestCase):
    def test_ruleset_requires_the_checks_the_gate_produces(self):
        with open(os.path.join(ROOT, '.github', 'rulesets', 'main.json'), encoding='utf-8') as f:
            ruleset = json.load(f)
        rule = next(r for r in ruleset['rules'] if r['type'] == 'required_status_checks')
        required = {c['context'] for c in rule['parameters']['required_status_checks']}
        jobs = load_workflow('pr-gate.yml')['jobs']
        self.assertIn('validate', jobs)
        produced = {'validate'} | {f'tests ({os_name})' for os_name in jobs['tests']['strategy']['matrix']['os']}
        self.assertEqual(required, produced)

    def test_ruleset_matches_the_maintenance_mode(self):
        """One maintainer: no CODEOWNERS and 0 approvals (authors cannot approve their own pull requests).
        Several maintainers: a CODEOWNERS file, at least one approval and code-owner review."""
        with open(os.path.join(ROOT, '.github', 'rulesets', 'main.json'), encoding='utf-8') as f:
            ruleset = json.load(f)
        pr = next(r for r in ruleset['rules'] if r['type'] == 'pull_request')['parameters']
        if os.path.exists(os.path.join(ROOT, '.github', 'CODEOWNERS')):
            self.assertGreaterEqual(pr['required_approving_review_count'], 1)
            self.assertTrue(pr['require_code_owner_review'])
        else:
            self.assertEqual(pr['required_approving_review_count'], 0)
            self.assertFalse(pr['require_code_owner_review'])
        self.assertEqual(ruleset['bypass_actors'], [])

    def test_actions_are_pinned_to_commits(self):
        for path in glob.glob(os.path.join(WORKFLOWS, '*.yml')):
            with open(path, encoding='utf-8') as f:
                for line in f:
                    m = re.search(r'uses:\s*(\S+)', line)
                    if m:
                        self.assertRegex(m.group(1), r'^[\w.-]+/[\w./-]+@[0-9a-f]{40}$', f'{os.path.basename(path)}: {line.strip()}')

    def test_pipes_cannot_hide_failures(self):
        # without an explicit `shell: bash` a run step uses `bash -e` without pipefail, and `cmd | tee file`
        # reports tee's success even when cmd failed
        for path in glob.glob(os.path.join(WORKFLOWS, '*.yml')):
            with open(path, encoding='utf-8') as f:
                text = f.read()
            if re.search(r'\|\s*tee\b', text):
                data = yaml.safe_load(text)
                self.assertEqual((data.get('defaults') or {}).get('run', {}).get('shell'), 'bash',
                                 os.path.basename(path))

    def test_workflows_default_to_read_only(self):
        # write access is granted per job, where it is needed; the workflow-wide default only reads
        for path in glob.glob(os.path.join(WORKFLOWS, '*.yml')):
            with open(path, encoding='utf-8') as f:
                data = yaml.safe_load(f)
            permissions = data.get('permissions')
            self.assertIsInstance(permissions, dict, os.path.basename(path))
            self.assertTrue(set(permissions.values()) <= {'read', 'none'}, os.path.basename(path))

    def test_no_local_paths_in_the_repository(self):
        """Nothing from a maintainer's machine may be committed: local paths, user folders, scratch files."""
        forbidden = [
            re.compile(r'(?<!\w)[A-Za-z]:\\[A-Za-z_]'),          # Windows absolute paths
            re.compile(r'(?<![\w.:/])/[a-z]/[A-Za-z_]'),         # the same in Git Bash form (/c/...)
            re.compile(r'AppData[\\/]|scratchpad[\\/]', re.I),
        ]
        here = os.path.abspath(__file__)
        hits = []
        for rel in tracked_files():
            path = os.path.join(ROOT, rel)
            if os.path.abspath(path) == here:
                continue
            try:
                with open(path, encoding='utf-8') as f:
                    text = f.read()
            except (UnicodeDecodeError, OSError):
                continue
            for pattern in forbidden:
                m = pattern.search(text)
                if m:
                    hits.append(f'{rel}: {m.group(0)}')
        self.assertEqual(hits, [])

    def test_archive_pull_requests_get_checked(self):
        # checks started with workflow_dispatch do not count for a ruleset; a pull request opened with the
        # built-in token gets pull_request runs once the maintainer approves them, so the body says how
        self.assertEqual(set(load_workflow('pr-gate.yml')[True]), {'pull_request'})   # YAML 1.1 reads "on" as True
        with open(os.path.join(WORKFLOWS, 'health.yml'), encoding='utf-8') as f:
            text = f.read()
        self.assertNotIn('gh workflow run', text)
        self.assertIn('Approve workflows', text)
        self.assertIn('gh pr list --state open --head', text)       # one archive pull request at a time


if __name__ == '__main__':
    unittest.main()
