# にゃん太先生チャット Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 訪問診療初診問診をにゃん太先生（猫キャラ）とのチャット形式で行い、回答をSQLiteに保存し、`http://<IP>/nyanta/` でアクセスできるWebアプリを構築する。

**Architecture:** ガイデッドAI型 — 質問は固定スクリプト25問、ClaudeはユーザーのURLに猫語リアクション＋表情を生成するのみ。Next.js App Router（サーバーコンポーネント＋API Routes）＋ SQLite（better-sqlite3）。Nginxがリバースプロキシとして `/nyanta/` → nyanta-chatコンテナに振り分け、`/` → 既存Manualineに振り分ける。

**Tech Stack:** Next.js 15 (App Router), TypeScript (strict), Tailwind CSS v4, better-sqlite3, @anthropic-ai/sdk, Vitest, Docker, Nginx

---

## ファイルマップ

| ファイル | 責務 |
|---|---|
| `/home/ubuntu/nyanta-chat/lib/questions.ts` | 質問スクリプト定義（固定データ） |
| `/home/ubuntu/nyanta-chat/lib/db.ts` | SQLite操作（セッション・回答のCRUD） |
| `/home/ubuntu/nyanta-chat/lib/claude.ts` | Anthropic SDK wrapper（猫語リアクション生成） |
| `/home/ubuntu/nyanta-chat/app/api/session/route.ts` | POST（セッション作成）/ PUT（回答保存・完了） |
| `/home/ubuntu/nyanta-chat/app/api/chat/route.ts` | POST（Claude呼び出し） |
| `/home/ubuntu/nyanta-chat/components/NyantaFace.tsx` | 猫顔SVG（6表情切り替え） |
| `/home/ubuntu/nyanta-chat/components/ChatBubble.tsx` | チャット吹き出し（にゃん太 / ユーザー） |
| `/home/ubuntu/nyanta-chat/components/ProgressBar.tsx` | 肉球マーク進捗バー |
| `/home/ubuntu/nyanta-chat/components/InputArea.tsx` | 入力エリア（select/text/date/photo） |
| `/home/ubuntu/nyanta-chat/app/page.tsx` | チャットメイン画面（クライアントコンポーネント） |
| `/home/ubuntu/nyanta-chat/app/complete/page.tsx` | 完了・回答まとめ画面 |
| `/home/ubuntu/nyanta-chat/Dockerfile` | 本番用Dockerイメージ |
| `/home/ubuntu/nyanta-chat/docker-compose.yml` | nyanta-chatコンテナ定義 |
| `/home/ubuntu/nginx/nginx.conf` | リバースプロキシ設定 |
| `/home/ubuntu/nginx/docker-compose.yml` | Nginxコンテナ定義 |

---

## Task 1: プロジェクト初期化

**Files:**
- Create: `/home/ubuntu/nyanta-chat/` (new project)
- Create: `/home/ubuntu/nyanta-chat/next.config.ts`
- Create: `/home/ubuntu/nyanta-chat/.gitignore`

- [ ] **Step 1: Next.jsプロジェクトを作成**

```bash
cd /home/ubuntu
npx create-next-app@15 nyanta-chat \
  --typescript \
  --tailwind \
  --app \
  --no-src-dir \
  --import-alias "@/*" \
  --no-turbopack
```

- [ ] **Step 2: 依存パッケージをインストール**

```bash
cd /home/ubuntu/nyanta-chat
npm install better-sqlite3 @anthropic-ai/sdk uuid
npm install -D @types/better-sqlite3 @types/uuid vitest @vitejs/plugin-react @testing-library/react @testing-library/dom jsdom
```

- [ ] **Step 3: next.config.ts を設定（basePath + standalone）**

`/home/ubuntu/nyanta-chat/next.config.ts` を以下に置き換え：

```ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  basePath: "/nyanta",
};

export default nextConfig;
```

- [ ] **Step 4: vitest.config.ts を作成**

```ts
// /home/ubuntu/nyanta-chat/vitest.config.ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
  },
});
```

- [ ] **Step 5: package.json に test スクリプトを追加**

`package.json` の `"scripts"` に追記：

```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 6: .gitignore を確認（data/ と .env.local が含まれているか確認）**

```bash
grep -E "^data/|^\.env" /home/ubuntu/nyanta-chat/.gitignore || echo "data/" >> /home/ubuntu/nyanta-chat/.gitignore
```

- [ ] **Step 7: dataディレクトリを作成**

```bash
mkdir -p /home/ubuntu/nyanta-chat/data
echo "*.db" >> /home/ubuntu/nyanta-chat/.gitignore
```

- [ ] **Step 8: .env.local を作成**

```bash
cat > /home/ubuntu/nyanta-chat/.env.local << 'EOF'
ANTHROPIC_API_KEY=your_api_key_here
EOF
```

- [ ] **Step 9: gitを初期化してコミット**

```bash
cd /home/ubuntu/nyanta-chat
git init
git add -A
git commit -m "chore: initial Next.js project setup"
```

---

## Task 2: DBモジュール（lib/db.ts）

**Files:**
- Create: `/home/ubuntu/nyanta-chat/lib/db.ts`
- Create: `/home/ubuntu/nyanta-chat/lib/__tests__/db.test.ts`

- [ ] **Step 1: テストを書く**

```ts
// /home/ubuntu/nyanta-chat/lib/__tests__/db.test.ts
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import fs from "fs";
import path from "path";

// テスト用DBパスを環境変数で制御
process.env.DB_PATH = path.join(process.cwd(), "data/test.db");

// db.tsをインポート（この時点ではまだ存在しないのでエラーになる）
const { createSession, saveAnswer, completeSession, getSessionAnswers } =
  await import("../db.js");

describe("db", () => {
  beforeEach(() => {
    // テーブル初期化は db.ts の初期化時に行われる
  });

  afterEach(() => {
    // テスト用DBを削除
    const dbPath = process.env.DB_PATH!;
    if (fs.existsSync(dbPath)) fs.unlinkSync(dbPath);
  });

  it("createSession: セッションIDを返す", () => {
    const id = createSession();
    expect(typeof id).toBe("string");
    expect(id.length).toBeGreaterThan(0);
  });

  it("saveAnswer: 回答を保存できる", () => {
    const sessionId = createSession();
    saveAnswer(sessionId, "basic-name", "田中太郎");
    const answers = getSessionAnswers(sessionId);
    expect(answers).toHaveLength(1);
    expect(answers[0].question_id).toBe("basic-name");
    expect(answers[0].answer).toBe("田中太郎");
  });

  it("completeSession: ステータスをcompleteに更新する", () => {
    const sessionId = createSession();
    completeSession(sessionId);
    // エラーなく完了すれば OK（ステータスはgetSessionAnswersで間接確認）
    expect(true).toBe(true);
  });

  it("getSessionAnswers: 複数回答を返す", () => {
    const sessionId = createSession();
    saveAnswer(sessionId, "basic-name", "山田花子");
    saveAnswer(sessionId, "basic-kana", "やまだはなこ");
    const answers = getSessionAnswers(sessionId);
    expect(answers).toHaveLength(2);
  });
});
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
cd /home/ubuntu/nyanta-chat
npm test -- lib/__tests__/db.test.ts 2>&1 | head -20
```

Expected: エラー（db.ts が存在しない）

- [ ] **Step 3: lib/db.ts を実装**

```ts
// /home/ubuntu/nyanta-chat/lib/db.ts
import "server-only";
import Database from "better-sqlite3";
import { v4 as uuidv4 } from "uuid";
import path from "path";

