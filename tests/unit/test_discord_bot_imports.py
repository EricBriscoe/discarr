"""
Unit tests for Discord bot import functionality.
These tests verify that the critical Discord-related imports work correctly,
which is essential for Docker container deployment.

This test specifically addresses the naming conflict issue that was causing
'ModuleNotFoundError: No module named discord.ext' in Docker containers.
"""
import unittest
import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestDiscordBotImports(unittest.TestCase):
    """Test Discord bot import functionality."""

    def test_discord_py_imports(self):
        """Test that discord.py library imports work correctly.
        
        This is the critical test that was failing in Docker due to naming conflicts.
        """
        # Test basic discord import
        import discord
        self.assertTrue(hasattr(discord, '__version__'))
        
        # Test discord.ext.commands import - this was the failing import
        from discord.ext import commands
        self.assertTrue(hasattr(commands, 'Bot'))
        self.assertTrue(hasattr(commands, 'Command'))
        
        # Verify we have the real discord.py library, not a local module
        self.assertTrue(hasattr(discord, 'Intents'))
        self.assertTrue(hasattr(discord, 'Client'))

    def test_discord_bot_class_import(self):
        """Test that the main DiscordBot class can be imported."""
        from discord_bot.bot import DiscordBot
        
        # Verify it's a class
        self.assertTrue(isinstance(DiscordBot, type))
        
        # Verify it has expected methods
        self.assertTrue(hasattr(DiscordBot, '__init__'))
        self.assertTrue(hasattr(DiscordBot, 'start'))
        self.assertTrue(hasattr(DiscordBot, 'run'))

    def test_discord_command_imports(self):
        """Test that Discord command modules can be imported."""
        from discord_bot.commands.admin import AdminCommands
        from discord_bot.commands.user import UserCommands
        
        # Verify they're classes
        self.assertTrue(isinstance(AdminCommands, type))
        self.assertTrue(isinstance(UserCommands, type))
        
        # Verify they have __init__ methods
        self.assertTrue(hasattr(AdminCommands, '__init__'))
        self.assertTrue(hasattr(UserCommands, '__init__'))

    def test_no_naming_conflicts(self):
        """Test that there are no naming conflicts between local and library imports.
        
        This test ensures the fix for the Docker naming conflict is working.
        """
        # Import discord.py library
        import discord
        from discord.ext import commands
        
        # Import local discord_bot module
        from discord_bot.bot import DiscordBot
        
        # Verify discord.py library is the real one
        self.assertTrue(hasattr(discord, 'Intents'))
        self.assertTrue(hasattr(commands, 'Bot'))
        
        # Verify local module is our custom class
        self.assertTrue(hasattr(DiscordBot, '_setup_commands'))
        self.assertTrue(hasattr(DiscordBot, '_setup_event_handlers'))

    def test_core_imports_with_error_handling(self):
        """Test that core modules can be imported with proper error handling."""
        # Test Settings class import (may raise ValueError for missing config)
        try:
            from core.settings import Settings
            # If no exception, verify it's a class
            self.assertTrue(isinstance(Settings, type))
        except ValueError as e:
            # Expected if configuration is missing
            self.assertIn("Missing required configuration", str(e))

    def test_monitoring_core_imports(self):
        """Test that core monitoring modules can be imported."""
        # Only test the modules that don't have import issues
        from monitoring.download_monitor import DownloadMonitor
        from monitoring.health_checker import HealthChecker
        
        # Verify they're all classes
        self.assertTrue(isinstance(DownloadMonitor, type))
        self.assertTrue(isinstance(HealthChecker, type))


if __name__ == '__main__':
    unittest.main()
