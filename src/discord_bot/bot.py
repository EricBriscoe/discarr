"""
Simplified Discord bot for Discarr.
Handles bot initialization and delegates to specialized components.
"""
import logging
import discord
from discord.ext import commands
import asyncio
import signal
import sys

from discord_bot.commands.admin import AdminCommands
from discord_bot.commands.user import UserCommands
from monitoring.download_monitor import DownloadMonitor

logger = logging.getLogger(__name__)


class DiscordBot:
    """Main Discord bot class with simplified architecture."""
    
    def __init__(self, settings):
        """Initialize the Discord bot.
        
        Args:
            settings: Application settings instance
        """
        self.settings = settings
        
        # Configure Discord intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        
        # Create bot with command prefix and intents
        self.bot = commands.Bot(command_prefix='!', intents=intents)
        self.download_monitor = None
        
        # Set up components
        self._setup_event_handlers()
        self._setup_commands()
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
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
        
    def _setup_event_handlers(self):
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
            
            # Initialize the download monitor
            if not self.download_monitor:
                logger.info("Initializing DownloadMonitor...")
                asyncio.create_task(self._initialize_monitor())
    
    async def _initialize_monitor(self):
        """Initialize and start the DownloadMonitor."""
        if self.download_monitor:
            return
            
        logger.info("Starting DownloadMonitor...")
        self.download_monitor = DownloadMonitor(self.bot, self.settings)
        
        # Register the persistent view for buttons
        self.bot.add_view(self.download_monitor.pagination_view)
        
        await self.download_monitor.start()
        logger.info("DownloadMonitor started.")

    def _setup_commands(self):
        """Set up Discord bot slash commands."""
        # Initialize command handlers
        admin_commands = AdminCommands(self.settings)
        user_commands = UserCommands(self.settings)
        
        # Register user commands
        @self.bot.tree.command(name="check", description="Manually refresh the download status")
        async def check_slash(interaction: discord.Interaction):
            await user_commands.check_command(interaction, self.download_monitor)

        @self.bot.tree.command(name="health", description="Check server health status")
        async def health_slash(interaction: discord.Interaction):
            await user_commands.health_command(interaction, self.download_monitor)

        # Register admin commands
        @self.bot.tree.command(name="verbose", description="Toggle verbose logging (admin only)")
        async def verbose_slash(interaction: discord.Interaction):
            await admin_commands.verbose_command(interaction, self.download_monitor)

        @self.bot.tree.command(name="progress", description="Show progress tracking statistics (admin only)")
        async def progress_slash(interaction: discord.Interaction):
            await admin_commands.progress_command(interaction, self.download_monitor)

        @self.bot.tree.command(name="cleanup", description="Remove stuck and inactive downloads from queue (admin only)")
        async def cleanup_slash(interaction: discord.Interaction):
            await admin_commands.cleanup_command(interaction, self.download_monitor)
    
    async def run(self):
        """Run the Discord bot asynchronously."""
        try:
            await self.bot.start(self.settings.discord_token)
        finally:
            # Ensure background tasks are cleaned up
            if self.download_monitor:
                await self.download_monitor.stop()
                
    def start(self):
        """Start the Discord bot (blocking call)."""
        self.bot.run(self.settings.discord_token)
