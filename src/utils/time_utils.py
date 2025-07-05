"""
Time-related utility functions for Discarr.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


def format_discord_timestamp(iso_time_str: str, format_code: str = "R") -> str:
    """Format an ISO timestamp for Discord relative time display.
    
    Args:
        iso_time_str: ISO format timestamp string
        format_code: Discord timestamp format code (R for relative)
        
    Returns:
        Formatted Discord timestamp string
    """
    try:
        # Parse the ISO timestamp
        dt = datetime.fromisoformat(iso_time_str.replace('Z', '+00:00'))
        # Convert to Unix timestamp
        timestamp = int(dt.timestamp())
        # Return Discord timestamp format
        return f"<t:{timestamp}:{format_code}>"
    except (ValueError, AttributeError) as e:
        logger.debug(f"Could not parse timestamp '{iso_time_str}': {e}")
        return iso_time_str


def calculate_time_remaining(item: dict) -> Optional[str]:
    """Calculate time remaining for a download item.
    
    Args:
        item: Download item dictionary
        
    Returns:
        Formatted time remaining string or None
    """
    try:
        # Check for estimated completion time first
        if "estimatedCompletionTime" in item and item["estimatedCompletionTime"]:
            return format_discord_timestamp(item["estimatedCompletionTime"])
        
        # Fall back to timeleft field
        if "timeleft" in item and item["timeleft"]:
            return item["timeleft"]
        
        # Calculate based on progress and speed if available
        if all(key in item for key in ["size", "sizeleft", "downloadRate"]) and item["downloadRate"] > 0:
            remaining_bytes = item["sizeleft"]
            download_rate = item["downloadRate"]  # bytes per second
            remaining_seconds = remaining_bytes / download_rate
            
            # Convert to timedelta for formatting
            td = timedelta(seconds=remaining_seconds)
            return format_timedelta(td)
        
        return None
        
    except (ValueError, TypeError, ZeroDivisionError) as e:
        logger.debug(f"Could not calculate time remaining: {e}")
        return None


def format_timedelta(td: timedelta) -> str:
    """Format a timedelta object into a human-readable string.
    
    Args:
        td: timedelta object
        
    Returns:
        Formatted time string (e.g., "2h 30m")
    """
    total_seconds = int(td.total_seconds())
    
    if total_seconds < 60:
        return f"{total_seconds}s"
    
    minutes = total_seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if hours < 24:
        if remaining_minutes > 0:
            return f"{hours}h {remaining_minutes}m"
        return f"{hours}h"
    
    days = hours // 24
    remaining_hours = hours % 24
    
    if remaining_hours > 0:
        return f"{days}d {remaining_hours}h"
    return f"{days}d"


def parse_time_string(time_str: str) -> Optional[timedelta]:
    """Parse various time string formats into timedelta.
    
    Args:
        time_str: Time string to parse
        
    Returns:
        timedelta object or None if parsing fails
    """
    if not time_str:
        return None
        
    try:
        # Handle HH:MM:SS format
        if ':' in time_str:
            parts = time_str.split(':')
            if len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                return timedelta(hours=hours, minutes=minutes, seconds=seconds)
            elif len(parts) == 2:
                minutes, seconds = map(int, parts)
                return timedelta(minutes=minutes, seconds=seconds)
        
        # Handle other formats as needed
        # Could add support for "2h 30m" style strings here
        
        return None
        
    except (ValueError, TypeError) as e:
        logger.debug(f"Could not parse time string '{time_str}': {e}")
        return None


def calculate_elapsed_time(last_update_time: Optional[datetime]) -> Optional[timedelta]:
    """Calculate elapsed time since last update.
    
    Args:
        last_update_time: Datetime when the last update occurred
        
    Returns:
        timedelta object representing elapsed time or None if no update time
    """
    if not last_update_time:
        return None
        
    try:
        return datetime.now() - last_update_time
    except (ValueError, TypeError) as e:
        logger.debug(f"Could not calculate elapsed time: {e}")
        return None


def format_elapsed_time(elapsed_time: Optional[timedelta]) -> str:
    """Format elapsed time into a Discord relative timestamp for the footer.
    
    Args:
        elapsed_time: timedelta object representing elapsed time
        
    Returns:
        Discord relative timestamp string (e.g., "Updated <t:1234567890:R>")
    """
    if not elapsed_time:
        return "Updated just now"
        
    try:
        # Calculate the timestamp when the update occurred
        update_time = datetime.now() - elapsed_time
        
        # Convert to Unix timestamp
        timestamp = int(update_time.timestamp())
        
        # Return Discord relative timestamp format
        return f"Updated <t:{timestamp}:R>"
        
    except (ValueError, TypeError) as e:
        logger.debug(f"Could not format elapsed time: {e}")
        return "Updated recently"
