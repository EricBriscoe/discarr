# Discarr

A Discord bot for monitoring and managing your Radarr and Sonarr instances.

## Requirements

- Python 3.12+
- Discord Bot Token
- Radarr and/or Sonarr with API access

## Quick Start

### Python (Local)

1. **Clone and install**
   ```bash
   git clone https://github.com/EricBriscoe/discarr.git
   cd discarr
   pip install -r requirements.txt
   ```

2. **Configure**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Run**
   ```bash
   python bot.py
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

   **Or run manually**
   ```bash
   docker build -t discarr .
   docker run -d --env-file config/.env discarr
   ```

## Configuration

Edit `.env` (local) or `config/.env` (Docker) with your settings:

```env
# Discord
DISCORD_TOKEN=your_discord_bot_token
DISCORD_CHANNEL_ID=your_channel_id

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
VERBOSE=false
```

## Commands

- `/health` - Check service health status
- `/check` - Manually refresh downloads
- `/progress` - Show progress statistics (admin)
- `/cleanup` - Remove stuck downloads (admin)
- `/verbose` - Toggle verbose logging (admin)

## License

MIT