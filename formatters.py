"""
Message formatting utilities for Discarr bot.
Handles formatting movie and TV show information for Discord messages.
"""
import discord
import pytz
import logging
from datetime import datetime
from utils import get_status_emoji, truncate_title, format_relative_time
from pagination import FIRST_PAGE, PREV_PAGE, NEXT_PAGE, LAST_PAGE

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
        return "No movies in queue."
        
    start_idx, end_idx = pagination_manager.get_page_indices(is_movie=True)
    end_idx = min(end_idx, len(movie_downloads))
    
    content = ""
    for i in range(start_idx, end_idx):
        movie = movie_downloads[i]
        title = truncate_title(movie['title'])
        time_left = movie.get('time_left', 'unknown')
        display_status = movie.get('status', 'unknown')
        
        # Include error messages if present
        if movie.get('errorMessage') and movie.get('status', '').lower() == "warning":
            error_msg = movie['errorMessage'].split(': ')[-1].strip() if ': ' in movie['errorMessage'] else "warning"
            display_status = f"warning: {error_msg}"
        
        status_emoji = get_status_emoji(display_status)
        
        # Create the progress bar
        progress_bar = create_progress_bar(movie['progress'])
        
        # Format the movie entry
        content += f"{status_emoji} **{title}**\n"
        content += f"Status: `{display_status}` | Size: `{movie['size']:.2f} GB` | Time Left: `{time_left}`\n"
        content += f"{progress_bar}\n\n"
    
    return content

def format_tv_section(tv_downloads, pagination_manager):
    """Format the TV section of the embed."""
    # Get pagination information
    current_page, total_pages = pagination_manager.get_pagination_info(is_movie=False)
    
    if not tv_downloads:
        return "No TV shows in queue."
        
    start_idx, end_idx = pagination_manager.get_page_indices(is_movie=False)
    end_idx = min(end_idx, len(tv_downloads))
    
    content = ""
    for i in range(start_idx, end_idx):
        tv = tv_downloads[i]
        series = truncate_title(tv['series'], 40)
        time_left = tv.get('time_left', 'unknown')
        display_status = tv.get('status', 'unknown')
        
        # Include error messages if present
        if tv.get('errorMessage') and tv.get('status', '').lower() == "warning":
            error_msg = tv['errorMessage'].split(': ')[-1].strip() if ': ' in tv['errorMessage'] else "warning"
            display_status = f"warning: {error_msg}"
        
        status_emoji = get_status_emoji(display_status)
        
        # Create the progress bar
        progress_bar = create_progress_bar(tv['progress'])
        
        # Format the TV entry
        content += f"{status_emoji} **{series} S{tv['season']:02d}E{tv['episode_number']:02d}**\n"
        content += f"Status: `{display_status}` | Size: `{tv['size']:.2f} GB` | Time Left: `{time_left}`\n"
        content += f"{progress_bar}\n\n"
    
    return content

def format_summary_message(movie_downloads, tv_downloads, pagination_manager, last_updated=None):
    """Format the complete summary message as a Discord embed."""
    # Update pagination limits first
    pagination_manager.update_page_limits(len(movie_downloads), len(tv_downloads))
    
    # Create a new embed
    embed = discord.Embed(
        title="📊 Download Status",
        color=discord.Color.blue(),
        description="Current download status for movies and TV shows"
    )
    
    # Get pagination information
    movie_current_page, movie_total_pages = pagination_manager.get_pagination_info(is_movie=True)
    tv_current_page, tv_total_pages = pagination_manager.get_pagination_info(is_movie=False)
    
    # Add movie section with page indicator in the name
    movie_section = format_movie_section(movie_downloads, pagination_manager)
    embed.add_field(
        name=f"🎬 Movies (Page {movie_current_page}/{movie_total_pages})",
        value=movie_section,
        inline=False
    )
    
    # Add TV section with page indicator in the name
    tv_section = format_tv_section(tv_downloads, pagination_manager)
    embed.add_field(
        name=f"📺 TV Shows (Page {tv_current_page}/{tv_total_pages})",
        value=tv_section,
        inline=False
    )
    
    # Add navigation controls as footer
    controls = f"{FIRST_PAGE} First | {PREV_PAGE} Previous | {NEXT_PAGE} Next | {LAST_PAGE} Last"
    
    # Add relative time if provided
    if last_updated:
        relative_time = format_relative_time(last_updated)
        footer_text = f"{controls} • Last updated: {relative_time}"
    else:
        footer_text = controls
        
    embed.set_footer(text=footer_text)
    
    # Add timestamp (still needed for Discord's internal tracking)
    embed.timestamp = discord.utils.utcnow()
    
    # Return the embed object
    return embed

def format_loading_message():
    """Create a loading message embed."""
    embed = discord.Embed(
        title="📊 Download Status",
        color=discord.Color.blue(),
        description="Loading download information from Radarr and Sonarr..."
    )
    
    embed.add_field(
        name="🎬 Movies",
        value="Loading movie data...\n⏳ Please wait, this may take a moment for large libraries.",
        inline=False
    )
    
    embed.add_field(
        name="📺 TV Shows",
        value="Loading TV show data...\n⏳ Please wait, this may take a moment for large libraries.",
        inline=False
    )
    
    # Add navigation controls as footer
    controls = f"{FIRST_PAGE} First | {PREV_PAGE} Previous | {NEXT_PAGE} Next | {LAST_PAGE} Last"
    embed.set_footer(text=controls)
    
    # Add timestamp
    embed.timestamp = discord.utils.utcnow()
    
    return embed

