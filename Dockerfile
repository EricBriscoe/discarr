FROM node:18-alpine

WORKDIR /app

# Set environment variables for better container logging
ENV NODE_ENV=production \
    NPM_CONFIG_CACHE=/tmp/.npm

# Install all dependencies (including devDependencies for build)
COPY package*.json ./
RUN npm ci

# Copy source code and build
COPY . .
RUN npm run build

# Remove devDependencies after build
RUN npm ci --only=production && npm cache clean --force

# Create a volume mount point for persistent data (backward compatibility)
VOLUME ["/app/config"]

# Verify the installation
RUN node --version && npm --version && ls -la dist/

# Run the application
CMD ["npm", "start"]
