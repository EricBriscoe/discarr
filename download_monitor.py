"""
Download monitoring service for Discarr bot.
Handles checking download status and formatting updates.
"""
import asyncio
import logging
import discord
from discord.ext import tasks
from datetime import datetime, timezone
import config
from radarr import RadarrClient
from sonarr import SonarrClient
from health_checker import HealthChecker
from formatters import (
    format_summary_message, 
    format_loading_message, 
    format_partial_loading_message,
    format_health_status_message
)
from pagination import PaginationManager, BUTTON_CONTROLS
from cache_manager import CacheManager

logger = logging.getLogger(__name__)

class PaginationView(discord.ui.View):
    """View containing pagination buttons."""
    
    def __init__(self, download_monitor):
        """Initialize the pagination view.
        
        Args:
            download_monitor: Reference to the DownloadMonitor instance
        """
        super().__init__(timeout=None)  # Persistent view that doesn't time out
        self.download_monitor = download_monitor
        
        # Add buttons based on the BUTTON_CONTROLS configuration
        for button_config in BUTTON_CONTROLS:
            # Create the button with the specified properties
            btn = discord.ui.Button(
                custom_id=button_config["id"],
                emoji=button_config["emoji"],
                style=getattr(discord.ButtonStyle, button_config["style"].upper())
            )
            # Set the callback for when the button is pressed
            btn.callback = self.button_callback
            # Add the button to the view
            self.add_item(btn)
            
    async def button_callback(self, interaction):
        """Handle button press events."""
        # Get the custom_id of the pressed button
        button_id = interaction.data["custom_id"]
        
        # Update pagination state based on the button press
        if self.download_monitor.pagination.handle_button(button_id):
            # Acknowledge the interaction without sending a response
            await interaction.response.defer(ephemeral=True)
            
            # Update the display with the new pagination state
            await self.download_monitor.check_downloads()
        else:
            # No state change (likely at first/last page already)
            await interaction.response.defer(ephemeral=True)

