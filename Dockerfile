# ===== ビルドステージ =====
FROM node:20-alpine AS builder
WORKDIR /app

# 依存関係インストール
COPY package*.json ./
RUN npm ci --frozen-lockfile

# ソースコードコピー＆ビルド
COPY . .
# standalone出力を確実に生成するため環境変数を追加
ENV NEXT_PRIVATE_STANDALONE=true
RUN npm run build

# ===== 本番実行ステージ =====
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# 非rootユーザー作成
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# 必要なファイルだけコピー
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

# Next.js standaloneのserver.jsを実行
CMD ["node", "server.js"]
