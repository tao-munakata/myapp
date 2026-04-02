This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.

## Shared Terminal Agent Bridge

This repo includes a minimal file-backed bridge for running two coding agents through a shared terminal multiplexer such as `smux`.

The bridge does not require an API or a custom transport layer. Each agent only needs shell access to the same working directory.

### Initialize the bridge

```bash
npm run bridge:init
```

This creates `.smux-bridge/` with:

- `events.jsonl`: append-only message log
- `cursors/*.txt`: per-agent read cursors
- `state.json`: next message id

### Wrapper script

For local setup, use the wrapper:

```bash
npm run bridge:launch
```

This initializes the bridge and prints the exact commands to use in the Codex and Claude panes.

If you want a quick local check and `tmux` is installed:

```bash
bash scripts/launch-agent-bridge.sh tmux
tmux attach -t agent-bridge
```

That opens two panes and prints the corresponding initial prompts inside them.

On this machine, `screen` is also available:

```bash
npm run bridge:launch:screen
screen -r agent-bridge
```

If you want to use `smux` on your VPS:

```bash
cp scripts/smux-adapter.template.sh scripts/smux-adapter.sh
chmod +x scripts/smux-adapter.sh
bash scripts/launch-agent-bridge.sh smux
```

The wrapper will call `scripts/smux-adapter.sh` if `smux` is installed. You only need to encode your VPS-specific `smux` pane/session commands in that adapter.

### Start two panes in `smux`

Open two terminals that share this repository. One can host Claude Code and the other Codex.

In each pane, tell the agent to use these commands:

```bash
node scripts/agent-bridge.mjs read --agent codex
node scripts/agent-bridge.mjs send --from codex --to claude --text "message"
```

```bash
node scripts/agent-bridge.mjs read --agent claude
node scripts/agent-bridge.mjs send --from claude --to codex --text "message"
```

### Suggested operating contract

Use a simple turn format so both agents stay deterministic:

1. `read`
2. reason locally
3. `send` one concise response
4. stop after a fixed number of turns or when either side emits `DONE`

Recommended message template:

```text
TASK: <what you want from the other agent>
CONTEXT: <relevant state only>
CONSTRAINTS: <safety limits, files, scope>
DONE-WHEN: <clear stopping condition>
```

### Inspect bridge state

```bash
npm run bridge:status
```

### Reset the bridge

```bash
node scripts/agent-bridge.mjs reset
```

This is intentionally small. `smux` remains responsible for pane creation and terminal control, while the bridge only handles durable message passing inside the shared workspace.

The prompt files used by the wrapper are:

- `prompts/codex-bridge-init.txt`
- `prompts/claude-bridge-init.txt`

The `smux` integration point is:

- `scripts/smux-adapter.template.sh`

## Session Logging

This repository includes a local logging wrapper for future Codex or shell work:

```bash
npm run session:log
```

That starts a login shell through `script` and saves:

- `logs/session-*.typescript`
- `logs/session-*.timing`

Important limitation:

- This can automatically save terminal transcripts started through the wrapper.
- It does not automatically export hidden chat history from the platform unless that history is printed to the terminal.

Current work summary is saved in:

- `docs/WORKLOG.md`
