#!/usr/bin/env sh
set -eu
test -n "${1:-}" || { echo "usage: scripts/rollback.sh <commit-sha>" >&2; exit 2; }
gh workflow run deploy.yml --ref main -f "ref=$1"
echo "Rollback deployment requested for $1"
