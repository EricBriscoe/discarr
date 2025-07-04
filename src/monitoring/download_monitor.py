"""
Download monitor module for Discarr bot.
Handles monitoring and displaying download status from Radarr and Sonarr.
"""
import asyncio
import logging
import discord
from datetime import datetime

from discord_bot.ui.views import PaginationView
from discord_bot.ui.formatters import format_summary_message, format_loading_message, format_partial_loading_message
from monitoring.cache_manager import CacheManager
from clients.radarr import RadarrClient
from clients.sonarr import SonarrClient

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
        
        logger.info("DownloadMonitor initialized with real clients")
    
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
        
        # Start background data refresh
        self.cache_manager.start_background_refresh()
        
        # Start the monitoring task
        self._task = asyncio.create_task(self._monitor_loop())
        
        logger.info("DownloadMonitor started successfully")
    
    async def stop(self):
        """Stop the download monitor."""
        if not self._running:
            return
        
        self._running = False
        
        # Stop background refresh
        self.cache_manager.stop_background_refresh()
        
        # Cancel the monitoring task
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("DownloadMonitor stopped")
    
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
        """Check and update download status."""
        try:
            # Get current data from cache manager
            movie_downloads = self.cache_manager.get_movie_queue()
            tv_downloads = self.cache_manager.get_tv_queue()
            
            # Check if data is ready
            radarr_ready = self.cache_manager.is_radarr_ready()
            sonarr_ready = self.cache_manager.is_sonarr_ready()
            
            # Create appropriate embed based on data availability
            if radarr_ready and sonarr_ready:
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
                # No services ready - show loading message
                embed = format_loading_message()
            
            # Update or create the message
            await self._update_message(embed)
            
            # Update last update time
            self.last_update = datetime.now()
            
            logger.debug("Download status updated successfully")
            
        except Exception as e:
            logger.error(f"Error checking downloads: {e}", exc_info=True)
    
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
