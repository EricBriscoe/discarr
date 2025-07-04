"""
User commands for Discarr Discord bot.
Commands that regular users can execute.
"""
import logging
import discord

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
            await interaction.response.send_message(
                "This command can only be used in the designated channel.", 
                ephemeral=True
            )
            return

        # Defer the response and trigger manual check
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send("Manual check triggered...", ephemeral=True)
        
        if download_monitor:
            await download_monitor.check_downloads()
