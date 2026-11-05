#!/bin/bash
# =============================================================================
# new-service.sh — 新サービス追加スクリプト（サービスごとに実行）
# 実行: bash new-service.sh <ドメイン> [nextjs|static]
# 例:   bash new-service.sh example.com nextjs
# =============================================================================
set -euo pipefail

DOMAIN="${1:-}"
APP_TYPE="${2:-nextjs}"

if [[ -z "$DOMAIN" ]]; then
  echo "使い方: bash new-service.sh <ドメイン名> [nextjs|static]"
  exit 1
fi

# サービス名はドメインの . を _ に変換 (Traefik のラベル用)
SERVICE_NAME=$(echo "$DOMAIN" | tr '.' '_')
PROJECT_DIR="/opt/services/${DOMAIN}"

echo "=============================================="
echo " サービス作成: ${DOMAIN} (${APP_TYPE})"
echo "=============================================="

# ディレクトリ構成
mkdir -p "${PROJECT_DIR}"
cd "${PROJECT_DIR}"

# ランダムシークレット生成
JWT_SECRET=$(openssl rand -hex 32)

echo "--- .env 生成"
cat > .env <<EOF
DOMAIN=${DOMAIN}
NODE_ENV=production
JWT_SECRET=${JWT_SECRET}
# DB を使う場合はコメント解除:
# DATABASE_URL=file:/app/data/db.sqlite
EOF

# =============================================================================
# Next.js 構成
# =============================================================================
if [[ "$APP_TYPE" == "nextjs" ]]; then

echo "--- Dockerfile 生成 (Next.js)"
cat > Dockerfile <<'DOCKERFILE'
FROM node:22-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000
CMD ["node", "server.js"]
DOCKERFILE

echo "--- docker-compose.yml 生成 (Next.js)"
cat > docker-compose.yml <<EOF
services:
  app:
    build: .
    container_name: ${SERVICE_NAME}_app
    env_file: .env
    volumes:
      - ./data:/app/data
    networks:
      - proxy
    restart: always
    labels:
      - traefik.enable=true
      - traefik.http.routers.${SERVICE_NAME}.rule=Host(\`${DOMAIN}\`)
      - traefik.http.routers.${SERVICE_NAME}.entrypoints=websecure
      - traefik.http.routers.${SERVICE_NAME}.tls.certresolver=le
      - traefik.http.services.${SERVICE_NAME}.loadbalancer.server.port=3000

networks:
  proxy:
    external: true
EOF

mkdir -p data

echo "--- .dockerignore 生成"
cat > .dockerignore <<'EOF'
node_modules
.next
.git
.env*
*.md
EOF

echo ""
echo "Next.js サービス作成完了: ${PROJECT_DIR}"
echo ""
echo "次のステップ:"
echo "  1. Next.js のソースを ${PROJECT_DIR}/ に配置"
echo "     (next.config.js に output: 'standalone' を追加する)"
echo "  2. cd ${PROJECT_DIR} && docker compose up -d --build"

# =============================================================================
# 静的HTML構成
# =============================================================================
elif [[ "$APP_TYPE" == "static" ]]; then

echo "--- docker-compose.yml 生成 (静的HTML)"
cat > docker-compose.yml <<EOF
services:
  app:
    image: nginx:alpine
    container_name: ${SERVICE_NAME}_app
    volumes:
      - ./html:/usr/share/nginx/html:ro
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    networks:
      - proxy
    restart: always
    labels:
      - traefik.enable=true
      - traefik.http.routers.${SERVICE_NAME}.rule=Host(\`${DOMAIN}\`)
      - traefik.http.routers.${SERVICE_NAME}.entrypoints=websecure
      - traefik.http.routers.${SERVICE_NAME}.tls.certresolver=le
      - traefik.http.services.${SERVICE_NAME}.loadbalancer.server.port=80

networks:
  proxy:
    external: true
EOF

cat > nginx.conf <<'EOF'
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    gzip on;
    gzip_types text/plain text/css application/javascript application/json;
}
EOF

mkdir -p html
cat > html/index.html <<EOF
<!DOCTYPE html>
<html lang="ja">
<head><meta charset="UTF-8"><title>${DOMAIN}</title></head>
<body>
  <h1>${DOMAIN} は稼働中</h1>
  <p>Claude がコードを注入するのを待っています...</p>
</body>
</html>
EOF

# コンテナ起動
docker compose up -d
echo ""
echo "静的サイト起動完了: https://${DOMAIN}"
echo "(DNSがこのサーバーを向いていればSSLは自動取得されます)"

else
  echo "エラー: APP_TYPEは 'nextjs' または 'static' を指定してください"
  exit 1
fi

echo ""
echo "=============================================="
echo " 管理コマンド一覧"
echo "=============================================="
echo "  ログ確認:    cd ${PROJECT_DIR} && docker compose logs -f"
echo "  再起動:      cd ${PROJECT_DIR} && docker compose restart"
echo "  ビルド&起動: cd ${PROJECT_DIR} && docker compose up -d --build"
echo "  停止:        cd ${PROJECT_DIR} && docker compose down"
echo "  SSL確認:     docker exec traefik cat /acme.json | jq '.le.Certificates[].domain'"
echo ""
