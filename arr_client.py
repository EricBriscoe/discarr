import requests
import logging
from abc import ABC, abstractmethod
from datetime import datetime

logger = logging.getLogger(__name__)

class ArrClient(ABC):
    def __init__(self, base_url, api_key, verbose):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            'X-Api-Key': self.api_key,
            'Content-Type': 'application/json'
        }
        self.previous_status = {}
        self.verbose = verbose
        
    def parse_time_left(self, time_str):
        """Parse time left string into a human-readable format"""
        if self.verbose:
            logger.debug(f"Parsing time string: '{time_str}'")
            
        if not time_str or time_str == "unknown":
            return "∞"
        
        try:
            # Handle time format with days (e.g. "49.14:36:30")
            if '.' in time_str:
                days_part, time_part = time_str.split('.', 1)
                days = int(days_part)
                
                # Parse the time part
                if time_part.count(':') == 2:  # HH:MM:SS
                    time_obj = datetime.strptime(time_part, "%H:%M:%S")
                    hours, minutes = time_obj.hour, time_obj.minute
                    return f"{days}d {hours}h {minutes}m"
                else:
                    return f"{days}d {time_part}"
            
            # Handle HH:MM:SS format
            elif time_str.count(':') == 2:
                time_obj = datetime.strptime(time_str, "%H:%M:%S")
                total_seconds = time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second
                
                if total_seconds < 60:
                    return "< 1 min"
                elif time_obj.hour == 0:
                    return f"{time_obj.minute}m"
                else:
                    return f"{time_obj.hour}h {time_obj.minute}m"
            
            # Handle MM:SS format
            elif time_str.count(':') == 1:
                time_obj = datetime.strptime(time_str, "%M:%S")
                total_seconds = time_obj.minute * 60 + time_obj.second
                
                if total_seconds < 60:
                    return "< 1 min"
                else:
                    return f"{time_obj.minute}m"
            
            # Try to interpret as seconds
            else:
                try:
                    seconds = int(time_str)
                    if seconds < 60:
                        return "< 1 min"
                    else:
                        minutes = seconds // 60
                        return f"{minutes}m"
                except ValueError:
                    return time_str
                
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse time format: '{time_str}' - {e}")
            return time_str
            
    def get_queue(self):
        """Get the current download queue"""
        try:
            url = f"{self.base_url}/api/v3/queue"
            params = self.get_queue_params()
            
            if self.verbose:
                logger.debug(f"Making request to queue API: {url}")
                
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()

            if self.verbose:
                logger.debug(f"Queue contains {len(data.get('records', []))} records")
                
            return data
        except requests.RequestException as e:
            logger.error(f"Error fetching queue: {e}")
            if self.verbose and hasattr(e, 'response') and e.response:
                logger.debug(f"Response: {e.response.status_code} - {e.response.text[:200]}...")
            return {"records": []}
    
    @abstractmethod
    def get_queue_params(self):
        """Return parameters for queue API call"""
        pass
    
    def get_queue_items(self):
        """Get all items in the queue regardless of status"""
        queue = self.get_queue()
        items = []
        
        if self.verbose:
            logger.debug(f"Processing {len(queue.get('records', []))} items from queue")
        
        for item in queue.get("records", []):
            # Get basic status information
            item_id = item.get("id", 0)
            status = item.get("status", "unknown")
            tracked_status = item.get("trackedDownloadState", status)
            
            # Get media specific information through the abstract method
            media_info = self.get_media_info(item)
            
            # Calculate progress
            progress = 0
            if "sizeleft" in item and "size" in item and item["size"] > 0:
                progress = 100 * (1 - item["sizeleft"] / item["size"])
            else:
                progress = item.get("progress", 0)
            
            # Convert to GB for display
            size = item.get("size", 0) / (1024 * 1024 * 1024)
            
            # Parse time left
            time_left = "unknown"
            if "timeleft" in item:
                time_left = self.parse_time_left(item.get("timeleft"))
                if self.verbose:
                    logger.debug(f"Parsed time left: '{time_left}'")
            
            # Build queue item with common fields
            queue_item = {
                "id": item_id,
                "progress": progress,
                "size": size,
                "sizeleft": item.get("sizeleft", 0),
                "time_left": time_left,
                "status": tracked_status or status,
                "protocol": item.get("protocol", "unknown"),
                "download_client": item.get("downloadClient", "unknown"),
                "errorMessage": item.get("errorMessage", ""),
                "added": item.get("added", ""),
            }
            
            # Add media specific fields
            queue_item.update(media_info)
            
            items.append(queue_item)
                
        return items
    
    @abstractmethod
    def get_media_info(self, queue_item):
        """Extract media specific information from the queue item"""
        pass
    
    def get_active_downloads(self):
        """Get the currently downloading items"""
        return [item for item in self.get_queue_items() if item["status"] == "downloading"]
    
    @abstractmethod
    def get_download_updates(self):
        """Get updates for downloads that need to be reported to Discord"""
        pass
    
    def remove_inactive_items(self):
        """Remove all non-downloading items from the queue"""
        queue_items = self.get_queue_items()
        inactive_ids = [item["id"] for item in queue_items if item["status"] != "downloading"]
        
        if not inactive_ids:
            return 0
        
        try:
            url = f"{self.base_url}/api/v3/queue/bulk"
            payload = {"ids": inactive_ids}
            params = {
                "removeFromClient": True,
                "blocklist": False,
                "skipRedownload": False,
                "changeCategory": False
            }
            
            if self.verbose:
                logger.debug(f"Removing {len(inactive_ids)} inactive items from queue")
                
            response = requests.delete(url, headers=self.headers, params=params, json=payload)
            response.raise_for_status()
            
            if self.verbose:
                logger.debug(f"Successfully removed {len(inactive_ids)} inactive items from queue")
                
            return len(inactive_ids)
        except requests.RequestException as e:
            logger.error(f"Error removing inactive items: {e}")
            if self.verbose and hasattr(e, 'response') and e.response:
                logger.debug(f"Response: {e.response.status_code} - {e.response.text[:200]}...")
            return 0
            
    def remove_all_items(self):
        """Remove all items from the queue regardless of status"""
        queue_items = self.get_queue_items()
        all_ids = [item["id"] for item in queue_items]
        
        if not all_ids:
            return 0
        
        try:
            url = f"{self.base_url}/api/v3/queue/bulk"
            payload = {"ids": all_ids}
            params = {
                "removeFromClient": True,
                "blocklist": False,
                "skipRedownload": False,
                "changeCategory": False
            }
            
            if self.verbose:
                logger.debug(f"Removing ALL {len(all_ids)} items from queue")
                
            response = requests.delete(url, headers=self.headers, params=params, json=payload)
            response.raise_for_status()
            
            if self.verbose:
                logger.debug(f"Successfully removed all {len(all_ids)} items from queue")
                
            return len(all_ids)
        except requests.RequestException as e:
            logger.error(f"Error removing all items: {e}")
            if self.verbose and hasattr(e, 'response') and e.response:
                logger.debug(f"Response: {e.response.status_code} - {e.response.text[:200]}...")
            return 0
