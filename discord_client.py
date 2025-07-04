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

        @self.bot.tree.command(name="progress", description="Show progress tracking statistics (admin only)")
        async def progress_slash(interaction: discord.Interaction):
            """Slash command to show progress tracking statistics."""
            # Check if user has admin privileges
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("You need administrator permissions to use this command.", ephemeral=True)
                return
                
            await interaction.response.defer(ephemeral=True)
            
            try:
                # Check if download monitor is available
                if not self.download_monitor:
                    await interaction.followup.send("Download monitor is not initialized yet. Please try again later.", ephemeral=True)
                    return
                
                # Get progress tracking statistics
                progress_stats = self.download_monitor.cache_manager.get_progress_statistics()
                stuck_downloads = self.download_monitor.cache_manager.analyze_stuck_downloads()
                
                # Create statistics embed
                embed = discord.Embed(
                    title="📊 Progress Tracking Statistics",
                    description="Current status of download progress monitoring.",
                    color=discord.Color.blue()
                )
                
                # Add tracking statistics
                embed.add_field(
                    name="🔍 Tracking Overview",
                    value=f"• **Downloads tracked:** {progress_stats.get('total_downloads', 0)}\n"
                          f"• **Total snapshots:** {progress_stats.get('total_snapshots', 0)}\n"
                          f"• **Avg snapshots/download:** {progress_stats.get('avg_snapshots_per_download', 0)}\n"
                          f"• **Memory usage:** {progress_stats.get('memory_usage_estimate_kb', 0):.1f} KB",
                    inline=False
                )
                
                # Add stuck download analysis
                embed.add_field(
                    name="🚫 Stuck Download Analysis",
                    value=f"• **Currently stuck:** {len(stuck_downloads)}\n"
                          f"• **Threshold:** {config.STUCK_THRESHOLD_MINUTES} minutes\n"
                          f"• **Min progress change:** {config.MIN_PROGRESS_CHANGE}%\n"
                          f"• **Min size change:** {config.MIN_SIZE_CHANGE / (1024*1024):.0f} MB",
                    inline=False
                )
                
                # Add configuration details
                embed.add_field(
                    name="⚙️ Configuration",
                    value=f"• **History window:** {config.PROGRESS_HISTORY_HOURS} hours\n"
                          f"• **Max snapshots/download:** {config.MAX_SNAPSHOTS_PER_DOWNLOAD}\n"
                          f"• **Refresh interval:** 5 seconds\n"
                          f"• **Check interval:** {config.CHECK_INTERVAL} seconds",
                    inline=False
                )
                
                # Add details about stuck downloads if any
                if stuck_downloads:
                    stuck_details = []
                    for item in stuck_downloads[:3]:  # Show first 3 stuck downloads
                        duration_hours = item['stuck_duration_minutes'] / 60
                        progress = item['progress_percent']
                        stuck_details.append(f"• **{item['title'][:25]}...** ({duration_hours:.1f}h, {progress:.1f}%)")
                    
                    if len(stuck_downloads) > 3:
                        stuck_details.append(f"• ... and {len(stuck_downloads) - 3} more")
                    
                    embed.add_field(
                        name="🔴 Currently Stuck Downloads",
                        value="\n".join(stuck_details),
                        inline=False
                    )
                
                # Set color based on stuck downloads
                if len(stuck_downloads) > 0:
                    embed.color = discord.Color.orange()
                else:
                    embed.color = discord.Color.green()
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
            except Exception as e:
                logger.error(f"Error in progress command: {e}", exc_info=True)
                await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)

        @self.bot.tree.command(name="cleanup", description="Remove stuck and inactive downloads from queue (admin only)")
        async def cleanup_slash(interaction: discord.Interaction):
            """Slash command to remove stuck and inactive downloads from queue."""
            # Check if user has admin privileges
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("You need administrator permissions to use this command.", ephemeral=True)
                return
                
            # Always acknowledge the interaction immediately to avoid timeout
            await interaction.response.defer(ephemeral=True)
            
            try:
                # Check if download monitor is available
                if not self.download_monitor:
                    await interaction.followup.send("Download monitor is not initialized yet. Please try again later.", ephemeral=True)
                    return
                
                # Analyze stuck downloads using progress tracking
                stuck_downloads = self.download_monitor.cache_manager.analyze_stuck_downloads()
                
                # Separate stuck downloads by service
                radarr_stuck_ids = [item['id'] for item in stuck_downloads if item['service'] == 'radarr']
                sonarr_stuck_ids = [item['id'] for item in stuck_downloads if item['service'] == 'sonarr']
                
                # Remove stuck downloads
                radarr_stuck_count = self.download_monitor.radarr_client.remove_stuck_downloads(radarr_stuck_ids)
                sonarr_stuck_count = self.download_monitor.sonarr_client.remove_stuck_downloads(sonarr_stuck_ids)
                
                # Also remove traditionally inactive items (failed, completed with errors, etc.)
                radarr_inactive_count = self.download_monitor.radarr_client.remove_inactive_items()
                sonarr_inactive_count = self.download_monitor.sonarr_client.remove_inactive_items()
                
                # Get progress tracking statistics
                progress_stats = self.download_monitor.cache_manager.get_progress_statistics()
                
                # Create detailed response embed
                embed = discord.Embed(
                    title="Smart Queue Cleanup Completed",
                    description="Analyzed download progress and removed stuck/inactive items.",
                    color=discord.Color.green()
                )
                
                # Add analysis results
                embed.add_field(
                    name="📊 Analysis Results",
                    value=f"• {progress_stats.get('total_downloads', 0)} downloads tracked\n"
                          f"• {len(stuck_downloads)} stuck downloads identified\n"
                          f"• Memory usage: {progress_stats.get('memory_usage_estimate_kb', 0):.1f} KB",
                    inline=False
                )
                
                # Add removal results
                total_stuck = radarr_stuck_count + sonarr_stuck_count
                total_inactive = radarr_inactive_count + sonarr_inactive_count
                
                embed.add_field(
                    name="🗑️ Removed Items",
                    value=f"**Stuck Downloads:** {total_stuck}\n"
                          f"• Radarr: {radarr_stuck_count}\n"
                          f"• Sonarr: {sonarr_stuck_count}\n\n"
                          f"**Inactive Items:** {total_inactive}\n"
                          f"• Radarr: {radarr_inactive_count}\n"
                          f"• Sonarr: {sonarr_inactive_count}",
                    inline=False
                )
                
                # Add details about stuck downloads if any were found
                if stuck_downloads:
                    stuck_details = []
                    for item in stuck_downloads[:5]:  # Show first 5 stuck downloads
                        duration_hours = item['stuck_duration_minutes'] / 60
                        stuck_details.append(f"• {item['title'][:30]}... ({duration_hours:.1f}h no progress)")
                    
                    if len(stuck_downloads) > 5:
                        stuck_details.append(f"• ... and {len(stuck_downloads) - 5} more")
                    
                    embed.add_field(
                        name="🚫 Stuck Downloads Removed",
                        value="\n".join(stuck_details),
                        inline=False
                    )
                
                # Set color based on results
                if total_stuck > 0:
                    embed.color = discord.Color.orange()  # Orange if stuck downloads were found
                elif total_inactive > 0:
                    embed.color = discord.Color.blue()    # Blue if only inactive items
                else:
                    embed.color = discord.Color.green()   # Green if nothing to clean
                
                # Send the final response
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                # Refresh the queue display
                if self.download_monitor:
                    # Use create_task to avoid blocking this interaction
                    asyncio.create_task(self.download_monitor.check_downloads())
                    
            except Exception as e:
                logger.error(f"Error in cleanup command: {e}", exc_info=True)
                await interaction.followup.send(f"An error occurred during cleanup: {str(e)}", ephemeral=True)
    
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
