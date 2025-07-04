"""
Message formatting utilities for Discarr bot.
Handles formatting movie and TV show information for Discord messages.
"""
import logging
from datetime import datetime

import discord

from src.utils.discord_utils import get_status_emoji, truncate_title
from src.utils.time_utils import calculate_elapsed_time, format_elapsed_time

logger = logging.getLogger(__name__)

def create_progress_bar(progress, length=10):
    """Create a fancy emoji-based progress bar.
    
    Args:
        progress: Float between 0 and 100
        length: Length of the progress bar in emoji characters
        
    Returns:
        String containing a visually appealing progress bar
    """
    # Ensure progress is between 0 and 100
    progress = max(0, min(100, progress))
    
    # Calculate completed and remaining portions
    completed_length = int(length * progress / 100)
    remaining_length = length - completed_length
    
    # Choose characters based on progress (using block characters for better appearance in embeds)
    filled = "█"
    empty = "░"
    
    # Build progress bar
    bar = filled * completed_length + empty * remaining_length
    return f"`{bar}` {progress:.1f}%"

def format_movie_section(movie_downloads, pagination_manager):
    """Format the movie section of the embed."""
    # Get pagination information
    current_page, total_pages = pagination_manager.get_pagination_info(is_movie=True)
    
    if not movie_downloads:
        return [], "No movies in queue."
        
    start_idx, end_idx = pagination_manager.get_page_indices(is_movie=True)
    end_idx = min(end_idx, len(movie_downloads))
    
    embed_fields = []
    
    for i in range(start_idx, end_idx):
        movie = movie_downloads[i]
        logger.debug(f"Processing movie: {movie}")
        title = truncate_title(movie['title'])
        eta = movie.get('time_left', None)
        display_status = movie.get('status', 'unknown')
        
        # Include error messages if present
        if movie.get('errorMessage') and movie.get('status', '').lower() == "warning":
            error_msg = movie['errorMessage'].split(': ')[-1].strip() if ': ' in movie['errorMessage'] else "warning"
            display_status = f"warning: {error_msg}"
        
        status_emoji = get_status_emoji(display_status)
        
        # Create the progress bar
        progress_bar = create_progress_bar(movie['progress'])
        
        # Add title field with progress bar
        embed_fields.append({
            "name": f"{status_emoji} {title}",
            "value": f"Progress: {progress_bar}",
            "inline": False
        })
        
        # Add combined status and size field
        embed_fields.append({
            "name": "Status & Size",
            "value": f"**Status:** `{display_status}`\n**Size:** `{movie['size']:.2f} GB`",
            "inline": True
        })
        
        embed_fields.append({
            "name": "Estimated Completion",
            "value": eta,
            "inline": True
        })
        
    return embed_fields, None

def format_tv_section(tv_downloads, pagination_manager):
    """Format the TV section of the embed."""
    # Get pagination information
    current_page, total_pages = pagination_manager.get_pagination_info(is_movie=False)
    
    if not tv_downloads:
        return [], "No TV shows in queue."
        
    start_idx, end_idx = pagination_manager.get_page_indices(is_movie=False)
    end_idx = min(end_idx, len(tv_downloads))
    
    embed_fields = []
    
    for i in range(start_idx, end_idx):
        tv = tv_downloads[i]
        logger.debug(f"Processing TV show: {tv}")
        series = truncate_title(tv['series'], 40)
        eta = tv.get('time_left', None)
        display_status = tv.get('status', 'unknown')
        
        # Include error messages if present
        if tv.get('errorMessage') and tv.get('status', '').lower() == "warning":
            error_msg = tv['errorMessage'].split(': ')[-1].strip() if ': ' in tv['errorMessage'] else "warning"
            display_status = f"warning: {error_msg}"
        
        status_emoji = get_status_emoji(display_status)
        
        # Create the progress bar
        progress_bar = create_progress_bar(tv['progress'])
        
        # Add title field with progress bar
        embed_fields.append({
            "name": f"{status_emoji} {series} S{tv['season']:02d}E{tv['episode_number']:02d}",
            "value": f"Progress: {progress_bar}",
            "inline": False
        })
        
        # Add combined status and size field
        embed_fields.append({
            "name": "Status & Size",
            "value": f"**Status:** `{display_status}`\n**Size:** `{tv['size']:.2f} GB`",
            "inline": True
        })
        
        # Add time left in its own field for proper rendering
        embed_fields.append({
            "name": "Time Left",
            "value": eta,
            "inline": True
        })
        
    return embed_fields, None

