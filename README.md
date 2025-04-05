# Discarr - Discord Bot for Radarr & Sonarr Progress Tracking

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)

Discarr is a Discord bot that provides real-time monitoring of Radarr and Sonarr download activities. Keep track of your media downloads directly in Discord with progress updates, notifications, and status summaries.

## 🌟 Features

- **Real-time Download Tracking**: Monitor download progress for movies and TV shows
- **Automatic Notifications**: Receive alerts when downloads start and complete
- **Interactive Status Board**: Single, auto-updating message with current queue status
- **Pagination Controls**: Navigate through multiple downloads with reaction-based controls
- **Slash Commands**: Modern Discord slash commands with autocompletion
- **Minimal Configuration**: Simple setup with environment variables
- **Docker Support**: Easy deployment with Docker, including on TrueNAS Scale

## 📋 Prerequisites

- Python 3.8 or higher (for non-Docker installs)
- Discord account and server with admin privileges
- Radarr and/or Sonarr instances with API access
- Docker and Docker Compose (for Docker-based installation)

## 🐳 Docker Installation

### Quick Start with Docker Compose

1. **Clone the repository**:
   ```bash
   git clone https://github.com/EricBriscoe/discarr.git
   cd discarr
   ```

2. **Create a config directory and environment file**:
   ```bash
   mkdir -p config
   cp .env.example config/.env
   ```

3. **Edit the config/.env file** with your configuration details:
   - Discord bot token and channel ID
   - Radarr/Sonarr URLs and API keys
   - Preferred check interval and verbosity settings

4. **Run using Docker Compose**:
   ```bash
   docker-compose up -d
   ```

### Using Docker directly

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
  -e CHECK_INTERVAL=300 \
  -e VERBOSE=false \
  -e TZ=America/Chicago \
  ghcr.io/yourusername/discarr:latest
```

## 🔱 TrueNAS Scale Deployment

### Using TrueNAS Apps (Recommended)

1. **Log in** to your TrueNAS Scale dashboard.

2. **Navigate** to Apps > Available Applications.

3. **Click** "Launch Docker Image".

4. **Configure** the Docker application:
   - **Application Name**: `discarr`
   - **Image**: `ghcr.io/yourusername/discarr:latest` (or build your own)
   - **Container Command**: Leave default
   
5. **Enable** the Environment Variables panel and add:
   - `DISCORD_TOKEN`: Your Discord bot token
   - `DISCORD_CHANNEL_ID`: Your Discord channel ID
   - `RADARR_URL`: URL to your Radarr instance
   - `RADARR_API_KEY`: Your Radarr API key
   - `SONARR_URL`: URL to your Sonarr instance
   - `SONARR_API_KEY`: Your Sonarr API key
   - `CHECK_INTERVAL`: 300 (or your preferred value)
   - `VERBOSE`: false (or true if you want detailed logs)
   - `TZ`: Your preferred timezone (e.g., America/Chicago)

6. **Create** a Storage volume with:
   - **Host Path**: Choose a directory on your TrueNAS system
   - **Container Path**: `/app/config`

7. **Click** "Deploy" to start the application.

### Using Docker Compose in TrueNAS

Alternatively, you can use the "Launch Docker Image" with Docker Compose:

1. **Upload** your `docker-compose.yml` to a directory on your TrueNAS system.
2. **Create** a config/.env file with your settings.
3. **Navigate** to Apps > Launch Docker Image.
4. **Select** "Docker Compose" and provide the path to your compose file.
5. **Deploy** the container.

## 🔧 Standard Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/discarr.git
   cd discarr
   ```

2. **Set up a Python virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   mkdir -p config
   cp .env.example config/.env
   ```

5. **Edit the `config/.env` file** with your configuration details

6. **Run the bot**:
   ```bash
   python bot.py
   ```

## 🤖 Discord Bot Setup

1. **Create a Discord application**:
   - Visit the [Discord Developer Portal](https://discord.com/developers/applications)
   - Click "New Application" and give it a name
   - Navigate to the "Bot" tab and click "Add Bot"

2. **Configure bot permissions**:
   - Under the "Bot" tab, enable the following Privileged Gateway Intents:
     - Message Content Intent
     - Server Members Intent (optional)
   - This is required for the bot to read messages and handle commands

3. **Get your bot token**:
   - In the "Bot" tab, click "Reset Token" or "Copy" to get your token
   - Add this token to the `DISCORD_TOKEN` field in your `.env` file

4. **Invite the bot to your server**:
   - Go to OAuth2 > URL Generator
   - Select "bot" and "applications.commands" scopes
   - Select the following permissions:
     - Send Messages
     - Read Messages/View Channels
     - Manage Messages (for reaction handling)
     - Add Reactions
     - Use Slash Commands
   - Use the generated URL to add the bot to your server

## 📝 Channel Configuration

1. **Enable Developer Mode**:
   - Open Discord Settings > Advanced
   - Enable "Developer Mode"

2. **Get the Channel ID**:
   - Right-click on your desired channel
   - Select "Copy ID"
   - Add this ID to the `DISCORD_CHANNEL_ID` field in your `.env` file

## 🎬 Radarr/Sonarr Configuration

1. **Get Radarr API Key**:
   - In Radarr, go to Settings > General
   - Find your API Key and copy it
   - Add to `RADARR_API_KEY` in your `.env` file

2. **Get Sonarr API Key**:
   - In Sonarr, go to Settings > General
   - Find your API Key and copy it
   - Add to `SONARR_API_KEY` in your `.env` file

3. **Add the correct URLs**:
   - Set `RADARR_URL` and `SONARR_URL` to point to your instances
   - Include any base paths if needed (e.g., `http://localhost:7878`)
   - When using Docker, use the container name or IP address if services are on the same Docker network

## 📟 Bot Commands

The bot supports modern Discord slash commands:

- `/check` - Manually refresh the download status
- `/verbose` - Toggle verbose logging (admin only)
- `/cleanup` - Remove inactive downloads from queue (admin only)

Legacy prefix commands (`!check`, `!verbose`) are still supported for backward compatibility.

## 🔄 How It Works

Discarr maintains a single status message in your designated channel that refreshes automatically at the interval specified in your configuration. The message includes:

- Current movie downloads with progress percentages
- Current TV show downloads with progress percentages
- Pagination controls for navigating through multiple downloads

You can navigate through pages using the reaction controls:
- ⏮️ - First page
- ◀️ - Previous page
- ▶️ - Next page
- ⏭️ - Last page

## 🔍 Troubleshooting

- **Bot not responding**: Ensure the bot token is correct and the bot has been invited to your server.
- **No messages appearing**: Check that your channel ID is correct and the bot has permission to send messages.
- **API connection issues**: Verify your Radarr/Sonarr URLs and API keys are correct.
- **Slash commands not appearing**: Try reinviting the bot with both `bot` and `applications.commands` scopes.
- **Enable verbose logging**: Set `VERBOSE=true` in your `.env` file for detailed logs.
- **Docker container exiting**: Check the container logs with `docker logs discarr` to see any error messages.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

