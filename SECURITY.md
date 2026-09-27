# Security

## Reporting

Report a vulnerability in the engine or the workflows through GitHub's private vulnerability reporting
(Security tab, "Report a vulnerability"), not in a public issue. The maintainer answers within seven days.

A resource that has been taken over (its domain now serves malware, phishing, gambling or unrelated
content) is not a vulnerability of this project: open a normal issue or pull request that archives it.

## How the pipelines are protected

- Resource files are parsed with a safe YAML loader that also rejects duplicate keys; no code in a pull
  request is executed with credentials. The PR gate runs with read-only permissions and no secrets; the
  comment is posted by a separate workflow that never checks out pull request code.
- Jobs that hold a write token never check out or run anything from a pull request. The Pages deployment
  receives the build artifact, and the link check and archive pull requests work on `main`, whose content
  was reviewed before it was merged. The comment job reads the report a pull request's checks uploaded as
  plain text, and posts it only on the pull request whose head is the commit that was checked.
- Tokens are short-lived: OIDC for Pages and the workflows' built-in token for everything else. There
  are no long-lived secrets and no keys in the repository.
- Every action is pinned to a commit SHA and every Python dependency to a version in requirements.txt.
  Dependabot proposes updates for both monthly, and raises an alert when a pinned Python dependency has a
  known vulnerability (it cannot do so for actions pinned to a SHA, which is why they are updated
  monthly). An update is merged only after the Linux and Windows tests pass.
- The default-branch ruleset (`.github/rulesets/main.json`) applies to the owner too: every change, the
  maintainer's own included, goes through a pull request and the required checks.