def format_summary_message(movie_downloads, tv_downloads, pagination_manager, last_updated=None):
    """Format the complete summary message as a Discord embed."""
    # Update pagination limits first
    pagination_manager.update_page_limits(len(movie_downloads), len(tv_downloads))
    
    # Calculate elapsed time for the description
    elapsed_time = calculate_elapsed_time(last_updated)
    elapsed_text = format_elapsed_time(elapsed_time)
    
    # Create a new embed
    embed = discord.Embed(
        title="📊 Download Status",
        color=discord.Color.blue(),
        description=f"Current download status. Last updated: {elapsed_text}"
    )
    
    # Get pagination information
    movie_current_page, movie_total_pages = pagination_manager.get_pagination_info(is_movie=True)
    tv_current_page, tv_total_pages = pagination_manager.get_pagination_info(is_movie=False)
    
    # Add movie section with page indicator in the name
    movie_fields, movie_empty_message = format_movie_section(movie_downloads, pagination_manager)
    
    # Add movie header
    embed.add_field(
        name=f"🎬 Movies (Page {movie_current_page}/{movie_total_pages})",
        value=movie_empty_message if movie_empty_message else "\u200b",
        inline=False
    )
    
    # Add all movie fields if we have any
    if not movie_empty_message:
        for field in movie_fields:
            embed.add_field(name=field["name"], value=field["value"], inline=field["inline"])
    
    # Add TV section with page indicator in the name
    tv_fields, tv_empty_message = format_tv_section(tv_downloads, pagination_manager)
    
    # Add TV header
    embed.add_field(
        name=f"📺 TV Shows (Page {tv_current_page}/{tv_total_pages})",
        value=tv_empty_message if tv_empty_message else "\u200b",
        inline=False
    )
    
    # Add all TV fields if we have any
    if not tv_empty_message:
        for field in tv_fields:
            embed.add_field(name=field["name"], value=field["value"], inline=field["inline"])
    
    # Return the embed object
    return embed

def format_loading_message(loading_start_time=None):
    """Create a loading message embed with optional stuck detection."""
    embed = discord.Embed(
        title="📊 Download Status",
        color=discord.Color.blue(),
        description="Loading download information from Radarr and Sonarr..."
    )
    
    # Check if loading has been stuck for too long
    stuck_warning = ""
    if loading_start_time:
        import time
        elapsed_time = time.time() - loading_start_time
        if elapsed_time > 120:  # 2 minutes
            stuck_warning = "\n⚠️ **Loading is taking longer than expected. This may indicate:**\n" \
                          "• Very large library (>1000 items)\n" \
                          "• API connectivity issues\n" \
                          "• Server performance problems"
            embed.color = discord.Color.orange()
    
    embed.add_field(
        name="🎬 Movies",
        value=f"Loading movie data...\n⏳ Please wait, this may take a moment for large libraries.{stuck_warning}",
        inline=False
    )
    
    embed.add_field(
        name="📺 TV Shows",
        value="Loading TV show data...\n⏳ Please wait, this may take a moment for large libraries.",
        inline=False
    )
    
    # Add timestamp
    embed.timestamp = discord.utils.utcnow()
    
    return embed

def format_error_message(radarr_error=None, sonarr_error=None):
    """Create an error message embed when loading fails."""
    embed = discord.Embed(
        title="📊 Download Status",
        color=discord.Color.red(),
        description="❌ **Error loading download information**"
    )
    
    if radarr_error:
        embed.add_field(
            name="🎬 Movies (Radarr)",
            value=f"❌ **Error:** {radarr_error}\n\n**Possible solutions:**\n"
                  "• Check Radarr server status\n"
                  "• Verify API key and URL\n"
                  "• Check network connectivity",
            inline=False
        )
    else:
        embed.add_field(
            name="🎬 Movies (Radarr)",
            value="✅ **Status:** Connected",
            inline=False
        )
    
    if sonarr_error:
        embed.add_field(
            name="📺 TV Shows (Sonarr)",
            value=f"❌ **Error:** {sonarr_error}\n\n**Possible solutions:**\n"
                  "• Check Sonarr server status\n"
                  "• Verify API key and URL\n"
                  "• Check network connectivity",
            inline=False
        )
    else:
        embed.add_field(
            name="📺 TV Shows (Sonarr)",
            value="✅ **Status:** Connected",
            inline=False
        )
    
    embed.add_field(
        name="🔧 Troubleshooting",
        value="• Check the health status message above\n"
              "• Verify your .env configuration\n"
              "• Check server logs for detailed errors\n"
              "• Try restarting the bot if issues persist",
        inline=False
    )
    
    # Add timestamp
    embed.timestamp = discord.utils.utcnow()
    
    return embed

