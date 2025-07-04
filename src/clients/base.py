"""
Base client class for media service APIs (Radarr, Sonarr, etc.).
Provides common functionality and interface for all media clients.
"""
import logging
import httpx
import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Set
from datetime import datetime, timedelta
from collections import defaultdict

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
        
        # Configure async client with connection pooling and optimization
        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=30.0
        )
        
        timeout = httpx.Timeout(
            connect=10.0,
            read=30.0,
            write=10.0,
            pool=5.0
        )
        
        # Try to enable HTTP/2 if h2 package is available
        try:
            import h2
            http2_enabled = True
        except ImportError:
            http2_enabled = False
        
        self.session = httpx.AsyncClient(
            limits=limits,
            timeout=timeout,
            http2=http2_enabled,  # Enable HTTP/2 only if h2 package is available
            headers={
                'X-Api-Key': self.api_key,
                'Content-Type': 'application/json',
                'Accept-Encoding': 'gzip, deflate'  # Enable compression
            }
        )
        
        # Enhanced caching with TTL
        self._cache = {}
        self._cache_timestamps = {}
        self._cache_ttl = 300  # 5 minutes TTL
        self._request_semaphore = asyncio.Semaphore(10)  # Limit concurrent requests
        self._pending_requests = {}  # Request deduplication
        
    async def _make_request(self, endpoint: str, method: str = 'GET', params: Optional[Dict] = None, 
                           data: Optional[Dict] = None) -> Optional[Dict]:
        """Make an async HTTP request to the API with request deduplication.
        
        Args:
            endpoint: API endpoint (without base URL)
            method: HTTP method
            params: Query parameters
            data: Request body data
            
        Returns:
            Response data as dictionary, or None if request failed
        """
        url = f"{self.base_url}/api/v3/{endpoint}"
        
        # Create request key for deduplication
        request_key = f"{method}:{url}:{str(params)}:{str(data)}"
        
        # Check if this request is already pending
        if request_key in self._pending_requests:
            if self.verbose:
                logger.debug(f"Deduplicating request to {url}")
            return await self._pending_requests[request_key]
        
        # Create the request coroutine
        request_coro = self._execute_request(url, method, params, data)
        self._pending_requests[request_key] = request_coro
        
        try:
            result = await request_coro
            return result
        finally:
            # Clean up pending request
            self._pending_requests.pop(request_key, None)
    
    async def _execute_request(self, url: str, method: str, params: Optional[Dict], 
                              data: Optional[Dict]) -> Optional[Dict]:
        """Execute the actual HTTP request with rate limiting."""
        async with self._request_semaphore:
            try:
                if self.verbose:
                    logger.debug(f"Making {method} request to {url}")
                    
                response = await self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data
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
    
    async def test_connection(self) -> bool:
        """Test connection to the API.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            response = await self._make_request('system/status')
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
    async def get_queue_items(self) -> List[Dict]:
        """Get queue items from the API.
        
        Returns:
            List of queue items
        """
        pass
    
    @abstractmethod
    async def get_media_info(self, queue_item: Dict) -> Dict:
        """Get media information for a queue item.
        
        Args:
            queue_item: Queue item from API
            
        Returns:
            Dictionary with media information
        """
        pass
    
    async def get_queue(self) -> List[Dict]:
        """Get formatted queue items.
        
        Returns:
            List of formatted queue items
        """
        try:
            queue_items = await self.get_queue_items()
            if not queue_items:
                return []
            
            formatted_items = []
            for item in queue_items:
                try:
                    media_info = await self.get_media_info(item)
                    if media_info:
                        formatted_items.append(media_info)
                except Exception as e:
                    logger.error(f"Error processing {self.service_name} queue item: {e}")
                    continue
            
            return formatted_items
            
        except Exception as e:
            logger.error(f"Error getting {self.service_name} queue: {e}")
            return []
    
    async def get_active_downloads(self) -> List[Dict]:
        """Get only active downloads from the queue.
        
        Returns:
            List of active download items
        """
        queue = await self.get_queue()
        return [item for item in queue if item.get('status', '').lower() in ['downloading', 'queued']]
    
    async def get_download_updates(self) -> List[Dict]:
        """Get download updates for progress tracking.
        
        Returns:
            List of download items with progress information
        """
        return await self.get_active_downloads()
    
    async def remove_inactive_items(self) -> int:
        """Remove inactive items from the queue.
        
        Returns:
            Number of items removed
        """
        try:
            queue_data = await self._make_request('queue', params=self.get_queue_params())
            if not queue_data or 'records' not in queue_data:
                return 0
            
            inactive_statuses = ['failed', 'completed', 'warning']
            removal_tasks = []
            
            for item in queue_data['records']:
                status = item.get('status', '').lower()
                if status in inactive_statuses:
                    item_id = item.get('id')
                    if item_id:
                        removal_tasks.append(self._remove_queue_item(item_id))
            
            # Execute removals concurrently
            results = await asyncio.gather(*removal_tasks, return_exceptions=True)
            removed_count = sum(1 for result in results if result is True)
            
            return removed_count
            
        except Exception as e:
            logger.error(f"Error removing inactive {self.service_name} items: {e}")
            return 0
    
    async def remove_stuck_downloads(self, stuck_download_ids: List[str]) -> int:
        """Remove stuck downloads from the queue.
        
        Args:
            stuck_download_ids: List of download IDs that are stuck
            
        Returns:
            Number of items removed
        """
        removal_tasks = [self._remove_queue_item(download_id) for download_id in stuck_download_ids]
        
        try:
            results = await asyncio.gather(*removal_tasks, return_exceptions=True)
            removed_count = sum(1 for result in results if result is True)
            return removed_count
        except Exception as e:
            logger.error(f"Error removing stuck {self.service_name} downloads: {e}")
            return 0
    
    async def remove_all_items(self) -> int:
        """Remove all items from the queue.
        
        Returns:
            Number of items removed
        """
        try:
            queue_data = await self._make_request('queue', params=self.get_queue_params())
            if not queue_data or 'records' not in queue_data:
                return 0
            
            removal_tasks = []
            for item in queue_data['records']:
                item_id = item.get('id')
                if item_id:
                    removal_tasks.append(self._remove_queue_item(item_id))
            
            # Execute all removals concurrently
            results = await asyncio.gather(*removal_tasks, return_exceptions=True)
            removed_count = sum(1 for result in results if result is True)
            
            return removed_count
            
        except Exception as e:
            logger.error(f"Error removing all {self.service_name} items: {e}")
            return 0
    
    async def _remove_queue_item(self, item_id: str) -> bool:
        """Remove a specific item from the queue.
        
        Args:
            item_id: ID of the item to remove
            
        Returns:
            True if removal was successful, False otherwise
        """
        try:
            response = await self._make_request(f'queue/{item_id}', method='DELETE')
            return response is not None
        except Exception as e:
            logger.error(f"Error removing {self.service_name} queue item {item_id}: {e}")
            return False
    
    def _get_cache_key(self, endpoint: str, item_id: int) -> str:
        """Generate cache key for an item."""
        return f"{self.service_name}:{endpoint}:{item_id}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached item is still valid based on TTL."""
        if cache_key not in self._cache_timestamps:
            return False
        
        timestamp = self._cache_timestamps[cache_key]
        return (datetime.now().timestamp() - timestamp) < self._cache_ttl
    
    def _cache_item(self, cache_key: str, item: Dict) -> None:
        """Cache an item with timestamp."""
        self._cache[cache_key] = item
        self._cache_timestamps[cache_key] = datetime.now().timestamp()
    
    def _get_cached_item(self, cache_key: str) -> Optional[Dict]:
        """Get item from cache if valid."""
        if self._is_cache_valid(cache_key):
            return self._cache.get(cache_key)
        else:
            # Clean up expired cache entry
            self._cache_timestamps.pop(cache_key, None)
            self._cache.pop(cache_key, None)
            return None
    
    def _cleanup_expired_cache(self) -> None:
        """Clean up expired cache entries to prevent memory leaks."""
        current_time = datetime.now().timestamp()
        expired_keys = []
        
        for cache_key, timestamp in self._cache_timestamps.items():
            if (current_time - timestamp) >= self._cache_ttl:
                expired_keys.append(cache_key)
        
        for key in expired_keys:
            self._cache_timestamps.pop(key, None)
            self._cache.pop(key, None)
    
    async def close(self):
        """Close the HTTP client session."""
        try:
            if hasattr(self, 'session') and self.session:
                await self.session.aclose()
                logger.debug(f"Closed HTTP session for {self.service_name}")
        except Exception as e:
            logger.error(f"Error closing HTTP session for {self.service_name}: {e}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
