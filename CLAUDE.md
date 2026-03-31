@AGENTS.md

# myapp プロジェクト設定

## 技術スタック
- **Next.js 16.2.1** / React 19.2.4（カスタム版 — 標準の知識と異なる場合あり）
- **TypeScript 5**（strict モード）
- **Tailwind CSS 4**
- **Python**（バックエンド / スクリプト）

## Next.js に関する注意
- このNext.jsはカスタム版でAPIや規約が標準と異なる可能性がある
- コードを書く前に必ず `node_modules/next/dist/docs/` のガイドを確認する
- deprecation警告には必ず従う

## コーディングスタイル
- TypeScriptは型を明示する（`any` 禁止）
- Reactコンポーネントは関数コンポーネントで書く
- Tailwindのクラスは可読性のため適宜改行・整理する
- Pythonは PEP 8 に従う

## ディレクトリ構成
- フロントエンド: `app/` 配下（Next.js App Router）
- 静的ファイル: `public/`