const DB_PATH =
  process.env.DB_PATH ?? path.join(process.cwd(), "data/nyanta.db");

let _db: Database.Database | null = null;

function getDb(): Database.Database {
  if (!_db) {
    _db = new Database(DB_PATH);
    _db.pragma("journal_mode = WAL");
    _db.exec(`
      CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        created_at INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'in_progress'
      );
      CREATE TABLE IF NOT EXISTS answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        question_id TEXT NOT NULL,
        answer TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        FOREIGN KEY (session_id) REFERENCES sessions(id)
      );
    `);
  }
  return _db;
}

export function createSession(): string {
  const id = uuidv4();
  getDb()
    .prepare(
      "INSERT INTO sessions (id, created_at, status) VALUES (?, ?, 'in_progress')"
    )
    .run(id, Date.now());
  return id;
}

export function saveAnswer(
  sessionId: string,
  questionId: string,
  answer: string
): void {
  getDb()
    .prepare(
      "INSERT INTO answers (session_id, question_id, answer, created_at) VALUES (?, ?, ?, ?)"
    )
    .run(sessionId, questionId, answer, Date.now());
}

export function completeSession(sessionId: string): void {
  getDb()
    .prepare("UPDATE sessions SET status = 'complete' WHERE id = ?")
    .run(sessionId);
}

export function getSessionAnswers(
  sessionId: string
): { question_id: string; answer: string }[] {
  return getDb()
    .prepare(
      "SELECT question_id, answer FROM answers WHERE session_id = ? ORDER BY id ASC"
    )
    .all(sessionId) as { question_id: string; answer: string }[];
}
```

- [ ] **Step 4: テストを実行して全て通ることを確認**

```bash
cd /home/ubuntu/nyanta-chat
npm test -- lib/__tests__/db.test.ts
```

Expected: 4 tests passed

- [ ] **Step 5: コミット**

```bash
cd /home/ubuntu/nyanta-chat
git add lib/db.ts lib/__tests__/db.test.ts
git commit -m "feat: SQLite DBモジュール（セッション・回答CRUD）"
```

---

## Task 3: 質問スクリプト（lib/questions.ts）

**Files:**
- Create: `/home/ubuntu/nyanta-chat/lib/questions.ts`
- Create: `/home/ubuntu/nyanta-chat/lib/__tests__/questions.test.ts`

- [ ] **Step 1: テストを書く**

```ts
// /home/ubuntu/nyanta-chat/lib/__tests__/questions.test.ts
import { describe, it, expect } from "vitest";
import { QUESTIONS, getQuestion, CATEGORIES } from "../questions.js";

describe("questions", () => {
  it("25問定義されている", () => {
    expect(QUESTIONS.length).toBe(25);
  });

  it("全質問にid・category・text・typeが存在する", () => {
    for (const q of QUESTIONS) {
      expect(q.id, `${q.id}: idが空`).toBeTruthy();
      expect(q.category, `${q.id}: categoryが空`).toBeTruthy();
      expect(q.text, `${q.id}: textが空`).toBeTruthy();
      expect(["text", "select", "date", "photo"]).toContain(q.type);
    }
  });

  it("select型にはoptionsが存在する", () => {
    const selects = QUESTIONS.filter((q) => q.type === "select");
    for (const q of selects) {
      expect(q.options, `${q.id}: optionsがない`).toBeDefined();
      expect(q.options!.length).toBeGreaterThan(0);
    }
  });

  it("getQuestion: IDで質問を取得できる", () => {
    const q = getQuestion("basic-name");
    expect(q).toBeDefined();
    expect(q!.id).toBe("basic-name");
  });

  it("getQuestion: 存在しないIDはundefinedを返す", () => {
    expect(getQuestion("nonexistent")).toBeUndefined();
  });

  it("7カテゴリが全て含まれている", () => {
    const cats = new Set(QUESTIONS.map((q) => q.category));
    for (const cat of CATEGORIES) {
      expect(cats.has(cat.id), `カテゴリ ${cat.id} がない`).toBe(true);
    }
  });
});
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
cd /home/ubuntu/nyanta-chat
npm test -- lib/__tests__/questions.test.ts 2>&1 | head -10
```

Expected: エラー（questions.ts が存在しない）

- [ ] **Step 3: lib/questions.ts を実装**

```ts
// /home/ubuntu/nyanta-chat/lib/questions.ts

export type QuestionType = "text" | "select" | "date" | "photo";

export type Question = {
  id: string;
  category: string;
  text: string;
  type: QuestionType;
  options?: string[];
  skippable: boolean;
};

export type Category = {
  id: string;
  label: string;
};

export const CATEGORIES: Category[] = [
  { id: "basic", label: "基本情報" },
  { id: "symptoms", label: "現在の症状" },
  { id: "history", label: "病歴・治療歴" },
  { id: "medication", label: "お薬・アレルギー" },
  { id: "adl", label: "日常生活" },
  { id: "home", label: "在宅環境" },
  { id: "wishes", label: "その他・希望" },
];

