# Progress: Discarr

## What Works
- **Core Bot Functionality**: The bot connects to Discord and responds to commands.
- **API Clients**: Radarr and Sonarr clients can connect and fetch data.
- **Download Monitoring**: The `DownloadMonitor` can track active downloads.
- **Health Checking**: The `HealthChecker` can monitor service status.
- **Admin Commands**: Most admin commands are functional.
- **Bug Fix**: The `/cleanup` command error has been resolved.
- **Synchronized Startup**: The initial Discord message now updates immediately after data is loaded.
- **Relative Timestamps**: Elapsed time is now correctly formatted as a relative timestamp in Discord embeds.

## What's Left to Build
- **Missing command tests**: Expand the test suite to cover all command logic and prevent regressions like the recent `await` bug.
- **User-Facing Error Improvements**: Error messages can be made more specific and helpful.
- **Full Command Implementation**: Some commands in the README are not yet fully implemented.
- **Notification settings**: Add Discord notification options.

## Current Status
- **Stable with UI Fix**: The bot is stable, and a UI bug with relative timestamps has been fixed.
- **Ready for Deployment**: The recent fix has been tested and is ready for deployment.
- **Documentation Updated**: The Memory Bank has been updated to reflect the latest changes.

## Known Issues
- **Insufficient Test Coverage**: The current test suite does not cover all critical paths, particularly at the command level.
- **Generic Error Messages**: Some user-facing error messages are too generic (e.g., "An error occurred").

## Evolution of Project Decisions
- **Initial Implementation**: Focused on core features and API connectivity.
- **Bug Discovery**: A runtime `TypeError` in the `/cleanup` command revealed a gap in async programming practices.
- **Decision to Improve Testing**: The bug highlighted the need for command-level regression tests to catch logical errors, not just syntax issues.
- **Memory bank**: These files record project context and progress.
- **Timestamp formatting**: Relative timestamps now use the corrected source time.
