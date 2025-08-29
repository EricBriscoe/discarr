# Discarr

Discarr is a production-ready monorepo that provides:
- a secure HTTP API and React web UI to manage your *arr stack (Radarr/Sonarr/Plex/qBittorrent), and
- an optional Discord bot that mirrors health/downloads and offers slash commands.

This reorganization sets a solid foundation for adding features while keeping a clear separation between core logic, the bot, the API server, and the web app.

## Monorepo Structure

- `packages/core` — Shared core library: config, types, service clients, monitoring.
- `packages/discord-bot` — Discord bot implementation (UI builders, commands, bot runtime).
- `apps/server` — Express API server that also serves the web UI and can start the bot.
- `apps/web` — React + Vite web application.

## Requirements

- Node.js 18+
- At least one of Radarr or Sonarr with API access (qBittorrent, Plex optional)
- For Discord features: Discord Bot Token, Channel ID, and Client ID

## Quick Start (Local)

1. Install deps
   - `npm ci`
2. Configure env
   - `cp .env.example .env`
   - Edit `.env` with your settings (see Configuration).
3. Build everything
   - `npm run build`
4. Start the API server (serves web UI on port 8080 by default)
   - `npm start`

Open http://localhost:8080 to use the web UI.

To run only the web app during development: `npm run dev:web` and browse http://localhost:5173

## Docker

1. Copy and edit environment file
   - `cp .env.example config/.env`
2. Run
   - `docker-compose up -d`
3. Open http://localhost:8080

## Configuration

Edit `.env` (local) or `config/.env` (Docker):

Key variables:
- `ENABLE_DISCORD_BOT=true|false` — Disable to run as web/API only
- `ADMIN_API_KEY` — Required to use protected API actions from the web UI (approve/reject, cleanup). Enter this key in the Settings page.
- `SERVER_PORT` — API + web server port (default 8080)
- Discord: `DISCORD_TOKEN`, `DISCORD_CHANNEL_ID`, `DISCORD_CLIENT_ID`
- Radarr: `RADARR_URL`, `RADARR_API_KEY`
- Sonarr: `SONARR_URL`, `SONARR_API_KEY`
- Plex: `PLEX_URL`
- qBittorrent: `QBITTORRENT_URL`, `QBITTORRENT_USERNAME`, `QBITTORRENT_PASSWORD`
- Intervals: `CHECK_INTERVAL`, `HEALTH_CHECK_INTERVAL`, `MIN_REFRESH_INTERVAL`, `MAX_REFRESH_INTERVAL`, `VERBOSE`

## API Endpoints

- `GET /api/health` — Aggregated health for services
- `GET /api/downloads` — Active downloads
- `GET /api/blocked` — Import blocked items (requires API key if configured)
- `POST /api/blocked/:service/:id/approve` — Approve import (requires `X-API-Key`)
- `DELETE /api/blocked/:service/:id` — Remove queue item (requires `X-API-Key`)
- `POST /api/actions/cleanup` — Remove stalled/seeded torrents with Sonarr/Radarr labels (requires `X-API-Key`)
- `POST /api/actions/series-search` — Trigger Sonarr series search by `seriesId` (requires `X-API-Key`)

## Discord Bot

When enabled, the server will start the Discord bot automatically. It registers application-level slash commands and posts/upgrades embeds for health and downloads.

Disable via `ENABLE_DISCORD_BOT=false`.

## CI/CD

GitHub Actions build and verify all packages (typecheck, lint, build). A Docker workflow builds and pushes a single image.

## License

MIT