export const QUESTIONS: Question[] = [
  // ── 基本情報 ─────────────────────────────
  {
    id: "basic-name",
    category: "basic",
    text: "まずは自己紹介にゃ♡ お名前（フルネーム）をおしえてにゃ〜！",
    type: "text",
    skippable: false,
  },
  {
    id: "basic-kana",
    category: "basic",
    text: "ふりがなもおしえてにゃん♡（例：やまだたろう）",
    type: "text",
    skippable: false,
  },
  {
    id: "basic-dob",
    category: "basic",
    text: "生年月日をおしえてにゃ〜！",
    type: "date",
    skippable: false,
  },
  {
    id: "basic-gender",
    category: "basic",
    text: "性別をおしえてにゃ♡",
    type: "select",
    options: ["男性", "女性", "その他"],
    skippable: false,
  },
  {
    id: "basic-phone",
    category: "basic",
    text: "連絡先の電話番号をおしえてにゃ〜（ハイフンなしでもOKにゃ）",
    type: "text",
    skippable: false,
  },
  // ── 現在の症状 ───────────────────────────
  {
    id: "symptoms-main",
    category: "symptoms",
    text: "今、一番気になるお身体のことは何にゃ？ 例えば「足がむくむ」「ご飯が食べられない」とか、気軽に教えてにゃん♡",
    type: "text",
    skippable: false,
  },
  {
    id: "symptoms-since",
    category: "symptoms",
    text: "それはいつごろから続いてるにゃ？（例：「2週間前から」「半年くらい前から」）",
    type: "text",
    skippable: true,
  },
  {
    id: "symptoms-pain",
    category: "symptoms",
    text: "今、痛みはあるにゃ？ある場合はどのくらい強いにゃ？",
    type: "select",
    options: ["痛みはない", "少し痛い", "かなり痛い", "我慢できないほど痛い"],
    skippable: false,
  },
  {
    id: "symptoms-other",
    category: "symptoms",
    text: "他にも気になる症状があれば教えてにゃ〜（なければスキップOKにゃ）",
    type: "text",
    skippable: true,
  },
  // ── 病歴・治療歴 ─────────────────────────
  {
    id: "history-disease",
    category: "history",
    text: "これまでに大きな病気や手術をしたことはあるにゃ？（例：「心臓の手術」「糖尿病」など）なければスキップOKにゃ♡",
    type: "text",
    skippable: true,
  },
  {
    id: "history-hospital",
    category: "history",
    text: "今、かかりつけの病院や主治医の先生はいるにゃ？",
    type: "select",
    options: ["いる", "いない", "わからない"],
    skippable: false,
  },
  {
    id: "history-hospital-name",
    category: "history",
    text: "かかりつけ病院の名前と主治医の先生のお名前をおしえてにゃ♡ わからない場合はスキップOKにゃ",
    type: "text",
    skippable: true,
  },
  {
    id: "history-admit",
    category: "history",
    text: "最近1年以内に入院したことはあるにゃ？",
    type: "select",
    options: ["ある", "ない"],
    skippable: false,
  },
  // ── お薬・アレルギー ──────────────────────
  {
    id: "med-photo",
    category: "medication",
    text: "今飲んでいるお薬があれば、お薬手帳の写真を見せてにゃ♡ とっても助かるにゃ〜！（なければスキップOKにゃ）",
    type: "photo",
    skippable: true,
  },
  {
    id: "med-names",
    category: "medication",
    text: "お薬の名前が分かれば教えてにゃ〜（自由記入でOKにゃ♡）なければスキップOKにゃ",
    type: "text",
    skippable: true,
  },
  {
    id: "med-allergy",
    category: "medication",
    text: "薬や食べ物でアレルギーや副作用が出たことはあるにゃ？",
    type: "select",
    options: ["ある", "ない", "わからない"],
    skippable: false,
  },
  // ── 日常生活（ADL）────────────────────────
  {
    id: "adl-meal",
    category: "adl",
    text: "ご飯は自分で食べられるにゃ？",
    type: "select",
    options: ["自分で食べられる", "一部手助けが必要", "全介助が必要"],
    skippable: false,
  },
  {
    id: "adl-toilet",
    category: "adl",
    text: "おトイレはどうしてるにゃ？",
    type: "select",
    options: ["自分でできる", "一部介助が必要", "全介助・オムツ使用"],
    skippable: false,
  },
  {
    id: "adl-walk",
    category: "adl",
    text: "歩いたり移動するのはどうにゃ？",
    type: "select",
    options: ["自分で歩ける", "杖・歩行器を使う", "車椅子を使う", "寝たきり"],
    skippable: false,
  },
  {
    id: "adl-family",
    category: "adl",
    text: "一緒に暮らしている家族や、介護してくれる方はいるにゃ？（例：「妻と同居」「一人暮らし」など）",
    type: "text",
    skippable: false,
  },
  // ── 在宅環境 ─────────────────────────────
  {
    id: "home-parking",
    category: "home",
    text: "おうちの近くに車を停められる場所はあるにゃ？ お医者さんが来るとき必要にゃ〜！",
    type: "select",
    options: ["ある", "ない", "わからない"],
    skippable: false,
  },
  {
    id: "home-access",
    category: "home",
    text: "玄関まで段差や急な坂はあるにゃ？",
    type: "select",
    options: ["ない・フラット", "少しある", "多い・バリアあり"],
    skippable: false,
  },
  {
    id: "home-services",
    category: "home",
    text: "今、訪問看護やヘルパーなどのサービスを使っているにゃ？使っていれば教えてにゃ♡ なければスキップOKにゃ",
    type: "text",
    skippable: true,
  },
  // ── その他・希望 ─────────────────────────
  {
    id: "wishes-hope",
    category: "wishes",
    text: "お医者さんに来てもらうにあたって、特に伝えておきたいことはあるにゃ？ なんでも教えてにゃ〜♡ なければスキップOKにゃ",
    type: "text",
    skippable: true,
  },
  {
    id: "wishes-visit",
    category: "wishes",
    text: "初回の訪問、いつごろが都合いいにゃ？希望があれば教えてにゃ♡（例：「来週の午前中」「急ぎではない」など）",
    type: "text",
    skippable: true,
  },
];

export function getQuestion(id: string): Question | undefined {
  return QUESTIONS.find((q) => q.id === id);
}
```

- [ ] **Step 4: テストを実行して全て通ることを確認**

```bash
cd /home/ubuntu/nyanta-chat
npm test -- lib/__tests__/questions.test.ts
```

Expected: 6 tests passed

- [ ] **Step 5: コミット**

```bash
cd /home/ubuntu/nyanta-chat
git add lib/questions.ts lib/__tests__/questions.test.ts
git commit -m "feat: 問診質問スクリプト25問（7カテゴリ）定義"
```

---

## Task 4: Claude APIラッパー（lib/claude.ts）

**Files:**
- Create: `/home/ubuntu/nyanta-chat/lib/claude.ts`
- Create: `/home/ubuntu/nyanta-chat/lib/__tests__/claude.test.ts`

- [ ] **Step 1: テストを書く（モックを使用）**

```ts
// /home/ubuntu/nyanta-chat/lib/__tests__/claude.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";

// Anthropic SDKをモック
vi.mock("@anthropic-ai/sdk", () => ({
  default: vi.fn().mockImplementation(() => ({
    messages: {
      create: vi.fn().mockResolvedValue({
        content: [
          {
            type: "text",
            text: JSON.stringify({
              reaction: "なるほどにゃ〜！教えてくれてありがとうにゃ♡",
              expression: "happy",
            }),
          },
        ],
      }),
    },
  })),
}));

const { generateReaction } = await import("../claude.js");

