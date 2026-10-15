<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know
This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

# Shared Agent Workflow
このリポジトリでは、Claude が設計し、Codex が実装します。両者とも `plan/` を見てから作業してください。

## Source Of Truth
- 要件: `plan/TASK.md`
- 設計: `plan/ARCHITECTURE.md`
- 実装手順: `plan/IMPLEMENTATION.md`
- 実装ログ: `plan/WORKLOG.md`
- 引き継ぎと残課題: `plan/HANDOFF.md`

## Role Split
- **Claude**: 設計、優先順位、リスク整理、完了条件の定義
- **Codex**: 実装、テスト、修正内容の記録、未解決事項のエスカレーション

## Operating Rules(両者共通)
- `plan/` に書いていない前提を勝手に増やさない
- 実装前に対象ファイルと非対象ファイルを確認する
- 大きい判断変更があれば、先に `plan/ARCHITECTURE.md` を更新する
- 実装中の事実は `plan/WORKLOG.md` に残す
- 完了時は `plan/HANDOFF.md` に確認結果と次アクションを書く
- `plan/` に書いていない作業を口頭だけで依頼/実行しない

## Starter Commands
- 初期化: `npm run ai:init`
- 状態確認: `npm run ai:status`
- 実行環境確認: `npm run ai:doctor`
- tmux 起動: `npm run ai:tmux`
