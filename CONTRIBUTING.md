# Contributing

Thank you for adding to the registry. One resource per pull request, please. The checks comment on your
pull request within a few minutes and list every problem at once (on your first pull request they start
once the maintainer has approved the run). The registry is maintained by one person, who reviews every
pull request, usually within a few days.

## Add a resource

1. Check that it is not already listed: search the site, or run `python -m registry_kit validate` after
   adding your file; it reports any resource with the same URL, including archived ones.
2. Copy `docs/resource-template.yml` to `data/<domain>/<id>.yml`, fill in every `<...>` slot and delete
   the blocks that do not apply.
3. Run `python -m registry_kit format` and `python -m registry_kit validate`, then open the pull request.

A Chinese translation is welcome but optional: add `i18n/zh-CN/<id>.yml` with `id` and `description`.
The maintainer may add one later.

## What belongs here

A resource is included when **all** of these hold:

- It provides data: downloadable files, a data portal or repository, or a documented API or MCP server.
- It can be used today, free of charge: open download, a free account, a free application process, or a
  free tier that gives real access. Paid-only resources and "contact sales" pages are not listed.
- The URL is the resource's own page (the publisher, the project, or a recognised repository record),
  without tracking parameters.

It is not included when it is a blog post, an article, a list of links, a marketing page, a thin wrapper
around another API that is already listed, a small table whose main purpose is to promote a site, data
whose licence claim is contradicted by its own sources, or personal data collected without consent.

## Fields

| Field | Rule |
|---|---|
| `id` | lowercase letters, digits and hyphens; equal to the file name; never changes |
| `kind` | one or more of `api`, `dataset`, `mcp-server`; a resource with both an API and downloads is one file with both kinds |
| `name` | the resource's own name, at most 80 characters, not ending in " API"; unique within the domain |
| `url` | `https://` where the site supports it; unique across the registry after removing the scheme, `www.`, a trailing slash and tracking parameters |
| `description` | English, one plain sentence of 10 to 200 characters: what it is and its scope. Capital first letter, no final period, no URLs, no marketing words |
| `domain` | one id from `vocab/domains.yml`, chosen by the subject; read the domain's scope. Cross-cutting topics go in `tags` |
| `tags` | up to 8 lowercase tags such as `air-quality`; not the domain id |
| `license` | an id from `vocab/licenses.yml` (see below), or `unknown`. New resources need a known licence |
| `license_url` | the page where the licence or terms are stated; new resources need it, and so does every resource with `LicenseRef-Open-Government`, `LicenseRef-Custom-Open` or `LicenseRef-Research-Only` |
| `publisher` | `{name, kind}`; the organisation or person that publishes the data, not the hosting platform. New resources need it |
| `provenance` | `added` (a real date, not in the future), `origin` (`contribution` for new resources), optional `reviewed` (date of the last review, not before `added`) and `sponsored` |
| `api` | when kind has `api`: `auth` (`none`, `api-key`, `oauth`, `user-agent`, `x-mashape-key`), `https`, `cors` (`yes`, `no`, `unknown`), optional `docs` and `spec` |
| `dataset` | when kind has `dataset`: `formats` (ids from `vocab/formats.yml`), `access` (`public`, `registration`, `application`, `paid-tier`), optional `url`, `temporal`, `spatial`, `update_frequency`, `size` |
| `mcp` | when kind has `mcp-server`: `auth`, `transport` (`stdio`, `http`, `sse`), optional `install` links |

`cors: yes` means an `Access-Control-Allow-Origin` header was seen on an actual API response.

### Licences

Use the SPDX id when the publisher names a standard licence (`CC-BY-4.0`, `CC0-1.0`, `ODbL-1.0`,
`OGL-UK-3.0`, `etalab-2.0`...). The version matters: a Creative Commons deed without a version takes the
version the site links to. For everything else:

| Value | When |
|---|---|
| `LicenseRef-US-Government-Work` | a work of the US federal government with no other statement |
| `LicenseRef-Public-Domain` | the publisher declares it public domain without naming an instrument |
| `LicenseRef-Open-Government` | a national or regional open-government licence without an SPDX id |
| `LicenseRef-Custom-Open` | the publisher's own terms allow free reuse, including commercial reuse |
| `LicenseRef-Research-Only` | free for research, academic or non-commercial use under the publisher's own agreement |
| `LicenseRef-Provider-Terms` | use is governed by terms of service, without an open licence (typical for company APIs) |
| `unknown` | no statement found on the resource's site |

Never guess a licence from the kind of publisher.

### Commercial and sponsored resources

Company resources are welcome when they meet the rules above. If you work for the publisher, say so in
the pull request and keep the description factual. Resources of a sponsor of this project would carry
`provenance.sponsored: true` and be marked as such everywhere they are shown; the project has no sponsors.

## Corrections, moves and removals

- Fix a field: edit the file. Moving a resource to another domain moves the file; the id stays.
- A resource is gone: run `python -m registry_kit archive <id> --reason "..."`. The file moves to
  `data/_archive/` and its URL stays reserved. `python -m registry_kit restore <id>` brings it back.
- The link check marks resources `failing` after 3 failed checks in a row spanning at least 7 days, and
  opens an archive pull request 30 days after the first failed check. If the resource moved, update its
  `url` instead.
- A harmless signal that keeps a resource `suspicious` (a planned redirect to a sister site) goes into
  `health/acknowledged.yml` with the reason.

## Engine, schema and vocabularies

Changes to `registry_kit/`, `schema/`, `vocab/` or `.github/` affect every resource. For anything larger
than a fix, open an issue first so the approach is agreed before you write it. After changing `vocab/`,
run `python -m registry_kit schema`. Run the tests with
`python -m unittest discover -s tests -t .`; they include regression tests on the real data.

## Code of conduct

This project follows the [code of conduct](CODE_OF_CONDUCT.md).
