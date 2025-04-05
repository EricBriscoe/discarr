"""
Utility functions for Discarr bot.
Provides helpers for time formatting, status display, and text handling.
"""
import logging
import re
import pytz
from datetime import datetime
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
