# Docker Deployment Guide for Discarr

This guide provides instructions for deploying the Discarr Discord bot using Docker.

## Prerequisites

1. Docker installed on your host system
2. API keys for Radarr, Sonarr
3. Discord bot token

## Quick Start

### Using Docker Run

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
  -e PLEX_URL=http://your-plex-url:32400 \
  -e HEALTH_CHECK_INTERVAL=60 \
  -e CHECK_INTERVAL=300 \
  ghcr.io/ericbriscoe/discarr:latest
```

### Using Docker Compose

1. Create a `docker-compose.yml` file:

```yaml
version: '3'

services:
  discarr:
    image: ghcr.io/ericbriscoe/discarr:latest
    container_name: discarr
    restart: unless-stopped
    volumes:
      - ./config:/app/config
    environment:
      - DISCORD_TOKEN=your_token
      - DISCORD_CHANNEL_ID=your_channel_id
      - RADARR_URL=http://your-radarr-url:7878
      - RADARR_API_KEY=your_radarr_api_key
      - SONARR_URL=http://your-sonarr-url:8989
      - SONARR_API_KEY=your_sonarr_api_key
      - PLEX_URL=http://your-plex-url:32400
      - HEALTH_CHECK_INTERVAL=60
      - CHECK_INTERVAL=300
      - TZ=America/Chicago
```

2. Run with Docker Compose:

```bash
docker-compose up -d
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DISCORD_TOKEN` | Your Discord bot token | (required) |
| `DISCORD_CHANNEL_ID` | Channel ID where the bot will post updates | (required) |
| `RADARR_URL` | URL of your Radarr instance | `http://localhost:7878` |
| `RADARR_API_KEY` | API key for Radarr | (required for movie monitoring) |
| `SONARR_URL` | URL of your Sonarr instance | `http://localhost:8989` |
| `SONARR_API_KEY` | API key for Sonarr | (required for TV monitoring) |
| `PLEX_URL` | URL of your Plex instance | `http://localhost:32400` |
| `CHECK_INTERVAL` | How often to check downloads (seconds) | `300` |
| `HEALTH_CHECK_INTERVAL` | How often to check service health (seconds) | `60` |
| `VERBOSE` | Enable verbose logging | `false` |
| `TZ` | Timezone for the container | System default |

## Plex Health Checking

Discarr checks Plex health status by accessing the `/identity` endpoint, which doesn't require authentication. The bot will show if your Plex server is online or offline in the health status message.

## Volume Mounts

The Docker container uses a volume mount for `/app/config` to store persistent data. This includes:

- `.env` configuration file (if not using environment variables)
- Log files

## Updating

To update to the latest version:

```bash
# Using docker run
docker pull ghcr.io/ericbriscoe/discarr:latest
docker stop discarr
docker rm discarr
# Run the docker run command again

# Using docker-compose
docker-compose pull
docker-compose up -d
```

## Troubleshooting

Check the logs if you encounter any issues:

```bash
docker logs discarr
```

If you need more detailed logs, set the `VERBOSE` environment variable to `true`.
