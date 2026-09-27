# tools/

Maintenance helpers. Day-to-day work uses `python -m registry_kit`.

| Script | What it does |
|---|---|
| `github_setup.sh` | one-time GitHub configuration: ruleset, Pages, Actions permissions, security features, labels, `health-data` branch. Re-run it after changing `.github/rulesets/main.json` |
| `apply_licence_checks.py` | applies licence checks made on the resources' own sites: a JSON list of `{id, license, license_url, evidence}` records; `unknown` records change nothing |

The one-off converters that built the initial data in September 2026 are not part of the repository; their
method and totals are described in `docs/provenance.zh-CN.md`.