def format_partial_loading_message(movie_downloads, tv_downloads, pagination_manager, radarr_ready, sonarr_ready, last_updated=None):
    """Create a message for when one service is ready but the other is still loading."""
    # Calculate elapsed time for the description
    elapsed_time = calculate_elapsed_time(last_updated)
    elapsed_text = format_elapsed_time(elapsed_time)

    # Create a new embed
    embed = discord.Embed(
        title="📊 Download Status",
        color=discord.Color.blue(),
        description=f"Current download status. Last updated: {elapsed_text}"
    )
    
    # Update pagination limits for the service that's ready
    if radarr_ready:
        pagination_manager.update_movie_page_limit(len(movie_downloads))
    if sonarr_ready:
        pagination_manager.update_tv_page_limit(len(tv_downloads))
    
    # Get pagination information
    movie_current_page, movie_total_pages = pagination_manager.get_pagination_info(is_movie=True)
    tv_current_page, tv_total_pages = pagination_manager.get_pagination_info(is_movie=False)
    
    # Add movie section
    if radarr_ready:
        movie_fields, movie_empty_message = format_movie_section(movie_downloads, pagination_manager)
        
        # Add movie header
        embed.add_field(
            name=f"🎬 Movies (Page {movie_current_page}/{movie_total_pages})",
            value=movie_empty_message if movie_empty_message else "\u200b",
            inline=False
        )
        
        # Add all movie fields if we have any
        if not movie_empty_message:
            for field in movie_fields:
                embed.add_field(name=field["name"], value=field["value"], inline=field["inline"])
    else:
        embed.add_field(
            name="🎬 Movies",
            value="Loading movie data...\n⏳ Please wait, this may take a moment for large libraries.",
            inline=False
        )
    
    # Add TV section
    if sonarr_ready:
        tv_fields, tv_empty_message = format_tv_section(tv_downloads, pagination_manager)
        
        # Add TV header
        embed.add_field(
            name=f"📺 TV Shows (Page {tv_current_page}/{tv_total_pages})",
            value=tv_empty_message if tv_empty_message else "\u200b",
            inline=False
        )
        
        # Add all TV fields if we have any
        if not tv_empty_message:
            for field in tv_fields:
                embed.add_field(name=field["name"], value=field["value"], inline=field["inline"])
    else:
        embed.add_field(
            name="📺 TV Shows",
            value="Loading TV show data...\n⏳ Please wait, this may take a moment for large libraries.",
            inline=False
        )
    
    return embed

def format_health_status_message(health_status, last_updated=None):
    """Format the health status message as a Discord embed.
    
    Args:
        health_status: Dictionary containing health check results
        last_updated: Datetime when the health check was performed
        
    Returns:
        A Discord embed object containing the health status information
    """
    # Calculate elapsed time for the description
    elapsed_time = calculate_elapsed_time(last_updated)
    elapsed_text = format_elapsed_time(elapsed_time)

    embed = discord.Embed(
        title="🏥 Service Health Status",
        color=discord.Color.green(),
        description=f"Current health status of media server services. Last updated: {elapsed_text}"
    )
    
    # Add Plex status field - without individual timestamp
    plex_status = health_status.get('plex', {'status': 'unknown'})
    plex_emoji = get_status_emoji(plex_status.get('status', 'unknown'))
    plex_content = f"{plex_emoji} **Status:** {plex_status.get('status', 'unknown')}"
    
    embed.add_field(name="🎞️ Plex Media Server", value=plex_content, inline=False)
    
    # Add Radarr status field - without individual timestamp
    radarr_status = health_status.get('radarr', {'status': 'unknown'})
    radarr_emoji = get_status_emoji(radarr_status.get('status', 'unknown'))
    radarr_content = f"{radarr_emoji} **Status:** {radarr_status.get('status', 'unknown')}"
    
    embed.add_field(name="🎬 Radarr", value=radarr_content, inline=False)
    
    # Add Sonarr status field - without individual timestamp
    sonarr_status = health_status.get('sonarr', {'status': 'unknown'})
    sonarr_emoji = get_status_emoji(sonarr_status.get('status', 'unknown'))
    sonarr_content = f"{sonarr_emoji} **Status:** {sonarr_status.get('status', 'unknown')}"
    
    embed.add_field(name="📺 Sonarr", value=sonarr_content, inline=False)
    
    # Add timestamp for Discord's internal tracking (Discord will automatically show "Last updated X minutes ago")
    embed.timestamp = discord.utils.utcnow()
    
    # Set color based on overall status
    if any(health_status.get(service, {}).get('status') == 'offline' for service in ['plex', 'radarr', 'sonarr']):
        embed.color = discord.Color.red()
    elif any(health_status.get(service, {}).get('status') in ['error', 'unknown'] for service in ['plex', 'radarr', 'sonarr']):
        embed.color = discord.Color.orange()
    
    return embed
