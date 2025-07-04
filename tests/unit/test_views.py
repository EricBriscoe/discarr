"""
Tests for the Discord UI views module.
"""
import pytest
import sys
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path
import discord
from discord.ui import Button

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from discord_bot.ui.views import PaginationView
from discord_bot.ui.pagination import FIRST_PAGE_ID, PREV_PAGE_ID, NEXT_PAGE_ID, LAST_PAGE_ID


class TestPaginationView:
    """Test pagination view functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_download_monitor = Mock()
        self.mock_download_monitor.cache_manager = Mock()
        self.mock_download_monitor.last_update = Mock()
        self.mock_download_monitor._update_message = AsyncMock()
        self.mock_download_monitor.check_downloads = AsyncMock()
        
        # Mock the View initialization to avoid event loop issues
        with patch('discord.ui.View.__init__'):
            self.view = PaginationView(self.mock_download_monitor)
    
    def test_initialization_with_download_monitor(self):
        """Test PaginationView initialization with download monitor."""
        with patch('discord.ui.View.__init__') as mock_init:
            view = PaginationView(self.mock_download_monitor)
            # Manually set the required attributes since we're mocking __init__
            view._View__timeout = None
            view._View__timeout_task = None
        
        assert view.download_monitor == self.mock_download_monitor
        assert view.pagination_manager is not None
    
    def test_initialization_without_download_monitor(self):
        """Test PaginationView initialization without download monitor."""
        with patch('discord.ui.View.__init__') as mock_init:
            view = PaginationView()
            # Manually set the required attributes since we're mocking __init__
            view._View__timeout = None
            view._View__timeout_task = None
        
        assert view.download_monitor is None
        assert view.pagination_manager is not None
    
    @pytest.mark.asyncio
    async def test_first_page_button(self):
        """Test first page button functionality."""
        mock_interaction = Mock(spec=discord.Interaction)
        mock_button = Mock(spec=Button)
        
        with patch.object(self.view, '_handle_pagination') as mock_handle:
            await self.view.first_page(mock_interaction, mock_button)
            
            mock_handle.assert_called_once_with(mock_interaction, FIRST_PAGE_ID)
    
    @pytest.mark.asyncio
    async def test_previous_page_button(self):
        """Test previous page button functionality."""
        mock_interaction = Mock(spec=discord.Interaction)
        mock_button = Mock(spec=Button)
        
        with patch.object(self.view, '_handle_pagination') as mock_handle:
            await self.view.previous_page(mock_interaction, mock_button)
            
            mock_handle.assert_called_once_with(mock_interaction, PREV_PAGE_ID)
    
    @pytest.mark.asyncio
    async def test_next_page_button(self):
        """Test next page button functionality."""
        mock_interaction = Mock(spec=discord.Interaction)
        mock_button = Mock(spec=Button)
        
        with patch.object(self.view, '_handle_pagination') as mock_handle:
            await self.view.next_page(mock_interaction, mock_button)
            
            mock_handle.assert_called_once_with(mock_interaction, NEXT_PAGE_ID)
    
    @pytest.mark.asyncio
    async def test_last_page_button(self):
        """Test last page button functionality."""
        mock_interaction = Mock(spec=discord.Interaction)
        mock_button = Mock(spec=Button)
        
        with patch.object(self.view, '_handle_pagination') as mock_handle:
            await self.view.last_page(mock_interaction, mock_button)
            
            mock_handle.assert_called_once_with(mock_interaction, LAST_PAGE_ID)
    
    @pytest.mark.asyncio
    async def test_handle_pagination_success_with_change(self):
        """Test successful pagination handling when page changes."""
        mock_interaction = Mock(spec=discord.Interaction)
        
        with patch('discord_bot.ui.views.safe_defer_interaction', return_value=True) as mock_defer, \
             patch('discord_bot.ui.views.safe_send_response') as mock_send, \
             patch.object(self.view.pagination_manager, 'handle_button', return_value=True) as mock_handle_button, \
             patch.object(self.view, '_update_display_only') as mock_update:
            
            await self.view._handle_pagination(mock_interaction, NEXT_PAGE_ID)
            
            # Verify all steps were called
            mock_defer.assert_called_once_with(mock_interaction, ephemeral=True)
            mock_handle_button.assert_called_once_with(NEXT_PAGE_ID)
            mock_update.assert_called_once()
            mock_send.assert_called_once_with(
                mock_interaction,
                content="✅ Page updated",
                ephemeral=True
            )
    
    @pytest.mark.asyncio
    async def test_handle_pagination_success_no_change(self):
        """Test pagination handling when page doesn't change."""
        mock_interaction = Mock(spec=discord.Interaction)
        
        with patch('discord_bot.ui.views.safe_defer_interaction', return_value=True) as mock_defer, \
             patch('discord_bot.ui.views.safe_send_response') as mock_send, \
             patch.object(self.view.pagination_manager, 'handle_button', return_value=False) as mock_handle_button, \
             patch.object(self.view, '_update_display_only') as mock_update:
            
            await self.view._handle_pagination(mock_interaction, FIRST_PAGE_ID)
            
            # Verify pagination was handled but display wasn't updated
            mock_defer.assert_called_once_with(mock_interaction, ephemeral=True)
            mock_handle_button.assert_called_once_with(FIRST_PAGE_ID)
            mock_update.assert_not_called()  # No change, so no update
            mock_send.assert_called_once_with(
                mock_interaction,
                content="✅ Page updated",
                ephemeral=True
            )
    
    @pytest.mark.asyncio
    async def test_handle_pagination_defer_failure(self):
        """Test pagination handling when defer fails."""
        mock_interaction = Mock(spec=discord.Interaction)
        
        with patch('discord_bot.ui.views.safe_defer_interaction', return_value=False) as mock_defer, \
             patch('discord_bot.ui.views.logger') as mock_logger:
            
            await self.view._handle_pagination(mock_interaction, NEXT_PAGE_ID)
            
            mock_defer.assert_called_once_with(mock_interaction, ephemeral=True)
            mock_logger.error.assert_called_once_with(f"Failed to defer interaction for button {NEXT_PAGE_ID}")
    
    @pytest.mark.asyncio
    async def test_handle_pagination_no_download_monitor(self):
        """Test pagination handling without download monitor."""
        view = PaginationView()  # No download monitor
        mock_interaction = Mock(spec=discord.Interaction)
        
        with patch('discord_bot.ui.views.safe_defer_interaction', return_value=True) as mock_defer, \
             patch('discord_bot.ui.views.safe_send_response') as mock_send, \
             patch.object(view.pagination_manager, 'handle_button', return_value=True) as mock_handle_button:
            
            await view._handle_pagination(mock_interaction, NEXT_PAGE_ID)
            
            # Should still work but not update display
            mock_defer.assert_called_once_with(mock_interaction, ephemeral=True)
            mock_handle_button.assert_called_once_with(NEXT_PAGE_ID)
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_pagination_exception(self):
        """Test pagination handling when exception occurs."""
        mock_interaction = Mock(spec=discord.Interaction)
        
        with patch('discord_bot.ui.views.safe_defer_interaction', return_value=True), \
             patch.object(self.view.pagination_manager, 'handle_button', side_effect=Exception("Test error")), \
             patch('discord_bot.ui.views.handle_interaction_error') as mock_error, \
             patch('discord_bot.ui.views.logger') as mock_logger:
            
            await self.view._handle_pagination(mock_interaction, NEXT_PAGE_ID)
            
            # Should handle exception gracefully
            mock_logger.error.assert_called()
            mock_error.assert_called_once_with(
                mock_interaction,
                "Failed to update page. Please try again.",
                ephemeral=True
            )
    
    @pytest.mark.asyncio
    async def test_update_display_only_success(self):
        """Test successful display-only update."""
        # Setup mock data
        mock_movies = [{'title': 'Test Movie'}]
        mock_tv = [{'series': 'Test Series'}]
        
        self.mock_download_monitor.cache_manager.get_movie_queue.return_value = mock_movies
        self.mock_download_monitor.cache_manager.get_tv_queue.return_value = mock_tv
        self.mock_download_monitor.cache_manager.is_radarr_ready.return_value = True
        self.mock_download_monitor.cache_manager.is_sonarr_ready.return_value = True
        
        mock_embed = Mock()
        
        with patch('src.discord_bot.ui.formatters.format_summary_message', return_value=mock_embed) as mock_format:
            await self.view._update_display_only()
            
            # Verify all steps
            self.mock_download_monitor.cache_manager.get_movie_queue.assert_called_once()
            self.mock_download_monitor.cache_manager.get_tv_queue.assert_called_once()
            self.mock_download_monitor.cache_manager.is_radarr_ready.assert_called_once()
            self.mock_download_monitor.cache_manager.is_sonarr_ready.assert_called_once()
            
            mock_format.assert_called_once_with(
                mock_movies,
                mock_tv,
                self.view.pagination_manager,
                self.mock_download_monitor.last_update
            )
            
            self.mock_download_monitor._update_message.assert_called_once_with(mock_embed)
    
    @pytest.mark.asyncio
    async def test_update_display_only_not_ready(self):
        """Test display-only update when services not ready."""
        self.mock_download_monitor.cache_manager.is_radarr_ready.return_value = False
        self.mock_download_monitor.cache_manager.is_sonarr_ready.return_value = True
        
        with patch('src.discord_bot.ui.formatters.format_summary_message') as mock_format:
            await self.view._update_display_only()
            
            # Should not format or update message when not ready
            mock_format.assert_not_called()
            self.mock_download_monitor._update_message.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_update_display_only_no_download_monitor(self):
        """Test display-only update without download monitor."""
        view = PaginationView()  # No download monitor
        
        # Should return early without error
        await view._update_display_only()
        # No assertions needed - just ensuring no exception is raised
    
    @pytest.mark.asyncio
    async def test_update_display_only_exception_fallback(self):
        """Test display-only update exception with fallback."""
        self.mock_download_monitor.cache_manager.get_movie_queue.side_effect = Exception("Test error")
        
        with patch('discord_bot.ui.views.logger') as mock_logger:
            await self.view._update_display_only()
            
            # Should log error and fallback to full refresh
            mock_logger.error.assert_called()
            self.mock_download_monitor.check_downloads.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_display_only_format_exception_fallback(self):
        """Test display-only update when formatting fails."""
        # Setup successful cache calls
        self.mock_download_monitor.cache_manager.get_movie_queue.return_value = []
        self.mock_download_monitor.cache_manager.get_tv_queue.return_value = []
        self.mock_download_monitor.cache_manager.is_radarr_ready.return_value = True
        self.mock_download_monitor.cache_manager.is_sonarr_ready.return_value = True
        
        with patch('src.discord_bot.ui.formatters.format_summary_message', side_effect=Exception("Format error")), \
             patch('discord_bot.ui.views.logger') as mock_logger:
            
            await self.view._update_display_only()
            
            # Should log error and fallback to full refresh
            mock_logger.error.assert_called()
            self.mock_download_monitor.check_downloads.assert_called_once()


