"""
Unit tests for Discord interaction utilities.
"""
import pytest
from unittest.mock import Mock, AsyncMock
import discord
from src.utils.interaction_utils import (
    safe_defer_interaction, 
    safe_send_response, 
    handle_interaction_error,
    has_admin_permissions,
    is_guild_owner
)


class TestSafeDeferInteraction:
    """Test cases for safe_defer_interaction function."""
    
    @pytest.mark.asyncio
    async def test_successful_defer(self):
        """Test successful interaction deferral."""
        # Arrange
        mock_interaction = Mock(spec=discord.Interaction)
        mock_response = Mock()
        mock_response.is_done.return_value = False
        mock_response.defer = AsyncMock()
        mock_interaction.response = mock_response
        
        # Act
        result = await safe_defer_interaction(mock_interaction)
        
        # Assert
        assert result is True
        mock_response.defer.assert_called_once_with(ephemeral=True)
    
    @pytest.mark.asyncio
    async def test_defer_with_custom_ephemeral(self):
        """Test deferral with custom ephemeral setting."""
        # Arrange
        mock_interaction = Mock(spec=discord.Interaction)
        mock_response = Mock()
        mock_response.is_done.return_value = False
        mock_response.defer = AsyncMock()
        mock_interaction.response = mock_response
        
        # Act
        result = await safe_defer_interaction(mock_interaction, ephemeral=False)
        
        # Assert
        assert result is True
        mock_response.defer.assert_called_once_with(ephemeral=False)
    
    @pytest.mark.asyncio
    async def test_defer_already_responded(self):
        """Test deferral when interaction already responded."""
        # Arrange
        mock_interaction = Mock(spec=discord.Interaction)
        mock_response = Mock()
        mock_response.is_done.return_value = True
        mock_interaction.response = mock_response
        
        # Act
        result = await safe_defer_interaction(mock_interaction)
        
        # Assert
        assert result is True  # Changed: now returns True when already handled
    
    @pytest.mark.asyncio
    async def test_defer_interaction_timeout(self):
        """Test deferral when interaction times out."""
        # Arrange
        mock_interaction = Mock(spec=discord.Interaction)
        mock_response = Mock()
        mock_response.is_done.return_value = False
        mock_response.defer = AsyncMock(side_effect=discord.errors.NotFound(
            Mock(status=404), 
            'Unknown interaction'
        ))
        mock_interaction.response = mock_response
        
        # Act
        result = await safe_defer_interaction(mock_interaction)
        
        # Assert
        assert result is False
    
    @pytest.mark.asyncio
    async def test_defer_http_exception(self):
        """Test deferral with HTTP exception."""
        # Arrange
        mock_interaction = Mock(spec=discord.Interaction)
        mock_response = Mock()
        mock_response.is_done.return_value = False
        mock_response.defer = AsyncMock(side_effect=discord.errors.HTTPException(
            Mock(status=500), 
            'Server error'
        ))
        mock_interaction.response = mock_response
        
        # Act
        result = await safe_defer_interaction(mock_interaction)
        
        # Assert
        assert result is False


class TestSafeSendResponse:
    """Test cases for safe_send_response function."""
    
    @pytest.mark.asyncio
    async def test_send_initial_response_with_content(self):
        """Test sending initial response with content."""
        # Arrange
        mock_interaction = Mock(spec=discord.Interaction)
        mock_response = Mock()
        mock_response.is_done.return_value = False
        mock_response.send_message = AsyncMock()
        mock_interaction.response = mock_response
        
        # Act
        result = await safe_send_response(mock_interaction, content="Test message")
        
        # Assert
        assert result is True
        mock_response.send_message.assert_called_once_with(
            content="Test message", 
            ephemeral=True
        )
    
    @pytest.mark.asyncio
    async def test_send_followup_response(self):
        """Test sending followup response after defer."""
        # Arrange
        mock_interaction = Mock(spec=discord.Interaction)
        mock_response = Mock()
        mock_response.is_done.return_value = True
        mock_interaction.response = mock_response
        
        mock_followup = Mock()
        mock_followup.send = AsyncMock()
        mock_interaction.followup = mock_followup
        
        # Act
        result = await safe_send_response(mock_interaction, content="Test message")
        
        # Assert
        assert result is True
        mock_followup.send.assert_called_once_with(
            content="Test message", 
            ephemeral=True
        )
    
    @pytest.mark.asyncio
    async def test_send_with_embed(self):
        """Test sending response with embed."""
        # Arrange
        mock_interaction = Mock(spec=discord.Interaction)
        mock_response = Mock()
        mock_response.is_done.return_value = False
        mock_response.send_message = AsyncMock()
        mock_interaction.response = mock_response
        
        embed = discord.Embed(title="Test", description="Test embed")
        
        # Act
        result = await safe_send_response(mock_interaction, embed=embed)
        
        # Assert
        assert result is True
        mock_response.send_message.assert_called_once_with(
            embed=embed, 
            ephemeral=True
        )
    
    @pytest.mark.asyncio
    async def test_send_default_message(self):
        """Test sending default message when no content provided."""
        # Arrange
        mock_interaction = Mock(spec=discord.Interaction)
        mock_response = Mock()
        mock_response.is_done.return_value = False
        mock_response.send_message = AsyncMock()
        mock_interaction.response = mock_response
        
        # Act
        result = await safe_send_response(mock_interaction)
        
        # Assert
        assert result is True
        # Check that send_message was called with the default message
        mock_response.send_message.assert_called_once()
        call_args = mock_response.send_message.call_args
        assert "Command completed." in str(call_args)
        assert call_args[1]['ephemeral'] is True
    
    @pytest.mark.asyncio
    async def test_send_response_timeout(self):
        """Test sending response when interaction times out."""
        # Arrange
        mock_interaction = Mock(spec=discord.Interaction)
        mock_response = Mock()
        mock_response.is_done.return_value = False
        mock_response.send_message = AsyncMock(side_effect=discord.errors.NotFound(
            Mock(status=404), 
            'Unknown interaction'
        ))
        mock_interaction.response = mock_response
        
        # Act
        result = await safe_send_response(mock_interaction, content="Test message")
        
        # Assert
        assert result is False