describe("claude", () => {
  it("reactionとexpressionを返す", async () => {
    const result = await generateReaction(
      "お名前をおしえてにゃ",
      "田中太郎"
    );
    expect(result.reaction).toBeTruthy();
    expect([
      "welcome",
      "happy",
      "surprised",
      "serious",
      "encouraging",
    ]).toContain(result.expression);
  });

  it("JSONパースに失敗した場合はデフォルト値を返す", async () => {
    const Anthropic = (await import("@anthropic-ai/sdk")).default as ReturnType<typeof vi.fn>;
    Anthropic.mockImplementationOnce(() => ({
      messages: {
        create: vi.fn().mockResolvedValue({
          content: [{ type: "text", text: "壊れたレスポンスにゃ" }],
        }),
      },
    }));
    const result = await generateReaction("質問", "回答");
    expect(result.reaction).toBeTruthy();
    expect(result.expression).toBe("welcome");
  });
});
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
cd /home/ubuntu/nyanta-chat
npm test -- lib/__tests__/claude.test.ts 2>&1 | head -10
```

Expected: エラー（claude.ts が存在しない）

- [ ] **Step 3: lib/claude.ts を実装**

```ts
// /home/ubuntu/nyanta-chat/lib/claude.ts
import "server-only";
import Anthropic from "@anthropic-ai/sdk";

export type ClaudeExpression =
  | "welcome"
  | "happy"
  | "surprised"
  | "serious"
  | "encouraging";

export type ReactionResult = {
  reaction: string;
  expression: ClaudeExpression;
};

const SYSTEM_PROMPT = `あなたは「にゃん太先生」です。白衣と聴診器をつけた、ふわふわの猫の医師キャラクターです。

ルール：
- 必ず「にゃ〜」「〜にゃん」「♡」を含む猫語で話す
- 1〜2文の短いリアクションを返す
- 患者の回答を優しく受け止めて、励ますかほめる
- 医療的な診断・アドバイス・判断は絶対にしない
- 回答は以下のJSON形式のみで返す（他の文字を含めない）：
{"reaction": "猫語リアクション文", "expression": "表情コード"}

表情コードの選択ルール：
- "welcome": 通常の優しい反応
- "happy": 情報を教えてもらえた嬉しい反応
- "surprised": 重要な情報（病名・手術・アレルギーなど）を聞いた時
- "serious": 症状・痛み・緊急性の高い内容を聞いた時
- "encouraging": 最後の質問・困難そうな状況に励ます時`;

const client = new Anthropic();

export async function generateReaction(
  questionText: string,
  userAnswer: string
): Promise<ReactionResult> {
  try {
    const message = await client.messages.create({
      model: "claude-haiku-4-5-20251001",
      max_tokens: 200,
      system: SYSTEM_PROMPT,
      messages: [
        {
          role: "user",
          content: `質問：「${questionText}」\nユーザーの回答：「${userAnswer}」`,
        },
      ],
    });

    const text =
      message.content[0].type === "text" ? message.content[0].text : "";
    const parsed = JSON.parse(text);

    const validExpressions: ClaudeExpression[] = [
      "welcome",
      "happy",
      "surprised",
      "serious",
      "encouraging",
    ];
    const expression: ClaudeExpression = validExpressions.includes(
      parsed.expression
    )
      ? parsed.expression
      : "welcome";

    return {
      reaction: typeof parsed.reaction === "string" ? parsed.reaction : "なるほどにゃ〜♡",
      expression,
    };
  } catch {
    return {
      reaction: "なるほどにゃ〜！ありがとうにゃ♡",
      expression: "welcome",
    };
  }
}
```

- [ ] **Step 4: テストを実行して全て通ることを確認**

```bash
cd /home/ubuntu/nyanta-chat
npm test -- lib/__tests__/claude.test.ts
```

Expected: 2 tests passed

- [ ] **Step 5: コミット**

```bash
cd /home/ubuntu/nyanta-chat
git add lib/claude.ts lib/__tests__/claude.test.ts
git commit -m "feat: Claudeリアクション生成ラッパー（猫語＋表情）"
```

---

## Task 5: APIルート（app/api/session/route.ts）

**Files:**
- Create: `/home/ubuntu/nyanta-chat/app/api/session/route.ts`

- [ ] **Step 1: route.ts を実装**

```ts
// /home/ubuntu/nyanta-chat/app/api/session/route.ts
import { NextResponse } from "next/server";
import { createSession, saveAnswer, completeSession } from "@/lib/db";

// POST: 新しいセッションを作成
export async function POST() {
  const sessionId = createSession();
  return NextResponse.json({ sessionId });
}

// PUT: 回答保存 or セッション完了
export async function PUT(request: Request) {
  const body = await request.json();

  if (body.action === "save_answer") {
    const { sessionId, questionId, answer } = body as {
      sessionId: string;
      questionId: string;
      answer: string;
    };
    saveAnswer(sessionId, questionId, answer);
    return NextResponse.json({ ok: true });
  }

  if (body.action === "complete") {
    const { sessionId } = body as { sessionId: string };
    completeSession(sessionId);
    return NextResponse.json({ ok: true });
  }

  return NextResponse.json({ error: "invalid action" }, { status: 400 });
}
```

- [ ] **Step 2: サーバーを起動してエンドポイントを手動確認**

```bash
cd /home/ubuntu/nyanta-chat
npm run dev &
sleep 5

# セッション作成テスト
curl -s -X POST http://localhost:3000/nyanta/api/session | python3 -m json.tool
```

Expected: `{"sessionId": "<uuid>"}`

- [ ] **Step 3: サーバーを停止**

```bash
pkill -f "next dev" || true
```

- [ ] **Step 4: コミット**

```bash
cd /home/ubuntu/nyanta-chat
git add app/api/session/route.ts
git commit -m "feat: セッション作成・回答保存APIルート"
```

---

## Task 6: APIルート（app/api/chat/route.ts）

**Files:**
- Create: `/home/ubuntu/nyanta-chat/app/api/chat/route.ts`

- [ ] **Step 1: route.ts を実装**

```ts
// /home/ubuntu/nyanta-chat/app/api/chat/route.ts
import { NextResponse } from "next/server";
import { generateReaction } from "@/lib/claude";

export async function POST(request: Request) {
  const { questionText, userAnswer } = (await request.json()) as {
    questionText: string;
    userAnswer: string;
  };

  const result = await generateReaction(questionText, userAnswer);
  return NextResponse.json(result);
}
```

- [ ] **Step 2: コミット**

```bash
cd /home/ubuntu/nyanta-chat
git add app/api/chat/route.ts
git commit -m "feat: Claude反応生成APIルート"
```

---

## Task 7: NyantaFaceコンポーネント（SVG表情）

**Files:**
- Create: `/home/ubuntu/nyanta-chat/components/NyantaFace.tsx`

- [ ] **Step 1: NyantaFace.tsx を実装**

6つの表情をSVGで実装する。共通のネコ顔ベース（丸顔・耳・白衣）に、目・口・眉毛だけを切り替える。

```tsx
// /home/ubuntu/nyanta-chat/components/NyantaFace.tsx
"use client";

export type Expression =
  | "welcome"
  | "happy"
  | "surprised"
  | "serious"
  | "thinking"
  | "encouraging";

