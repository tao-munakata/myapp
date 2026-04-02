# Worklog

## 2026-04-03

### Shared terminal bridge setup

- Added a file-backed bridge at `scripts/agent-bridge.mjs` for agent-to-agent message passing through the shared workspace.
- Added bridge npm scripts in `package.json` for initialization and status checks.
- Added `scripts/launch-agent-bridge.sh` to print launch commands and support `screen`, `tmux`, and `smux` modes.
- Added prompt files in `prompts/` for Codex and Claude Code bridge startup.
- Added `scripts/smux-adapter.template.sh` as the VPS-side integration point for environment-specific `smux` commands.
- Added README instructions for bridge initialization, wrapper usage, and local `screen`-based verification.

### Local verification

- Verified `init`, `send`, `read`, `status`, and `reset` flows for the bridge.
- Added locking to bridge writes so concurrent sends do not reuse message ids.
- Started a local `screen` session named `agent-bridge` for bridge verification on this machine.
- Confirmed lint passes after the changes.

### Backups

- Created local backup archive: `backups/myapp-backup-20260403-062434.tar.gz`
- Created distributable backup archive without `.env`: `backups/myapp-distributable-20260403-062434.tar.gz`

### Logging

- Added automatic transcript logging via `scripts/start-logged-shell.sh`
- Added `logs/README.md` and npm script support for starting logged sessions from this repository

### Limitation

- This repository can automatically save terminal transcripts started through the logging wrapper.
- It cannot retroactively or universally capture hidden chat/session state outside the terminal transcript managed from this workspace.
