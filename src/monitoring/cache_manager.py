"""
Cache manager for Discarr bot.
Handles background data fetching and caching of API results.
"""
import threading
import time
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from src.monitoring.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)

class CacheManager:
    """Manages background data fetching and caching for Radarr and Sonarr."""
    
    def __init__(self, radarr_client, sonarr_client):
        """Initialize the cache manager with Radarr and Sonarr clients."""
        self.radarr_client = radarr_client
        self.sonarr_client = sonarr_client
        self.movie_queue = []
        self.tv_queue = []
        self.movie_queue_lock = Lock()
        self.tv_queue_lock = Lock()
        self.last_refresh = 0
        self.refresh_interval = 5  # Seconds
        # Track loading state separately for each service
        self.radarr_loaded = False
        self.sonarr_loaded = False
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._stop_event = threading.Event()
        self._fetch_thread = None
        # Initialize progress tracker for stuck download detection
        self.progress_tracker = ProgressTracker()
    
    def start_background_refresh(self):
        """Start background thread for periodic data refresh."""
        if self._fetch_thread is None or not self._fetch_thread.is_alive():
            self._stop_event.clear()
            self._fetch_thread = threading.Thread(target=self._background_refresh_loop, daemon=True)
            self._fetch_thread.start()
            logger.info("Started background data refresh thread")
    
    def stop_background_refresh(self):
        """Stop the background refresh thread."""
        if self._fetch_thread and self._fetch_thread.is_alive():
            self._stop_event.set()
            self._fetch_thread.join(timeout=5)
            logger.info("Stopped background data refresh thread")
    
    def _background_refresh_loop(self):
        """Background thread function that periodically refreshes data."""
        while not self._stop_event.is_set():
            self.refresh_data()
            # Wait for the next refresh cycle or until stop is requested
            self._stop_event.wait(self.refresh_interval)
    
    def refresh_data(self):
        """Refresh data from Radarr and Sonarr using async clients."""
        current_time = time.time()
        if current_time - self.last_refresh < self.refresh_interval and self.radarr_loaded and self.sonarr_loaded:
            return
        
        try:
            # Run async refresh in a new event loop
            asyncio.run(self._async_refresh_data())
            self.last_refresh = current_time
            # Ensure we have valid lists before getting length
            movie_count = len(self.movie_queue) if isinstance(self.movie_queue, list) else 0
            tv_count = len(self.tv_queue) if isinstance(self.tv_queue, list) else 0
            logger.debug(f"Data refresh complete. Found {movie_count} movies and {tv_count} TV shows")
        except Exception as e:
            logger.error(f"Error in refresh_data: {e}", exc_info=True)
    
    async def _async_refresh_data(self):
        """Async method to refresh data from both services concurrently."""
        # Handle each service independently to avoid one failure affecting the other
        await self._refresh_radarr_data()
        await self._refresh_sonarr_data()
    
    async def _refresh_radarr_data(self):
        """Refresh Radarr data independently."""
        try:
            # Wrap the client call in executor with timeout to handle slow operations
            movie_queue = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, 
                    self.radarr_client.get_queue_items
                ),
                timeout=10.0
            )
            
            # If the result is a coroutine (shouldn't happen with executor), await it
            if asyncio.iscoroutine(movie_queue):
                movie_queue = await movie_queue
            
            # Process movie queue results
            if movie_queue is None:
                movie_queue = []
            
            if isinstance(movie_queue, list):
                with self.movie_queue_lock:
                    self.movie_queue = movie_queue
                # Record progress snapshots for Radarr items
                self.progress_tracker.record_progress_snapshot(movie_queue, 'radarr')
                # Get download updates asynchronously
                try:
                    update_result = self.radarr_client.get_download_updates()
                    if asyncio.iscoroutine(update_result):
                        await update_result
                except Exception as e:
                    logger.error(f"Error getting Radarr download updates: {e}")
                self.radarr_loaded = True
                logger.debug("Radarr data loaded successfully")
            else:
                logger.error(f"Invalid movie queue data type: {type(movie_queue)}")
                
        except Exception as e:
            logger.error(f"Error refreshing Radarr data: {e}")
            self.radarr_loaded = False
    
    async def _refresh_sonarr_data(self):
        """Refresh Sonarr data independently."""
        try:
            # Wrap the client call in executor with timeout to handle slow operations
            tv_queue = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, 
                    self.sonarr_client.get_queue_items
                ),
                timeout=10.0
            )
            
            # If the result is a coroutine (shouldn't happen with executor), await it
            if asyncio.iscoroutine(tv_queue):
                tv_queue = await tv_queue
            
            # Process TV queue results
            if tv_queue is None:
                tv_queue = []
                
            if isinstance(tv_queue, list):
                with self.tv_queue_lock:
                    self.tv_queue = tv_queue
                # Record progress snapshots for Sonarr items
                self.progress_tracker.record_progress_snapshot(tv_queue, 'sonarr')
                # Get download updates asynchronously
                try:
                    update_result = self.sonarr_client.get_download_updates()
                    if asyncio.iscoroutine(update_result):
                        await update_result
                except Exception as e:
                    logger.error(f"Error getting Sonarr download updates: {e}")
                self.sonarr_loaded = True
                logger.debug("Sonarr data loaded successfully")
            else:
                logger.error(f"Invalid TV queue data type: {type(tv_queue)}")
                
        except Exception as e:
            logger.error(f"Error refreshing Sonarr data: {e}")
            self.sonarr_loaded = False
    
    async def _wrap_sync_result(self, result):
        """Wrap a synchronous result in an async function for testing."""
        return result
    
    def get_movie_queue(self):
        """Thread-safe access to movie queue data."""
        with self.movie_queue_lock:
            return list(self.movie_queue)  # Return a copy to avoid race conditions
    
    def get_tv_queue(self):
        """Thread-safe access to TV queue data."""
        with self.tv_queue_lock:
            return list(self.tv_queue)  # Return a copy to avoid race conditions
    
    def is_data_ready(self):
        """Check if initial data from both services has been loaded."""
        return self.radarr_loaded and self.sonarr_loaded
    
    def is_radarr_ready(self):
        """Check if Radarr data has been loaded."""
        return self.radarr_loaded
    
    def is_sonarr_ready(self):
        """Check if Sonarr data has been loaded."""
        return self.sonarr_loaded
    
    def analyze_stuck_downloads(self):
        """Analyze progress history to identify stuck downloads.
        
        Returns:
            List of dictionaries containing stuck download information
        """
        return self.progress_tracker.analyze_stuck_downloads()
    
    def get_progress_statistics(self):
        """Get overall statistics about tracked downloads.
        
        Returns:
            Dictionary with tracking statistics
        """
        return self.progress_tracker.get_statistics()
    
    def get_download_progress_summary(self, download_id):
        """Get a summary of progress for a specific download.
        
        Args:
            download_id: Unique identifier for the download
            
        Returns:
            Dictionary with progress summary or None if not found
        """
        return self.progress_tracker.get_download_progress_summary(download_id)
