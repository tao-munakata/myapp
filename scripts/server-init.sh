#!/bin/bash
# =============================================================================
# server-init.sh — さくらVPS Ubuntu 24.04 初期セットアップ（サーバー1回のみ実行）
# 実行: bash server-init.sh your@email.com
# =============================================================================
set -euo pipefail

EMAIL="${1:-}"
if [[ -z "$EMAIL" ]]; then
  echo "使い方: bash server-init.sh your@email.com"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

echo "=============================================="
echo " [1/8] システムアップデート"
echo "=============================================="
apt-get update && apt-get upgrade -y
apt-get install -y ca-certificates curl gnupg lsb-release ufw fail2ban

echo "=============================================="
echo " [2/8] スワップ設定 (2GB)"
echo "=============================================="
if ! swapon --show | grep -q swap; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
  echo "vm.swappiness=10" >> /etc/sysctl.conf
  sysctl -p
  echo "スワップ: 2GB 設定完了"
else
  echo "スワップ: すでに設定済み"
fi

echo "=============================================="
echo " [3/8] fail2ban (SSH ブルートフォース対策)"
echo "=============================================="
systemctl enable fail2ban
systemctl start fail2ban
echo "fail2ban: 起動完了"

echo "=============================================="
echo " [4/8] Docker インストール"
echo "=============================================="
if ! command -v docker &>/dev/null; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg

  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | tee /etc/apt/sources.list.d/docker.list > /dev/null

  apt-get update
  apt-get install -y \
    docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin

  systemctl enable docker
  systemctl start docker
  echo "Docker: インストール完了"
else
  echo "Docker: すでにインストール済み"
fi

echo "=============================================="
echo " [5/8] ファイアウォール設定"
echo "=============================================="
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
echo "y" | ufw enable
echo "UFW: SSH/80/443 開放"

echo "=============================================="
echo " [6/8] 共有 Docker ネットワーク作成"
echo "=============================================="
docker network create proxy 2>/dev/null || echo "proxy ネットワーク: すでに存在"

echo "=============================================="
echo " [7/8] Traefik (リバースプロキシ + 自動SSL)"
echo "=============================================="
mkdir -p /opt/traefik

# Let's Encrypt の証明書ストレージ（権限必須）
touch /opt/traefik/acme.json
chmod 600 /opt/traefik/acme.json

cat > /opt/traefik/docker-compose.yml <<EOF
services:
  traefik:
    image: traefik:v3.3
    container_name: traefik
    command:
      - --log.level=INFO
      - --accesslog=true
      - --providers.docker=true
      - --providers.docker.exposedbydefault=false
      - --providers.docker.network=proxy
      - --entrypoints.web.address=:80
      - --entrypoints.web.http.redirections.entrypoint.to=websecure
      - --entrypoints.web.http.redirections.entrypoint.scheme=https
      - --entrypoints.websecure.address=:443
      - --certificatesresolvers.le.acme.email=${EMAIL}
      - --certificatesresolvers.le.acme.storage=/acme.json
      - --certificatesresolvers.le.acme.httpchallenge.entrypoint=web
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /opt/traefik/acme.json:/acme.json
    networks:
      - proxy
    restart: always

networks:
  proxy:
    external: true
EOF

cd /opt/traefik
docker compose up -d
echo "Traefik: 起動完了"

echo "=============================================="
echo " [8/8] サービスディレクトリ作成"
echo "=============================================="
mkdir -p /opt/services
echo "ディレクトリ: /opt/services 作成完了"

echo ""
echo "=============================================="
echo " セットアップ完了!"
echo "=============================================="
echo ""
echo "次のコマンドで新しいサービスを追加:"
echo "  bash new-service.sh <ドメイン名> [nextjs|static]"
echo ""
echo "例:"
echo "  bash new-service.sh example.com nextjs"
echo "  bash new-service.sh example.com static"
echo ""
