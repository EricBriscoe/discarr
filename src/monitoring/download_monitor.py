"""
Download monitor module for Discarr bot.
Handles monitoring and displaying download status from Radarr and Sonarr.
"""
import asyncio
import logging
import time
import discord
from datetime import datetime

from src.discord_bot.ui.views import PaginationView
from src.discord_bot.ui.formatters import format_summary_message, format_loading_message, format_partial_loading_message, format_health_status_message, format_error_message
from src.monitoring.cache_manager import CacheManager
from src.monitoring.health_checker import HealthChecker
from src.clients.radarr import RadarrClient
from src.clients.sonarr import SonarrClient

logger = logging.getLogger(__name__)


class DownloadMonitor:
    """Monitors and displays download status from Radarr and Sonarr."""
    
    def __init__(self, bot, settings):
        """Initialize the download monitor.
        
        Args:
            bot: Discord bot instance
            settings: Application settings instance
        """
        self.bot = bot
        self.settings = settings
        self.channel = None
        self.message = None
        self.last_update = None
        self._running = False
        self._task = None
        self.loading_start_time = None
        self.last_error_state = {'radarr': None, 'sonarr': None}
        
        # Initialize clients
        self.radarr_client = RadarrClient(
            settings.radarr_url, 
            settings.radarr_api_key, 
            settings.verbose
        )
        self.sonarr_client = SonarrClient(
            settings.sonarr_url, 
            settings.sonarr_api_key, 
            settings.verbose
        )
        
        # Initialize cache manager
        self.cache_manager = CacheManager(self.radarr_client, self.sonarr_client)
        
        # Initialize pagination view
        self.pagination_view = PaginationView(download_monitor=self)
        
        # Initialize health checker
        self.health_checker = HealthChecker(settings)
        
        # Health monitoring state
        self.health_message = None
        self.last_health_update = None
        self._health_task = None
        
        logger.info("DownloadMonitor initialized with real clients and health checker")
    
    async def start(self):
        """Start the download monitor."""
        if self._running:
            logger.warning("DownloadMonitor is already running")
            return
        
        self._running = True
        
        # Get the Discord channel
        try:
            self.channel = self.bot.get_channel(self.settings.discord_channel_id)
            if not self.channel:
                logger.error(f"Could not find Discord channel with ID {self.settings.discord_channel_id}")
                return
        except Exception as e:
            logger.error(f"Error getting Discord channel: {e}")
            return
        
        # Clean up previous bot messages if enabled
        if self.settings.cleanup_previous_messages:
            await self._cleanup_previous_messages()
        
        # Start background data refresh
        self.cache_manager.start_background_refresh()
        
        # Create initial health status message first to ensure proper ordering
        await self._create_initial_health_message()
        
        # Start the monitoring task
        self._task = asyncio.create_task(self._monitor_loop())
        
        # Start the health monitoring task
        self._health_task = asyncio.create_task(self._health_monitor_loop())
        
        logger.info("DownloadMonitor started successfully")
    
    async def stop(self):
        """Stop the download monitor."""
        if not self._running:
            return
        
        self._running = False
        
        # Stop background refresh
        await self.cache_manager.stop_background_refresh()
        
        # Cancel the monitoring task
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        # Cancel the health monitoring task
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
        
        # Close HTTP client sessions
        try:
            await self.radarr_client.close()
            await self.sonarr_client.close()
            logger.debug("Closed HTTP client sessions")
        except Exception as e:
            logger.error(f"Error closing HTTP client sessions: {e}")
        
        logger.info("DownloadMonitor stopped")
    
    async def _create_initial_health_message(self):
        """Create the initial health status message to ensure proper ordering."""
        try:
            if not self.channel:
                logger.error("No channel available for initial health message creation")
                return
            
            # Update the last health update time
            self.last_health_update = datetime.now()
            
            # Check health of all services
            health_status = self.health_checker.check_all_services()
            
            # Format the health status embed
            health_embed = format_health_status_message(health_status, self.last_health_update)
            
            # Create the initial health message
            self.health_message = await self.channel.send(embed=health_embed)
            logger.info("Created initial health status message")
            
        except Exception as e:
            logger.error(f"Error creating initial health message: {e}", exc_info=True)
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        try:
            while self._running:
                await self.check_downloads()
                await asyncio.sleep(self.settings.check_interval)
        except asyncio.CancelledError:
            logger.info("Monitor loop cancelled")
        except Exception as e:
            logger.error(f"Error in monitor loop: {e}", exc_info=True)
    
    async def check_downloads(self):
        """Check and update download status with enhanced error handling."""
        try:
            # Get current data from cache manager
            movie_downloads = self.cache_manager.get_movie_queue()
            tv_downloads = self.cache_manager.get_tv_queue()
            
            # Check if data is ready
            radarr_ready = self.cache_manager.is_radarr_ready()
            sonarr_ready = self.cache_manager.is_sonarr_ready()
            
            # Track loading start time
            if not radarr_ready or not sonarr_ready:
                if self.loading_start_time is None:
                    self.loading_start_time = time.time()
            else:
                # Reset loading start time when both services are ready
                self.loading_start_time = None
            
            # Check for stuck loading (after 5 minutes, show error)
            if self.loading_start_time and (time.time() - self.loading_start_time) > 300:
                # Show error message for stuck loading
                radarr_error = None if radarr_ready else "Loading timeout - check server status and library size"
                sonarr_error = None if sonarr_ready else "Loading timeout - check server status and library size"
                
                embed = format_error_message(radarr_error, sonarr_error)
                logger.warning(f"Loading stuck for {time.time() - self.loading_start_time:.1f} seconds")
            elif radarr_ready and sonarr_ready:
                # Both services ready - show full data
                embed = format_summary_message(
                    movie_downloads, 
                    tv_downloads, 
                    self.pagination_view.pagination_manager,
                    self.last_update
                )
            elif radarr_ready or sonarr_ready:
                # One service ready - show partial data
                embed = format_partial_loading_message(
                    movie_downloads,
                    tv_downloads,
                    self.pagination_view.pagination_manager,
                    radarr_ready,
                    sonarr_ready,
                    self.last_update
                )
            else:
                # No services ready - show loading message with stuck detection
                embed = format_loading_message(self.loading_start_time)
            
            # Update or create the message
            await self._update_message(embed)
            
            # Update last update time
            self.last_update = datetime.now()
            
            logger.debug("Download status updated successfully")
            
        except Exception as e:
            logger.error(f"Error checking downloads: {e}", exc_info=True)
    
    async def _cleanup_previous_messages(self):
        """Clean up any previous messages sent by this bot in the channel."""
        if not self.channel:
            logger.warning("No channel available for message cleanup")
            return
            
        try:
            def is_bot_message(message):
                return message.author == self.bot.user
            
            # Use purge to efficiently delete bot messages
            deleted = await self.channel.purge(limit=100, check=is_bot_message)
            
            if deleted:
                logger.info(f"Cleaned up {len(deleted)} previous bot messages from channel")
            else:
                logger.debug("No previous bot messages found to clean up")
                
        except discord.Forbidden:
            logger.warning("Bot lacks permission to delete messages. Skipping cleanup.")
        except discord.HTTPException as e:
            logger.warning(f"HTTP error during message cleanup: {e}")
        except Exception as e:
            logger.warning(f"Could not clean up previous messages: {e}")
    
    async def _update_message(self, embed):
        """Update or create the Discord message with the embed.
        
        Args:
            embed: Discord embed to send
        """
        try:
            if not self.channel:
                logger.error("No channel available for message update")
                return
            
            # If we don't have a message yet, create one
            if not self.message:
                self.message = await self.channel.send(
                    embed=embed, 
                    view=self.pagination_view
                )
                logger.info("Created new download status message")
            else:
                # Try to edit the existing message
                try:
                    await self.message.edit(embed=embed, view=self.pagination_view)
                    logger.debug("Updated existing download status message")
                except discord.NotFound:
                    # Message was deleted, create a new one
                    logger.warning("Previous message was deleted, creating new one")
                    self.message = await self.channel.send(
                        embed=embed, 
                        view=self.pagination_view
                    )
                except discord.HTTPException as e:
                    logger.error(f"HTTP error updating message: {e}")
                    # Try to create a new message
                    self.message = await self.channel.send(
                        embed=embed, 
                        view=self.pagination_view
                    )
        
        except Exception as e:
            logger.error(f"Error updating Discord message: {e}", exc_info=True)
    
    def get_download_count(self):
        """Get the total number of downloads being monitored.
        
        Returns:
            Tuple of (movie_count, tv_count)
        """
        movie_count = len(self.cache_manager.get_movie_queue())
        tv_count = len(self.cache_manager.get_tv_queue())
        return movie_count, tv_count
    
    def is_ready(self):
        """Check if the download monitor is ready and has data.
        
        Returns:
            bool: True if both services have loaded data
        """
        return self.cache_manager.is_data_ready()
    
    async def _health_monitor_loop(self):
        """Health monitoring loop."""
        try:
            while self._running:
                await self.check_health()
                await asyncio.sleep(self.settings.health_check_interval)
        except asyncio.CancelledError:
            logger.info("Health monitor loop cancelled")
        except Exception as e:
            logger.error(f"Error in health monitor loop: {e}", exc_info=True)
    
    async def check_health(self):
        """Check and update health status of services."""
        try:
            if not self.channel:
                logger.error("No channel available for health update")
                return
            
            # Update the last health update time
            self.last_health_update = datetime.now()
            
            # Check health of all services
            health_status = self.health_checker.check_all_services()
            
            # Format the health status embed
            health_embed = format_health_status_message(health_status, self.last_health_update)
            
            # Update the health message
            await self._update_health_message(health_embed)
            
            logger.debug("Health status updated successfully")
            
        except Exception as e:
            logger.error(f"Error checking health: {e}", exc_info=True)
    
    async def _update_health_message(self, embed):
        """Update or create the health status message.
        
        Args:
            embed: Discord embed to send
        """
        try:
            if not self.channel:
                logger.error("No channel available for health message update")
                return
            
            # If we don't have a health message yet, create one
            if not self.health_message:
                self.health_message = await self.channel.send(embed=embed)
                logger.info("Created new health status message")
            else:
                # Try to edit the existing message
                try:
                    await self.health_message.edit(embed=embed)
                    logger.debug("Updated existing health status message")
                except discord.NotFound:
                    # Message was deleted, need to recreate and ensure proper ordering
                    logger.warning("Previous health message was deleted, recreating with proper ordering")
                    await self._recreate_health_message_with_ordering(embed)
                except discord.HTTPException as e:
                    logger.error(f"HTTP error updating health message: {e}")
                    # Try to recreate with proper ordering
                    await self._recreate_health_message_with_ordering(embed)
        
        except Exception as e:
            logger.error(f"Error updating health Discord message: {e}", exc_info=True)
    
    async def _recreate_health_message_with_ordering(self, embed):
        """Recreate the health message ensuring it appears before the download message.
        
        Args:
            embed: Discord embed to send
        """
        try:
            # If we have a download message, we need to recreate both messages in the correct order
            if self.message:
                # Store the current download message embed
                download_embed = None
                try:
                    # Get the current download message content
                    download_message = await self.channel.fetch_message(self.message.id)
                    if download_message.embeds:
                        download_embed = download_message.embeds[0]
                except (discord.NotFound, discord.HTTPException):
                    # Download message doesn't exist or can't be fetched
                    pass
                
                # Delete the old download message if it exists
                try:
                    await self.message.delete()
                    logger.debug("Deleted old download message for reordering")
                except (discord.NotFound, discord.HTTPException):
                    pass
                
                # Create health message first
                self.health_message = await self.channel.send(embed=embed)
                logger.info("Recreated health status message with proper ordering")
                
                # Recreate download message if we had one
                if download_embed:
                    self.message = await self.channel.send(
                        embed=download_embed, 
                        view=self.pagination_view
                    )
                    logger.info("Recreated download status message after health message")
                else:
                    # Reset message reference since we deleted it
                    self.message = None
            else:
                # No download message exists, just create the health message
                self.health_message = await self.channel.send(embed=embed)
                logger.info("Created new health status message")
                
        except Exception as e:
            logger.error(f"Error recreating health message with ordering: {e}", exc_info=True)
            # Fallback: just create a new health message
            try:
                self.health_message = await self.channel.send(embed=embed)
                logger.info("Created fallback health status message")
            except Exception as fallback_error:
                logger.error(f"Error creating fallback health message: {fallback_error}", exc_info=True)
