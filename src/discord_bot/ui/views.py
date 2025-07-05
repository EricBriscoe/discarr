"""
Discord UI Views for Discarr bot.
Contains View classes for interactive components like pagination.
"""
import discord
from discord.ui import View, Button
from src.discord_bot.ui.pagination import PaginationManager, FIRST_PAGE_ID, PREV_PAGE_ID, NEXT_PAGE_ID, LAST_PAGE_ID
from src.utils.interaction_utils import safe_defer_interaction, safe_send_response, handle_interaction_error
import logging

logger = logging.getLogger(__name__)


class PaginationView(View):
    """Discord View for pagination controls."""
    
    def __init__(self, download_monitor=None):
        """Initialize the pagination view.
        
        Args:
            download_monitor: Reference to the DownloadMonitor instance
        """
        super().__init__(timeout=None)  # Persistent view
        self.download_monitor = download_monitor
        self.pagination_manager = PaginationManager()
    
    @discord.ui.button(label="First", style=discord.ButtonStyle.secondary, custom_id=FIRST_PAGE_ID)
    async def first_page(self, interaction: discord.Interaction, button: Button):
        """Handle first page button click."""
        await self._handle_pagination(interaction, FIRST_PAGE_ID)
    
    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary, custom_id=PREV_PAGE_ID)
    async def previous_page(self, interaction: discord.Interaction, button: Button):
        """Handle previous page button click."""
        await self._handle_pagination(interaction, PREV_PAGE_ID)
    
    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, custom_id=NEXT_PAGE_ID)
    async def next_page(self, interaction: discord.Interaction, button: Button):
        """Handle next page button click."""
        await self._handle_pagination(interaction, NEXT_PAGE_ID)
    
    @discord.ui.button(label="Last", style=discord.ButtonStyle.secondary, custom_id=LAST_PAGE_ID)
    async def last_page(self, interaction: discord.Interaction, button: Button):
        """Handle last page button click."""
        await self._handle_pagination(interaction, LAST_PAGE_ID)
    
    async def _handle_pagination(self, interaction: discord.Interaction, button_id: str):
        """Handle pagination button clicks.
        
        Args:
            interaction: Discord interaction object
            button_id: ID of the button that was clicked
        """
        try:
            # Safely defer the interaction to avoid timeout
            defer_success = await safe_defer_interaction(interaction, ephemeral=True)
            if not defer_success:
                logger.error(f"Failed to defer interaction for button {button_id}")
                return
            
            # Update pagination state
            changed = self.pagination_manager.handle_button(button_id)
            
            if changed and self.download_monitor:
                # Instead of triggering a full check_downloads (which can be slow),
                # just update the display with existing cached data
                await self._update_display_only()
                logger.debug(f"Pagination updated via button {button_id}")
            
        except Exception as e:
            logger.error(f"Error handling pagination button {button_id}: {e}", exc_info=True)
            await handle_interaction_error(
                interaction, 
                f"Failed to update page. Please try again.",
                ephemeral=True
            )
    
    async def _update_display_only(self):
        """Update the display with current cached data without triggering a full refresh."""
        try:
            if not self.download_monitor:
                return
                
            # Get current cached data
            movie_downloads = self.download_monitor.cache_manager.get_movie_queue()
            tv_downloads = self.download_monitor.cache_manager.get_tv_queue()
            
            # Check if data is ready
            radarr_ready = self.download_monitor.cache_manager.is_radarr_ready()
            sonarr_ready = self.download_monitor.cache_manager.is_sonarr_ready()
            
            if radarr_ready and sonarr_ready:
                # Import the formatter here to avoid circular imports
                from src.discord_bot.ui.formatters import format_summary_message
                
                # Format the message with updated pagination
                embed = format_summary_message(
                    movie_downloads, 
                    tv_downloads, 
                    self.pagination_manager,
                    self.download_monitor.last_update
                )
                
                # Update the message directly
                await self.download_monitor._update_message(embed)
                
        except Exception as e:
            logger.error(f"Error updating display only: {e}", exc_info=True)
            # Fallback to full refresh if display-only update fails
            if self.download_monitor:
                await self.download_monitor.check_downloads()
