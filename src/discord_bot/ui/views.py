"""
Discord UI Views for Discarr bot.
Contains View classes for interactive components like pagination.
"""
import discord
from discord.ui import View, Button
from discord_bot.ui.pagination import PaginationManager, FIRST_PAGE_ID, PREV_PAGE_ID, NEXT_PAGE_ID, LAST_PAGE_ID
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
            # Defer the interaction to avoid timeout
            await interaction.response.defer()
            
            # Update pagination state
            changed = self.pagination_manager.handle_button(button_id)
            
            if changed and self.download_monitor:
                # Trigger a refresh of the download display
                await self.download_monitor.check_downloads()
                logger.debug(f"Pagination updated via button {button_id}")
            
            # Send acknowledgment
            await interaction.followup.send("Page updated.", ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error handling pagination button {button_id}: {e}", exc_info=True)
            try:
                await interaction.followup.send("Error updating page.", ephemeral=True)
            except:
                pass  # Ignore if we can't send error message
