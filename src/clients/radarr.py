"""
Radarr API client for movie download monitoring.
"""
import logging
from typing import Dict, List, Any
from .base import MediaClient
from utils.time_utils import format_discord_timestamp

logger = logging.getLogger(__name__)


class RadarrClient(MediaClient):
    """Client for interacting with Radarr API."""
    
    def __init__(self, base_url: str, api_key: str, verbose: bool = False):
        """Initialize Radarr client.
        
        Args:
            base_url: Radarr server URL
            api_key: Radarr API key
            verbose: Enable verbose logging
        """
        super().__init__(base_url, api_key, "Radarr", verbose)
        self.movie_cache = {}
        self.previous_status = {}

    def get_queue_params(self) -> Dict[str, Any]:
        """Return parameters for queue API call."""
        return {
            "pageSize": 1000,
            "page": 1,
            "sortKey": "timeleft",
            "sortDirection": "ascending",
            "includeMovie": True
        }
    
    def get_queue_items(self) -> List[Dict]:
        """Get all movies in the queue regardless of status."""
        queue_data = self._make_request('queue', params=self.get_queue_params())
        if not queue_data:
            return []
        
        items = []
        records = queue_data.get("records", [])
        
        if self.verbose:
            logger.debug(f"Processing {len(records)} items from Radarr queue")
        
        for item in records:
            try:
                processed_item = self._process_queue_item(item)
                if processed_item:
                    items.append(processed_item)
            except Exception as e:
                logger.error(f"Error processing Radarr queue item: {e}")
                continue
                
        return items
    
    def _process_queue_item(self, item: Dict) -> Dict:
        """Process a single queue item into standardized format."""
        # Get basic status information
        item_id = item.get("id", 0)
        status = item.get("status", "unknown")
        tracked_status = item.get("trackedDownloadState", status)
        
        # Extract media-specific information
        media_info = self.get_media_info(item)
        
        # Calculate progress
        progress = 0
        if "sizeleft" in item and "size" in item and item["size"] > 0:
            progress = 100 * (1 - item["sizeleft"] / item["size"])
        else:
            progress = item.get("progress", 0)
        
        size = item.get("size", 0) / (1024 * 1024 * 1024)  # Convert to GB
        
        # Parse time left - use estimatedCompletionTime as Discord relative timestamp if available
        time_left = "∞"
        if "estimatedCompletionTime" in item and item["estimatedCompletionTime"]:
            time_left = format_discord_timestamp(item["estimatedCompletionTime"])
        elif "timeleft" in item:
            time_str = item.get("timeleft", "")
            time_left = self.parse_time_left(time_str)
        
        if self.verbose:
            logger.debug(f"Queue item: {media_info['title']} ({tracked_status})")
        
        return {
            "id": item_id,
            "title": media_info["title"],
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
    
    def get_media_info(self, queue_item: Dict) -> Dict:
        """Extract movie specific information from the queue item."""
        movie_id = queue_item.get("movieId")
        movie_title = "Unknown Movie"
        
        if movie_id:
            movie_data = self.get_movie_by_id(movie_id)
            if movie_data:
                movie_title = movie_data.get("title", movie_title)
        else:
            movie_title = queue_item.get("title", movie_title)
        
        if self.verbose:
            logger.debug(f"Queue item: {movie_title} ({queue_item.get('trackedDownloadState', 'status not found')})")
        
        return {
            "title": movie_title
        }
    
    def get_movie_by_id(self, movie_id: int) -> Dict:
        """Get movie details by ID with caching."""
        if movie_id in self.movie_cache:
            return self.movie_cache[movie_id]
            
        movie_data = self._make_request(f'movie/{movie_id}')
        if movie_data:
            self.movie_cache[movie_id] = movie_data
            return movie_data
        
        return {}
    
    def get_download_updates(self) -> List[Dict]:
        """Get updates for downloads that need to be reported to Discord."""
        current_downloads = self.get_active_downloads()
        updates = []
        
        # Check for new downloads or progress updates
        for download in current_downloads:
            dl_id = download["id"]
            if dl_id not in self.previous_status or abs(self.previous_status[dl_id]["progress"] - download["progress"]) >= 10:
                updates.append({
                    "type": "movie",
                    "title": download["title"],
                    "progress": download["progress"],
                    "size": download["size"],
                    "time_left": download["time_left"],
                    "is_new": dl_id not in self.previous_status
                })
                self.previous_status[dl_id] = download
        
        # Check for completed downloads
        for dl_id in list(self.previous_status.keys()):
            if not any(d["id"] == dl_id for d in current_downloads):
                completed_download = self.previous_status[dl_id]
                updates.append({
                    "type": "movie",
                    "title": completed_download["title"],
                    "progress": 100,
                    "size": completed_download["size"],
                    "status": "completed"
                })
                if self.verbose:
                    logger.debug(f"Completed movie: {completed_download['title']}")
                del self.previous_status[dl_id]
            
        return updates
