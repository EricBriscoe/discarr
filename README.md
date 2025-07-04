# Discarr - Discord Bot for Radarr & Sonarr Progress Tracking

![Discarr Example](./assets/image.png)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)

Discarr is a simple Discord bot that provides real-time monitoring of Radarr and Sonarr download activities directly in Discord.

## Prerequisites

- Discord account and bot token
- Radarr and/or Sonarr instances with API access

## Quick Start with Docker Compose

```bash
docker run -d \
  --name discarr \
  --restart unless-stopped \
  -v $(pwd)/config:/app/config \
  -e DISCORD_TOKEN=your_token \
  -e DISCORD_CHANNEL_ID=your_channel_id \
  -e RADARR_URL=http://your-radarr-url:7878 \
  -e RADARR_API_KEY=your_radarr_api_key \
  -e SONARR_URL=http://your-sonarr-url:8989 \
  -e SONARR_API_KEY=your_sonarr_api_key \
  ghcr.io/ericbriscoe/discarr:latest
```

## Local Installation

```bash
# Clone and set up environment
git clone https://github.com/EricBriscoe/discarr.git
cd discarr
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure and run
mkdir -p config
cp .env.example config/.env
# Edit config/.env with your details
python bot.py
```

## Discord Setup

1. Create a bot at [Discord Developer Portal](https://discord.com/developers/applications)
   - Create application → Add bot → Enable Message Content Intent
   - Copy token to `DISCORD_TOKEN` in your config

2. Invite bot to server
   - OAuth2 → URL Generator → Select "bot" and "applications.commands"
   - Required permissions: Send Messages, Read Messages, Manage Messages, Add Reactions
   - Use generated URL to add bot to server

3. Get your channel ID (Enable Developer Mode in Discord settings)
   - Right-click channel → Copy ID → Add to `DISCORD_CHANNEL_ID` in config

## Bot Commands

- `/check` - Manually refresh download status
- `/verbose` - Toggle verbose logging (admin only)
- `/progress` - Show progress tracking statistics (admin only)
- `/cleanup` - Remove stuck and inactive downloads from queue (admin only)

## Smart Cleanup Features

The `/cleanup` command now uses intelligent progress tracking to identify truly stuck downloads:

- **Progress Tracking**: Monitors download progress over time (default: 4 hours of history)
- **Stuck Detection**: Identifies downloads with no progress for 2+ hours (configurable)
- **Smart Removal**: Removes both stuck downloads and traditionally inactive items
- **Detailed Reporting**: Shows exactly what was removed and why

### Configuration Options

Add these environment variables to customize stuck download detection:

```bash
# Stuck download detection (optional)
STUCK_THRESHOLD_MINUTES=120        # Minutes without progress before considered stuck
MIN_PROGRESS_CHANGE=1.0           # Minimum % progress change required
MIN_SIZE_CHANGE=104857600         # Minimum bytes downloaded required (100MB)
PROGRESS_HISTORY_HOURS=4          # Hours of progress history to keep
MAX_SNAPSHOTS_PER_DOWNLOAD=50     # Maximum snapshots per download
```

## Troubleshooting

- **Bot not responding**: Verify token and permissions
- **No updates**: Check Radarr/Sonarr URLs and API keys
- **Docker issues**: Check container logs with `docker logs discarr`

## License

Licensed under the MIT License
