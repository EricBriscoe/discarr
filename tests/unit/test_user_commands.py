"""
Tests for the Discord bot user commands module.
"""
import pytest
import sys
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import discord

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from discord_bot.commands.user import UserCommands


class TestUserCommands:
    """Test user command functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_settings = Mock()
        self.mock_settings.discord_channel_id = 123456789
        self.user_commands = UserCommands(self.mock_settings)
    
    def test_initialization(self):
        """Test UserCommands initialization."""
        assert self.user_commands.settings == self.mock_settings
    
    @pytest.mark.asyncio
    async def test_check_command_success(self):
        """Test successful check command execution."""
        # Setup mocks
        mock_interaction = Mock(spec=discord.Interaction)
        mock_interaction.channel_id = 123456789
        
        mock_download_monitor = AsyncMock()
        
        with patch('discord_bot.commands.user.safe_defer_interaction', return_value=True) as mock_defer, \
             patch('discord_bot.commands.user.safe_send_response') as mock_send:
            
            await self.user_commands.check_command(mock_interaction, mock_download_monitor)
            
            # Verify interactions
            mock_defer.assert_called_once_with(mock_interaction, ephemeral=True)
            mock_send.assert_called_once_with(
                mock_interaction, 
                content="Manual check triggered...", 
                ephemeral=True
            )
            mock_download_monitor.check_downloads.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_command_wrong_channel(self):
        """Test check command in wrong channel."""
        # Setup mocks
        mock_interaction = Mock(spec=discord.Interaction)
        mock_interaction.channel_id = 987654321  # Different channel
        
        mock_download_monitor = AsyncMock()
        
        with patch('discord_bot.commands.user.safe_send_response') as mock_send:
            
            await self.user_commands.check_command(mock_interaction, mock_download_monitor)
            
            # Verify error response
            mock_send.assert_called_once_with(
                mock_interaction,
                content="This command can only be used in the designated channel.",
                ephemeral=True
            )
            # Download monitor should not be called
            mock_download_monitor.check_downloads.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_check_command_defer_failure(self):
        """Test check command when defer fails."""
        # Setup mocks
        mock_interaction = Mock(spec=discord.Interaction)
        mock_interaction.channel_id = 123456789
        
        mock_download_monitor = AsyncMock()
        
        # Mock interaction response to simulate not being done yet
        mock_interaction.response.is_done.return_value = False
        
        with patch('discord_bot.commands.user.safe_defer_interaction', return_value=False) as mock_defer, \
             patch('discord_bot.commands.user.handle_interaction_error') as mock_error:
            
            await self.user_commands.check_command(mock_interaction, mock_download_monitor)
            
            # Verify error handling
            mock_defer.assert_called_once_with(mock_interaction, ephemeral=True)
            mock_error.assert_called_once_with(
                mock_interaction,
                "Failed to process command due to interaction timeout. Please try again."
            )
            # Download monitor should not be called
            mock_download_monitor.check_downloads.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_check_command_no_download_monitor(self):
        """Test check command with no download monitor."""
        # Setup mocks
        mock_interaction = Mock(spec=discord.Interaction)
        mock_interaction.channel_id = 123456789
        
        with patch('discord_bot.commands.user.safe_defer_interaction', return_value=True) as mock_defer, \
             patch('discord_bot.commands.user.safe_send_response') as mock_send:
            
            await self.user_commands.check_command(mock_interaction, None)
            
            # Verify interactions
            mock_defer.assert_called_once_with(mock_interaction, ephemeral=True)
            mock_send.assert_called_once_with(
                mock_interaction, 
                content="Manual check triggered...", 
                ephemeral=True
            )
            # No exception should be raised
    
    @pytest.mark.asyncio
    async def test_health_command_success(self):
        """Test successful health command execution."""
        # Setup mocks
        mock_interaction = Mock(spec=discord.Interaction)
        mock_interaction.channel_id = 123456789
        
        mock_download_monitor = AsyncMock()
        
        with patch('discord_bot.commands.user.safe_defer_interaction', return_value=True) as mock_defer, \
             patch('discord_bot.commands.user.safe_send_response') as mock_send:
            
            await self.user_commands.health_command(mock_interaction, mock_download_monitor)
            
            # Verify interactions
            mock_defer.assert_called_once_with(mock_interaction, ephemeral=True)
            mock_send.assert_called_once_with(
                mock_interaction, 
                content="Manual health check triggered...", 
                ephemeral=True
            )
            mock_download_monitor.check_health.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_command_wrong_channel(self):
        """Test health command in wrong channel."""
        # Setup mocks
        mock_interaction = Mock(spec=discord.Interaction)
        mock_interaction.channel_id = 987654321  # Different channel
        
        mock_download_monitor = AsyncMock()
        
        with patch('discord_bot.commands.user.safe_send_response') as mock_send:
            
            await self.user_commands.health_command(mock_interaction, mock_download_monitor)
            
            # Verify error response
            mock_send.assert_called_once_with(
                mock_interaction,
                content="This command can only be used in the designated channel.",
                ephemeral=True
            )
            # Download monitor should not be called
            mock_download_monitor.check_health.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_health_command_defer_failure(self):
        """Test health command when defer fails."""
        # Setup mocks
        mock_interaction = Mock(spec=discord.Interaction)
        mock_interaction.channel_id = 123456789
        
        mock_download_monitor = AsyncMock()
        
        # Mock interaction response to simulate not being done yet
        mock_interaction.response.is_done.return_value = False
        
        with patch('discord_bot.commands.user.safe_defer_interaction', return_value=False) as mock_defer, \
             patch('discord_bot.commands.user.handle_interaction_error') as mock_error:
            
            await self.user_commands.health_command(mock_interaction, mock_download_monitor)
            
            # Verify error handling
            mock_defer.assert_called_once_with(mock_interaction, ephemeral=True)
            mock_error.assert_called_once_with(
                mock_interaction,
                "Failed to process command due to interaction timeout. Please try again."
            )
            # Download monitor should not be called
            mock_download_monitor.check_health.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_health_command_no_download_monitor(self):
        """Test health command with no download monitor."""
        # Setup mocks
        mock_interaction = Mock(spec=discord.Interaction)
        mock_interaction.channel_id = 123456789
        
        with patch('discord_bot.commands.user.safe_defer_interaction', return_value=True) as mock_defer, \
             patch('discord_bot.commands.user.safe_send_response') as mock_send:
            
            await self.user_commands.health_command(mock_interaction, None)
            
            # Verify interactions
            mock_defer.assert_called_once_with(mock_interaction, ephemeral=True)
            mock_send.assert_called_once_with(
                mock_interaction, 
                content="Manual health check triggered...", 
                ephemeral=True
            )
            # No exception should be raised
    
    @pytest.mark.asyncio
    async def test_check_command_with_different_settings(self):
        """Test check command with different channel settings."""
        # Create user commands with different channel ID
        different_settings = Mock()
        different_settings.discord_channel_id = 555666777
        user_commands = UserCommands(different_settings)
        
        mock_interaction = Mock(spec=discord.Interaction)
        mock_interaction.channel_id = 555666777  # Matching channel
        
        mock_download_monitor = AsyncMock()
        
        with patch('discord_bot.commands.user.safe_defer_interaction', return_value=True) as mock_defer, \
             patch('discord_bot.commands.user.safe_send_response') as mock_send:
            
            await user_commands.check_command(mock_interaction, mock_download_monitor)
            
            # Should work with the correct channel ID
            mock_defer.assert_called_once_with(mock_interaction, ephemeral=True)
            mock_send.assert_called_once()
            mock_download_monitor.check_downloads.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_command_with_different_settings(self):
        """Test health command with different channel settings."""
        # Create user commands with different channel ID
        different_settings = Mock()
        different_settings.discord_channel_id = 555666777
        user_commands = UserCommands(different_settings)
        
        mock_interaction = Mock(spec=discord.Interaction)
        mock_interaction.channel_id = 555666777  # Matching channel
        
        mock_download_monitor = AsyncMock()
        
        with patch('discord_bot.commands.user.safe_defer_interaction', return_value=True) as mock_defer, \
             patch('discord_bot.commands.user.safe_send_response') as mock_send:
            
            await user_commands.health_command(mock_interaction, mock_download_monitor)
            
            # Should work with the correct channel ID
            mock_defer.assert_called_once_with(mock_interaction, ephemeral=True)
            mock_send.assert_called_once()
            mock_download_monitor.check_health.assert_called_once()


class TestUserCommandsEdgeCases:
    """Test edge cases and error scenarios for user commands."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_settings = Mock()
        self.mock_settings.discord_channel_id = 123456789
        self.user_commands = UserCommands(self.mock_settings)
    
    @pytest.mark.asyncio
    async def test_check_command_exception_in_download_monitor(self):
        """Test check command when download monitor raises exception."""
        mock_interaction = Mock(spec=discord.Interaction)
        mock_interaction.channel_id = 123456789
        
        mock_download_monitor = AsyncMock()
        mock_download_monitor.check_downloads.side_effect = Exception("Test error")
        
        with patch('discord_bot.commands.user.safe_defer_interaction', return_value=True), \
             patch('discord_bot.commands.user.safe_send_response'):
            
            # The user commands don't handle exceptions - they propagate them
            # This is the expected behavior, so we test that the exception is raised
            with pytest.raises(Exception, match="Test error"):
                await self.user_commands.check_command(mock_interaction, mock_download_monitor)
    
    @pytest.mark.asyncio
    async def test_health_command_exception_in_download_monitor(self):
        """Test health command when download monitor raises exception."""
        mock_interaction = Mock(spec=discord.Interaction)
        mock_interaction.channel_id = 123456789
        
        mock_download_monitor = AsyncMock()
        mock_download_monitor.check_health.side_effect = Exception("Test error")
        
        with patch('discord_bot.commands.user.safe_defer_interaction', return_value=True), \
             patch('discord_bot.commands.user.safe_send_response'):
            
            # The user commands don't handle exceptions - they propagate them
            # This is the expected behavior, so we test that the exception is raised
            with pytest.raises(Exception, match="Test error"):
                await self.user_commands.health_command(mock_interaction, mock_download_monitor)
    
    @pytest.mark.asyncio
    async def test_commands_with_none_channel_id(self):
        """Test commands when channel_id is None."""
        mock_settings = Mock()
        mock_settings.discord_channel_id = None
        user_commands = UserCommands(mock_settings)
        
        mock_interaction = Mock(spec=discord.Interaction)
        mock_interaction.channel_id = 123456789
        
        with patch('discord_bot.commands.user.safe_send_response') as mock_send:
            await user_commands.check_command(mock_interaction, None)
            
            # Should send error message since channel IDs don't match (None != 123456789)
            mock_send.assert_called_once_with(
                mock_interaction,
                content="This command can only be used in the designated channel.",
                ephemeral=True
            )
    
    @pytest.mark.asyncio
    async def test_commands_with_zero_channel_id(self):
        """Test commands when channel_id is 0."""
        mock_settings = Mock()
        mock_settings.discord_channel_id = 0
        user_commands = UserCommands(mock_settings)
        
        mock_interaction = Mock(spec=discord.Interaction)
        mock_interaction.channel_id = 0  # Matching zero
        
        mock_download_monitor = AsyncMock()
        
        with patch('discord_bot.commands.user.safe_defer_interaction', return_value=True), \
             patch('discord_bot.commands.user.safe_send_response'):
            
            await user_commands.check_command(mock_interaction, mock_download_monitor)
            
            # Should work even with zero channel ID
            mock_download_monitor.check_downloads.assert_called_once()
