#!/usr/bin/env bash
#
# Install (or remove) the scheduled comment scanner on macOS.
#
#   ./scripts/install_scheduler.sh            install
#   ./scripts/install_scheduler.sh --uninstall
#
# The job runs hourly and exits immediately when the app decides it is not due
# (SCHEDULER_INTERVAL_HOURS = 5, plus jitter). It only discovers posts and
# drafts comments — it never posts.
set -euo pipefail

LABEL="com.linkedinaiagent.comments"
PLIST_SRC="$(cd "$(dirname "$0")" && pwd)/${LABEL}.plist"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="$HOME/Library/LaunchAgents/${LABEL}.plist"

if [[ "${1:-}" == "--uninstall" ]]; then
    launchctl unload "$TARGET" 2>/dev/null || true
    rm -f "$TARGET"
    echo "Removed $LABEL"
    exit 0
fi

POETRY_BIN="$(command -v poetry || true)"
if [[ -z "$POETRY_BIN" ]]; then
    echo "poetry not found in PATH. Install it first: https://python-poetry.org"
    exit 1
fi

mkdir -p "$PROJECT_DIR/logs" "$HOME/Library/LaunchAgents"

sed -e "s|__POETRY__|${POETRY_BIN}|g" \
    -e "s|__PROJECT__|${PROJECT_DIR}|g" \
    "$PLIST_SRC" > "$TARGET"

launchctl unload "$TARGET" 2>/dev/null || true
launchctl load "$TARGET"

echo "Installed $LABEL"
echo "  project : $PROJECT_DIR"
echo "  poetry  : $POETRY_BIN"
echo "  runs    : hourly tick, actual scan every ${SCHEDULER_INTERVAL_HOURS:-5}h (see app/core/config.py)"
echo "  logs    : $PROJECT_DIR/logs/comment_scheduler.log"
echo
echo "Run one cycle now:   poetry run python -m app.services.comment_scheduler --force"
echo "Remove the schedule: ./scripts/install_scheduler.sh --uninstall"
