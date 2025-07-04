"""
Base client class for media service APIs (Radarr, Sonarr, etc.).
Provides common functionality and interface for all media clients.
"""
import logging
import httpx
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MediaClientError(Exception):
    """Base exception for media client errors."""
    pass


class MediaClient(ABC):
    """Abstract base class for media service API clients."""
    
    def __init__(self, base_url: str, api_key: str, service_name: str, verbose: bool = False):
        """Initialize the media client.
        
        Args:
            base_url: Base URL of the media service
            api_key: API key for authentication
            service_name: Name of the service (for logging)
            verbose: Enable verbose logging
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.service_name = service_name
        self.verbose = verbose
        self.session = httpx.Client()
        self.session.headers.update({
            'X-Api-Key': self.api_key,
            'Content-Type': 'application/json'
        })
        
    def _make_request(self, endpoint: str, method: str = 'GET', params: Optional[Dict] = None, 
                     data: Optional[Dict] = None) -> Optional[Dict]:
        """Make an HTTP request to the API.
        
        Args:
            endpoint: API endpoint (without base URL)
            method: HTTP method
            params: Query parameters
            data: Request body data
            
        Returns:
            Response data as dictionary, or None if request failed
        """
        url = f"{self.base_url}/api/v3/{endpoint}"
        
        try:
            if self.verbose:
                logger.debug(f"Making {method} request to {url}")
                
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"{self.service_name} API returned status {response.status_code}: {response.text}")
                return None
                
        except httpx.RequestError as e:
            logger.error(f"Error connecting to {self.service_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error with {self.service_name} API: {e}")
            return None
    
    def test_connection(self) -> bool:
        """Test connection to the API.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            response = self._make_request('system/status')
            return response is not None
        except Exception as e:
            logger.error(f"Connection test failed for {self.service_name}: {e}")
            return False
    
    def parse_time_left(self, time_str: str) -> Optional[timedelta]:
        """Parse time left string into timedelta object.
        
        Args:
            time_str: Time string (e.g., "01:23:45")
            
        Returns:
            timedelta object or None if parsing fails
        """
        if not time_str:
            return None
            
        try:
            # Handle different time formats
            if ':' in time_str:
                parts = time_str.split(':')
                if len(parts) == 3:
                    hours, minutes, seconds = map(int, parts)
                    return timedelta(hours=hours, minutes=minutes, seconds=seconds)
                elif len(parts) == 2:
                    minutes, seconds = map(int, parts)
                    return timedelta(minutes=minutes, seconds=seconds)
            
            # Handle other formats as needed
            return None
            
        except (ValueError, TypeError) as e:
            if self.verbose:
                logger.debug(f"Could not parse time string '{time_str}': {e}")
            return None
    
    @abstractmethod
    def get_queue_params(self) -> Dict[str, Any]:
        """Get parameters for queue API request.
        
        Returns:
            Dictionary of parameters for the queue endpoint
        """
        pass
    
    @abstractmethod
    def get_queue_items(self) -> List[Dict]:
        """Get queue items from the API.
        
        Returns:
            List of queue items
        """
        pass
    
    @abstractmethod
    def get_media_info(self, queue_item: Dict) -> Dict:
        """Get media information for a queue item.
        
        Args:
            queue_item: Queue item from API
            
        Returns:
            Dictionary with media information
        """
        pass
    
    def get_queue(self) -> List[Dict]:
        """Get formatted queue items.
        
        Returns:
            List of formatted queue items
        """
        try:
            queue_items = self.get_queue_items()
            if not queue_items:
                return []
            
            formatted_items = []
            for item in queue_items:
                try:
                    media_info = self.get_media_info(item)
                    if media_info:
                        formatted_items.append(media_info)
                except Exception as e:
                    logger.error(f"Error processing {self.service_name} queue item: {e}")
                    continue
            
            return formatted_items
            
        except Exception as e:
            logger.error(f"Error getting {self.service_name} queue: {e}")
            return []
    
    def get_active_downloads(self) -> List[Dict]:
        """Get only active downloads from the queue.
        
        Returns:
            List of active download items
        """
        queue = self.get_queue()
        return [item for item in queue if item.get('status', '').lower() in ['downloading', 'queued']]
    
    def get_download_updates(self) -> List[Dict]:
        """Get download updates for progress tracking.
        
        Returns:
            List of download items with progress information
        """
        return self.get_active_downloads()
    
    def remove_inactive_items(self) -> int:
        """Remove inactive items from the queue.
        
        Returns:
            Number of items removed
        """
        try:
            queue_data = self._make_request('queue', params=self.get_queue_params())
            if not queue_data or 'records' not in queue_data:
                return 0
            
            inactive_statuses = ['failed', 'completed', 'warning']
            removed_count = 0
            
            for item in queue_data['records']:
                status = item.get('status', '').lower()
                if status in inactive_statuses:
                    item_id = item.get('id')
                    if item_id and self._remove_queue_item(item_id):
                        removed_count += 1
            
            return removed_count
            
        except Exception as e:
            logger.error(f"Error removing inactive {self.service_name} items: {e}")
            return 0
    
    def remove_stuck_downloads(self, stuck_download_ids: List[str]) -> int:
        """Remove stuck downloads from the queue.
        
        Args:
            stuck_download_ids: List of download IDs that are stuck
            
        Returns:
            Number of items removed
        """
        removed_count = 0
        
        for download_id in stuck_download_ids:
            try:
                if self._remove_queue_item(download_id):
                    removed_count += 1
            except Exception as e:
                logger.error(f"Error removing stuck {self.service_name} download {download_id}: {e}")
        
        return removed_count
    
    def remove_all_items(self) -> int:
        """Remove all items from the queue.
        
        Returns:
            Number of items removed
        """
        try:
            queue_data = self._make_request('queue', params=self.get_queue_params())
            if not queue_data or 'records' not in queue_data:
                return 0
            
            removed_count = 0
            for item in queue_data['records']:
                item_id = item.get('id')
                if item_id and self._remove_queue_item(item_id):
                    removed_count += 1
            
            return removed_count
            
        except Exception as e:
            logger.error(f"Error removing all {self.service_name} items: {e}")
            return 0
    
    def _remove_queue_item(self, item_id: str) -> bool:
        """Remove a specific item from the queue.
        
        Args:
            item_id: ID of the item to remove
            
        Returns:
            True if removal was successful, False otherwise
        """
        try:
            response = self._make_request(f'queue/{item_id}', method='DELETE')
            return response is not None
        except Exception as e:
            logger.error(f"Error removing {self.service_name} queue item {item_id}: {e}")
            return False
