#!/bin/bash
# =============================================================================
# setup-deploy-key.sh — VPS の SSH 鍵を生成して GitHub Secrets に登録
# VPS上で実行: bash setup-deploy-key.sh <GITHUB_TOKEN>
# =============================================================================
set -euo pipefail

TOKEN="${1:-}"
if [[ -z "$TOKEN" ]]; then
  echo "使い方: bash setup-deploy-key.sh <GITHUB_PERSONAL_ACCESS_TOKEN>"
  echo ""
  echo "トークン取得: https://github.com/settings/tokens"
  echo "  必要スコープ: repo, admin:public_key"
  exit 1
fi

REPO="tao-munakata/myapp"
KEY_PATH="/home/ubuntu/.ssh/github_deploy"

echo "[1/4] SSH 鍵ペア生成"
ssh-keygen -t ed25519 -f "$KEY_PATH" -N "" -C "manualine-deploy" -q
echo "✅ 鍵生成完了: $KEY_PATH"

echo "[2/4] 公開鍵を GitHub に登録（Deploy Key）"
curl -s -X POST \
  -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/$REPO/keys" \
  -d "{\"title\":\"manualine-vps-deploy\",\"key\":\"$(cat ${KEY_PATH}.pub)\",\"read_only\":true}" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('Key ID:', d.get('id','ERROR:', d))"

echo "[3/4] GitHub Secrets に登録"
# VPS_SSH_KEY
PRIVATE_KEY=$(cat "$KEY_PATH")
curl -s -X PUT \
  -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/$REPO/actions/secrets/VPS_SSH_KEY" \
  -d "{\"encrypted_value\":\"$(echo -n "$PRIVATE_KEY" | base64 -w0)\",\"key_id\":\"\"}" 2>/dev/null || \
echo "⚠️  VPS_SSH_KEY は GitHub UI から手動で登録してください（base64不要、秘密鍵をそのままペースト）"

# VPS_HOST
curl -s -X PUT \
  -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/$REPO/actions/secrets/VPS_HOST" \
  -d '{"encrypted_value":"MTUzLjEyNi4xNDAuMTg4","key_id":""}' 2>/dev/null || true

# VPS_USER
curl -s -X PUT \
  -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/$REPO/actions/secrets/VPS_USER" \
  -d '{"encrypted_value":"dWJ1bnR1","key_id":""}' 2>/dev/null || true

echo "[4/4] VPS の authorized_keys に公開鍵を追加"
cat "${KEY_PATH}.pub" >> /home/ubuntu/.ssh/authorized_keys
chmod 600 /home/ubuntu/.ssh/authorized_keys
echo "✅ authorized_keys に追加済み"

echo ""
echo "════════════════════════════════════════"
echo "✅ セットアップ完了"
echo ""
echo "GitHub Secrets に以下を手動登録してください:"
echo "  URL: https://github.com/$REPO/settings/secrets/actions"
echo ""
echo "  VPS_HOST  = 153.126.140.188"
echo "  VPS_USER  = ubuntu"
echo "  VPS_SSH_KEY = (以下の秘密鍵をそのままペースト)"
echo "────────────────────────────────────────"
cat "$KEY_PATH"
echo "────────────────────────────────────────"
