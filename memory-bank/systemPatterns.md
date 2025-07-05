# System Patterns: Discarr

## System Architecture
Discarr follows a modular, asynchronous architecture designed for scalability and maintainability.

- **Asynchronous Core**: Built on `asyncio` for non-blocking I/O operations
- **Modular Components**: Separated into clients, monitoring, Discord bot, and utilities
- **Centralized Settings**: Configuration managed through a single `Settings` class
- **Background Tasks**: `asyncio.Task` used for continuous monitoring and health checks
- **Event-Driven**: Responds to Discord events and scheduled background tasks

## Key Technical Decisions
1. **`httpx` for API Calls**: Chosen for its async capabilities, HTTP/2 support, and connection pooling
2. **Abstract Base Class for Clients**: `MediaClient` provides a common interface for Radarr/Sonarr
3. **Request Deduplication**: `_pending_requests` dictionary prevents redundant API calls
4. **Paginated API Fetching**: `get_all_queue_items_paginated` handles large media libraries efficiently
5. **Safe Interaction Handling**: `safe_defer_interaction` and `safe_send_response` prevent Discord API timeouts
6. **Role-Based Permissions**: `has_admin_permissions` and `is_guild_owner` for secure command access
7. **Environment-Based Configuration**: `.env` files for secure and flexible setup

## Design Patterns
- **Singleton**: The `Settings` class is treated as a singleton to provide global configuration
- **Strategy**: Different media services (Radarr, Sonarr) are implemented as strategies under the `MediaClient` interface
- **Observer**: The `DownloadMonitor` observes the state of media clients and notifies Discord
- **Facade**: The `AdminCommands` and `UserCommands` classes provide a simplified interface to complex underlying operations
- **Decorator**: Used for logging, error handling, and potentially caching in the future

## Component Relationships
- `main.py`: Entry point, initializes all components
- `DiscordBot`: Contains command handlers (`AdminCommands`, `UserCommands`)
- `DownloadMonitor`: Runs in the background, uses `CacheManager` to track downloads
- `CacheManager`: Holds API clients (`RadarrClient`, `SonarrClient`) and manages data
- `MediaClient`: Base for API clients, handles all HTTP communication

## Critical Implementation Paths
1. **Command Execution**: `Interaction` -> `Command Handler` -> `API Client` -> `Discord Response`
2. **Download Monitoring**: `DownloadMonitor` -> `CacheManager` -> `API Client` -> `Update Discord Embed`
3. **Health Checking**: `HealthChecker` -> `API Client` -> `Log/Notify Status`
4. **Cleanup Command**: `Interaction` -> `cleanup_command` -> `CacheManager` -> `API Client` -> `Remove Items`

## Error Handling
- **`try...except` blocks**: Used extensively in API calls and command handlers
- **`safe_*` utilities**: Gracefully handle Discord interaction errors
- **`MediaClientError`**: Custom exception for client-specific issues
- **Logging**: Detailed error logging with `exc_info=True` for debugging
