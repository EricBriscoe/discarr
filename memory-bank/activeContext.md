# Active Context: Discarr

## Current Work Focus
- **Bug Fix**: Resolved a persistent interaction timeout issue affecting all commands and buttons.
- **Cause**: The root cause was identified as blocking I/O in the `HealthChecker` background task. The synchronous `httpx.get()` calls were freezing the `asyncio` event loop, preventing the bot from processing new interactions (like command invocations or button clicks) in time, leading to "token expired" errors.
- **Files Modified**: 
  - `src/monitoring/health_checker.py`
  - `src/monitoring/download_monitor.py`

## Recent Changes
- **`health_checker.py`**:
  - Refactored the entire class to be fully asynchronous.
  - Replaced blocking `httpx.get()` calls with `await client.get()` using an `httpx.AsyncClient`.
  - Used `asyncio.gather` to run all health checks concurrently for better performance.
- **`download_monitor.py`**:
  - Updated the `check_health` and `_create_initial_health_message` methods to `await` the new asynchronous `check_all_services()` call.

## Next Steps
1. **Update Progress**: Update `progress.md` to reflect this critical fix.
2. **Final Review**: This should finally resolve all interaction timeout issues.

## Active Decisions & Considerations
- **No Blocking I/O**: Absolutely no blocking I/O operations should exist on the main event loop. All network requests, file operations, etc., must be asynchronous.

## Important Patterns & Preferences
- **Async Purity**: Background tasks are just as important as foreground command handlers when it comes to maintaining a non-blocking event loop. A single blocking call in a background loop can bring the entire bot to its knees.

## Learnings & Project Insights
- Interaction timeout errors are almost always caused by a blocked event loop.
- The source of the block can be anywhere in the application, not just in the code for the command that's failing. Background tasks are a common culprit.
- Thoroughly auditing the entire codebase for blocking calls is essential for a stable `asyncio` application.
