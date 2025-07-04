# Discarr

[![CI/CD Pipeline](https://github.com/EricBriscoe/discarr/actions/workflows/ci.yml/badge.svg)](https://github.com/EricBriscoe/discarr/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/EricBriscoe/discarr/branch/main/graph/badge.svg)](https://codecov.io/gh/EricBriscoe/discarr)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Discarr monitors Radarr and Sonarr from Discord. It sends download notifications and provides management commands.

## ✨ Features

- **Real-time Monitoring**: Track downloads, health status, and system performance
- **Interactive Commands**: Manage your media servers directly from Discord
- **Smart Notifications**: Customizable alerts for downloads, errors, and system events
- **Multi-Instance Support**: Monitor multiple Radarr and Sonarr instances
- **Health Checking**: Automated health monitoring with configurable intervals
- **Cache Management**: Efficient caching system for improved performance
- **Progress Tracking**: Visual progress indicators for ongoing downloads
- **Security**: Built-in security scanning and safe configuration handling

## 🚀 Quick Start

### Prerequisites

- Python 3.12 or higher
- Discord Bot Token
- Radarr and/or Sonarr instances with API access

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/EricBriscoe/discarr.git
   cd discarr
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run the bot**
   ```bash
   python src/main.py
   ```

### Docker Deployment

```bash
# Using docker-compose
docker-compose up -d

# Or build and run manually
docker build -t discarr .
docker run -d --env-file .env discarr
```

## ⚙️ Configuration

Create a `.env` file based on `.env.example`:

```env
# Discord Configuration
DISCORD_TOKEN=your_discord_bot_token
DISCORD_GUILD_ID=your_guild_id

# Radarr Configuration
RADARR_URL=http://localhost:7878
RADARR_API_KEY=your_radarr_api_key

# Sonarr Configuration
SONARR_URL=http://localhost:8989
SONARR_API_KEY=your_sonarr_api_key

# Optional Settings
VERBOSE=false
HEALTH_CHECK_INTERVAL=300
CACHE_TTL=3600
```

## 🧪 Development

### Running Tests

```bash
# Run all tests
python run_tests.py

# Run unit tests only
python run_tests.py tests/unit/

# Run integration tests only
python run_tests.py tests/integration/

# Run tests with coverage
python run_tests.py tests/unit/ --cov=src --cov-report=html
```

### Code Coverage

Generate and view coverage reports:

```bash
# Generate coverage report
python run_tests.py tests/unit/ --cov=src --cov-report=html --cov-report=term-missing

# View HTML coverage report
open htmlcov/index.html
```

### Code Quality

The project uses several tools to maintain code quality:

- **pytest**: Testing framework
- **flake8**: Code linting
- **safety**: Security vulnerability scanning
- **bandit**: Security static analysis

```bash
# Run linting
flake8 src --max-line-length=127

# Run security checks
safety check -r requirements.txt
bandit -r src/
```

## 📊 Project Structure

```
discarr/
├── src/                    # Source code
│   ├── clients/           # API clients for Radarr/Sonarr
│   ├── core/              # Core configuration and settings
│   ├── discord_bot/       # Discord bot implementation
│   ├── monitoring/        # Monitoring and health checking
│   └── utils/             # Utility functions
├── tests/                 # Test suite
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
├── .github/workflows/     # CI/CD pipelines
└── config/                # Configuration files
```

## 🤖 Bot Commands

### User Commands
- `/status` - Show system status
- `/downloads` - View active downloads
- `/search <query>` - Search for media
- `/help` - Show available commands

### Admin Commands
- `/health` - Detailed health check
- `/cache clear` - Clear system cache
- `/config reload` - Reload configuration
- `/logs` - View recent logs

## 🔧 Architecture

Discarr is built with a modular architecture:

- **Clients**: Abstracted API clients for different services
- **Monitoring**: Background tasks for health and download monitoring
- **Discord Bot**: Command handling and user interaction
- **Utils**: Shared utilities for common operations

## 📈 Monitoring & Observability

- **Health Checks**: Automated monitoring of service availability
- **Progress Tracking**: Real-time download progress updates
- **Cache Management**: TTL caching
- **Error Handling**: Error tracking and reporting

## 🛡️ Security

- Environment-based configuration
- API key protection
- Input validation and sanitization
- Regular security scanning with Bandit and Safety

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
