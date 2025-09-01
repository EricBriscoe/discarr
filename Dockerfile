FROM node:18-alpine AS base
WORKDIR /app

# Install dependencies (monorepo)
COPY package.json ./
COPY package-lock.json ./
COPY tsconfig.base.json ./
COPY packages/core/package.json packages/core/package.json
COPY packages/discord-bot/package.json packages/discord-bot/package.json
COPY apps/server/package.json apps/server/package.json
COPY apps/web/package.json apps/web/package.json
RUN npm ci

# Build all packages
COPY . .
RUN npm run build

FROM node:18-alpine AS runtime
ENV NODE_ENV=production
WORKDIR /app

# Copy package manifests and install production deps
COPY package.json ./
COPY package-lock.json ./
COPY packages/core/package.json packages/core/package.json
COPY packages/discord-bot/package.json packages/discord-bot/package.json
COPY apps/server/package.json apps/server/package.json
COPY apps/web/package.json apps/web/package.json
RUN npm ci --omit=dev

# Copy built artifacts
COPY --from=base /app/packages /app/packages
COPY --from=base /app/apps/server/dist /app/apps/server/dist
COPY --from=base /app/apps/web/dist /app/apps/web/dist

# Security: non-root user
RUN addgroup -g 1001 -S nodejs && adduser -S discarr -u 1001
RUN chown -R discarr:nodejs /app
USER discarr

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD node -e "require('http').get('http://127.0.0.1:8080/api/health', r => process.exit(r.statusCode===200?0:1)).on('error', _=>process.exit(1))"

CMD ["node", "apps/server/dist/server.js"]
