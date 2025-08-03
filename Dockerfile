FROM node:18-alpine

WORKDIR /app

# Set environment variables for better container logging
ENV NODE_ENV=production \
    NPM_CONFIG_CACHE=/tmp/.npm

# Copy package files and install ALL dependencies (including devDependencies)
COPY package*.json ./
RUN npm ci

# Copy source code and build the application
COPY . .
RUN npm run build

# Remove devDependencies to minimize image size
RUN npm prune --production && npm cache clean --force

# Create a volume mount point for persistent data (backward compatibility)
VOLUME ["/app/config"]

# Verify the installation
RUN node --version && npm --version && ls -la dist/

# Run the application
CMD ["npm", "start"]
