# Project Brief: Discarr

## Overview
Discarr is a powerful Discord bot for monitoring and managing Radarr and Sonarr instances. It provides real-time notifications, download monitoring, and interactive management capabilities directly through Discord.

## Core Requirements
- **Real-time Monitoring**: Track downloads, health status, and system performance
- **Interactive Commands**: Manage media servers directly from Discord
- **Smart Notifications**: Customizable alerts for downloads, errors, and system events
- **Multi-Instance Support**: Monitor multiple Radarr and Sonarr instances
- **Health Checking**: Automated health monitoring with configurable intervals
- **Cache Management**: Efficient caching system for improved performance
- **Progress Tracking**: Visual progress indicators for ongoing downloads
- **Security**: Built-in security scanning and safe configuration handling

## Technical Stack
- **Language**: Python 3.12+
- **Discord Library**: discord.py
- **HTTP Client**: httpx (with HTTP/2 support)
- **Testing**: pytest with coverage reporting
- **Code Quality**: flake8, bandit, safety
- **Deployment**: Docker with docker-compose support

## Key Components
1. **API Clients** (`src/clients/`): Abstracted clients for Radarr/Sonarr APIs
2. **Discord Bot** (`src/discord_bot/`): Command handling and user interaction
3. **Monitoring** (`src/monitoring/`): Background tasks for health and download monitoring
4. **Core** (`src/core/`): Configuration and settings management
5. **Utils** (`src/utils/`): Shared utilities for common operations

## Project Goals
- Provide seamless Discord integration for media server management
- Maintain high code quality with comprehensive testing (65%+ coverage)
- Ensure robust error handling and security practices
- Support scalable deployment options (local and Docker)
- Enable real-time monitoring and notifications

## Success Criteria
- Bot successfully connects to Discord and media services
- Commands execute without errors and provide useful feedback
- Download monitoring works reliably with progress tracking
- Health checks detect and report service issues
- Code maintains high quality standards and test coverage
