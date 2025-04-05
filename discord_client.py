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

logger = logging.getLogger(__name__)

class DiscordClient:
    """Discord client for Discarr bot."""
    
    def __init__(self):
        """Initialize the Discord client."""
        # Configure Discord intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.reactions = True
        
        # Create bot with command prefix and intents
        self.bot = commands.Bot(command_prefix='!', intents=intents)
        self.download_monitor = None
        
        # Set up event handlers
        self.setup_event_handlers()
        self.setup_commands()
        
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
            
            # Initialize and start the download monitor
            if not self.download_monitor:
                self.download_monitor = DownloadMonitor(self.bot, config.DISCORD_CHANNEL_ID)
                await self.download_monitor.start()
            else:
                logger.info("Download monitor already initialized")
            
        @self.bot.event
        async def on_reaction_add(reaction, user):
            """Handle pagination reactions."""
            if not self.download_monitor or user == self.bot.user:
                return
                
            if reaction.message.id != self.download_monitor.summary_message_id:
                return
                
            # Process the reaction
            if self.download_monitor.handle_reaction(reaction.emoji):
                # If state changed, update the display
                await self.download_monitor.check_downloads()
            
            # Remove the user's reaction
            try:
                await reaction.remove(user)
            except discord.Forbidden:
                logger.warning("Missing permissions to remove reactions.")
            except Exception as e:
                logger.error(f"Error removing reaction: {e}")
    
    def setup_commands(self):
        """Set up Discord bot slash commands."""
        @self.bot.tree.command(name="check", description="Manually refresh the download status")
        async def check_slash(interaction: discord.Interaction):
            """Slash command to manually refresh the download status."""
            if interaction.channel_id != config.DISCORD_CHANNEL_ID:
                await interaction.response.send_message("This command can only be used in the designated channel.", ephemeral=True)
                return

            await interaction.response.send_message("Manual check triggered...", ephemeral=True)
            if self.download_monitor:
                await self.download_monitor.check_downloads()

        @self.bot.tree.command(name="verbose", description="Toggle verbose logging (admin only)")
        async def verbose_slash(interaction: discord.Interaction):
            """Slash command to toggle verbose logging (admin only)."""
            if str(interaction.user.id) != str(interaction.guild.owner_id):
                await interaction.response.send_message("Only the server owner can use this command.", ephemeral=True)
                return
                
            config.VERBOSE = not config.VERBOSE
            
            root_logger = logging.getLogger()
            root_logger.setLevel(logging.DEBUG if config.VERBOSE else logging.INFO)
            
            status = "enabled" if config.VERBOSE else "disabled"
            logger.info(f"Verbose mode {status} by admin command")
            
            embed = discord.Embed(
                title="Verbose Mode Updated",
                description=f"Verbose mode {status}.",
                color=discord.Color.green()
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        @self.bot.tree.command(name="cleanup", description="Remove inactive downloads from queue (admin only)")
        async def cleanup_slash(interaction: discord.Interaction):
            """Slash command to remove inactive downloads from queue."""
            # Check if user has admin privileges
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("You need administrator permissions to use this command.", ephemeral=True)
                return
                
            await interaction.response.defer(ephemeral=True)
            
            # Remove inactive items from both Radarr and Sonarr
            radarr_count = self.download_monitor.radarr_client.remove_inactive_items()
            sonarr_count = self.download_monitor.sonarr_client.remove_inactive_items()
            
            # Create response embed
            embed = discord.Embed(
                title="Queue Cleanup Completed",
                description=f"Removed {radarr_count + sonarr_count} inactive items from download queues.",
                color=discord.Color.green()
            )
            
            embed.add_field(name="Radarr", value=f"{radarr_count} items removed", inline=True)
            embed.add_field(name="Sonarr", value=f"{sonarr_count} items removed", inline=True)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Refresh the queue display
            if self.download_monitor:
                await self.download_monitor.check_downloads()
    
    async def run(self):
        """Run the Discord bot."""
        await self.bot.start(config.DISCORD_TOKEN)
        
    def start(self):
        """Start the Discord bot (blocking call)."""
        self.bot.run(config.DISCORD_TOKEN)