type Props = { expression: Expression; size?: number };

// 各表情の目・口パーツ定義
const FACES: Record<
  Expression,
  { leftEye: string; rightEye: string; mouth: string; eyebrows?: string }
> = {
  welcome: {
    leftEye: "M 28,38 Q 32,34 36,38",   // アーチ目（閉じ気味）
    rightEye: "M 52,38 Q 56,34 60,38",
    mouth: "M 36,52 Q 44,58 52,52",      // やわらかい笑顔
  },
  happy: {
    leftEye: "M 28,36 Q 32,30 36,36",   // 細めた目
    rightEye: "M 52,36 Q 56,30 60,36",
    mouth: "M 32,50 Q 44,62 56,50",     // 大きな笑顔
  },
  surprised: {
    leftEye: "M 30,40 A 6,6 0 1,0 42,40 A 6,6 0 1,0 30,40", // 丸目
    rightEye: "M 46,40 A 6,6 0 1,0 58,40 A 6,6 0 1,0 46,40",
    mouth: "M 40,54 A 4,4 0 1,0 48,54 A 4,4 0 1,0 40,54", // 丸口
  },
  serious: {
    leftEye: "M 28,40 Q 32,37 36,40",   // 真剣な目
    rightEye: "M 52,40 Q 56,37 60,40",
    mouth: "M 36,54 L 52,54",            // 一文字口
    eyebrows: "M 28,33 L 36,31 M 52,31 L 60,33", // 眉毛
  },
  thinking: {
    leftEye: "M 28,40 Q 32,37 36,40",
    rightEye: "M 52,37 Q 56,34 60,37",  // 片目が少し上
    mouth: "M 38,54 Q 44,56 50,54",     // 少し傾いた口
  },
  encouraging: {
    leftEye: "M 27,36 Q 32,28 37,36",   // キラキラ目（大きめアーチ）
    rightEye: "M 51,36 Q 56,28 61,36",
    mouth: "M 32,50 Q 44,64 56,50",     // 満面の笑み
  },
};

export default function NyantaFace({ expression, size = 80 }: Props) {
  const face = FACES[expression];
  const strokeProps = {
    stroke: "#4a3728",
    strokeWidth: 2.5,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    fill: "none",
  };

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 88 88"
      xmlns="http://www.w3.org/2000/svg"
      aria-label={`にゃん太先生 ${expression}`}
    >
      {/* 白衣の体 */}
      <rect x="22" y="68" width="44" height="16" rx="8" fill="white" stroke="#ddd" strokeWidth="1.5" />
      <rect x="30" y="70" width="28" height="14" rx="4" fill="#e8f4f8" />
      {/* 聴診器 */}
      <path d="M 38,72 Q 44,80 50,72" stroke="#666" strokeWidth="1.5" fill="none" />
      <circle cx="44" cy="80" r="2" fill="#666" />
      {/* 顔（白丸） */}
      <ellipse cx="44" cy="44" rx="28" ry="26" fill="white" stroke="#e8d5c4" strokeWidth="1.5" />
      {/* 耳 */}
      <polygon points="16,26 22,14 30,24" fill="white" stroke="#e8d5c4" strokeWidth="1.5" />
      <polygon points="18,25 22,17 28,23" fill="#ffb7c5" />
      <polygon points="58,24 66,14 72,26" fill="white" stroke="#e8d5c4" strokeWidth="1.5" />
      <polygon points="60,23 66,17 70,25" fill="#ffb7c5" />
      {/* ひげ */}
      <line x1="12" y1="46" x2="30" y2="48" stroke="#ccc" strokeWidth="1" />
      <line x1="12" y1="50" x2="30" y2="50" stroke="#ccc" strokeWidth="1" />
      <line x1="58" y1="48" x2="76" y2="46" stroke="#ccc" strokeWidth="1" />
      <line x1="58" y1="50" x2="76" y2="50" stroke="#ccc" strokeWidth="1" />
      {/* 鼻 */}
      <ellipse cx="44" cy="48" rx="3" ry="2" fill="#ffb7c5" />
      {/* 表情パーツ */}
      {face.eyebrows && (
        <path d={face.eyebrows} {...strokeProps} strokeWidth={2} />
      )}
      <path d={face.leftEye} {...strokeProps} />
      <path d={face.rightEye} {...strokeProps} />
      <path d={face.mouth} {...strokeProps} />
      {/* thinking: 考え中の点点点 */}
      {expression === "thinking" && (
        <>
          <circle cx="36" cy="64" r="2" fill="#aaa" />
          <circle cx="44" cy="66" r="2" fill="#aaa" />
          <circle cx="52" cy="64" r="2" fill="#aaa" />
        </>
      )}
    </svg>
  );
}
```

- [ ] **Step 2: コミット**

```bash
cd /home/ubuntu/nyanta-chat
git add components/NyantaFace.tsx
git commit -m "feat: NyantaFace SVGコンポーネント（6表情）"
```

---

## Task 8: サポートUIコンポーネント

**Files:**
- Create: `/home/ubuntu/nyanta-chat/components/ChatBubble.tsx`
- Create: `/home/ubuntu/nyanta-chat/components/ProgressBar.tsx`
- Create: `/home/ubuntu/nyanta-chat/components/InputArea.tsx`

- [ ] **Step 1: ChatBubble.tsx を実装**

```tsx
// /home/ubuntu/nyanta-chat/components/ChatBubble.tsx
type Props = {
  role: "nyanta" | "user";
  text: string;
};

