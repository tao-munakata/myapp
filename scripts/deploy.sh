#!/bin/bash
# =============================================================================
# deploy.sh — 開発機から VPS に直接デプロイ
# 使い方: bash scripts/deploy.sh
# エラーが5回に達したら停止
# =============================================================================
set -euo pipefail

VPS_HOST="153.126.140.188"
VPS_USER="ubuntu"
VPS_SSH_KEY="$HOME/.ssh/deploy_key"
REMOTE_DIR="~/services/manualine.tech"
ERROR_COUNT_FILE="/tmp/manualine_deploy_errors"
MAX_ERRORS=5
BACKUP_DIR="$HOME/backups"

export PATH="$HOME/.local/bin:$PATH"

# ── エラーカウント確認 ────────────────────────────────
errors=$(cat "$ERROR_COUNT_FILE" 2>/dev/null || echo 0)
if [ "$errors" -ge "$MAX_ERRORS" ]; then
  echo "════════════════════════════════════════"
  echo "⛔ エラー上限 (${errors}/${MAX_ERRORS}) に達しました"
  echo "  人間の確認が必要です"
  echo "════════════════════════════════════════"
  exit 1
fi

# ── ローカルバックアップ ──────────────────────────────
mkdir -p "$BACKUP_DIR"
timestamp=$(date +%Y%m%d-%H%M%S)
rsync -a --exclude='.git' --exclude='node_modules' --exclude='__pycache__' \
  /home/ubuntu/myapp/ "$BACKUP_DIR/myapp-$timestamp/" 2>/dev/null || true
echo "✅ バックアップ: $BACKUP_DIR/myapp-$timestamp"

# ── git コミット & プッシュ ───────────────────────────
cd /home/ubuntu/myapp
if ! git diff --quiet || ! git diff --cached --quiet; then
  git add -A
  git commit -m "auto: $timestamp"
  git push origin main
  echo "✅ GitHub にプッシュ完了"
else
  echo "ℹ️  変更なし"
fi

# ── VPS にデプロイ ────────────────────────────────────
echo "🚀 VPS にデプロイ中..."

ssh -i "$VPS_SSH_KEY" \
    -o StrictHostKeyChecking=no \
    -o ConnectTimeout=15 \
    "${VPS_USER}@${VPS_HOST}" << ENDSSH
set -e

# コード取得
rm -rf ${REMOTE_DIR}
mkdir -p ${REMOTE_DIR}
git clone https://github.com/tao-munakata/myapp.git ${REMOTE_DIR}
cd ${REMOTE_DIR}

# コンテナ起動
docker compose -f docker-compose.prod.yml up -d --build

# ヘルスチェック
for i in \$(seq 1 6); do
  sleep 5
  if docker compose -f docker-compose.prod.yml ps | grep -q "Up\|running"; then
    echo "✅ 起動確認 OK"
    exit 0
  fi
  echo "⏳ 待機中 \$i/6..."
done

echo "❌ 起動タイムアウト"
docker compose -f docker-compose.prod.yml logs --tail=30
exit 1
ENDSSH

if [ $? -eq 0 ]; then
  echo "✅ デプロイ成功！"
  echo 0 > "$ERROR_COUNT_FILE"
  echo ""
  echo "🌐 https://manualine.tech"
else
  new_errors=$((errors + 1))
  echo "$new_errors" > "$ERROR_COUNT_FILE"
  echo "❌ デプロイ失敗 (${new_errors}/${MAX_ERRORS})"
  exit 1
fi
