#!/bin/bash
# VPS上で実行されるデプロイスクリプト（GitHub ActionsからSSH経由でパイプ実行）
set -e

echo "=== デプロイ開始 ==="

# バックアップ
timestamp=$(date +%Y%m%d-%H%M%S)
mkdir -p ~/vps-backups

if [ -d ~/services/manualine.tech ]; then
  cp -r ~/services/manualine.tech ~/vps-backups/manualine-$timestamp
  echo "✅ バックアップ完了: manualine-$timestamp"
fi

# コード取得
rm -rf ~/services/manualine.tech
mkdir -p ~/services/manualine.tech
git clone https://github.com/tao-munakata/myapp.git ~/services/manualine.tech
cd ~/services/manualine.tech

echo "✅ コード取得完了"

# ビルド & 起動
docker compose -f docker-compose.prod.yml up -d --build
echo "✅ コンテナ起動完了"

# ヘルスチェック（最大30秒）
for i in $(seq 1 6); do
  sleep 5
  if docker compose -f ~/services/manualine.tech/docker-compose.prod.yml ps | grep -q "Up"; then
    echo "✅ ヘルスチェック OK"
    exit 0
  fi
  echo "⏳ 起動待機中... ($i/6)"
done

echo "❌ コンテナ起動タイムアウト"
docker compose -f ~/services/manualine.tech/docker-compose.prod.yml logs --tail=50
exit 1
