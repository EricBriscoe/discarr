"""
Sonarr API client for TV show download monitoring.
"""
import logging
import asyncio
from typing import Dict, List, Any
from .base import MediaClient
from src.utils.time_utils import format_discord_timestamp

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
    
    async def get_queue_items(self) -> List[Dict]:
        """Get all episodes in the queue regardless of status using pagination."""
        # Progress callback for large libraries
        def progress_callback(loaded_items, total_items, current_page):
            if self.verbose:
                logger.info(f"Sonarr: Loaded {loaded_items}/{total_items} items (page {current_page})")
        
        # Get all records using pagination
        try:
            records = await asyncio.wait_for(
                self.get_all_queue_items_paginated(progress_callback),
                timeout=300.0  # 5 minute timeout for large libraries
            )
        except asyncio.TimeoutError:
            logger.error("Timeout loading Sonarr queue items - library may be too large")
            return []
        
        if not records:
            return []
        
        if self.verbose:
            logger.debug(f"Processing {len(records)} items from Sonarr queue")
        
        # Process items in batches to avoid overwhelming the system
        items = []
        batch_size = 50  # Process 50 items at a time
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            
            # Process batch concurrently with individual timeouts
            tasks = []
            for item in batch:
                task = asyncio.wait_for(
                    self._process_queue_item(item),
                    timeout=10.0  # 10 second timeout per item
                )
                tasks.append(task)
            
            # Execute batch processing
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, Exception):
                        logger.error(f"Error processing Sonarr queue item: {result}")
                        continue
                    if result:
                        items.append(result)
            except Exception as e:
                logger.error(f"Error processing Sonarr batch: {e}")
                continue
        
        logger.info(f"Successfully processed {len(items)} Sonarr queue items")
        return items
    
    async def _process_queue_item(self, item: Dict) -> Dict:
        """Process a single queue item into standardized format."""
        # Get basic status information
        item_id = item.get("id", 0)
        status = item.get("status", "unknown")
        tracked_status = item.get("trackedDownloadState", status)
        
        # Extract media-specific information
        media_info = await self.get_media_info(item)
        
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
    
    async def get_media_info(self, queue_item: Dict) -> Dict:
        """Extract TV series specific information from the queue item."""
        # Extract IDs for series and episode
        series_id = queue_item.get("seriesId")
        episode_id = queue_item.get("episodeId")
        
        # Default values
        series_title = "Unknown Series"
        episode_title = "Unknown Episode"
        season_number = queue_item.get("seasonNumber", 0)
        episode_number = 0
        
        # Fetch series and episode data concurrently
        tasks = []
        if series_id:
            tasks.append(self.get_series_by_id(series_id))
        else:
            tasks.append(asyncio.create_task(self._return_none()))
            
        if episode_id:
            tasks.append(self.get_episode_by_id(episode_id))
        else:
            tasks.append(asyncio.create_task(self._return_none()))
        
        # Execute both requests concurrently
        series_data, episode_data = await asyncio.gather(*tasks)
        
        # Process series data
        if series_data:
            series_title = series_data.get("title", series_title)
        
        # Process episode data
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
    
    async def _return_none(self) -> None:
        """Helper method to return None asynchronously."""
        return None
    
    async def get_series_by_id(self, series_id: int) -> Dict:
        """Get series details by ID with enhanced caching."""
        cache_key = self._get_cache_key("series", series_id)
        
        # Check cache first
        cached_item = self._get_cached_item(cache_key)
        if cached_item:
            return cached_item
        
        # Check legacy cache for backward compatibility
        if series_id in self.series_cache:
            series_data = self.series_cache[series_id]
            # Migrate to new cache
            self._cache_item(cache_key, series_data)
            return series_data
            
        series_data = await self._make_request(f'series/{series_id}')
        if series_data:
            # Cache in both old and new systems during transition
            self.series_cache[series_id] = series_data
            self._cache_item(cache_key, series_data)
            return series_data
        
        return {}
    
    async def get_episode_by_id(self, episode_id: int) -> Dict:
        """Get episode details by ID with enhanced caching."""
        cache_key = self._get_cache_key("episode", episode_id)
        
        # Check cache first
        cached_item = self._get_cached_item(cache_key)
        if cached_item:
            return cached_item
        
        # Check legacy cache for backward compatibility
        if episode_id in self.episode_cache:
            episode_data = self.episode_cache[episode_id]
            # Migrate to new cache
            self._cache_item(cache_key, episode_data)
            return episode_data
            
        episode_data = await self._make_request(f'episode/{episode_id}')
        if episode_data:
            # Cache in both old and new systems during transition
            self.episode_cache[episode_id] = episode_data
            self._cache_item(cache_key, episode_data)
            return episode_data
        
        return {}
    
    async def get_download_updates(self) -> List[Dict]:
        """Get updates for downloads that need to be reported to Discord."""
        current_downloads = await self.get_active_downloads()
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