class DownloadMonitor:
    """Monitors downloads from Radarr and Sonarr and updates Discord."""
    
    def __init__(self, bot, channel_id):
        """Initialize the download monitor.
        
        Args:
            bot: Discord bot instance
            channel_id: ID of the channel to post updates
        """
        self.bot = bot
        self.channel_id = channel_id
        self.summary_message_id = None
        self.health_message_id = None
        self.radarr_client = RadarrClient()
        self.sonarr_client = SonarrClient()
        self.pagination = PaginationManager()
        self.pagination_view = PaginationView(self)
        self.check_loop = None  # Initialize as None, will create later
        self.health_check_loop = None  # Initialize health check loop as None
        # Initialize the cache manager
        self.cache_manager = CacheManager(self.radarr_client, self.sonarr_client)
        # Initialize health checker
        self.health_checker = HealthChecker(config)
        # Track last update times
        self.last_data_update = datetime.now(timezone.utc)
        self.last_health_update = datetime.now(timezone.utc)
        
    async def start(self):
        """Start the download monitoring loop."""
        # First post the loading messages and start background data refresh
        await self.find_or_create_messages(show_loading=True)
        self.cache_manager.start_background_refresh()
        
        # Create the download check task loop
        self.check_loop = tasks.loop(
            seconds=config.CHECK_INTERVAL,
            reconnect=True
        )(self._check_downloads_wrapper)
        
        # Create the health check task loop
        self.health_check_loop = tasks.loop(
            seconds=config.HEALTH_CHECK_INTERVAL,
            reconnect=True
        )(self._check_health_wrapper)
        
        # Add before_loop function for download check
        @self.check_loop.before_loop
        async def before_check_downloads():
            await self.bot.wait_until_ready()
            logger.info("Bot is ready, starting check_downloads loop.")
        
        # Add before_loop function for health check
        @self.health_check_loop.before_loop
        async def before_check_health():
            await self.bot.wait_until_ready()
            logger.info("Bot is ready, starting health check loop.")
        
        # Start the loops
        self.check_loop.start()
        self.health_check_loop.start()
        
    async def stop(self):
        """Stop the monitoring loops."""
        if self.check_loop and self.check_loop.is_running():
            self.check_loop.cancel()
        if self.health_check_loop and self.health_check_loop.is_running():
            self.health_check_loop.cancel()
        self.cache_manager.stop_background_refresh()
    
    async def _check_downloads_wrapper(self):
        """Wrapper function for the downloads task loop."""
        await self.check_downloads()
    
    async def _check_health_wrapper(self):
        """Wrapper function for the health check task loop."""
        await self.check_health()
        
    async def check_downloads(self):
        """Periodically check downloads and update the summary message."""
        try:
            channel = self.bot.get_channel(self.channel_id)
            if not channel:
                logger.error(f"Cannot find channel {self.channel_id}")
                return

            # Update the last data update time
            self.last_data_update = datetime.now(timezone.utc)

            # Get cached queue items
            movie_queue = self.cache_manager.get_movie_queue()
            tv_queue = self.cache_manager.get_tv_queue()

            if config.VERBOSE:
                logger.debug(f"Found {len(movie_queue)} movies and {len(tv_queue)} TV shows in queue")

            # Create the embed based on loading status
            if not self.cache_manager.is_radarr_ready() and not self.cache_manager.is_sonarr_ready():
                # Both services are still loading
                summary_embed = format_loading_message()
            elif not self.cache_manager.is_data_ready():
                # One service is ready but the other is still loading
                radarr_ready = self.cache_manager.is_radarr_ready()
                sonarr_ready = self.cache_manager.is_sonarr_ready()
                summary_embed = format_partial_loading_message(
                    movie_queue if radarr_ready else [],
                    tv_queue if sonarr_ready else [],
                    self.pagination,
                    radarr_ready,
                    sonarr_ready,
                    self.last_data_update
                )
            else:
                # Both services are ready
                summary_embed = format_summary_message(
                    movie_queue, 
                    tv_queue, 
                    self.pagination,
                    self.last_data_update
                )
                
            await self.update_summary_message(channel, summary_embed)

        except Exception as e:
            logger.error(f"Error in check_downloads loop: {e}", exc_info=True)
    
    async def check_health(self):
        """Periodically check health of services and update the health message."""
        try:
            channel = self.bot.get_channel(self.channel_id)
            if not channel:
                logger.error(f"Cannot find channel {self.channel_id}")
                return
            
            # Update the last health update time
            self.last_health_update = datetime.now(timezone.utc)
            
            # Check health of all services
            health_status = self.health_checker.check_all_services()
            
            # Format the health status embed
            health_embed = format_health_status_message(health_status, self.last_health_update)
            
            # Update the health message
            await self.update_health_message(channel, health_embed)
            
        except Exception as e:
            logger.error(f"Error in check_health loop: {e}", exc_info=True)

    async def find_or_create_messages(self, show_loading=False):
        """Always delete existing messages and create new ones on startup."""
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            logger.error(f"Cannot find channel {self.channel_id}")
            return

        try:
            # Always delete all bot messages on startup
            logger.info("Deleting all existing bot messages on startup")
            await self.delete_all_bot_messages(channel)
            
            # Reset message IDs to ensure we create new ones
            self.summary_message_id = None
            self.health_message_id = None
            
            # Post initial loading messages if requested
            if show_loading:
                logger.info("Creating initial loading messages")
                
                # Create health status message first (appears at bottom)
                health_embed = format_health_status_message({})
                health_message = await channel.send(embed=health_embed)
                self.health_message_id = health_message.id
                
                # Create download summary message next (appears above health)
                summary_embed = format_loading_message()
                summary_message = await channel.send(embed=summary_embed, view=self.pagination_view)
                self.summary_message_id = summary_message.id
                
            else:
                logger.info("Will create new messages on first check")
            
        except discord.Forbidden:
            logger.error("Missing permissions to read channel history or delete messages.")
        except Exception as e:
            logger.error(f"Error during startup message cleanup: {e}")
        
    async def delete_all_bot_messages(self, channel):
        """Delete all messages sent by this bot in the channel."""
        try:
            deleted_count = 0
            async for message in channel.history(limit=100):
                if message.author == self.bot.user:
                    try:
                        await message.delete()
                        deleted_count += 1
                        await asyncio.sleep(0.5)  # Avoid rate limits
                    except (discord.Forbidden, discord.NotFound):
                        pass
                    except Exception as e:
                        logger.error(f"Failed to delete message {message.id}: {e}")
            
            if config.VERBOSE:
                logger.debug(f"Deleted {deleted_count} bot messages from channel")
                
        except discord.Forbidden:
            logger.error("Missing permissions to read or manage messages.")
        except Exception as e:
            logger.error(f"Error during message cleanup: {e}")

    async def cleanup_old_messages(self, channel, keep_message_ids=None):
        """Delete messages sent by the bot in the channel, except those to keep."""
        if keep_message_ids is None:
            keep_message_ids = []
            
        try:
            async for message in channel.history(limit=20):
                if message.author == self.bot.user and message.id not in keep_message_ids:
                    try:
                        await message.delete()
                        logger.info(f"Deleted old bot message: {message.id}")
                        await asyncio.sleep(1)  # Avoid rate limits
                    except (discord.Forbidden, discord.NotFound):
                        pass
                    except Exception as e:
                        logger.error(f"Failed to delete message {message.id}: {e}")
        except discord.Forbidden:
            logger.error("Missing permissions to manage messages.")
        except Exception as e:
            logger.error(f"Error during message cleanup: {e}")
            
    async def update_summary_message(self, channel, embed):
        """Update the summary message or create it if it doesn't exist."""
        try:
            # Check if we need new messages (e.g., another user posted)
            latest_messages = [message async for message in channel.history(limit=1)]
            if latest_messages and latest_messages[0].author != self.bot.user:
                await self.delete_all_bot_messages(channel)
                self.summary_message_id = None
                self.health_message_id = None
        except Exception as e:
            logger.error(f"Error checking latest message: {e}")
        
        # Update existing message if available
        if self.summary_message_id:
            try:
                message = await channel.fetch_message(self.summary_message_id)
                await message.edit(embed=embed, view=self.pagination_view)
                logger.info(f"Updated summary message: {self.summary_message_id}")
                return
            except discord.NotFound:
                logger.warning(f"Summary message {self.summary_message_id} not found.")
                self.summary_message_id = None
            except discord.Forbidden:
                logger.error("No permission to edit message.")
                return
            except Exception as e:
                logger.error(f"Failed to edit summary message: {e}")
                self.summary_message_id = None

        # Create a new message if needed
        if not self.summary_message_id:
            try:
                # Create health message first if it doesn't exist
                if not self.health_message_id:
                    health_embed = format_health_status_message({})
                    health_message = await channel.send(embed=health_embed)
                    self.health_message_id = health_message.id
                
                # Create summary message
                new_message = await channel.send(embed=embed, view=self.pagination_view)
                self.summary_message_id = new_message.id
                logger.info(f"Created new summary message: {self.summary_message_id}")
            except discord.Forbidden:
                logger.error("No permission to send messages in the channel.")
            except Exception as e:
                logger.error(f"Failed to send new summary message: {e}")
    
    async def update_health_message(self, channel, embed):
        """Update the health status message or create it if it doesn't exist."""
        # Update existing message if available
        if self.health_message_id:
            try:
                message = await channel.fetch_message(self.health_message_id)
                await message.edit(embed=embed)
                logger.info(f"Updated health message: {self.health_message_id}")
                return
            except discord.NotFound:
                logger.warning(f"Health message {self.health_message_id} not found.")
                self.health_message_id = None
            except discord.Forbidden:
                logger.error("No permission to edit message.")
                return
            except Exception as e:
                logger.error(f"Failed to edit health message: {e}")
                self.health_message_id = None

        # Create a new message if needed
        if not self.health_message_id:
            try:
                # Create health message
                new_message = await channel.send(embed=embed)
                self.health_message_id = new_message.id
                logger.info(f"Created new health message: {self.health_message_id}")
                
                # If summary message exists, make sure it appears above health message
                if self.summary_message_id:
                    try:
                        summary_message = await channel.fetch_message(self.summary_message_id)
                        summary_embed = summary_message.embeds[0] if summary_message.embeds else None
                        
                        # Re-send summary message to move it below health message
                        await summary_message.delete()
                        new_summary = await channel.send(embed=summary_embed, view=self.pagination_view)
                        self.summary_message_id = new_summary.id
                        
                    except Exception as e:
                        logger.error(f"Failed to reorder messages: {e}")
                
            except discord.Forbidden:
                logger.error("No permission to send messages in the channel.")
            except Exception as e:
                logger.error(f"Failed to send new health message: {e}")
                
    def handle_reaction(self, reaction_emoji):
        """Process a pagination reaction and update the state.
        
        Returns True if display should be updated.
        """
        return self.pagination.handle_reaction(reaction_emoji)