class TestPaginationViewIntegration:
    """Test pagination view integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_full_pagination_workflow(self):
        """Test complete pagination workflow."""
        mock_download_monitor = Mock()
        mock_download_monitor.cache_manager = Mock()
        mock_download_monitor.last_update = Mock()
        mock_download_monitor._update_message = AsyncMock()
        
        # Setup cache data
        mock_download_monitor.cache_manager.get_movie_queue.return_value = [
            {'title': f'Movie {i}'} for i in range(10)
        ]
        mock_download_monitor.cache_manager.get_tv_queue.return_value = [
            {'series': f'Series {i}'} for i in range(5)
        ]
        mock_download_monitor.cache_manager.is_radarr_ready.return_value = True
        mock_download_monitor.cache_manager.is_sonarr_ready.return_value = True
        
        view = PaginationView(mock_download_monitor)
        
        # Setup pagination for multiple pages
        view.pagination_manager.update_page_limits(movie_count=10, tv_count=5)
        
        mock_interaction = Mock(spec=discord.Interaction)
        mock_button = Mock(spec=Button)
        
        with patch('discord_bot.ui.views.safe_defer_interaction', return_value=True), \
             patch('discord_bot.ui.views.safe_send_response'), \
             patch('src.discord_bot.ui.formatters.format_summary_message', return_value=Mock()) as mock_format:
            
            # Test navigation through pages - call the method directly
            await view._handle_pagination(mock_interaction, NEXT_PAGE_ID)
            
            # Verify pagination state changed
            assert view.pagination_manager.movie_current_page == 2
            assert view.pagination_manager.tv_current_page == 2
            
            # Verify display was updated
            mock_format.assert_called()
            mock_download_monitor._update_message.assert_called()
    
    @pytest.mark.asyncio
    async def test_pagination_view_button_attributes(self):
        """Test that pagination view buttons have correct attributes."""
        view = PaginationView()
        
        # Find buttons by their custom_id
        first_button = None
        prev_button = None
        next_button = None
        last_button = None
        
        for item in view.children:
            if hasattr(item, 'custom_id'):
                if item.custom_id == FIRST_PAGE_ID:
                    first_button = item
                elif item.custom_id == PREV_PAGE_ID:
                    prev_button = item
                elif item.custom_id == NEXT_PAGE_ID:
                    next_button = item
                elif item.custom_id == LAST_PAGE_ID:
                    last_button = item
        
        # Verify all buttons exist
        assert first_button is not None
        assert prev_button is not None
        assert next_button is not None
        assert last_button is not None
        
        # Verify button properties
        assert first_button.label == "First"
        assert first_button.style == discord.ButtonStyle.secondary
        
        assert prev_button.label == "Previous"
        assert prev_button.style == discord.ButtonStyle.primary
        
        assert next_button.label == "Next"
        assert next_button.style == discord.ButtonStyle.primary
        
        assert last_button.label == "Last"
        assert last_button.style == discord.ButtonStyle.secondary
    
    @pytest.mark.asyncio
    async def test_pagination_view_with_partial_data_ready(self):
        """Test pagination view when only some services are ready."""
        mock_download_monitor = Mock()
        mock_download_monitor.cache_manager = Mock()
        mock_download_monitor.cache_manager.get_movie_queue.return_value = []
        mock_download_monitor.cache_manager.get_tv_queue.return_value = []
        mock_download_monitor.cache_manager.is_radarr_ready.return_value = True
        mock_download_monitor.cache_manager.is_sonarr_ready.return_value = False  # Not ready
        
        view = PaginationView(mock_download_monitor)
        
        with patch('src.discord_bot.ui.formatters.format_summary_message') as mock_format:
            await view._update_display_only()
            
            # Should not format when not all services are ready
            mock_format.assert_not_called()


class TestPaginationViewErrorHandling:
    """Test error handling in pagination view."""
    
    @pytest.mark.asyncio
    async def test_handle_pagination_with_interaction_error(self):
        """Test pagination handling when interaction methods fail."""
        view = PaginationView()
        mock_interaction = Mock(spec=discord.Interaction)
        
        with patch('discord_bot.ui.views.safe_defer_interaction', side_effect=Exception("Defer error")), \
             patch('discord_bot.ui.views.handle_interaction_error') as mock_error, \
             patch('discord_bot.ui.views.logger') as mock_logger:
            
            await view._handle_pagination(mock_interaction, NEXT_PAGE_ID)
            
            # Should handle exception and call error handler
            mock_logger.error.assert_called()
            mock_error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_display_only_with_missing_methods(self):
        """Test display update when download monitor is missing methods."""
        mock_download_monitor = Mock()
        mock_download_monitor.check_downloads = AsyncMock()
        # Don't set up cache_manager to simulate missing attribute
        
        view = PaginationView(mock_download_monitor)
        
        with patch('discord_bot.ui.views.logger') as mock_logger:
            await view._update_display_only()
            
            # Should handle missing attributes gracefully
            mock_logger.error.assert_called()
            # Should fallback to check_downloads
            mock_download_monitor.check_downloads.assert_called_once()
