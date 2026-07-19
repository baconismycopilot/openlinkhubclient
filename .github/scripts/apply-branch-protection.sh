#!/usr/bin/env bash
# Applies this repo's "basic" branch protection to a branch via the GitHub API.
#
# Rules applied: block force-pushes and branch deletion. No required reviews
# or status checks — this is a solo-maintained repo, so the goal is just to
# prevent accidental history rewrites/deletion, not to gate every push behind
# a PR. Re-run any time to reassert these settings (e.g. after they're
# changed by mistake in the UI); idempotent.
#
# Requires: gh (authenticated with a token that has admin rights on the repo)
#
# Usage:
#   .github/scripts/apply-branch-protection.sh <owner>/<repo> [branch]

set -euo pipefail

REPO="${1:?Usage: $0 <owner>/<repo> [branch]}"
BRANCH="${2:-main}"

gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  "repos/${REPO}/branches/${BRANCH}/protection" \
  --input - <<'EOF'
{
  "required_status_checks": null,
  "enforce_admins": null,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF

echo "Branch protection applied to ${REPO}@${BRANCH}."
