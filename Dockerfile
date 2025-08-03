FROM node:18-alpine

# Create non-root user for security
RUN addgroup -g 1001 -S nodejs && \
    adduser -S discarr -u 1001

WORKDIR /app

# Set npm cache location (don't set NODE_ENV=production yet as it prevents devDependencies)
ENV NPM_CONFIG_CACHE=/tmp/.npm

# Copy package files and install ALL dependencies (including devDependencies)
COPY package*.json ./
RUN npm ci

# Copy source code and build the application
COPY . .
RUN npm run build

# Now set production environment and remove devDependencies to minimize image size
ENV NODE_ENV=production
RUN npm prune --production && npm cache clean --force

# Remove source files and keep only built artifacts
RUN rm -rf src/ tsconfig.json .eslintrc.* prettier.config.* && \
    find . -name "*.ts" -not -path "./node_modules/*" -delete && \
    find . -name "*.map" -delete

# Change ownership to non-root user
RUN chown -R discarr:nodejs /app
USER discarr

# Create a volume mount point for persistent data
VOLUME ["/app/config"]

# Health check for Discord bot - check if process is running and can import config
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD node -e "try { require('./dist/config.js'); process.exit(0); } catch(e) { process.exit(1); }"

# Run the application directly with node instead of npm for better signal handling
CMD ["node", "dist/index.js"]
