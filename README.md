# Discarr

A Discord bot for monitoring Radarr, Sonarr, and Plex instances with real-time download tracking.

## Requirements

- Node.js 18+
- Discord Bot Token & Client ID
- Radarr and/or Sonarr with API access

## Quick Start

### Node.js (Local)

1. **Clone and install**
   ```bash
   git clone https://github.com/EricBriscoe/discarr.git
   cd discarr
   npm install
   ```

2. **Configure**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Build and run**
   ```bash
   npm run build
   npm start
   ```

### Docker

1. **Setup configuration**
   ```bash
   git clone https://github.com/EricBriscoe/discarr.git
   cd discarr
   cp .env.example config/.env
   # Edit config/.env with your settings
   ```

2. **Run with Docker Compose**
   ```bash
   docker-compose up -d
   ```

## Configuration

Edit `.env` (local) or `config/.env` (Docker) with your settings:

```env
# Discord
DISCORD_TOKEN=your_discord_bot_token
DISCORD_CHANNEL_ID=your_channel_id
DISCORD_CLIENT_ID=your_client_id

# Radarr
RADARR_URL=http://localhost:7878
RADARR_API_KEY=your_radarr_api_key

# Sonarr  
SONARR_URL=http://localhost:8989
SONARR_API_KEY=your_sonarr_api_key

# Plex (optional)
PLEX_URL=http://localhost:32400

# Settings
CHECK_INTERVAL=300
HEALTH_CHECK_INTERVAL=60
VERBOSE=false
```

## Commands

- `/cleanup` - Remove all importBlocked items from Radarr and Sonarr queues

## License

MIT