def format_partial_loading_message(movie_downloads, tv_downloads, pagination_manager, radarr_ready, sonarr_ready, last_updated=None):
    """Create a message for when one service is ready but the other is still loading."""
    # Create a new embed
    embed = discord.Embed(
        title="📊 Download Status",
        color=discord.Color.blue(),
        description="Current download status for movies and TV shows"
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
        movie_section = format_movie_section(movie_downloads, pagination_manager)
        embed.add_field(
            name=f"🎬 Movies (Page {movie_current_page}/{movie_total_pages})",
            value=movie_section,
            inline=False
        )
    else:
        embed.add_field(
            name="🎬 Movies",
            value="Loading movie data...\n⏳ Please wait, this may take a moment for large libraries.",
            inline=False
        )
    
    # Add TV section
    if sonarr_ready:
        tv_section = format_tv_section(tv_downloads, pagination_manager)
        embed.add_field(
            name=f"📺 TV Shows (Page {tv_current_page}/{tv_total_pages})",
            value=tv_section,
            inline=False
        )
    else:
        embed.add_field(
            name="📺 TV Shows",
            value="Loading TV show data...\n⏳ Please wait, this may take a moment for large libraries.",
            inline=False
        )
    
    # Add navigation controls as footer
    controls = f"{FIRST_PAGE} First | {PREV_PAGE} Previous | {NEXT_PAGE} Next | {LAST_PAGE} Last"
    
    # Add relative time if provided
    if last_updated:
        relative_time = format_relative_time(last_updated)
        footer_text = f"{controls} • Last updated: {relative_time}"
    else:
        footer_text = controls
        
    embed.set_footer(text=footer_text)
    
    # Add timestamp
    embed.timestamp = discord.utils.utcnow()
    
    return embed

def format_health_status_message(health_status, last_updated=None):
    """Format the health status message as a Discord embed.
    
    Args:
        health_status: Dictionary containing health check results
        last_updated: Datetime when the health check was performed
        
    Returns:
        A Discord embed object containing the health status information
    """
    embed = discord.Embed(
        title="🏥 Service Health Status",
        color=discord.Color.green(),
        description="Current health status of media server services"
    )
    
    # Add Plex status field
    plex_status = health_status.get('plex', {'status': 'unknown'})
    plex_emoji = get_status_emoji(plex_status.get('status', 'unknown'))
    plex_content = f"{plex_emoji} **Status:** {plex_status.get('status', 'unknown')}\n"
    
    # Add additional info if service is online
    if plex_status.get('status') == 'online':
        plex_content += f"**Version:** {plex_status.get('version', 'unknown')}\n"
        plex_content += f"**Response Time:** {plex_status.get('response_time', 0)} ms\n"
    elif plex_status.get('status') == 'error' or plex_status.get('status') == 'offline':
        plex_content += f"**Error:** {plex_status.get('error', 'Unknown error')}\n"
    
    # Add last check time
    plex_check_time = plex_status.get('last_check')
    if plex_check_time:
        plex_content += f"**Last Check:** {format_relative_time(plex_check_time)}"
    
    embed.add_field(name="🎞️ Plex Media Server", value=plex_content, inline=False)
    
    # Add Radarr status field
    radarr_status = health_status.get('radarr', {'status': 'unknown'})
    radarr_emoji = get_status_emoji(radarr_status.get('status', 'unknown'))
    radarr_content = f"{radarr_emoji} **Status:** {radarr_status.get('status', 'unknown')}\n"
    
    # Add additional info if service is online
    if radarr_status.get('status') == 'online':
        radarr_content += f"**Version:** {radarr_status.get('version', 'unknown')}\n"
        radarr_content += f"**Response Time:** {radarr_status.get('response_time', 0)} ms\n"
    elif radarr_status.get('status') == 'error' or radarr_status.get('status') == 'offline':
        radarr_content += f"**Error:** {radarr_status.get('error', 'Unknown error')}\n"
    
    # Add last check time
    radarr_check_time = radarr_status.get('last_check')
    if radarr_check_time:
        radarr_content += f"**Last Check:** {format_relative_time(radarr_check_time)}"
    
    embed.add_field(name="🎬 Radarr", value=radarr_content, inline=True)
    
    # Add Sonarr status field
    sonarr_status = health_status.get('sonarr', {'status': 'unknown'})
    sonarr_emoji = get_status_emoji(sonarr_status.get('status', 'unknown'))
    sonarr_content = f"{sonarr_emoji} **Status:** {sonarr_status.get('status', 'unknown')}\n"
    
    # Add additional info if service is online
    if sonarr_status.get('status') == 'online':
        sonarr_content += f"**Version:** {sonarr_status.get('version', 'unknown')}\n"
        sonarr_content += f"**Response Time:** {sonarr_status.get('response_time', 0)} ms\n"
    elif sonarr_status.get('status') == 'error' or sonarr_status.get('status') == 'offline':
        sonarr_content += f"**Error:** {sonarr_status.get('error', 'Unknown error')}\n"
    
    # Add last check time
    sonarr_check_time = sonarr_status.get('last_check')
    if sonarr_check_time:
        sonarr_content += f"**Last Check:** {format_relative_time(sonarr_check_time)}"
    
    embed.add_field(name="📺 Sonarr", value=sonarr_content, inline=True)
    
    # Add overall status in footer with relative time
    if last_updated:
        relative_time = format_relative_time(last_updated)
        embed.set_footer(text=f"Last updated: {relative_time}")
    
    # Add timestamp for Discord's internal tracking
    embed.timestamp = discord.utils.utcnow()
    
    # Set color based on overall status
    if any(health_status.get(service, {}).get('status') == 'offline' for service in ['plex', 'radarr', 'sonarr']):
        embed.color = discord.Color.red()
    elif any(health_status.get(service, {}).get('status') in ['error', 'unknown'] for service in ['plex', 'radarr', 'sonarr']):
        embed.color = discord.Color.orange()
    
    return embed
