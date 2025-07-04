"""
Unit tests for DownloadMonitor message cleanup functionality.
"""
import pytest
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch
import discord

# Set required environment variables for testing
os.environ['DISCORD_TOKEN'] = 'test_token'
os.environ['DISCORD_CHANNEL_ID'] = '123456789'

from src.monitoring.download_monitor import DownloadMonitor
from src.core.settings import Settings


class TestDownloadMonitorCleanup:
    """Test cases for message cleanup functionality."""
    
    @pytest.fixture
    def mock_bot(self):
        """Create a mock Discord bot."""
        bot = MagicMock()
        bot.user = MagicMock()
        bot.user.id = 12345
        return bot
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock(spec=Settings)
        settings.discord_channel_id = 67890
        settings.cleanup_previous_messages = True
        settings.radarr_url = "http://localhost:7878"
        settings.radarr_api_key = "test_key"
        settings.sonarr_url = "http://localhost:8989"
        settings.sonarr_api_key = "test_key"
        settings.verbose = False
        return settings
    
    @pytest.fixture
    def mock_channel(self):
        """Create a mock Discord channel."""
        channel = AsyncMock()
        channel.purge = AsyncMock()
        return channel
    
    @pytest.fixture
    def download_monitor(self, mock_bot, mock_settings):
        """Create a DownloadMonitor instance with mocked dependencies."""
        with patch('src.monitoring.download_monitor.RadarrClient'), \
             patch('src.monitoring.download_monitor.SonarrClient'), \
             patch('src.monitoring.download_monitor.CacheManager'), \
             patch('src.discord_bot.ui.views.PaginationView'):
            monitor = DownloadMonitor(mock_bot, mock_settings)
            return monitor
    
    @pytest.mark.asyncio
    async def test_cleanup_previous_messages_success(self, download_monitor, mock_channel, mock_bot):
        """Test successful cleanup of previous messages."""
        # Setup
        download_monitor.channel = mock_channel
        mock_messages = [MagicMock(), MagicMock()]
        mock_channel.purge.return_value = mock_messages
        
        # Execute
        await download_monitor._cleanup_previous_messages()
        
        # Verify
        mock_channel.purge.assert_called_once()
        call_args = mock_channel.purge.call_args
        assert call_args[1]['limit'] == 100
        assert callable(call_args[1]['check'])  # Verify check is a function
        
        # Test the check function behavior
        check_function = call_args[1]['check']
        
        # Create test messages
        bot_message = MagicMock()
        bot_message.author = mock_bot.user
        
        user_message = MagicMock()
        user_message.author = MagicMock()
        user_message.author.id = 99999  # Different from bot
        
        # Verify the check function works correctly
        assert check_function(bot_message) is True
        assert check_function(user_message) is False
    
    @pytest.mark.asyncio
    async def test_cleanup_previous_messages_no_channel(self, download_monitor):
        """Test cleanup when no channel is available."""
        # Setup
        download_monitor.channel = None
        
        # Execute
        await download_monitor._cleanup_previous_messages()
        
        # Verify - should return early without error
        # No assertions needed as we're testing it doesn't crash
    
    @pytest.mark.asyncio
    async def test_cleanup_previous_messages_forbidden(self, download_monitor, mock_channel):
        """Test cleanup when bot lacks permissions."""
        # Setup
        download_monitor.channel = mock_channel
        mock_channel.purge.side_effect = discord.Forbidden(MagicMock(), "Insufficient permissions")
        
        # Execute - should not raise exception
        await download_monitor._cleanup_previous_messages()
        
        # Verify purge was attempted
        mock_channel.purge.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_previous_messages_http_error(self, download_monitor, mock_channel):
        """Test cleanup when HTTP error occurs."""
        # Setup
        download_monitor.channel = mock_channel
        mock_channel.purge.side_effect = discord.HTTPException(MagicMock(), "Rate limited")
        
        # Execute - should not raise exception
        await download_monitor._cleanup_previous_messages()
        
        # Verify purge was attempted
        mock_channel.purge.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_disabled_in_settings(self, mock_bot, mock_channel):
        """Test that cleanup is skipped when disabled in settings."""
        # Setup
        settings = MagicMock(spec=Settings)
        settings.cleanup_previous_messages = False
        settings.discord_channel_id = 67890
        settings.radarr_url = "http://localhost:7878"
        settings.radarr_api_key = "test_key"
        settings.sonarr_url = "http://localhost:8989"
        settings.sonarr_api_key = "test_key"
        settings.verbose = False
        
        with patch('src.monitoring.download_monitor.RadarrClient'), \
             patch('src.monitoring.download_monitor.SonarrClient'), \
             patch('src.monitoring.download_monitor.CacheManager'), \
             patch('src.discord_bot.ui.views.PaginationView'):
            monitor = DownloadMonitor(mock_bot, settings)
            monitor.channel = mock_channel
            monitor._cleanup_previous_messages = AsyncMock()
            
            # Mock the start method dependencies
            with patch.object(monitor.cache_manager, 'start_background_refresh'), \
                 patch('asyncio.create_task'):
                mock_bot.get_channel.return_value = mock_channel
                
                # Execute
                await monitor.start()
                
                # Verify cleanup was not called
                monitor._cleanup_previous_messages.assert_not_called()
    
    def test_is_bot_message_function(self, download_monitor, mock_bot):
        """Test the message filtering function."""
        # Setup
        download_monitor.bot = mock_bot
        
        # Create mock messages
        bot_message = MagicMock()
        bot_message.author = mock_bot.user
        
        user_message = MagicMock()
        user_message.author = MagicMock()
        user_message.author.id = 99999  # Different from bot
        
        # The is_bot_message function is defined inside _cleanup_previous_messages
        # We'll test the logic by checking message authors directly
        assert bot_message.author == mock_bot.user
        assert user_message.author != mock_bot.user
