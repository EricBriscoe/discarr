"""
Mock download monitor module for testing purposes.
This is a placeholder to resolve import issues in the Discord bot.
"""

class MockView:
    """Mock view class for pagination."""
    pass

class DownloadMonitor:
    """Mock download monitor class."""
    
    def __init__(self, bot, settings):
        """Initialize the download monitor."""
        self.bot = bot
        self.settings = settings
        self.pagination_view = MockView()
    
    async def start(self):
        """Start the download monitor."""
        pass
    
    async def stop(self):
        """Stop the download monitor."""
        pass
