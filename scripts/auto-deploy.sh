#!/bin/bash
# =============================================================================
# auto-deploy.sh — Claude Stop Hook: 自動バックアップ→コミット→プッシュ→CI監視
# エラーが5回に達したら中断して人間に判断を委ねる
# =============================================================================
set -euo pipefail

PROJECT_DIR="/home/ubuntu/myapp"
BACKUP_DIR="/home/ubuntu/backups"
ERROR_COUNT_FILE="/tmp/manualine_error_count"
MAX_ERRORS=5
GH_BIN="$HOME/.local/bin/gh"
export PATH="$HOME/.local/bin:$PATH"

cd "$PROJECT_DIR"

# ── エラーカウント確認 ────────────────────────────────────────
errors=$(cat "$ERROR_COUNT_FILE" 2>/dev/null || echo 0)
if [ "$errors" -ge "$MAX_ERRORS" ]; then
  echo "════════════════════════════════════════"
  echo "⛔ エラー上限 (${errors}/${MAX_ERRORS}) に達しました"
  echo "  人間の判断が必要です。以下を確認してください:"
  echo "  - 直近の CI/CD ログ: gh run view --log-failed"
  echo "  - バックアップ: ls $BACKUP_DIR"
  echo "════════════════════════════════════════"
  exit 1
fi

# ── バックアップ ──────────────────────────────────────────────
mkdir -p "$BACKUP_DIR"
timestamp=$(date +%Y%m%d-%H%M%S)
backup_path="$BACKUP_DIR/myapp-$timestamp"
cp -r "$PROJECT_DIR" "$backup_path" --exclude=".git" --exclude="node_modules" --exclude="__pycache__" 2>/dev/null || \
  rsync -a --exclude='.git' --exclude='node_modules' --exclude='__pycache__' \
    "$PROJECT_DIR/" "$backup_path/"
echo "✅ バックアップ完了: $backup_path"

# ── Git コミット & プッシュ ────────────────────────────────────
if git diff --quiet && git diff --cached --quiet; then
  echo "ℹ️  変更なし。スキップします。"
  exit 0
fi

git add -A
git commit -m "auto: $timestamp

🤖 Claude Code による自動コミット
エラー回数: ${errors}/${MAX_ERRORS}"

git push origin main
echo "✅ Push 完了"

# ── GitHub Actions 監視 ────────────────────────────────────────
if ! command -v "$GH_BIN" &>/dev/null; then
  echo "ℹ️  gh コマンドが未認証のため CI 監視をスキップ"
  exit 0
fi

echo "⏳ CI/CD を待機中..."
sleep 8

run_id=$("$GH_BIN" run list --limit 1 --json databaseId -q '.[0].databaseId' 2>/dev/null || echo "")
if [ -z "$run_id" ]; then
  echo "ℹ️  実行中の CI が見つかりません"
  exit 0
fi

# タイムアウト付きで待機（最大10分）
if "$GH_BIN" run watch "$run_id" --exit-status --interval 10 2>/dev/null; then
  echo "✅ デプロイ成功！"
  echo 0 > "$ERROR_COUNT_FILE"
else
  new_errors=$((errors + 1))
  echo "$new_errors" > "$ERROR_COUNT_FILE"

  echo "════════════════════════════════════════"
  echo "❌ デプロイ失敗 (エラー ${new_errors}/${MAX_ERRORS})"
  echo "── エラーログ ──────────────────────────"
  "$GH_BIN" run view "$run_id" --log-failed 2>/dev/null | tail -50 || true
  echo "════════════════════════════════════════"

  if [ "$new_errors" -ge "$MAX_ERRORS" ]; then
    echo "⛔ 次回の実行で停止します。人間の確認が必要です。"
  fi
  # 非ゼロで終了 → Claude がエラーを認識して修正ループへ
  exit 1
fi
