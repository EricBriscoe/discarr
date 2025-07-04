"""
Sonarr API client for TV show download monitoring.
"""
import logging
from typing import Dict, List, Any
from .base import MediaClient
from utils.time_utils import format_discord_timestamp

logger = logging.getLogger(__name__)


class SonarrClient(MediaClient):
    """Client for interacting with Sonarr API."""
    
    def __init__(self, base_url: str, api_key: str, verbose: bool = False):
        """Initialize Sonarr client.
        
        Args:
            base_url: Sonarr server URL
            api_key: Sonarr API key
            verbose: Enable verbose logging
        """
        super().__init__(base_url, api_key, "Sonarr", verbose)
        self.series_cache = {}
        self.episode_cache = {}
        self.previous_status = {}

    def get_queue_params(self) -> Dict[str, Any]:
        """Return parameters for queue API call."""
        return {
            "pageSize": 1000,
            "page": 1,
            "sortKey": "timeleft",
            "sortDirection": "ascending",
            "includeSeries": True,
            "includeEpisode": True
        }
    
    def get_queue_items(self) -> List[Dict]:
        """Get all episodes in the queue regardless of status."""
        queue_data = self._make_request('queue', params=self.get_queue_params())
        if not queue_data:
            return []
        
        items = []
        records = queue_data.get("records", [])
        
        if self.verbose:
            logger.debug(f"Processing {len(records)} items from Sonarr queue")
        
        for item in records:
            try:
                processed_item = self._process_queue_item(item)
                if processed_item:
                    items.append(processed_item)
            except Exception as e:
                logger.error(f"Error processing Sonarr queue item: {e}")
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
            logger.debug(f"Queue item: {media_info['series']} - S{media_info['season']:02d}E{media_info['episode_number']:02d} ({tracked_status})")
        
        return {
            "id": item_id,
            "series": media_info["series"],
            "episode": media_info["episode"],
            "season": media_info["season"],
            "episode_number": media_info["episode_number"],
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
        """Extract TV series specific information from the queue item."""
        # Extract IDs for series and episode
        series_id = queue_item.get("seriesId")
        episode_id = queue_item.get("episodeId")
        
        # Default values
        series_title = "Unknown Series"
        episode_title = "Unknown Episode"
        season_number = queue_item.get("seasonNumber", 0)
        episode_number = 0
        
        # Get series details
        if series_id:
            series_data = self.get_series_by_id(series_id)
            if series_data:
                series_title = series_data.get("title", series_title)
        
        # Get episode details
        if episode_id:
            episode_data = self.get_episode_by_id(episode_id)
            if episode_data:
                episode_title = episode_data.get("title", episode_title)
                if not season_number and "seasonNumber" in episode_data:
                    season_number = episode_data.get("seasonNumber", 0)
                episode_number = episode_data.get("episodeNumber", 0)
        
        if self.verbose:
            logger.debug(f"Queue item: {series_title} - S{season_number:02d}E{episode_number:02d} ({queue_item.get('trackedDownloadState', 'status not found')})")
        
        return {
            "series": series_title,
            "episode": episode_title,
            "season": season_number,
            "episode_number": episode_number
        }
    
    def get_series_by_id(self, series_id: int) -> Dict:
        """Get series details by ID with caching."""
        if series_id in self.series_cache:
            return self.series_cache[series_id]
            
        series_data = self._make_request(f'series/{series_id}')
        if series_data:
            self.series_cache[series_id] = series_data
            return series_data
        
        return {}
    
    def get_episode_by_id(self, episode_id: int) -> Dict:
        """Get episode details by ID with caching."""
        if episode_id in self.episode_cache:
            return self.episode_cache[episode_id]
            
        episode_data = self._make_request(f'episode/{episode_id}')
        if episode_data:
            self.episode_cache[episode_id] = episode_data
            return episode_data
        
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
                    "type": "tv",
                    "series": download["series"],
                    "episode": download["episode"],
                    "season": download["season"],
                    "episode_number": download["episode_number"],
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
                    "type": "tv",
                    "series": completed_download["series"],
                    "episode": completed_download["episode"],
                    "season": completed_download["season"],
                    "episode_number": completed_download["episode_number"],
                    "progress": 100,
                    "size": completed_download["size"],
                    "status": "completed"
                })
                
                if self.verbose:
                    logger.debug(f"Completed: {completed_download['series']} S{completed_download['season']:02d}E{completed_download['episode_number']:02d}")
                
                del self.previous_status[dl_id]
            
        return updates
