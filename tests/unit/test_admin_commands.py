"""
Unit tests for AdminCommands class.
"""
import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch
import discord

# Set required environment variables for testing
os.environ['DISCORD_TOKEN'] = 'test_token'
os.environ['DISCORD_CHANNEL_ID'] = '123456789'

from src.discord_bot.commands.admin import AdminCommands
from src.core.settings import Settings

@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock(spec=Settings)
    settings.verbose = False
    return settings

@pytest.fixture
def admin_commands(mock_settings):
    """Create an AdminCommands instance."""
    return AdminCommands(mock_settings)

@pytest.fixture
def mock_interaction():
    """Create a mock Discord interaction."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.edit_original_response = AsyncMock()
    return interaction

@pytest.fixture
def mock_download_monitor():
    """Create a mock DownloadMonitor."""
    monitor = MagicMock()
    monitor.cache_manager = MagicMock()
    monitor.cache_manager.radarr_client = MagicMock()
    monitor.cache_manager.sonarr_client = MagicMock()
    monitor.cache_manager.get_progress_statistics.return_value = {}
    monitor.cache_manager.analyze_stuck_downloads.return_value = []
    monitor.cache_manager.radarr_client.remove_stuck_downloads = AsyncMock(return_value=0)
    monitor.cache_manager.sonarr_client.remove_stuck_downloads = AsyncMock(return_value=0)
    monitor.cache_manager.radarr_client.remove_inactive_items = AsyncMock(return_value=0)
    monitor.cache_manager.sonarr_client.remove_inactive_items = AsyncMock(return_value=0)
    monitor.check_downloads = AsyncMock()
    return monitor

@pytest.mark.asyncio
class TestAdminCommands:
    """Test cases for admin commands."""

    async def test_verbose_command(self, admin_commands, mock_interaction, mock_download_monitor):
        """Test the /verbose command."""
        with patch('src.discord_bot.commands.admin.is_guild_owner', new_callable=AsyncMock) as mock_is_owner:
            mock_is_owner.return_value = True
            
            # Test enabling verbose mode
            await admin_commands.verbose_command(mock_interaction, mock_download_monitor)
            
            assert admin_commands.settings.verbose is True
            mock_interaction.followup.send.assert_awaited_once()
            
            # Reset and test disabling verbose mode
            mock_interaction.reset_mock()
            await admin_commands.verbose_command(mock_interaction, mock_download_monitor)
            
            assert admin_commands.settings.verbose is False
            mock_interaction.followup.send.assert_awaited_once()

    async def test_verbose_command_not_owner(self, admin_commands, mock_interaction, mock_download_monitor):
        """Test /verbose command when user is not owner."""
        with patch('src.discord_bot.commands.admin.is_guild_owner', new_callable=AsyncMock) as mock_is_owner, \
             patch('src.discord_bot.commands.admin.safe_send_response', new_callable=AsyncMock) as mock_safe_send:
            mock_is_owner.return_value = False
            
            await admin_commands.verbose_command(mock_interaction, mock_download_monitor)
            
            mock_safe_send.assert_awaited_once_with(
                mock_interaction,
                content="Only the server owner can use this command.",
                ephemeral=True
            )

    async def test_progress_command(self, admin_commands, mock_interaction, mock_download_monitor):
        """Test the /progress command."""
        with patch('src.discord_bot.commands.admin.has_admin_permissions', new_callable=AsyncMock) as mock_has_admin:
            mock_has_admin.return_value = True
            
            await admin_commands.progress_command(mock_interaction, mock_download_monitor)
            
            mock_interaction.followup.send.assert_awaited_once()

    async def test_cleanup_command(self, admin_commands, mock_interaction, mock_download_monitor):
        """Test the /cleanup command."""
        with patch('src.discord_bot.commands.admin.has_admin_permissions', new_callable=AsyncMock) as mock_has_admin, \
             patch('asyncio.create_task') as mock_create_task:
            mock_has_admin.return_value = True
            
            await admin_commands.cleanup_command(mock_interaction, mock_download_monitor)
            
            mock_interaction.followup.send.assert_awaited_once()
            mock_interaction.edit_original_response.assert_awaited_once()
            mock_create_task.assert_called_once()