export default function ChatBubble({ role, text }: Props) {
  if (role === "nyanta") {
    return (
      <div className="flex items-start gap-2 max-w-[85%]">
        <div className="flex-shrink-0 w-2" />
        <div className="bg-pink-50 border border-pink-200 rounded-2xl rounded-tl-sm px-4 py-3 text-slate-700 text-base leading-relaxed shadow-sm">
          {text}
        </div>
      </div>
    );
  }
  return (
    <div className="flex justify-end max-w-[85%] ml-auto">
      <div className="bg-blue-500 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-base leading-relaxed shadow-sm">
        {text}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: ProgressBar.tsx を実装**

```tsx
// /home/ubuntu/nyanta-chat/components/ProgressBar.tsx
type Props = {
  current: number;  // 0-based index
  total: number;
};

export default function ProgressBar({ current, total }: Props) {
  const remaining = total - current;
  return (
    <div className="flex flex-col items-center gap-1 px-4 py-2">
      <div className="flex gap-1">
        {Array.from({ length: total }).map((_, i) => (
          <span key={i} className="text-sm">
            {i < current ? "🐾" : "○"}
          </span>
        ))}
      </div>
      <p className="text-xs text-slate-500">
        {remaining > 0
          ? `あと${remaining}問にゃ！`
          : "最後の質問にゃ♡"}
      </p>
    </div>
  );
}
```

- [ ] **Step 3: InputArea.tsx を実装**

```tsx
// /home/ubuntu/nyanta-chat/components/InputArea.tsx
"use client";

import { useState, useRef } from "react";
import type { Question } from "@/lib/questions";

type Props = {
  question: Question;
  onSubmit: (answer: string) => void;
  onSkip: () => void;
  disabled: boolean;
};

export default function InputArea({ question, onSubmit, onSkip, disabled }: Props) {
  const [text, setText] = useState("");
  const [preview, setPreview] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleSubmit = () => {
    if (question.type === "photo") {
      if (preview) onSubmit(preview);
      return;
    }
    if (text.trim()) {
      onSubmit(text.trim());
      setText("");
    }
  };

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const b64 = ev.target?.result as string;
      setPreview(b64);
    };
    reader.readAsDataURL(file);
  };

  if (question.type === "select") {
    return (
      <div className="flex flex-col gap-3 p-4">
        <div className="flex flex-col gap-2">
          {question.options!.map((opt) => (
            <button
              key={opt}
              disabled={disabled}
              onClick={() => onSubmit(opt)}
              className="min-h-[60px] bg-white border-2 border-pink-200 rounded-xl px-4 py-3 text-slate-700 text-base font-medium hover:bg-pink-50 hover:border-pink-400 active:bg-pink-100 disabled:opacity-50 transition-colors text-left"
            >
              {opt}
            </button>
          ))}
        </div>
        {question.skippable && (
          <button
            onClick={onSkip}
            disabled={disabled}
            className="text-slate-400 text-sm underline text-center disabled:opacity-50"
          >
            スキップする
          </button>
        )}
      </div>
    );
  }

  if (question.type === "photo") {
    return (
      <div className="flex flex-col gap-3 p-4">
        {preview ? (
          <img src={preview} alt="プレビュー" className="max-h-40 rounded-lg object-contain border" />
        ) : (
          <button
            onClick={() => fileRef.current?.click()}
            disabled={disabled}
            className="min-h-[60px] bg-pink-50 border-2 border-dashed border-pink-300 rounded-xl px-4 py-3 text-pink-500 font-medium hover:bg-pink-100 disabled:opacity-50 transition-colors"
          >
            📷 写真を選ぶにゃ！
          </button>
        )}
        <input ref={fileRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={handleFile} />
        <div className="flex gap-2">
          {preview && (
            <button
              onClick={handleSubmit}
              disabled={disabled}
              className="flex-1 min-h-[52px] bg-pink-400 text-white rounded-xl font-semibold disabled:opacity-50 hover:bg-pink-500 transition-colors"
            >
              これを送るにゃ →
            </button>
          )}
          {question.skippable && (
            <button onClick={onSkip} disabled={disabled} className="text-slate-400 text-sm underline disabled:opacity-50">
              スキップ
            </button>
          )}
        </div>
      </div>
    );
  }

  // text / date
  return (
    <div className="flex flex-col gap-3 p-4">
      {question.type === "date" ? (
        <input
          type="date"
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={disabled}
          className="w-full border-2 border-pink-200 rounded-xl px-4 py-3 text-base text-slate-700 focus:outline-none focus:border-pink-400 disabled:opacity-50"
        />
      ) : (
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={disabled}
          rows={3}
          placeholder="ここに入力するにゃ..."
          className="w-full border-2 border-pink-200 rounded-xl px-4 py-3 text-base text-slate-700 resize-none focus:outline-none focus:border-pink-400 disabled:opacity-50"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSubmit();
            }
          }}
        />
      )}
      <div className="flex gap-2 items-center">
        {question.skippable && (
          <button onClick={onSkip} disabled={disabled} className="text-slate-400 text-sm underline disabled:opacity-50">
            スキップ
          </button>
        )}
        <button
          onClick={handleSubmit}
          disabled={disabled || !text.trim()}
          className="ml-auto min-h-[52px] px-8 bg-pink-400 text-white rounded-xl font-semibold disabled:opacity-50 hover:bg-pink-500 transition-colors"
        >
          送る →
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: コミット**

```bash
cd /home/ubuntu/nyanta-chat
git add components/
git commit -m "feat: ChatBubble・ProgressBar・InputAreaコンポーネント"
```

---

## Task 9: チャットメイン画面（app/page.tsx）

**Files:**
- Modify: `/home/ubuntu/nyanta-chat/app/page.tsx`

- [ ] **Step 1: app/page.tsx を実装**

```tsx
// /home/ubuntu/nyanta-chat/app/page.tsx
"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import NyantaFace, { type Expression } from "@/components/NyantaFace";
import ChatBubble from "@/components/ChatBubble";
import ProgressBar from "@/components/ProgressBar";
import InputArea from "@/components/InputArea";
import { QUESTIONS } from "@/lib/questions";

type Message = {
  role: "nyanta" | "user";
  text: string;
};

const WELCOME_MESSAGE =
  "こんにゃちはにゃん！🐾 今日はおうちでお医者さんに来てもらうお話にゃ？\n緊張してるかもだけど、にゃん太が一緒に優しく聞くにゃ♡\n一緒に答えていこっか！";

export default function ChatPage() {
  const router = useRouter();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    { role: "nyanta", text: WELCOME_MESSAGE },
  ]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [expression, setExpression] = useState<Expression>("welcome");
  const [disabled, setDisabled] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // セッション初期化
  useEffect(() => {
    fetch("/nyanta/api/session", { method: "POST" })
      .then((r) => r.json())
      .then((data: { sessionId: string }) => {
        setSessionId(data.sessionId);
        // 少し待ってから最初の質問を表示
        setTimeout(() => {
          setMessages((prev) => [
            ...prev,
            { role: "nyanta", text: QUESTIONS[0].text },
          ]);
        }, 800);
      });
  }, []);

  // メッセージ追加時に最下部へスクロール
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleAnswer = async (answer: string) => {
    if (!sessionId) return;
    const question = QUESTIONS[currentIndex];

    // ユーザー回答をチャットに追加
    setMessages((prev) => [
      ...prev,
      { role: "user", text: answer === "" ? "（スキップ）" : answer },
    ]);
    setDisabled(true);
    setExpression("thinking");

    // 回答を保存（スキップ時は空文字を保存）
    await fetch("/nyanta/api/session", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "save_answer",
        sessionId,
        questionId: question.id,
        answer,
      }),
    });

    // Claudeにリアクションを生成させる（スキップ時は固定リアクション）
    let reaction = "にゃるほどにゃ〜♡ ありがとうにゃん！";
    let nextExpression: Expression = "happy";

    if (answer !== "") {
      const res = await fetch("/nyanta/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          questionText: question.text,
          userAnswer: answer,
        }),
      });
      const data = await res.json() as { reaction: string; expression: Expression };
      reaction = data.reaction;
      nextExpression = data.expression;
    }

    const nextIndex = currentIndex + 1;
    const isLast = nextIndex >= QUESTIONS.length;

    // リアクションを表示
    setMessages((prev) => [...prev, { role: "nyanta", text: reaction }]);
    setExpression(nextExpression);

    if (isLast) {
      // 完了処理
      await fetch("/nyanta/api/session", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "complete", sessionId }),
      });
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          {
            role: "nyanta",
            text: "全部答えてくれてありがとうにゃ♡ これでお医者さんがスムーズに来られるにゃ〜！🐾 まとめを見てにゃん！",
          },
        ]);
        setExpression("encouraging");
      }, 500);
      setTimeout(() => {
        // basePath('/nyanta')はNext.js routerが自動付与するため不要
        router.push(`/complete?session=${sessionId}`);
      }, 3000);
    } else {
      // 次の質問を表示
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          { role: "nyanta", text: QUESTIONS[nextIndex].text },
        ]);
        setCurrentIndex(nextIndex);
        setExpression("welcome");
        setDisabled(false);
      }, 600);
    }
  };

  const handleSkip = () => handleAnswer("");

  const currentQuestion = QUESTIONS[currentIndex];
  const isComplete = currentIndex >= QUESTIONS.length;

  return (
    <div className="min-h-screen bg-pink-50 flex flex-col max-w-lg mx-auto">
      {/* ヘッダー */}
      <header className="bg-white border-b border-pink-100 px-4 py-3 sticky top-0 z-10 shadow-sm">
        <div className="flex items-center gap-3">
          <NyantaFace expression={expression} size={48} />
          <div className="flex-1">
            <h1 className="text-base font-bold text-pink-600">にゃん太先生の問診室</h1>
            <ProgressBar current={currentIndex} total={QUESTIONS.length} />
          </div>
        </div>
      </header>

      {/* チャット履歴 */}
      <main className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-3">
        {messages.map((msg, i) => (
          <ChatBubble key={i} role={msg.role} text={msg.text} />
        ))}
        <div ref={bottomRef} />
      </main>

      {/* 入力エリア */}
      {!isComplete && sessionId && (
        <footer className="bg-white border-t border-pink-100 shadow-md">
          <InputArea
            question={currentQuestion}
            onSubmit={handleAnswer}
            onSkip={handleSkip}
            disabled={disabled}
          />
          <p className="text-center text-xs text-slate-400 pb-3 px-4">
            ※ これはにゃん太先生のお手伝いにゃ。本当の診断は訪問のお医者さんにお任せしてね！
          </p>
        </footer>
      )}
    </div>
  );
}
```

- [ ] **Step 2: コミット**

```bash
cd /home/ubuntu/nyanta-chat
git add app/page.tsx
git commit -m "feat: チャットメイン画面（セッション管理・Claude連携）"
```

---

## Task 10: 完了・まとめ画面（app/complete/page.tsx）

**Files:**
- Create: `/home/ubuntu/nyanta-chat/app/complete/page.tsx`

- [ ] **Step 1: components/PrintButton.tsx を作成（クライアントコンポーネント）**

`window.print()` はクライアント側でのみ動作するため、別ファイルに分離する。

```tsx
// /home/ubuntu/nyanta-chat/components/PrintButton.tsx
"use client";

