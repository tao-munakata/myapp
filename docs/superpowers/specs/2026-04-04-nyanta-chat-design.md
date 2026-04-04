# にゃん太先生チャット — 設計ドキュメント

**日付:** 2026-04-04  
**スコープ:** コアチャット（MVP）  
**ステータス:** 承認済み

---

## 概要

訪問診療の初診前問診を、猫キャラクター「にゃん太先生」とのチャット形式でサポートするWebアプリ。高齢者・家族が紙の問診票なしに、かわいいキャラとの会話を通じて必要情報を入力できる。

---

## スコープ（MVP）

**含む:**
- にゃん太先生とのチャット形式問診（コアチャット）
- 回答のSQLite保存
- 完了後の回答まとめ画面

**含まない（将来対応）:**
- PDFダウンロード
- 医師ダッシュボード
- マルチアカウント（家族・ケアマネ代理入力）
- 音声入力

---

## アーキテクチャ

### プロジェクト配置

新規プロジェクト: `/home/ubuntu/nyanta-chat/`（既存のmanualineとは独立）

### ディレクトリ構成

```
nyanta-chat/
├── app/
│   ├── page.tsx                # チャット画面（メイン）
│   ├── complete/page.tsx       # 完了・回答まとめ画面
│   └── api/
│       ├── chat/route.ts       # Claude API呼び出し（反応生成）
│       └── session/route.ts    # セッション作成（POST）・回答保存（PUT）
├── components/
│   ├── NyantaFace.tsx          # 猫顔SVGコンポーネント（表情切り替え）
│   ├── ChatBubble.tsx          # チャットバブル（にゃん太 / ユーザー）
│   ├── ProgressBar.tsx         # 肉球マーク進捗バー
│   └── InputArea.tsx           # 入力エリア（select / text / date / photo）
├── lib/
│   ├── questions.ts            # 質問スクリプト定義（固定）
│   ├── db.ts                   # SQLite操作（better-sqlite3）
│   └── claude.ts               # Anthropic SDK wrapper
├── data/
│   └── nyanta.db               # SQLite DB（gitignore）
└── .env.local                  # ANTHROPIC_API_KEY
```

### 技術スタック

| 項目 | 技術 |
|---|---|
| フロントエンド | Next.js (App Router) + TypeScript + Tailwind CSS |
| DB | SQLite (`better-sqlite3`) |
| AI | Anthropic SDK (`claude-haiku-4-5-20251001`) |
| 認証 | なし（URLを開けばアクセス可能） |

---

## データモデル

### SQLiteテーブル

```sql
CREATE TABLE sessions (
  id TEXT PRIMARY KEY,       -- UUID
  created_at INTEGER NOT NULL,
  status TEXT NOT NULL       -- 'in_progress' | 'complete'
);

CREATE TABLE answers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  question_id TEXT NOT NULL,
  answer TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```

---

## 質問スクリプト

### 型定義

```ts
type QuestionType = 'text' | 'select' | 'date' | 'photo'

type Question = {
  id: string
  category: string
  text: string        // にゃん太先生の口調で記述
  type: QuestionType
  options?: string[]  // type === 'select' の場合のみ
  required: boolean
  skippable: boolean
}
```

### カテゴリと問数

| カテゴリID | カテゴリ名 | 問数 |
|---|---|---|
| `basic` | 基本情報 | 5問 |
| `symptoms` | 現在の症状 | 4問 |
| `history` | 病歴・治療歴 | 4問 |
| `medication` | お薬・アレルギー | 3問 |
| `adl` | 日常生活（ADL） | 4問 |
| `home` | 在宅環境 | 3問 |
| `wishes` | その他・希望 | 2問 |

合計: 約25問（1セッション10〜15分想定）

---

## Claude API連携

### エンドポイント: `POST /api/chat`

**リクエスト:**
```ts
{
  sessionId: string
  questionId: string
  questionText: string
  userAnswer: string
}
```

