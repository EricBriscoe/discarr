"""
Utility functions for Discarr bot.
Provides helpers for time formatting, status display, and text handling.
"""
import logging
import re
import pytz
from datetime import datetime, timezone
import config

logger = logging.getLogger(__name__)

def calculate_time_remaining(item):
    """Calculate time remaining based on download progress over time."""
    try:
        # Check for required data
        if 'sizeleft' not in item or 'size' not in item or not item['size']:
            return "unknown"
            
        # Get the time when download was added
        added_str = item.get('added')
        if not added_str:
            return "unknown"
            
        # Convert string time to datetime object
        try:
            added_time = datetime.strptime(added_str, '%Y-%m-%dT%H:%M:%SZ')
            added_time = added_time.replace(tzinfo=pytz.UTC)
        except ValueError:
            return "unknown"
            
        # Calculate elapsed time
        now = datetime.now(pytz.UTC)
        elapsed_seconds = max((now - added_time).total_seconds(), 1)
        
        # Calculate bytes downloaded
        downloaded_bytes = item['size'] - item['sizeleft']
        
        if downloaded_bytes <= 0:
            return "unknown"
            
        # Calculate average download rate
        average_download_rate = downloaded_bytes / elapsed_seconds  # bytes per second
        
        # Calculate remaining time
        if average_download_rate > 0:
            remaining_seconds = item['sizeleft'] / average_download_rate
            
            if remaining_seconds < 60:
                return "< 1 min"
                
            hours, remainder = divmod(remaining_seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            if hours > 24:
                days = int(hours // 24)
                hours = int(hours % 24)
                return f"{days}d {hours}h"
            elif hours >= 1:
                return f"{int(hours)}h {int(minutes)}m"
            else:
                return f"{int(minutes)}m"
        else:
            return "unknown"
            
    except Exception as e:
        if config.VERBOSE:
            logger.debug(f"Error calculating time remaining: {e}")
        return "unknown"

def get_status_emoji(status):
    """Return an emoji representing the download status."""
    status = status.lower() if isinstance(status, str) else "unknown"
    
    emojis = {
        "downloading": "⬇️",
        "completed": "✅",
        "imported": "✅", 
        "importing": "📤",
        "importpending": "📁⏳",
        "importblocked": "📁🔒",
        "failed": "❌",
        "failedpending": "⚠️❌",
        "ignored": "🔕",
        "warning": "⚠️",
        "online": "🟢",
        "offline": "🔴",
        "error": "🟠",
        "disabled": "⚫",
        "unknown": "❓",
    }
    
    return emojis.get(status, "🔄")

def truncate_title(title, max_length=50):
    """Truncate long titles to a reasonable length."""
    if not title:
        return "Unknown"
    if len(title) <= max_length:
        return title
    
    # Try to truncate after a year (e.g., "Movie Name (2023)...")
    year_match = re.search(r'\b(19|20)\d{2}\b', title[:max_length+10])
    if year_match and year_match.end() <= max_length + 5:
        return title[:year_match.end()] + "..."
    
    return title[:max_length] + "..."

def format_relative_time(dt):
    """Format a datetime as a relative time string (e.g., '5 minutes ago').
    
    Args:
        dt: The datetime to format (must have timezone info)
        
    Returns:
        A string representing the relative time
    """
    if not dt:
        return "unknown"
    
    # Ensure dt has timezone info
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    now = datetime.now(timezone.utc)
    diff = now - dt
    
    # Calculate the time difference in various units
    total_seconds = int(diff.total_seconds())
    
    if total_seconds < 0:
        return "in the future"  # This shouldn't happen unless clocks are out of sync
    
    # Less than a minute
    if total_seconds < 60:
        return "just now"
    
    # Less than an hour
    if total_seconds < 3600:
        minutes = total_seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    
    # Less than a day
    if total_seconds < 86400:
        hours = total_seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    
    # Less than 30 days
    if total_seconds < 2592000:
        days = total_seconds // 86400
        return f"{days} day{'s' if days != 1 else ''} ago"
    
    # Less than a year
    if total_seconds < 31536000:
        months = total_seconds // 2592000
        return f"{months} month{'s' if months != 1 else ''} ago"
    
    # More than a year
    years = total_seconds // 31536000
    return f"{years} year{'s' if years != 1 else ''} ago"

def format_discord_timestamp(iso_time_str, format_code="R"):
    """Convert ISO timestamp to Discord's timestamp format that updates automatically.
    
    Args:
        iso_time_str: ISO formatted timestamp string (e.g. "2023-10-10T15:30:45Z")
        format_code: Discord's format code (R=relative, F=full date/time, etc.)
    
    Returns:
        Discord timestamp format string like <t:1234567890:R>
    """
    try:
        if not iso_time_str:
            return "∞"
            
        # Parse ISO timestamp to datetime
        dt = datetime.fromisoformat(iso_time_str.replace('Z', '+00:00'))
        
        # Convert to Unix timestamp (seconds since epoch)
        unix_timestamp = int(dt.timestamp())
        
        # Return Discord's timestamp format
        return f"<t:{unix_timestamp}:{format_code}>"
    except Exception as e:
        if config.VERBOSE:
            logger.debug(f"Error formatting Discord timestamp: {e}")
        return "∞"
