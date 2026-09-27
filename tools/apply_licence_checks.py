# -*- coding: utf-8 -*-
"""Apply licence verifications to resource files.

usage: python tools/apply_licence_checks.py CHECKS.json [CHECKS.json ...]

Each check is {id, license, license_url, evidence, notes?} written by a reviewer who read the licence on the
resource's own site. A check with license "unknown" changes nothing. Otherwise the resource gets the
checked licence and its source link, and the change is printed so it can be reviewed in the diff.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from registry_kit import urls, yamlio  # noqa: E402
from registry_kit.repo import RESOURCE_ORDER, Repo, find_root, write_text  # noqa: E402


def main():
    repo = Repo(find_root())
    paths = {r.data['id']: r.path for r in repo.load_resources() if not r.archived}
    changed = unchanged = unknown = 0
    for path in sys.argv[1:]:
        with open(path, encoding='utf-8') as f:
            checks = json.load(f)
        for check in checks:
            rid, lic = check['id'], check['license']
            if rid not in paths:
                print(f'{rid}: no listed resource has this id; skipped')
                continue
            if lic == 'unknown':
                unknown += 1
                continue
            data = yamlio.load_file(repo.abs(paths[rid]))
            new_url = urls.strip_tracking(check['license_url'])
            if data.get('license') == lic and data.get('license_url'):
                unchanged += 1          # confirmed; keep the source link already recorded
                continue
            print(f'{rid}: {data.get("license")} -> {lic}  ({new_url})')
            data['license'] = lic
            data['license_url'] = new_url
            write_text(repo.abs(paths[rid]), yamlio.dump(data, RESOURCE_ORDER))
            changed += 1
    print(f'{changed} changed, {unchanged} already right, {unknown} still unknown')


if __name__ == '__main__':
    main()