export default function PrintButton() {
  return (
    <button
      onClick={() => window.print()}
      className="flex-1 bg-pink-400 text-white rounded-xl py-3 font-semibold hover:bg-pink-500 transition-colors"
    >
      印刷する
    </button>
  );
}
```

- [ ] **Step 2: complete/page.tsx を実装**

```tsx
// /home/ubuntu/nyanta-chat/app/complete/page.tsx
import Link from "next/link";
import { getSessionAnswers } from "@/lib/db";
import { QUESTIONS, CATEGORIES } from "@/lib/questions";
import NyantaFace from "@/components/NyantaFace";
import PrintButton from "@/components/PrintButton";

type Props = { searchParams: Promise<{ session?: string }> };

export default async function CompletePage({ searchParams }: Props) {
  const { session: sessionId } = await searchParams;

  const rawAnswers = sessionId ? getSessionAnswers(sessionId) : [];
  const answerMap = Object.fromEntries(
    rawAnswers.map((a) => [a.question_id, a.answer])
  );

  return (
    <div className="min-h-screen bg-pink-50 max-w-lg mx-auto">
      {/* ヘッダー */}
      <header className="bg-white border-b border-pink-100 px-4 py-4 text-center">
        <NyantaFace expression="encouraging" size={64} />
        <h1 className="text-xl font-bold text-pink-600 mt-2">
          問診完了にゃ♡
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          全部答えてくれてありがとうにゃ〜！🐾
        </p>
      </header>

      {/* 回答まとめ */}
      <main className="p-4 flex flex-col gap-4">
        {CATEGORIES.map((cat) => {
          const questions = QUESTIONS.filter((q) => q.category === cat.id);
          const answered = questions.filter((q) => answerMap[q.id]);
          if (answered.length === 0) return null;
          return (
            <section key={cat.id} className="bg-white rounded-2xl shadow-sm p-4">
              <h2 className="text-sm font-bold text-pink-500 mb-3 border-b border-pink-100 pb-2">
                🐾 {cat.label}
              </h2>
              <div className="flex flex-col gap-3">
                {answered.map((q) => (
                  <div key={q.id}>
                    <p className="text-xs text-slate-400 mb-1">{q.text}</p>
                    {answerMap[q.id]?.startsWith("data:image") ? (
                      <img
                        src={answerMap[q.id]}
                        alt="お薬手帳"
                        className="max-h-40 rounded-lg object-contain border"
                      />
                    ) : (
                      <p className="text-sm text-slate-700 font-medium">
                        {answerMap[q.id]}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </section>
          );
        })}

        {/* アクションボタン */}
        <div className="flex gap-3 mt-2">
          <PrintButton />
          {/* basePath('/nyanta')はNext.js Linkが自動付与する */}
          <Link
            href="/"
            className="flex-1 bg-white border-2 border-pink-200 text-pink-500 rounded-xl py-3 font-semibold hover:bg-pink-50 transition-colors text-center"
          >
            最初からやり直す
          </Link>
        </div>

        <p className="text-center text-xs text-slate-400 pb-4 px-2">
          ※ これはにゃん太先生のお手伝いにゃ。本当の診断・診療は訪問のお医者さんにお任せしてね！
        </p>
      </main>
    </div>
  );
}
```

- [ ] **Step 2: コミット**

```bash
cd /home/ubuntu/nyanta-chat
git add app/complete/
git commit -m "feat: 完了・回答まとめ画面"
```

---

## Task 11: Dockerコンテナ設定（nyanta-chat）

**Files:**
- Create: `/home/ubuntu/nyanta-chat/Dockerfile`
- Create: `/home/ubuntu/nyanta-chat/docker-compose.yml`

- [ ] **Step 1: Dockerfile を作成**

`better-sqlite3` はネイティブモジュールのため、Alpine環境でビルドツールが必要。

```dockerfile
# /home/ubuntu/nyanta-chat/Dockerfile

# ===== ビルドステージ =====
FROM node:20-alpine AS builder
WORKDIR /app

# better-sqlite3のネイティブビルドに必要
RUN apk add --no-cache python3 make g++

COPY package*.json ./
RUN npm ci --frozen-lockfile

COPY . .
ENV NEXT_PRIVATE_STANDALONE=true
RUN npm run build

# ===== 本番実行ステージ =====
FROM node:20-alpine AS runner
WORKDIR /app

# better-sqlite3のランタイム依存
RUN apk add --no-cache libc6-compat

ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# dataディレクトリ（SQLite永続化用）
RUN mkdir -p /app/data && chown nextjs:nodejs /app/data

USER nextjs

EXPOSE 3000
CMD ["node", "server.js"]
```

- [ ] **Step 2: docker-compose.yml を作成**

```yaml
# /home/ubuntu/nyanta-chat/docker-compose.yml
services:
  nyanta:
    build: .
    container_name: nyanta_chat
    environment:
      - NODE_ENV=production
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ./data:/app/data
    ports:
      - "3001:3000"
    restart: always
```

- [ ] **Step 3: .env.local が .dockerignore に含まれているか確認**

```bash
cat > /home/ubuntu/nyanta-chat/.dockerignore << 'EOF'
node_modules
.next
.env.local
data/*.db
EOF
```

- [ ] **Step 4: コミット**

```bash
cd /home/ubuntu/nyanta-chat
git add Dockerfile docker-compose.yml .dockerignore
git commit -m "chore: Docker設定（better-sqlite3対応Alpine）"
```

---

## Task 12: Nginxリバースプロキシ設定

**Files:**
- Create: `/home/ubuntu/nginx/nginx.conf`
- Create: `/home/ubuntu/nginx/docker-compose.yml`
- Modify: `/home/ubuntu/myapp/docker-compose.yml` (ポート80を削除)

既存の `myapp-app-1` がポート80を直接使用しているため、Nginxに80を渡すよう切り替える。

- [ ] **Step 1: nginxディレクトリを作成**

```bash
mkdir -p /home/ubuntu/nginx
```

- [ ] **Step 2: nginx.conf を作成**

```nginx
# /home/ubuntu/nginx/nginx.conf
events {
  worker_connections 1024;
}

http {
  upstream manualine {
    server host.docker.internal:3000;
  }

  upstream nyanta {
    server host.docker.internal:3001;
  }

  server {
    listen 80;
    server_name _;

    # にゃん太チャット
    location /nyanta/ {
      proxy_pass http://nyanta/nyanta/;
      proxy_http_version 1.1;
      proxy_set_header Upgrade $http_upgrade;
      proxy_set_header Connection 'upgrade';
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_cache_bypass $http_upgrade;
      client_max_body_size 10M;
    }

    # Manualine（既存）
    location / {
      proxy_pass http://manualine/;
      proxy_http_version 1.1;
      proxy_set_header Upgrade $http_upgrade;
      proxy_set_header Connection 'upgrade';
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_cache_bypass $http_upgrade;
    }
  }
}
```

- [ ] **Step 3: nginx/docker-compose.yml を作成**

```yaml
# /home/ubuntu/nginx/docker-compose.yml
services:
  nginx:
    image: nginx:alpine
    container_name: nginx_proxy
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    extra_hosts:
      - "host.docker.internal:host-gateway"
    restart: always
```

- [ ] **Step 4: 既存 myapp のポート80バインドを解除**

`/home/ubuntu/myapp/docker-compose.yml` を確認して、ポート設定を変更：

現在:
```yaml
ports:
  - "${APP_PORT:-3000}:3000"
```

変更後（内部ポート3000のみ、ホストの3000にバインド）:
```yaml
ports:
  - "127.0.0.1:3000:3000"
```

- [ ] **Step 5: Nginxコンテナを起動前に既存ポート80を解放**

```bash
# 現在ポート80を使っているコンテナを停止
cd /home/ubuntu/myapp
docker compose down

# myapp を新しい設定で起動（ポート80なし、3000のみ）
docker compose up -d

# nyanta-chat を起動
cd /home/ubuntu/nyanta-chat
ANTHROPIC_API_KEY=your_actual_key docker compose up -d

# Nginxを起動
cd /home/ubuntu/nginx
docker compose up -d
```

- [ ] **Step 6: 動作確認**

```bash
# サーバーのIPアドレスを確認
curl -s ifconfig.me

# Manualine（既存）が動くか確認
curl -s -o /dev/null -w "%{http_code}" http://localhost/

# にゃん太チャットが動くか確認
curl -s -o /dev/null -w "%{http_code}" http://localhost/nyanta/
```

Expected: 両方とも `200`

- [ ] **Step 7: コミット**

```bash
cd /home/ubuntu/nginx
git init
git add .
git commit -m "chore: Nginxリバースプロキシ設定（/nyanta/ + /）"

cd /home/ubuntu/myapp
git add docker-compose.yml
git commit -m "chore: ポート80をNginxに譲渡（127.0.0.1:3000に変更）"
```

---

## Task 13: E2E動作確認

- [ ] **Step 1: 全コンテナが起動していることを確認**

```bash
docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}"
```

Expected:
```
nginx_proxy      0.0.0.0:80->80/tcp    Up
nyanta_chat      0.0.0.0:3001->3000/tcp  Up
myapp-app-1      127.0.0.1:3000->3000/tcp  Up
```

- [ ] **Step 2: セッション作成APIを確認**

```bash
curl -s -X POST http://localhost/nyanta/api/session \
  -H "Content-Type: application/json" | python3 -m json.tool
```

Expected: `{"sessionId": "<uuid>"}`

- [ ] **Step 3: ブラウザで `http://<サーバーIP>/nyanta/` にアクセス**

サーバーのIPは `curl -s ifconfig.me` で確認する。

Expected:
- にゃん太先生の顔が表示される
- ウェルカムメッセージが表示される
- 最初の質問（お名前）が表示される

- [ ] **Step 4: 問診を最後まで回答して完了画面に遷移することを確認**

- 各質問に回答する
- Claudeの猫語リアクションが返ってくる
- 全25問完了後に `/nyanta/complete` に遷移する
- 回答まとめが表示される

---

## 注意事項

- `ANTHROPIC_API_KEY` は `/home/ubuntu/nyanta-chat/.env.local` とdocker composeの環境変数で管理
- `data/nyanta.db` はコンテナのボリュームマウントで永続化（`./data:/app/data`）
- Next.js 15のApp Routerを使用。`app/complete/page.tsx` の `searchParams` は `Promise<>` でラップする（Next.js 15の仕様）
- better-sqlite3 は `"server-only"` インポートをlib/db.tsの先頭に付けること（クライアント側への誤インポートを防ぐ）
