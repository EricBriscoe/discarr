"""
Download monitoring service for Discarr bot.
Handles checking download status and formatting updates.
"""
import asyncio
import logging
import discord
from discord.ext import tasks
import config
from radarr import RadarrClient
from sonarr import SonarrClient
from formatters import format_summary_message
from pagination import PaginationManager, REACTION_CONTROLS

logger = logging.getLogger(__name__)

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
        self.radarr_client = RadarrClient()
        self.sonarr_client = SonarrClient()
        self.pagination = PaginationManager()
        self.check_loop = None  # Initialize as None, will create later
        
    async def start(self):
        """Start the download monitoring loop."""
        await self.find_or_create_summary_message()
        
        # Create the task loop properly
        self.check_loop = tasks.loop(
            seconds=config.CHECK_INTERVAL,
            reconnect=True
        )(self._check_downloads_wrapper)
        
        # Add before_loop function
        @self.check_loop.before_loop
        async def before_check_downloads():
            await self.bot.wait_until_ready()
            logger.info("Bot is ready, starting check_downloads loop.")
            
        # Start the loop
        self.check_loop.start()
        
    async def stop(self):
        """Stop the download monitoring loop."""
        if self.check_loop and self.check_loop.is_running():
            self.check_loop.cancel()
    
    async def _check_downloads_wrapper(self):
        """Wrapper function for the task loop."""
        await self.check_downloads()
        
    async def check_downloads(self):
        """Periodically check downloads and update the summary message."""
        try:
            channel = self.bot.get_channel(self.channel_id)
            if not channel:
                logger.error(f"Cannot find channel {self.channel_id}")
                return

            # Get all queue items
            movie_queue = self.radarr_client.get_queue_items()
            tv_queue = self.sonarr_client.get_queue_items()

            if config.VERBOSE:
                logger.debug(f"Found {len(movie_queue)} movies and {len(tv_queue)} TV shows in queue")

            # Update internal state
            self.radarr_client.get_download_updates()
            self.sonarr_client.get_download_updates()

            # Create the embed
            summary_embed = format_summary_message(movie_queue, tv_queue, self.pagination)
            await self.update_summary_message(channel, summary_embed)

        except Exception as e:
            logger.error(f"Error in check_downloads loop: {e}", exc_info=True)

    async def find_or_create_summary_message(self):
        """Always delete existing messages and create a new one on startup."""
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            logger.error(f"Cannot find channel {self.channel_id}")
            return

        try:
            # Always delete all bot messages on startup
            logger.info("Deleting all existing bot messages on startup")
            await self.delete_all_bot_messages(channel)
            
            # Reset summary message ID to ensure we create a new one
            self.summary_message_id = None
            logger.info("Will create a new summary message on first check")
            
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

    async def cleanup_old_messages(self, channel, keep_message_id=None):
        """Delete messages sent by the bot in the channel, except the one to keep."""
        try:
            async for message in channel.history(limit=20):
                if message.author == self.bot.user and message.id != keep_message_id:
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
            
    async def add_pagination_controls(self, message):
        """Add reaction controls for pagination to the message."""
        for emoji in REACTION_CONTROLS:
            try:
                await message.add_reaction(emoji)
                await asyncio.sleep(0.5)  # Avoid rate limits
            except discord.Forbidden:
                logger.error("Missing permissions to add reactions.")
                return
            except Exception as e:
                logger.error(f"Error adding reaction {emoji}: {e}")

    async def update_summary_message(self, channel, embed):
        """Update the summary message or create it if it doesn't exist."""
        try:
            # Check if we need a new message (e.g., another user posted)
            latest_messages = [message async for message in channel.history(limit=1)]
            if latest_messages and latest_messages[0].author != self.bot.user:
                await self.delete_all_bot_messages(channel)
                self.summary_message_id = None
        except Exception as e:
            logger.error(f"Error checking latest message: {e}")
        
        # Update existing message if available
        if self.summary_message_id:
            try:
                message = await channel.fetch_message(self.summary_message_id)
                await message.edit(embed=embed)
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
                new_message = await channel.send(embed=embed)
                self.summary_message_id = new_message.id
                logger.info(f"Created new summary message: {self.summary_message_id}")
                await self.add_pagination_controls(new_message)
            except discord.Forbidden:
                logger.error("No permission to send messages in the channel.")
            except Exception as e:
                logger.error(f"Failed to send new summary message: {e}")
                
    def handle_reaction(self, reaction_emoji):
        """Process a pagination reaction and update the state.
        
        Returns True if display should be updated.
        """
        return self.pagination.handle_reaction(reaction_emoji)
