"""
Unit tests for the DiscordBot class.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock, call, ANY
import signal
import os

# Set required environment variables for testing
os.environ['DISCORD_TOKEN'] = 'test_token'
os.environ['DISCORD_CHANNEL_ID'] = '12345'

from src.discord_bot.bot import DiscordBot
from src.core.settings import Settings

@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock(spec=Settings)
    settings.discord_token = "test_token"
    settings.discord_channel_id = 12345
    return settings

@pytest.fixture
def discord_bot_with_mocks(mock_settings):
    """Create a DiscordBot instance with comprehensive mocks."""
    with patch('discord.ext.commands.Bot') as mock_bot_class, \
         patch('src.discord_bot.bot.AdminCommands') as mock_admin_commands, \
         patch('src.discord_bot.bot.UserCommands') as mock_user_commands, \
         patch('src.discord_bot.bot.DownloadMonitor') as mock_download_monitor:
        
        # Mock the bot instance that gets created
        mock_bot_instance = MagicMock()
        mock_bot_instance.tree = MagicMock()
        mock_bot_instance.tree.command = MagicMock(return_value=lambda f: f) # Decorator mock
        mock_bot_instance.event = MagicMock(return_value=lambda f: f) # Decorator mock
        mock_bot_instance.start = AsyncMock()
        mock_bot_instance.tree.sync = AsyncMock()
        mock_bot_class.return_value = mock_bot_instance
        
        bot = DiscordBot(mock_settings)
        yield bot, mock_bot_instance, mock_admin_commands, mock_user_commands, mock_download_monitor

@pytest.mark.asyncio
class TestDiscordBot:
    """Test cases for the DiscordBot class."""

    def test_init(self, discord_bot_with_mocks):
        """Test DiscordBot initialization."""
        discord_bot, mock_bot_instance, _, _, _ = discord_bot_with_mocks
        assert discord_bot.bot == mock_bot_instance
        assert discord_bot.download_monitor is None
        # Check that event handlers and commands are set up
        mock_bot_instance.event.assert_called_once()
        assert mock_bot_instance.tree.command.call_count > 0

    @patch('signal.signal')
    def test_setup_signal_handlers(self, mock_signal, discord_bot_with_mocks):
        """Test setting up signal handlers."""
        discord_bot, _, _, _, _ = discord_bot_with_mocks
        discord_bot._setup_signal_handlers()
        
        assert mock_signal.call_count == 2
        mock_signal.assert_any_call(signal.SIGINT, ANY)
        mock_signal.assert_any_call(signal.SIGTERM, ANY)

    async def test_on_ready(self, discord_bot_with_mocks):
        """Test the on_ready event handler."""
        discord_bot, mock_bot_instance, _, _, _ = discord_bot_with_mocks
        
        with patch('asyncio.create_task') as mock_create_task:
            # The decorator registers the function, so we can call it directly
            on_ready_func = discord_bot.bot.event.call_args.args[0]
            await on_ready_func()
            
            mock_bot_instance.tree.sync.assert_awaited_once()
            # Check that create_task was called with the _initialize_monitor method
            assert mock_create_task.call_count > 0
            # Get the coroutine that was passed to create_task
            coro = mock_create_task.call_args.args[0]
            assert coro.__name__ == '_initialize_monitor'

    async def test_initialize_monitor(self, discord_bot_with_mocks):
        """Test the _initialize_monitor method."""
        discord_bot, mock_bot_instance, _, _, mock_download_monitor_class = discord_bot_with_mocks
        discord_bot.download_monitor = None
        
        # Mock the instance returned by the class
        mock_monitor_instance = MagicMock()
        mock_monitor_instance.start = AsyncMock()
        mock_download_monitor_class.return_value = mock_monitor_instance

        await discord_bot._initialize_monitor()
        
        mock_download_monitor_class.assert_called_once_with(mock_bot_instance, discord_bot.settings)
        mock_bot_instance.add_view.assert_called_once_with(mock_monitor_instance.pagination_view)
        mock_monitor_instance.start.assert_awaited_once()

    def test_setup_commands(self, discord_bot_with_mocks):
        """Test that slash commands are registered."""
        discord_bot, mock_bot_instance, _, _, _ = discord_bot_with_mocks
        # The commands are set up in __init__, so we just check the mock
        assert mock_bot_instance.tree.command.call_count == 5
        
        # Check for a specific command registration
        decorator_calls = mock_bot_instance.tree.command.call_args_list
        assert any(call.kwargs['name'] == 'cleanup' for call in decorator_calls)

    async def test_run(self, discord_bot_with_mocks):
        """Test the run method."""
        discord_bot, mock_bot_instance, _, _, _ = discord_bot_with_mocks
        discord_bot.download_monitor = AsyncMock()
        
        await discord_bot.run()
        
        mock_bot_instance.start.assert_awaited_once_with(discord_bot.settings.discord_token)
        discord_bot.download_monitor.stop.assert_awaited_once()

    def test_start(self, discord_bot_with_mocks):
        """Test the start method."""
        discord_bot, mock_bot_instance, _, _, _ = discord_bot_with_mocks
        
        discord_bot.start()
        
        mock_bot_instance.run.assert_called_once_with(discord_bot.settings.discord_token)
