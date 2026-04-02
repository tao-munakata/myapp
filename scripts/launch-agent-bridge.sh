#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRIDGE_DIR="${BRIDGE_DIR:-$ROOT_DIR/.smux-bridge}"
SESSION_NAME="${SESSION_NAME:-agent-bridge}"
MODE="${1:-print}"
SMUX_ADAPTER="${SMUX_ADAPTER:-$ROOT_DIR/scripts/smux-adapter.sh}"

init_bridge() {
  node "$ROOT_DIR/scripts/agent-bridge.mjs" init --dir "$BRIDGE_DIR" >/dev/null
}

print_banner() {
  cat <<EOF
Bridge directory: $BRIDGE_DIR
Session name: $SESSION_NAME
EOF
}

print_commands() {
  cat <<EOF

[Pane 1: Codex]
cd "$ROOT_DIR"
cat "$ROOT_DIR/prompts/codex-bridge-init.txt"

[Pane 2: Claude Code]
cd "$ROOT_DIR"
cat "$ROOT_DIR/prompts/claude-bridge-init.txt"

[Shared bridge commands]
node scripts/agent-bridge.mjs read --agent codex --dir "$BRIDGE_DIR"
node scripts/agent-bridge.mjs send --from codex --to claude --text "message" --dir "$BRIDGE_DIR"
node scripts/agent-bridge.mjs read --agent claude --dir "$BRIDGE_DIR"
node scripts/agent-bridge.mjs send --from claude --to codex --text "message" --dir "$BRIDGE_DIR"
node scripts/agent-bridge.mjs status --dir "$BRIDGE_DIR"
EOF
}

launch_tmux() {
  if ! command -v tmux >/dev/null 2>&1; then
    echo "tmux not found. Falling back to command printout."
    print_banner
    print_commands
    return 0
  fi

  if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "tmux session '$SESSION_NAME' already exists."
    print_banner
    echo "Attach with: tmux attach -t $SESSION_NAME"
    return 0
  fi

  tmux new-session -d -s "$SESSION_NAME" -c "$ROOT_DIR"
  tmux rename-window -t "$SESSION_NAME:0" "agents"
  tmux split-window -h -t "$SESSION_NAME:0" -c "$ROOT_DIR"

  tmux send-keys -t "$SESSION_NAME:0.0" "clear" C-m
  tmux send-keys -t "$SESSION_NAME:0.0" "printf 'Codex pane\n\n'" C-m
  tmux send-keys -t "$SESSION_NAME:0.0" "cat \"$ROOT_DIR/prompts/codex-bridge-init.txt\"" C-m

  tmux send-keys -t "$SESSION_NAME:0.1" "clear" C-m
  tmux send-keys -t "$SESSION_NAME:0.1" "printf 'Claude Code pane\n\n'" C-m
  tmux send-keys -t "$SESSION_NAME:0.1" "cat \"$ROOT_DIR/prompts/claude-bridge-init.txt\"" C-m

  print_banner
  echo "tmux session created."
  echo "Attach with: tmux attach -t $SESSION_NAME"
}

launch_screen() {
  if ! command -v screen >/dev/null 2>&1; then
    echo "screen not found. Falling back to command printout."
    print_banner
    print_commands
    return 0
  fi

  if screen -list | grep -q "[.]$SESSION_NAME[[:space:]]"; then
    echo "screen session '$SESSION_NAME' already exists."
    print_banner
    echo "Attach with: screen -r $SESSION_NAME"
    return 0
  fi

  screen -dmS "$SESSION_NAME" -t codex bash -lc "cd \"$ROOT_DIR\" && clear && printf 'Codex window\n\n' && cat \"$ROOT_DIR/prompts/codex-bridge-init.txt\" && exec bash"
  screen -S "$SESSION_NAME" -X screen -t claude bash -lc "cd \"$ROOT_DIR\" && clear && printf 'Claude Code window\n\n' && cat \"$ROOT_DIR/prompts/claude-bridge-init.txt\" && exec bash"

  print_banner
  echo "screen session created."
  echo "Attach with: screen -r $SESSION_NAME"
  echo "Switch windows with: Ctrl-a n / Ctrl-a p"
}

launch_smux() {
  if ! command -v smux >/dev/null 2>&1; then
    echo "smux not found. Falling back to command printout."
    print_banner
    print_commands
    return 0
  fi

  if [[ ! -x "$SMUX_ADAPTER" ]]; then
    echo "smux adapter not found or not executable: $SMUX_ADAPTER"
    echo "Copy scripts/smux-adapter.template.sh to scripts/smux-adapter.sh and adapt it to your smux CLI."
    print_banner
    print_commands
    return 0
  fi

  "$SMUX_ADAPTER" \
    "$ROOT_DIR" \
    "$BRIDGE_DIR" \
    "$SESSION_NAME" \
    "$ROOT_DIR/prompts/codex-bridge-init.txt" \
    "$ROOT_DIR/prompts/claude-bridge-init.txt"

  print_banner
  echo "smux adapter completed: $SMUX_ADAPTER"
}

init_bridge

case "$MODE" in
  print)
    print_banner
    print_commands
    ;;
  screen)
    launch_screen
    ;;
  tmux)
    launch_tmux
    ;;
  smux)
    launch_smux
    ;;
  *)
    echo "Usage: bash scripts/launch-agent-bridge.sh [print|screen|tmux|smux]"
    exit 1
    ;;
esac
