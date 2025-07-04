"""
Admin commands for Discarr Discord bot.
Commands that require administrator permissions.
"""
import logging
import discord
import asyncio

logger = logging.getLogger(__name__)


class AdminCommands:
    """Handler for admin-level Discord commands."""
    
    def __init__(self, settings):
        """Initialize admin commands.
        
        Args:
            settings: Application settings instance
        """
        self.settings = settings
    
    async def verbose_command(self, interaction: discord.Interaction, download_monitor):
        """Handle the /verbose command to toggle verbose logging.
        
        Args:
            interaction: Discord interaction object
            download_monitor: DownloadMonitor instance
        """
        # Check if user has admin privileges
        if str(interaction.user.id) != str(interaction.guild.owner_id):
            await interaction.response.send_message(
                "Only the server owner can use this command.", 
                ephemeral=True
            )
            return

        # Defer the response immediately to avoid timeout
        await interaction.response.defer(ephemeral=True)

        # Toggle the global verbose setting
        self.settings.verbose = not self.settings.verbose
        new_level = logging.DEBUG if self.settings.verbose else logging.INFO
        status = "enabled" if self.settings.verbose else "disabled"

        # Update root logger level
        root_logger = logging.getLogger()
        root_logger.setLevel(new_level)

        # Update client instances if the monitor exists
        if download_monitor and download_monitor.cache_manager:
            if download_monitor.cache_manager.radarr_client:
                download_monitor.cache_manager.radarr_client.verbose = self.settings.verbose
                logger.debug(f"Updated RadarrClient verbose to {self.settings.verbose}")
            if download_monitor.cache_manager.sonarr_client:
                download_monitor.cache_manager.sonarr_client.verbose = self.settings.verbose
                logger.debug(f"Updated SonarrClient verbose to {self.settings.verbose}")

        logger.info(f"Verbose mode {status} by admin command")

        embed = discord.Embed(
            title="Verbose Mode Updated",
            description=f"Verbose mode has been {status}.",
            color=discord.Color.green()
        )

        # Send the confirmation via followup
        await interaction.followup.send(embed=embed, ephemeral=True)

    async def progress_command(self, interaction: discord.Interaction, download_monitor):
        """Handle the /progress command to show progress tracking statistics.
        
        Args:
            interaction: Discord interaction object
            download_monitor: DownloadMonitor instance
        """
        # Check if user has admin privileges
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "You need administrator permissions to use this command.", 
                ephemeral=True
            )
            return
            
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check if download monitor is available
            if not download_monitor:
                await interaction.followup.send(
                    "Download monitor is not initialized yet. Please try again later.", 
                    ephemeral=True
                )
                return
            
            # Get progress tracking statistics
            progress_stats = download_monitor.cache_manager.get_progress_statistics()
            stuck_downloads = download_monitor.cache_manager.analyze_stuck_downloads()
            
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
                      f"• **Threshold:** {self.settings.stuck_threshold_minutes} minutes\n"
                      f"• **Min progress change:** {self.settings.min_progress_change}%\n"
                      f"• **Min size change:** {self.settings.min_size_change / (1024*1024):.0f} MB",
                inline=False
            )
            
            # Add configuration details
            embed.add_field(
                name="⚙️ Configuration",
                value=f"• **History window:** {self.settings.progress_history_hours} hours\n"
                      f"• **Max snapshots/download:** {self.settings.max_snapshots_per_download}\n"
                      f"• **Refresh interval:** 5 seconds\n"
                      f"• **Check interval:** {self.settings.check_interval} seconds",
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

    async def cleanup_command(self, interaction: discord.Interaction, download_monitor):
        """Handle the /cleanup command to remove stuck and inactive downloads.
        
        Args:
            interaction: Discord interaction object
            download_monitor: DownloadMonitor instance
        """
        # Check if user has admin privileges
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "You need administrator permissions to use this command.", 
                ephemeral=True
            )
            return
            
        # Always acknowledge the interaction immediately to avoid timeout
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check if download monitor is available
            if not download_monitor:
                await interaction.followup.send(
                    "Download monitor is not initialized yet. Please try again later.", 
                    ephemeral=True
                )
                return
            
            # Analyze stuck downloads using progress tracking
            stuck_downloads = download_monitor.cache_manager.analyze_stuck_downloads()
            
            # Separate stuck downloads by service
            radarr_stuck_ids = [item['id'] for item in stuck_downloads if item['service'] == 'radarr']
            sonarr_stuck_ids = [item['id'] for item in stuck_downloads if item['service'] == 'sonarr']
            
            # Remove stuck downloads
            radarr_stuck_count = 0
            sonarr_stuck_count = 0
            if download_monitor.cache_manager.radarr_client:
                radarr_stuck_count = download_monitor.cache_manager.radarr_client.remove_stuck_downloads(radarr_stuck_ids)
            if download_monitor.cache_manager.sonarr_client:
                sonarr_stuck_count = download_monitor.cache_manager.sonarr_client.remove_stuck_downloads(sonarr_stuck_ids)
            
            # Also remove traditionally inactive items (failed, completed with errors, etc.)
            radarr_inactive_count = 0
            sonarr_inactive_count = 0
            if download_monitor.cache_manager.radarr_client:
                radarr_inactive_count = download_monitor.cache_manager.radarr_client.remove_inactive_items()
            if download_monitor.cache_manager.sonarr_client:
                sonarr_inactive_count = download_monitor.cache_manager.sonarr_client.remove_inactive_items()
            
            # Get progress tracking statistics
            progress_stats = download_monitor.cache_manager.get_progress_statistics()
            
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
            if download_monitor:
                # Use create_task to avoid blocking this interaction
                asyncio.create_task(download_monitor.check_downloads())
                
        except Exception as e:
            logger.error(f"Error in cleanup command: {e}", exc_info=True)
            await interaction.followup.send(f"An error occurred during cleanup: {str(e)}", ephemeral=True)
