#!/usr/bin/env bash
# Purge previously committed secrets from the entire git history.
#
# See task #34. The following paths once contained real credentials and are
# still recoverable from history even though they are no longer tracked:
#
#   deploy/env.production.template   (MiniMax sk-api-*, Langfuse sk-lf-*, JWT, INTERNAL_API_KEY)
#   frontend/.env.local              (NEXT_PUBLIC_INTERNAL_API_KEY)
#   secret_storage/                  (service_keys.json, secrets.json)
#   encryption_keys/                 (encryption_keys.json - AES master key)
#
# Rotating the upstream credentials (Langfuse / MiniMax consoles) is still
# required; history rewriting only removes the *copies*.
#
# Usage:
#   git stash push -u          # rewrite requires a clean worktree
#   ./scripts/purge_git_secrets.sh
#   git push --force-with-lease --all
#   git push --force-with-lease --tags
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ -n "$(git status --porcelain)" ]; then
  echo "ERROR: worktree is dirty. Commit or stash your changes first:" >&2
  echo "       git stash push -u" >&2
  exit 1
fi

# Safety net: tag every current ref so the rewrite is reversible locally.
BACKUP_TAG="pre-secret-purge-$(date +%Y%m%d%H%M%S)"
git tag "$BACKUP_TAG"
echo "Backup tag created: $BACKUP_TAG"

if ! command -v git-filter-repo >/dev/null 2>&1; then
  echo "git-filter-repo not found. Install it with:"
  echo "  pip install git-filter-repo      # or: brew install git-filter-repo"
  exit 1
fi

PATHS_FILE="$(mktemp)"
cat > "$PATHS_FILE" <<'PATHS'
deploy/env.production.template
frontend/.env.local
secret_storage/
encryption_keys/
PATHS

echo "Rewriting history; removing:"
cat "$PATHS_FILE"

git filter-repo --force --invert-paths --paths-from-file "$PATHS_FILE"
rm -f "$PATHS_FILE"

echo
echo "Verifying the blobs are gone from history…"
for path in deploy/env.production.template frontend/.env.local secret_storage encryption_keys; do
  if git log --all --oneline -- "$path" | grep -q .; then
    echo "  STILL PRESENT: $path"
    exit 1
  else
    echo "  clean: $path"
  fi
done

echo
echo "Local history is purged. To publish the rewrite:"
echo "  git push --force-with-lease --all && git push --force-with-lease --tags"
echo "Rollback: git reset --hard $BACKUP_TAG"