class TestHandleInteractionError:
    """Test cases for handle_interaction_error function."""
    
    @pytest.mark.asyncio
    async def test_handle_error_success(self):
        """Test successful error handling."""
        # Arrange
        mock_interaction = Mock(spec=discord.Interaction)
        mock_response = Mock()
        mock_response.is_done.return_value = False
        mock_response.send_message = AsyncMock()
        mock_interaction.response = mock_response
        
        # Act
        await handle_interaction_error(mock_interaction, "Test error")
        
        # Assert
        mock_response.send_message.assert_called_once()
        call_args = mock_response.send_message.call_args
        assert call_args[1]['ephemeral'] is True
        assert call_args[1]['embed'].description == "Test error"
    
    @pytest.mark.asyncio
    async def test_handle_error_failure(self):
        """Test error handling when sending error message fails."""
        # Arrange
        mock_interaction = Mock(spec=discord.Interaction)
        mock_response = Mock()
        mock_response.is_done.return_value = False
        mock_response.send_message = AsyncMock(side_effect=discord.errors.NotFound(
            Mock(status=404), 
            'Unknown interaction'
        ))
        mock_interaction.response = mock_response
        
        # Act - should not raise exception
        await handle_interaction_error(mock_interaction, "Test error")
        
        # Assert - function completes without exception


class TestPermissionHelpers:
    """Test cases for permission helper functions."""
    
    def test_has_admin_permissions_success(self):
        """Test successful admin permission check."""
        # Arrange
        mock_interaction = Mock(spec=discord.Interaction)
        mock_guild = Mock()
        mock_interaction.guild = mock_guild
        
        mock_user = Mock()
        mock_permissions = Mock()
        mock_permissions.administrator = True
        mock_user.guild_permissions = mock_permissions
        mock_interaction.user = mock_user
        
        # Act
        result = has_admin_permissions(mock_interaction)
        
        # Assert
        assert result is True
    
    def test_has_admin_permissions_no_admin(self):
        """Test admin permission check when user is not admin."""
        # Arrange
        mock_interaction = Mock(spec=discord.Interaction)
        mock_guild = Mock()
        mock_guild.owner_id = 12345
        mock_interaction.guild = mock_guild
        
        mock_user = Mock()
        mock_permissions = Mock()
        mock_permissions.administrator = False
        mock_user.guild_permissions = mock_permissions
        mock_user.id = 67890
        mock_interaction.user = mock_user
        
        # Act
        result = has_admin_permissions(mock_interaction)
        
        # Assert
        assert result is False
    
    def test_has_admin_permissions_no_guild(self):
        """Test admin permission check when not in guild."""
        # Arrange
        mock_interaction = Mock(spec=discord.Interaction)
        mock_interaction.guild = None
        
        # Act
        result = has_admin_permissions(mock_interaction)
        
        # Assert
        assert result is False
    
    def test_has_admin_permissions_fallback_to_owner(self):
        """Test admin permission check falls back to owner check."""
        # Arrange
        mock_interaction = Mock(spec=discord.Interaction)
        mock_guild = Mock()
        mock_guild.owner_id = 12345
        mock_interaction.guild = mock_guild
        
        mock_user = Mock()
        mock_user.id = 12345
        # Simulate User object without guild_permissions
        del mock_user.guild_permissions
        mock_interaction.user = mock_user
        
        # Act
        result = has_admin_permissions(mock_interaction)
        
        # Assert
        assert result is True
    
    def test_is_guild_owner_success(self):
        """Test successful guild owner check."""
        # Arrange
        mock_interaction = Mock(spec=discord.Interaction)
        mock_guild = Mock()
        mock_guild.owner_id = 12345
        mock_interaction.guild = mock_guild
        
        mock_user = Mock()
        mock_user.id = 12345
        mock_interaction.user = mock_user
        
        # Act
        result = is_guild_owner(mock_interaction)
        
        # Assert
        assert result is True
    
    def test_is_guild_owner_not_owner(self):
        """Test guild owner check when user is not owner."""
        # Arrange
        mock_interaction = Mock(spec=discord.Interaction)
        mock_guild = Mock()
        mock_guild.owner_id = 12345
        mock_interaction.guild = mock_guild
        
        mock_user = Mock()
        mock_user.id = 67890
        mock_interaction.user = mock_user
        
        # Act
        result = is_guild_owner(mock_interaction)
        
        # Assert
        assert result is False
    
    def test_is_guild_owner_no_guild(self):
        """Test guild owner check when not in guild."""
        # Arrange
        mock_interaction = Mock(spec=discord.Interaction)
        mock_interaction.guild = None
        
        # Act
        result = is_guild_owner(mock_interaction)
        
        # Assert
        assert result is False
