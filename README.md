# Public Registry

One catalogue for public **APIs**, downloadable **datasets** and **MCP servers**. Every resource is a
YAML file checked against a JSON Schema, records its access route and, where known, its own licence, and
gets its link checked every day. The lists, the site, the exports and the read-only API are all generated
from `data/`; none of them is edited by hand.

[中文说明](README.zh-CN.md)

| As of 2026-09-27 | |
|---|---|
| Resources | 2,352 in 45 domains (1,907 APIs, 680 datasets, 3 MCP servers; 238 are both an API and a dataset), plus 195 archived |
| Links working | 99.4% of those checked (15 not yet seen working, none failing) |
| Licence known | 74.4% of datasets, 9.4% of APIs (the public-apis list never recorded licences) |
| Chinese descriptions | 100% |

## Browse

- **Site**: <https://mytxf2002-eng.github.io/public_registry/>. Search and filter by domain, kind,
  licence, access, authentication and link status, with a quality dashboard. To build it locally, run
  `python -m registry_kit build` and open `build/site/index.html`.
- **Downloads**: `export/resources.csv`, `export/resources.json` and `export/registry.sqlite` next to the site.
- **Read-only API**: `api/v1/index.json`, `api/v1/resources/{id}.json`, `api/v1/domains/{domain}.json`,
  `api/v1/kinds/{kind}.json` (static JSON, no key, no rate limit).
- **Lists as Markdown**: `build/docs/en/` and `build/docs/zh-CN/`, one page per domain.

## How the repository is laid out

| Path | What it holds | Who changes it |
|---|---|---|
| `data/<domain>/<id>.yml` | one resource per file; the file name is its permanent id | contributors, through pull requests |
| `data/_archive/<id>.yml` | resources that are gone, with the date and reason; their URLs stay reserved | the link-health bot (pull request) or the maintainer |
| `i18n/zh-CN/<id>.yml` | Chinese name, description and group of a resource | translators |
| `vocab/` | domains, licences (SPDX ids plus six `LicenseRef-` values) and formats | the maintainer |
| `schema/` | JSON Schemas generated from `vocab/` (`registry_kit schema`) | nobody by hand |
| `registry_kit/` | the engine: validate, format, health, render, export, site | the maintainer |
| `health/` | link signals the maintainer accepted by hand; the daily state lives on the `health-data` branch | the maintainer (the link-health job writes only to `health-data`) |
| `tools/` | the one-time GitHub setup script and the licence-check helper | the maintainer |
| `docs/` | where the data came from (`provenance.zh-CN.md`), the maintainer's handbook, a resource template | the maintainer |

A resource file (`data/economics/world-bank.yml`, an API that also offers bulk downloads):

```yaml
id: world-bank
kind: [api, dataset]
name: World Bank
url: https://datahelpdesk.worldbank.org/knowledgebase/topics/125589
description: Development indicators such as GDP, population and poverty for all countries, many since 1960
domain: economics
tags: [development-indicators, wdi, poverty, time-series, country-statistics]
license: CC-BY-4.0
license_url: https://datacatalog.worldbank.org/public-licenses
publisher:
  name: World Bank
  kind: intergovernmental
provenance:
  added: 2017-02-28
  origin: public-apis
  reviewed: 2026-09-27
api:
  auth: none
  https: true
  cors: 'no'
dataset:
  formats: [csv, xml, xls]
  access: public
  temporal:
    start: '1960'
    end: null
  spatial: [global]
  update_frequency: irregular
```

Nothing about link status is ever written into a resource file. Rules for every field are in
[CONTRIBUTING.md](CONTRIBUTING.md); the machine-readable contract is `schema/resource.schema.json`.

## registry_kit

```
python -m pip install -r requirements.txt
python -m registry_kit validate            # every rule, every file, all problems at once
python -m registry_kit format              # canonical layout, licence and format aliases, tracking parameters
python -m registry_kit health              # check links, update health/status.json (3 failures over 7 days = failing)
python -m registry_kit build               # site, exports, static API, Markdown lists
python -m registry_kit stats               # counts and completeness
python -m unittest discover -s tests -t .  # engine tests plus regression tests on the real data
```

## How changes get in

1. **Pull request gate** (`pr-gate.yml`): schema, canonical form, uniqueness of the normalised URL across
   all resources including archived ones, controlled values, placeholder text, and a live check of new
   links. Files the pull request adds must also name a licence with the page that states it, and a
   publisher. Every check runs even when another fails, and `pr-comment.yml` posts one comment listing
   everything. Tests run on Linux and Windows.
2. **Merge gate** (`.github/rulesets/main.json`): every change reaches `main` through a pull request, the
   maintainer's own included, and only after `validate` and the Linux and Windows `tests` pass on a branch
   that is up to date with `main`, so two pull requests cannot add the same link. A pull request with
   commits that cannot be attributed to a GitHub account also needs one approval. No direct pushes, no
   force pushes, squash merges only. Only the maintainer can merge.
3. **Link health** (`health.yml`, daily): at most two concurrent requests per host, retries for timeouts
   and 5xx, 401/403/429 count as working. A resource becomes `failing` only after 3 failed checks in a row
   spanning at least 7 days; cross-site redirects and parked or gambling pages make it `suspicious`.
   30 days after its first failed check, the job opens a pull request that moves it to `data/_archive/`
   (one such pull request at a time). GitHub holds the checks of a pull request opened by a workflow until
   the maintainer approves them on the pull request page.
4. **Publish** (`publish.yml`): one concurrency group, so only the newest run publishes; the build job
   validates the data and can only read; Pages is deployed with OIDC, and the job then waits until the
   read-only API reports the commit it was built from.

## Licences

Code: [MIT](LICENSE). Catalogue data: [CC BY 4.0](LICENSE-DATA). The licence field of each resource
describes that resource, not this catalogue. Of the resources gathered in September 2026, 1,739 were
imported from the public-apis list (MIT) and 613 were researched independently; see [NOTICE](NOTICE) and
[docs/provenance.zh-CN.md](docs/provenance.zh-CN.md).

## Maintenance

Public Registry is maintained by one person. Anyone can contribute through a pull request: the checks
answer within minutes (for a first contribution, once the maintainer has approved the run), the
maintainer usually within a few days. The rules apply to the maintainer too,
so every change is checked and recorded the same way. Everything the registry needs is in this
repository (data, engine, workflows, and the link-state history on the `health-data` branch), so the
project can be forked and continued at any time. Co-maintainers can be added later with a
`.github/CODEOWNERS` file and a higher approval count in the ruleset. The maintainer's routine is
described in [docs/maintaining.zh-CN.md](docs/maintaining.zh-CN.md).

## Setting up the GitHub side

After the first push, run once with the GitHub CLI logged in as the owner:

```
bash tools/github_setup.sh OWNER/REPO
```

It sets squash-only merging, the default-branch ruleset from `.github/rulesets/main.json`, Pages deployed
by Actions, permission for workflows to open the archive pull requests, approval before first-time
contributors' workflows run, Dependabot alerts and security updates, private vulnerability reporting, the
labels, and seeds the `health-data` branch. Each step prints where to set it by hand if the API call fails.