**レスポンス:**
```ts
{
  reaction: string      // 1〜2文の猫語リアクション
  expression: ClaudeExpression  // 猫の表情（Claudeが選択）
}

// Claudeが返す表情（thinking はクライアント側で管理するため含まない）
type ClaudeExpression = 'welcome' | 'happy' | 'surprised' | 'serious' | 'encouraging'

// UI全体で使う表情（thinkingはAPI呼び出し中にクライアントがセット）
type Expression = ClaudeExpression | 'thinking'
```

**システムプロンプト方針:**
- にゃん太先生のペルソナを固定（白衣・聴診器の猫医師）
- 常に「にゃ〜」「〜にゃん」「♡」を含む猫語で返答
- 回答内容に応じて `expression` を選択（JSON形式で返す）
- 診断・医学的判断は絶対にしない旨を明記

**モデル:** `claude-haiku-4-5-20251001`（速度・コスト優先）

---

## UI設計

### チャット画面レイアウト

```
┌─────────────────────────────────┐
│ ヘッダー                         │
│  にゃん太先生の問診室            │
│  🐾🐾🐾○○○○○  あと5問にゃ！     │
├─────────────────────────────────┤
│ チャット履歴（スクロール可）      │
│                                  │
│  [NyantaFace] [吹き出し]         │
│  「こんにゃちはにゃん！...」     │
│                                  │
│                [ユーザー回答]    │
│                                  │
│  [NyantaFace] [吹き出し]         │
│  「なるほどにゃ〜♡」            │
│  「次の質問にゃ！...」           │
├─────────────────────────────────┤
│ 入力エリア                       │
│  [選択肢ボタン or テキスト入力]  │
│  [スキップ]          [送信→]    │
└─────────────────────────────────┘
```

### 猫の表情バリエーション

| expression | 説明 | 使用タイミング |
|---|---|---|
| `welcome` | 笑顔（デフォルト） | 起動時・通常の質問 |
| `happy` | 大笑い | 回答してくれた後 |
| `surprised` | びっくり | 重要情報を聞いた時 |
| `serious` | 真剣顔 | 病歴・薬など重要カテゴリ |
| `thinking` | 考え中 | Claudeローディング中 |
| `encouraging` | 感動・励まし | 最後の質問・完了時 |

SVGコンポーネントとして実装（軽量・アニメーション対応）。

### 入力タイプ別UI

| type | UI | 備考 |
|---|---|---|
| `select` | 大きめタップボタン式選択肢 | 高齢者向けに60px以上 |
| `text` | テキストエリア＋送信ボタン | 改行可能 |
| `date` | 日付ピッカー | ネイティブ `<input type="date">` |
| `photo` | 「写真を見せてにゃ！」ボタン＋プレビュー | Base64でDB保存 |

### 完了画面（`/complete`）

- 回答をカテゴリ別に整理して一覧表示
- 「コピー」「印刷」ボタン
- 「最初からやり直す」ボタン
- 免責表示：「これはにゃん太先生のお手伝いだにゃ。本当の診断・診療は訪問のお医者さんにお任せしてね！」

---

## データフロー

```
1. ユーザーがURLにアクセス
2. ページロード時にセッションID（UUID）を発行 → POST /api/session でsessionsテーブルにINSERT
3. 質問1（questions.ts から）をチャットに表示
4. ユーザーが回答を入力・送信
5. POST /api/chat → Claude が猫語リアクション＋表情を生成
6. POST /api/session → answersテーブルに INSERT
7. リアクション表示 → 次の質問を表示
8. 全問完了 → sessions.status を 'complete' に UPDATE
9. /complete にリダイレクト → 回答一覧を表示
```

---

## セキュリティ・注意事項

- `ANTHROPIC_API_KEY` は `.env.local` で管理（gitignore必須）
- 医療的診断・判断はClaudeに行わせない（システムプロンプトで明示的に禁止）
- 画面上に常に免責表示を配置
- 写真データはBase64でDBに保存（外部ストレージ不要のMVP構成）
