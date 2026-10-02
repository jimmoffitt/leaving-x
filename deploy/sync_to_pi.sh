#!/usr/bin/env bash
# Deploy leaving-x from the Mac to the Pi. Run on the Mac, any time.
#
#   1. Pull the Pi's posted_records.json back into backups/ (the Pi is the
#      source of truth for what's been posted -- this file is never pushed).
#   2. Push code with git, straight from here to a repo on the Pi over ssh
#      (no GitHub involved; the Pi's checkout updates in place). The first run
#      creates that repo. Refuses to run with uncommitted changes, so the Pi
#      only ever runs committed code.
#   3. Copy .env.local and the Twitter archive (tweets.js + tweets_media/,
#      ~400MB the first time, nothing after that) -- neither is in git.
#   4. With --install: create the venv, install packages, and install and
#      enable the systemd units. Re-run with --install after changing
#      deploy/requirements-pi.txt or the unit files.
#
# Code changes need no restart: the "On this day" timer starts fresh every
# 5 minutes. A running backfill keeps its old code until restarted.
#
# Usage: deploy/sync_to_pi.sh [--dry-run] [--install]
# DEPLOY_HOST defaults to the `pi` ssh alias; DEPLOY_DIR to projects/leaving-x.

set -euo pipefail

DEPLOY_DIR_ABS="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$DEPLOY_DIR_ABS")"

DRY_RUN=0
INSTALL=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --install) INSTALL=1 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

DEPLOY_HOST="${DEPLOY_HOST:-pi}"
DEPLOY_DIR="${DEPLOY_DIR:-projects/leaving-x}"  # relative = under the Pi user's home

RSYNC=(rsync -a --itemize-changes)
(( DRY_RUN )) && RSYNC+=(--dry-run)
run() { if (( DRY_RUN )); then echo "  [dry-run] $*"; else "$@"; fi; }

echo "Pi: $DEPLOY_HOST:$DEPLOY_DIR"

if [[ -n "$(git -C "$ROOT" status --porcelain --untracked-files=no)" ]]; then
  echo "Uncommitted changes in the repo -- commit them first (the Pi only runs committed state):" >&2
  git -C "$ROOT" status --short --untracked-files=no >&2
  exit 1
fi

echo
echo "== 1. Back up the Pi's posted_records.json"
if ssh "$DEPLOY_HOST" "test -f '$DEPLOY_DIR/posted_records.json'"; then
  mkdir -p "$ROOT/backups"
  run rsync -a "$DEPLOY_HOST:$DEPLOY_DIR/posted_records.json" "$ROOT/backups/posted_records.$(date +%Y%m%d-%H%M%S).json"
else
  echo "  (none yet)"
fi

echo
echo "== 2. Code via git (laptop -> Pi, directly)"
# updateInstead: a push to the Pi's checked-out branch updates its files too.
run ssh "$DEPLOY_HOST" "mkdir -p '$DEPLOY_DIR' && cd '$DEPLOY_DIR' && { [ -d .git ] || git init -q -b main; } && git config receive.denyCurrentBranch updateInstead"
run git -C "$ROOT" push "$DEPLOY_HOST:$DEPLOY_DIR" HEAD:main

echo
echo "== 3. Config and Twitter archive"
"${RSYNC[@]}" --chmod=F600 "$ROOT/.env.local" "$DEPLOY_HOST:$DEPLOY_DIR/.env.local"
run ssh "$DEPLOY_HOST" "mkdir -p '$DEPLOY_DIR/twitter_data'"
"${RSYNC[@]}" --exclude='.DS_Store' "$ROOT/twitter_data/tweets.js" "$ROOT/twitter_data/tweets_media" "$DEPLOY_HOST:$DEPLOY_DIR/twitter_data/"

if (( INSTALL )); then
  echo
  echo "== 4. venv, packages and systemd units"
  run ssh "$DEPLOY_HOST" "cd '$DEPLOY_DIR' && { [ -d .venv ] || python3 -m venv .venv; } && .venv/bin/pip install -q -r deploy/requirements-pi.txt"
  run ssh -t "$DEPLOY_HOST" "cd '$DEPLOY_DIR' && sudo cp deploy/leaving-x-on-this-day.service deploy/leaving-x-on-this-day.timer deploy/leaving-x-backfill.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable --now leaving-x-on-this-day.timer && systemctl --no-pager list-timers leaving-x-on-this-day.timer"
  echo "  The backfill is not started automatically. To start it: ssh $DEPLOY_HOST sudo systemctl start leaving-x-backfill"
fi

echo
echo "Done.$( (( DRY_RUN )) && echo ' (dry run -- nothing changed)')"
