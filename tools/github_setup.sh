#!/usr/bin/env bash
# One-time GitHub configuration for a personally maintained registry.
#
#   usage: bash tools/github_setup.sh OWNER/REPO [DOMAIN]
#
# Run it from the repository root after the first push, with the GitHub CLI logged in as the owner
# (gh auth login). Every step can be re-run; a step that fails prints where to set it by hand.
#
# DOMAIN (optional) serves the site from a custom domain such as reg.example.com instead of
# OWNER.github.io/REPO. Point the domain at GitHub first: for a subdomain a CNAME record to
# OWNER.github.io, for an apex domain the A and AAAA records of GitHub Pages. Verifying the domain for
# your account (Settings > Pages > Add a domain) keeps anyone else from using it. GitHub then issues
# the certificate, usually within minutes; re-run the script if HTTPS could not be enforced yet.
set -uo pipefail

repo="${1:?usage: bash tools/github_setup.sh OWNER/REPO [DOMAIN]}"
domain="${2:-}"
owner="$(printf '%s' "${repo%%/*}" | tr '[:upper:]' '[:lower:]')"
step() { printf '\n== %s\n' "$1"; }
manual() { printf '   could not set this automatically; set it by hand: %s\n' "$1"; }

step "Merging: squash only, delete branches after merge"
gh api -X PATCH "repos/$repo" -F allow_squash_merge=true -F allow_merge_commit=false \
  -F allow_rebase_merge=false -F delete_branch_on_merge=true >/dev/null \
  || manual "Settings > General > Pull Requests"

step "Actions: read-only token by default; workflows may open pull requests (archive pull requests)"
gh api -X PUT "repos/$repo/actions/permissions/workflow" -f default_workflow_permissions=read \
  -F can_approve_pull_request_reviews=true \
  || manual "Settings > Actions > General > Workflow permissions"

step "Workflows on pull requests from first-time contributors wait for the owner's approval"
gh api -X PUT "repos/$repo/actions/permissions/fork-pr-contributor-approval" \
  -f approval_policy=first_time_contributors \
  || manual "Settings > Actions > General > Approval for running fork pull request workflows"

step "GitHub Pages, deployed by the publish workflow"
gh api -X POST "repos/$repo/pages" -f build_type=workflow >/dev/null 2>&1 \
  || gh api -X PUT "repos/$repo/pages" -f build_type=workflow \
  || manual "Settings > Pages > Source: GitHub Actions"

if [ -n "$domain" ]; then
  step "Custom domain $domain, served over HTTPS"
  current="$(gh api "repos/$repo/pages" --jq '.cname // ""' 2>/dev/null)"
  if [ "$current" = "$domain" ]; then
    echo "   the site already uses $domain"
  else
    gh api -X PUT "repos/$repo/pages" -f cname="$domain" \
      || manual "Settings > Pages > Custom domain: $domain"
  fi
  if gh api -X PUT "repos/$repo/pages" -F https_enforced=true >/dev/null 2>&1; then
    echo "   HTTPS is enforced"
  else
    echo "   the certificate for $domain is not ready yet (GitHub issues it once the DNS records point"
    echo "   to GitHub, usually within minutes); re-run this script, or tick Settings > Pages > Enforce HTTPS"
  fi
fi

step "Ruleset for the default branch (.github/rulesets/main.json; re-run after changing that file)"
ruleset_id="$(gh api "repos/$repo/rulesets" --jq '.[] | select(.name == "main") | .id' 2>/dev/null)"
if [ -n "$ruleset_id" ]; then
  gh api -X PUT "repos/$repo/rulesets/$ruleset_id" --input .github/rulesets/main.json >/dev/null \
    && echo "   updated the existing ruleset" \
    || manual "Settings > Rules > Rulesets > main"
else
  gh api -X POST "repos/$repo/rulesets" --input .github/rulesets/main.json >/dev/null \
    || manual "Settings > Rules > Rulesets > New ruleset > Import (.github/rulesets/main.json)"
fi

step "Security: Dependabot alerts and security updates, private vulnerability reporting"
gh api -X PUT "repos/$repo/vulnerability-alerts" || manual "Settings > Code security"
gh api -X PUT "repos/$repo/automated-security-fixes" || manual "Settings > Code security"
gh api -X PUT "repos/$repo/private-vulnerability-reporting" || manual "Settings > Code security"

step "Labels"
gh label create link-health --repo "$repo" --color B60205 --description "Daily link check" --force
gh label create suggestion --repo "$repo" --color 0E8A16 --description "Suggested resource" --force

step "Seed the health-data branch with the current link state"
if [ ! -f health/status.json ]; then
  echo "   health/status.json not found; the first scheduled check will create the branch"
elif git ls-remote --exit-code "https://github.com/$repo.git" health-data >/dev/null 2>&1; then
  echo "   the health-data branch already exists"
else
  # the commit uses this repository's git identity (it may be set for this repository only), and the
  # push authenticates through the GitHub CLI for this one command; no git setting is changed
  name="$(git config user.name)"; email="$(git config user.email)"
  tmp="$(mktemp -d)"
  cp health/status.json "$tmp/status.json"
  (cd "$tmp" && git init -q -b health-data && git add status.json \
    && git -c user.name="$name" -c user.email="$email" commit -q -m "Seed link state" \
    && git -c credential.helper= -c 'credential.helper=!gh auth git-credential' \
         push -q "https://github.com/$repo.git" health-data) \
    || manual "push health/status.json as status.json to a new branch named health-data"
  rm -rf "$tmp"
fi

if [ -n "$domain" ]; then site="https://$domain/"; else site="https://$owner.github.io/${repo#*/}/"; fi
printf '\nDone. Next: run "Link health" once (Actions > Link health > Run workflow); "Publish" follows it\n'
printf 'and deploys the site to %s\n' "$site"
