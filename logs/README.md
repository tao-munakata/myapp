# Session Logs

Run logged work sessions from this repository with:

```bash
npm run session:log
```

This creates timestamped transcript files in `logs/`.

- `session-*.typescript`: terminal transcript
- `session-*.timing`: timing metadata from `script`

Notes:

- The transcript captures terminal I/O, not hidden platform metadata.
- If you want Codex work to be preserved reliably, start the shell through the logging wrapper before launching tools in that shell.
- These files are ignored by git by default.
