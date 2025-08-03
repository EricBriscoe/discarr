FROM node:18-alpine

WORKDIR /app

# Set environment variables for better container logging
ENV NODE_ENV=production \
    NPM_CONFIG_CACHE=/tmp/.npm

# Install dependencies
COPY package*.json ./
RUN npm ci --only=production

# Copy source code and build
COPY . .
RUN npm run build

# Create a volume mount point for persistent data (backward compatibility)
VOLUME ["/app/config"]

# Verify the installation
RUN node --version && npm --version && ls -la dist/

# Run the application
CMD ["npm", "start"]
