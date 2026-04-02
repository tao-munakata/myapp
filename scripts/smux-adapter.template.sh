#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:?missing root dir}"
BRIDGE_DIR="${2:?missing bridge dir}"
SESSION_NAME="${3:?missing session name}"
CODEX_PROMPT="${4:?missing codex prompt}"
CLAUDE_PROMPT="${5:?missing claude prompt}"

cat <<EOF
This is a template adapter for smux.

Arguments:
- ROOT_DIR=$ROOT_DIR
- BRIDGE_DIR=$BRIDGE_DIR
- SESSION_NAME=$SESSION_NAME
- CODEX_PROMPT=$CODEX_PROMPT
- CLAUDE_PROMPT=$CLAUDE_PROMPT

Expected job of this adapter:
1. Create or attach to an smux session.
2. Open two panes in $ROOT_DIR.
3. In pane 1, print $CODEX_PROMPT.
4. In pane 2, print $CLAUDE_PROMPT.
5. Optionally focus or attach to the session.

Replace this file with the real smux commands used on your VPS.
Then save it as scripts/smux-adapter.sh and make it executable.

Suggested pane commands:
- cd "$ROOT_DIR" && cat "$CODEX_PROMPT"
- cd "$ROOT_DIR" && cat "$CLAUDE_PROMPT"

Shared bridge commands:
- node scripts/agent-bridge.mjs read --agent codex --dir "$BRIDGE_DIR"
- node scripts/agent-bridge.mjs send --from codex --to claude --text "message" --dir "$BRIDGE_DIR"
- node scripts/agent-bridge.mjs read --agent claude --dir "$BRIDGE_DIR"
- node scripts/agent-bridge.mjs send --from claude --to codex --text "message" --dir "$BRIDGE_DIR"
EOF
