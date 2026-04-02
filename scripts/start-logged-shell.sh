#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${LOG_DIR:-$ROOT_DIR/logs}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
LOG_FILE="${LOG_FILE:-$LOG_DIR/session-$TIMESTAMP.typescript}"
TIMING_FILE="${TIMING_FILE:-$LOG_DIR/session-$TIMESTAMP.timing}"

mkdir -p "$LOG_DIR"

if ! command -v script >/dev/null 2>&1; then
  echo "script command not found"
  exit 1
fi

if [[ "$#" -eq 0 ]]; then
  SHELL_CMD="${SHELL:-/bin/bash} -l"
else
  SHELL_CMD="$*"
fi

cat <<EOF
Transcript log: $LOG_FILE
Timing log: $TIMING_FILE
Command: $SHELL_CMD
EOF

exec script --quiet --flush --return --command "$SHELL_CMD" --log-out "$LOG_FILE" --log-timing "$TIMING_FILE"
