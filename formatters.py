"""
Message formatting utilities for Discarr bot.
Handles formatting movie and TV show information for Discord messages.
"""
import discord
import pytz
import logging
from datetime import datetime
from utils import get_status_emoji, truncate_title
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

def format_summary_message(movie_downloads, tv_downloads, pagination_manager):
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
    embed.set_footer(text=controls)
    
    # Add timestamp
    utc_now = discord.utils.utcnow()
    central_tz = pytz.timezone('America/Chicago')
    central_time = utc_now.replace(tzinfo=pytz.utc).astimezone(central_tz)
    embed.timestamp = utc_now
    
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
    utc_now = discord.utils.utcnow()
    embed.timestamp = utc_now
    
    return embed

def format_partial_loading_message(movie_downloads, tv_downloads, pagination_manager, radarr_ready, sonarr_ready):
    """Create a message for when one service is ready but the other is still loading.
    
    Args:
        movie_downloads: List of movie downloads from Radarr
        tv_downloads: List of TV downloads from Sonarr
        pagination_manager: The pagination manager instance
        radarr_ready: Boolean indicating if Radarr data is ready
        sonarr_ready: Boolean indicating if Sonarr data is ready
    
    Returns:
        A Discord embed with appropriate content
    """
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
    embed.set_footer(text=controls)
    
    # Add timestamp
    utc_now = discord.utils.utcnow()
    embed.timestamp = utc_now
    
    return embed
