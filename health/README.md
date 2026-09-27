# health/

`status.json` holds the link state of every resource: the last result, the date of the last success,
the number of failures in a row and the resulting state (`verified`, `suspicious`, `unconfirmed`,
`failing`). It is written by `python -m registry_kit health` and kept on the `health-data` branch, one
commit per daily run, so the history of main is not filled with check results. It is not tracked on main.

`acknowledged.yml` lists what the maintainer has checked by hand and accepted for a resource, with the
reason: content signals that are harmless there, and check results a site gives only to automated
clients (these count as restricted, which is working).
