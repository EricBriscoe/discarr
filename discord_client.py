"""
Discord bot client for Discarr.
Handles Discord interactions, commands, and events.
"""
import logging
import discord
from discord.ext import commands
from discord import app_commands
import config
from download_monitor import DownloadMonitor
import asyncio
import signal
import sys

logger = logging.getLogger(__name__)

class DiscordClient:
    """Discord client for Discarr bot."""
    
    def __init__(self):
        """Initialize the Discord client."""
        # Configure Discord intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        
        # Create bot with command prefix and intents
        self.bot = commands.Bot(command_prefix='!', intents=intents)
        self.download_monitor = None
        
        # Set up event handlers
        self.setup_event_handlers()
        self.setup_commands()
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        def handle_shutdown_signal(sig, frame):
            """Handle shutdown signals by stopping background tasks."""
            logger.info(f"Received shutdown signal {sig}, cleaning up...")
            if self.download_monitor:
                # Create asyncio task to stop the monitor properly
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.download_monitor.stop())
            # Exit after a short delay to allow cleanup
            sys.exit(0)
            
        # Register signal handlers
        signal.signal(signal.SIGINT, handle_shutdown_signal)
        signal.signal(signal.SIGTERM, handle_shutdown_signal)
        
    def setup_event_handlers(self):
        """Set up Discord bot event handlers."""
        @self.bot.event
        async def on_ready():
            """Handle bot initialization when connected to Discord."""
            logger.info(f'Logged in as {self.bot.user.name} ({self.bot.user.id})')
            
            # Sync slash commands with Discord
            try:
                synced = await self.bot.tree.sync()
                logger.info(f"Synced {len(synced)} command(s)")
            except Exception as e:
                logger.error(f"Failed to sync commands: {e}")
            
            # Schedule the download monitor initialization and start as a background task
            if not self.download_monitor:
                logger.info("Scheduling DownloadMonitor initialization.")
                # Create a task to run the setup in the background
                asyncio.create_task(self.initialize_monitor())
            else:
                logger.info("Download monitor already initialized or initialization scheduled.")
    
    async def initialize_monitor(self):
        """Initializes and starts the DownloadMonitor."""
        # Ensure this runs only once
        if self.download_monitor:
            return
            
        logger.info("Initializing DownloadMonitor...")
        self.download_monitor = DownloadMonitor(self.bot, config.DISCORD_CHANNEL_ID)
        
        # Register the persistent view for our buttons
        self.bot.add_view(self.download_monitor.pagination_view)
        
        await self.download_monitor.start()
        logger.info("DownloadMonitor started.")

    def setup_commands(self):
        """Set up Discord bot slash commands."""
        @self.bot.tree.command(name="check", description="Manually refresh the download status")
        async def check_slash(interaction: discord.Interaction):
            """Slash command to manually refresh the download status."""
            if interaction.channel_id != config.DISCORD_CHANNEL_ID:
                await interaction.response.send_message("This command can only be used in the designated channel.", ephemeral=True)
                return

            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send("Manual check triggered...", ephemeral=True)
            if self.download_monitor:
                await self.download_monitor.check_downloads()

        @self.bot.tree.command(name="verbose", description="Toggle verbose logging (admin only)")
        async def verbose_slash(interaction: discord.Interaction):
            """Slash command to toggle verbose logging (admin only)."""
            if str(interaction.user.id) != str(interaction.guild.owner_id):
                await interaction.response.send_message("Only the server owner can use this command.", ephemeral=True)
                return

            # Defer the response immediately to avoid timeout
            await interaction.response.defer(ephemeral=True)

            # Toggle the global verbose setting
            config.VERBOSE = not config.VERBOSE
            new_level = logging.DEBUG if config.VERBOSE else logging.INFO
            status = "enabled" if config.VERBOSE else "disabled"

            # Update root logger level
            root_logger = logging.getLogger()
            root_logger.setLevel(new_level)

            # Update ArrClient instances if the monitor exists
            if self.download_monitor:
                if self.download_monitor.radarr_client:
                    self.download_monitor.radarr_client.verbose = config.VERBOSE
                    logger.debug(f"Updated RadarrClient verbose to {config.VERBOSE}")
                if self.download_monitor.sonarr_client:
                    self.download_monitor.sonarr_client.verbose = config.VERBOSE
                    logger.debug(f"Updated SonarrClient verbose to {config.VERBOSE}")

            logger.info(f"Verbose mode {status} by admin command")

            embed = discord.Embed(
                title="Verbose Mode Updated",
                description=f"Verbose mode has been {status}.",
                color=discord.Color.green()
            )

            # Send the confirmation via followup
            await interaction.followup.send(embed=embed, ephemeral=True)

        @self.bot.tree.command(name="cleanup", description="Remove inactive downloads from queue (admin only)")
        async def cleanup_slash(interaction: discord.Interaction):
            """Slash command to remove inactive downloads from queue."""
            # Check if user has admin privileges
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("You need administrator permissions to use this command.", ephemeral=True)
                return
                
            # Always acknowledge the interaction immediately to avoid timeout
            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send("Processing cleanup request...", ephemeral=True)
            
            try:
                # Get all queue items
                radarr_items = self.download_monitor.radarr_client.get_queue_items()
                logger.debug(f"Radarr queue items: {radarr_items}")
                sonarr_items = self.download_monitor.sonarr_client.get_queue_items()
                all_items = radarr_items + sonarr_items
                
                # Check if all items have unknown or infinity time remaining
                all_unknown_time = False
                if all_items:
                    all_unknown_time = all(
                        item.get("time_left") == "unknown" or 
                        item.get("time_left") == "∞"
                        for item in all_items
                    )
                
                # Choose the removal method based on the time remaining condition
                if all_unknown_time and all_items:
                    # If all items have unknown time remaining, remove all items
                    radarr_count = self.download_monitor.radarr_client.remove_all_items()
                    sonarr_count = self.download_monitor.sonarr_client.remove_all_items()
                    removal_type = "all"
                else:
                    # Otherwise, only remove inactive items
                    radarr_count = self.download_monitor.radarr_client.remove_inactive_items()
                    sonarr_count = self.download_monitor.sonarr_client.remove_inactive_items()
                    removal_type = "inactive"
                
                # Create response embed
                embed = discord.Embed(
                    title="Queue Cleanup Completed",
                    description=f"Removed {radarr_count + sonarr_count} {removal_type} items from download queues.",
                    color=discord.Color.green()
                )
                
                embed.add_field(name="Radarr", value=f"{radarr_count} items removed", inline=True)
                embed.add_field(name="Sonarr", value=f"{sonarr_count} items removed", inline=True)
                
                # Send the final response
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                # Refresh the queue display
                if self.download_monitor:
                    # Use create_task to avoid blocking this interaction
                    asyncio.create_task(self.download_monitor.check_downloads())
                    
            except Exception as e:
                logger.error(f"Error in cleanup command: {e}", exc_info=True)
                await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)
    
    async def run(self):
        """Run the Discord bot."""
        try:
            await self.bot.start(config.DISCORD_TOKEN)
        finally:
            # Ensure background tasks are cleaned up
            if self.download_monitor:
                await self.download_monitor.stop()
                
    def start(self):
        """Start the Discord bot (blocking call)."""
        self.bot.run(config.DISCORD_TOKEN)
