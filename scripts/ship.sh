#!/usr/bin/env bash
# scripts/ship.sh
# Safe end-to-end delivery workflow: Branch/Commit -> PR -> Human Checkpoint -> Squash Merge -> Coolify Deploy Verification.
# Usage: ./scripts/ship.sh [commit_message]

set -euo pipefail

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo "==> Starting deployment workflow on branch: $CURRENT_BRANCH"

# 1. Enforce no direct main push
if [ "$CURRENT_BRANCH" = "main" ]; then
  echo "ERROR: You are on 'main'. Direct pushes to main are prohibited."
  echo "Please create a feature or fix branch first: git checkout -b fix/<name> or feat/<name>"
  exit 1
fi

# 2. Run typecheck
echo "==> Running svelte-check..."
pnpm svelte-check --tsconfig ./tsconfig.json --threshold error

# 3. Stage & Commit if needed
COMMIT_MSG="${1:-}"
if [ -n "$(git status --porcelain)" ]; then
  if [ -z "$COMMIT_MSG" ]; then
    echo "ERROR: Working tree has uncommitted changes. Provide a commit message: ./scripts/ship.sh \"fix: your message\""
    exit 1
  fi
  echo "==> Staging and committing changes..."
  git add -A
  git commit -m "$COMMIT_MSG"
fi

# 4. Push branch
echo "==> Pushing branch to origin..."
git push -u origin "$CURRENT_BRANCH"

# 5. Check or create PR
PR_URL=$(gh pr view --json url -q .url 2>/dev/null || true)
if [ -z "$PR_URL" ]; then
  echo "==> Creating Pull Request..."
  PR_TITLE="$COMMIT_MSG"
  if [ -z "$PR_TITLE" ]; then
    PR_TITLE=$(git log -1 --pretty=%B)
  fi
  PR_URL=$(gh pr create --title "$PR_TITLE" --body "Automated PR created via scripts/ship.sh" --base main)
  echo "==> PR created: $PR_URL"
else
  echo "==> Existing PR found: $PR_URL"
fi

PR_NUMBER=$(gh pr view --json number -q .number)

# 6. Human In The Loop (HITL) Checkpoint
echo ""
echo "============================================================="
echo " [HUMAN IN THE LOOP CHECKPOINT]"
echo " PR #$PR_NUMBER is ready: $PR_URL"
echo " Review changes before merging to production."
echo "============================================================="
echo ""

read -r -p "Squash merge PR #$PR_NUMBER to main and trigger Coolify deployment? [y/N]: " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
  echo "==> Deployment halted by user. You can resume later by merging PR #$PR_NUMBER."
  exit 0
fi

# 7. Squash merge to main
echo "==> Squash merging PR #$PR_NUMBER to main..."
gh pr merge "$PR_NUMBER" --squash --delete-branch

# 8. Sync local main
echo "==> Syncing local main branch..."
git checkout main
git pull origin main

MERGE_SHA=$(git rev-parse HEAD)
echo "==> Merged commit on main: $MERGE_SHA"

# 9. Monitor Coolify deployment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$SCRIPT_DIR/monitor-deploy.sh" "$MERGE_SHA"
