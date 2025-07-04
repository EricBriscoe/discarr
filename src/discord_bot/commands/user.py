"""
User commands for Discarr Discord bot.
Commands that regular users can execute.
"""
import logging
import discord
from utils.interaction_utils import safe_defer_interaction, safe_send_response, handle_interaction_error

logger = logging.getLogger(__name__)


class UserCommands:
    """Handler for user-level Discord commands."""
    
    def __init__(self, settings):
        """Initialize user commands.
        
        Args:
            settings: Application settings instance
        """
        self.settings = settings
    
    async def check_command(self, interaction: discord.Interaction, download_monitor):
        """Handle the /check command to manually refresh download status.
        
        Args:
            interaction: Discord interaction object
            download_monitor: DownloadMonitor instance
        """
        # Verify command is used in the correct channel
        if interaction.channel_id != self.settings.discord_channel_id:
            await safe_send_response(
                interaction,
                content="This command can only be used in the designated channel.",
                ephemeral=True
            )
            return

        # Safely defer the interaction to avoid timeout
        defer_success = await safe_defer_interaction(interaction, ephemeral=True)
        if not defer_success:
            await handle_interaction_error(
                interaction,
                "Failed to process command due to interaction timeout. Please try again."
            )
            return

        # Send confirmation and trigger manual check
        await safe_send_response(interaction, content="Manual check triggered...", ephemeral=True)
        
        if download_monitor:
            await download_monitor.check_downloads()
    
    async def health_command(self, interaction: discord.Interaction, download_monitor):
        """Handle the /health command to manually check server health status.
        
        Args:
            interaction: Discord interaction object
            download_monitor: DownloadMonitor instance
        """
        # Verify command is used in the correct channel
        if interaction.channel_id != self.settings.discord_channel_id:
            await safe_send_response(
                interaction,
                content="This command can only be used in the designated channel.",
                ephemeral=True
            )
            return

        # Safely defer the interaction to avoid timeout
        defer_success = await safe_defer_interaction(interaction, ephemeral=True)
        if not defer_success:
            await handle_interaction_error(
                interaction,
                "Failed to process command due to interaction timeout. Please try again."
            )
            return

        # Send confirmation and trigger manual health check
        await safe_send_response(interaction, content="Manual health check triggered...", ephemeral=True)
        
        if download_monitor:
            await download_monitor.check_health()
