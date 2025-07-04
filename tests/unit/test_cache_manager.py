"""
Unit tests for the CacheManager class.
"""
import pytest
import threading
import time
import os
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import Future, TimeoutError

# Set required environment variables for testing
os.environ['DISCORD_TOKEN'] = 'test_token'
os.environ['DISCORD_CHANNEL_ID'] = '123456789'

from src.monitoring.cache_manager import CacheManager


class TestCacheManager:
    """Test cases for CacheManager class."""
    
    @pytest.fixture
    def mock_radarr_client(self):
        """Create a mock Radarr client."""
        client = Mock()
        client.get_queue_items.return_value = [
            {'id': 1, 'title': 'Movie 1', 'progress': 50},
            {'id': 2, 'title': 'Movie 2', 'progress': 75}
        ]
        client.get_download_updates.return_value = None
        return client
    
    @pytest.fixture
    def mock_sonarr_client(self):
        """Create a mock Sonarr client."""
        client = Mock()
        client.get_queue_items.return_value = [
            {'id': 3, 'title': 'TV Show 1', 'progress': 25},
            {'id': 4, 'title': 'TV Show 2', 'progress': 90}
        ]
        client.get_download_updates.return_value = None
        return client
    
    @pytest.fixture
    def cache_manager(self, mock_radarr_client, mock_sonarr_client):
        """Create a CacheManager instance with mock clients."""
        with patch('src.monitoring.cache_manager.ProgressTracker'):
            return CacheManager(mock_radarr_client, mock_sonarr_client)
    
    def test_init(self, cache_manager, mock_radarr_client, mock_sonarr_client):
        """Test CacheManager initialization."""
        assert cache_manager.radarr_client == mock_radarr_client
        assert cache_manager.sonarr_client == mock_sonarr_client
        assert cache_manager.movie_queue == []
        assert cache_manager.tv_queue == []
        assert cache_manager.last_refresh == 0
        assert cache_manager.refresh_interval == 5
        assert cache_manager.radarr_loaded is False
        assert cache_manager.sonarr_loaded is False
        assert cache_manager._fetch_thread is None
        assert cache_manager.progress_tracker is not None
    
    def test_refresh_data_success(self, cache_manager, mock_radarr_client, mock_sonarr_client):
        """Test successful data refresh."""
        cache_manager.refresh_data()
        
        # Verify clients were called
        mock_radarr_client.get_queue_items.assert_called_once()
        mock_sonarr_client.get_queue_items.assert_called_once()
        mock_radarr_client.get_download_updates.assert_called_once()
        mock_sonarr_client.get_download_updates.assert_called_once()
        
        # Verify data was loaded
        assert cache_manager.radarr_loaded is True
        assert cache_manager.sonarr_loaded is True
        assert len(cache_manager.movie_queue) == 2
        assert len(cache_manager.tv_queue) == 2
        assert cache_manager.last_refresh > 0
    
    def test_refresh_data_radarr_error(self, cache_manager, mock_radarr_client, mock_sonarr_client):
        """Test data refresh with Radarr error."""
        mock_radarr_client.get_queue_items.side_effect = Exception("Radarr connection failed")
        
        cache_manager.refresh_data()
        
        # Verify Sonarr still succeeded
        assert cache_manager.radarr_loaded is False
        assert cache_manager.sonarr_loaded is True
        assert len(cache_manager.movie_queue) == 0
        assert len(cache_manager.tv_queue) == 2
    
    def test_refresh_data_sonarr_error(self, cache_manager, mock_radarr_client, mock_sonarr_client):
        """Test data refresh with Sonarr error."""
        mock_sonarr_client.get_queue_items.side_effect = Exception("Sonarr connection failed")
        
        cache_manager.refresh_data()
        
        # Verify Radarr still succeeded
        assert cache_manager.radarr_loaded is True
        assert cache_manager.sonarr_loaded is False
        assert len(cache_manager.movie_queue) == 2
        assert len(cache_manager.tv_queue) == 0
    
    def test_refresh_data_both_errors(self, cache_manager, mock_radarr_client, mock_sonarr_client):
        """Test data refresh with both services failing."""
        mock_radarr_client.get_queue_items.side_effect = Exception("Radarr failed")
        mock_sonarr_client.get_queue_items.side_effect = Exception("Sonarr failed")
        
        cache_manager.refresh_data()
        
        # Verify both failed
        assert cache_manager.radarr_loaded is False
        assert cache_manager.sonarr_loaded is False
        assert len(cache_manager.movie_queue) == 0
        assert len(cache_manager.tv_queue) == 0
    
    def test_refresh_data_skip_when_recent(self, cache_manager, mock_radarr_client, mock_sonarr_client):
        """Test that refresh is skipped when data is recent and both services loaded."""
        # First refresh
        cache_manager.refresh_data()
        initial_refresh_time = cache_manager.last_refresh
        
        # Reset mock call counts
        mock_radarr_client.reset_mock()
        mock_sonarr_client.reset_mock()
        
        # Second refresh immediately after
        cache_manager.refresh_data()
        
        # Verify no additional calls were made
        mock_radarr_client.get_queue_items.assert_not_called()
        mock_sonarr_client.get_queue_items.assert_not_called()
        assert cache_manager.last_refresh == initial_refresh_time
    
    def test_refresh_data_force_when_not_loaded(self, cache_manager, mock_radarr_client, mock_sonarr_client):
        """Test that refresh is forced when services are not loaded."""
        # Set recent refresh time but keep services not loaded
        cache_manager.last_refresh = time.time()
        cache_manager.radarr_loaded = False
        cache_manager.sonarr_loaded = False
        
        cache_manager.refresh_data()
        
        # Verify calls were made despite recent refresh
        mock_radarr_client.get_queue_items.assert_called_once()
        mock_sonarr_client.get_queue_items.assert_called_once()
    
    def test_get_movie_queue_thread_safe(self, cache_manager):
        """Test thread-safe access to movie queue."""
        # Set up test data
        test_data = [{'id': 1, 'title': 'Test Movie'}]
        cache_manager.movie_queue = test_data
        
        result = cache_manager.get_movie_queue()
        
        # Verify it returns a copy
        assert result == test_data
        assert result is not test_data
        
        # Modify the returned copy and verify original is unchanged
        result.append({'id': 2, 'title': 'Another Movie'})
        assert len(cache_manager.movie_queue) == 1
    
    def test_get_tv_queue_thread_safe(self, cache_manager):
        """Test thread-safe access to TV queue."""
        # Set up test data
        test_data = [{'id': 1, 'title': 'Test Show'}]
        cache_manager.tv_queue = test_data
        
        result = cache_manager.get_tv_queue()
        
        # Verify it returns a copy
        assert result == test_data
        assert result is not test_data
        
        # Modify the returned copy and verify original is unchanged
        result.append({'id': 2, 'title': 'Another Show'})
        assert len(cache_manager.tv_queue) == 1
    
    def test_is_data_ready(self, cache_manager):
        """Test data ready status checking."""
        # Initially not ready
        assert cache_manager.is_data_ready() is False
        
        # Only Radarr loaded
        cache_manager.radarr_loaded = True
        assert cache_manager.is_data_ready() is False
        
        # Only Sonarr loaded
        cache_manager.radarr_loaded = False
        cache_manager.sonarr_loaded = True
        assert cache_manager.is_data_ready() is False
        
        # Both loaded
        cache_manager.radarr_loaded = True
        cache_manager.sonarr_loaded = True
        assert cache_manager.is_data_ready() is True
    
    def test_is_radarr_ready(self, cache_manager):
        """Test Radarr ready status checking."""
        assert cache_manager.is_radarr_ready() is False
        
        cache_manager.radarr_loaded = True
        assert cache_manager.is_radarr_ready() is True
    
    def test_is_sonarr_ready(self, cache_manager):
        """Test Sonarr ready status checking."""
        assert cache_manager.is_sonarr_ready() is False
        
        cache_manager.sonarr_loaded = True
        assert cache_manager.is_sonarr_ready() is True
    
    def test_start_background_refresh(self, cache_manager):
        """Test starting background refresh thread."""
        assert cache_manager._fetch_thread is None
        
        cache_manager.start_background_refresh()
        
        assert cache_manager._fetch_thread is not None
        assert cache_manager._fetch_thread.is_alive()
        assert cache_manager._fetch_thread.daemon is True
        
        # Clean up
        cache_manager.stop_background_refresh()
    
    def test_start_background_refresh_already_running(self, cache_manager):
        """Test starting background refresh when already running."""
        cache_manager.start_background_refresh()
        first_thread = cache_manager._fetch_thread
        
        # Try to start again
        cache_manager.start_background_refresh()
        
        # Should be the same thread
        assert cache_manager._fetch_thread == first_thread
        
        # Clean up
        cache_manager.stop_background_refresh()
    
    def test_stop_background_refresh(self, cache_manager):
        """Test stopping background refresh thread."""
        cache_manager.start_background_refresh()
        assert cache_manager._fetch_thread.is_alive()
        
        cache_manager.stop_background_refresh()
        
        # Give it a moment to stop
        time.sleep(0.1)
        assert not cache_manager._fetch_thread.is_alive()
    
    def test_stop_background_refresh_not_running(self, cache_manager):
        """Test stopping background refresh when not running."""
        # Should not raise an exception
        cache_manager.stop_background_refresh()
        assert cache_manager._fetch_thread is None
    
    def test_background_refresh_loop(self, cache_manager):
        """Test the background refresh loop."""
        with patch.object(cache_manager, 'refresh_data_sync') as mock_refresh:
            # Set a very short refresh interval for testing
            cache_manager.refresh_interval = 0.1
            
            cache_manager.start_background_refresh()
            
            # Wait for a few refresh cycles
            time.sleep(0.3)
            
            cache_manager.stop_background_refresh()
            
            # Verify refresh_data_sync was called multiple times
            assert mock_refresh.call_count >= 2
    
    def test_progress_tracker_integration(self, cache_manager):
        """Test integration with progress tracker."""
        mock_progress_tracker = cache_manager.progress_tracker
        
        # Test analyze_stuck_downloads delegation
        mock_progress_tracker.analyze_stuck_downloads.return_value = ['stuck1', 'stuck2']
        result = cache_manager.analyze_stuck_downloads()
        assert result == ['stuck1', 'stuck2']
        mock_progress_tracker.analyze_stuck_downloads.assert_called_once()
        
        # Test get_progress_statistics delegation
        mock_progress_tracker.get_statistics.return_value = {'total': 10, 'stuck': 2}
        result = cache_manager.get_progress_statistics()
        assert result == {'total': 10, 'stuck': 2}
        mock_progress_tracker.get_statistics.assert_called_once()
        
        # Test get_download_progress_summary delegation
        mock_progress_tracker.get_download_progress_summary.return_value = {'id': 1, 'progress': 50}
        result = cache_manager.get_download_progress_summary('test_id')
        assert result == {'id': 1, 'progress': 50}
        mock_progress_tracker.get_download_progress_summary.assert_called_once_with('test_id')
    
    def test_concurrent_queue_access(self, cache_manager):
        """Test concurrent access to queues is thread-safe."""
        import threading
        
        def update_movie_queue():
            for i in range(10):
                with cache_manager.movie_queue_lock:
                    cache_manager.movie_queue.append({'id': i, 'title': f'Movie {i}'})
                time.sleep(0.001)
        
        def read_movie_queue():
            for i in range(10):
                queue = cache_manager.get_movie_queue()
                assert isinstance(queue, list)
                time.sleep(0.001)
        
        # Run concurrent threads
        threads = []
        for _ in range(3):
            threads.append(threading.Thread(target=update_movie_queue))
            threads.append(threading.Thread(target=read_movie_queue))
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify final state
        assert len(cache_manager.movie_queue) == 30  # 3 threads * 10 items each
    
    @patch('src.monitoring.cache_manager.logger')
    def test_logging(self, mock_logger, cache_manager, mock_radarr_client, mock_sonarr_client):
        """Test that appropriate logging occurs."""
        # Test successful refresh logging
        cache_manager.refresh_data()
        
        mock_logger.debug.assert_any_call("Radarr data loaded successfully")
        mock_logger.debug.assert_any_call("Sonarr data loaded successfully")
        mock_logger.debug.assert_any_call("Data refresh complete. Found 2 movies and 2 TV shows")
        
        # Test error logging - create a fresh cache manager to avoid state issues
        mock_radarr_client.reset_mock()
        mock_sonarr_client.reset_mock()
        mock_logger.reset_mock()
        
        # Reset the loaded flags to force refresh
        cache_manager.radarr_loaded = False
        cache_manager.sonarr_loaded = False
        cache_manager.last_refresh = 0
        
        mock_radarr_client.get_queue_items.side_effect = Exception("Test error")
        cache_manager.refresh_data()
        
        # Check that error was logged (the exact message format might vary)
        error_calls = [call for call in mock_logger.error.call_args_list if 'Test error' in str(call)]
        assert len(error_calls) > 0, f"Expected error log with 'Test error', got: {mock_logger.error.call_args_list}"
    
    def test_executor_timeout_handling(self, cache_manager, mock_radarr_client, mock_sonarr_client):
        """Test handling of executor timeouts."""
        # Mock a slow response that times out
        def slow_response():
            time.sleep(15)  # Longer than the 10-second timeout
            return []
        
        mock_radarr_client.get_queue_items.side_effect = slow_response
        
        # This should handle the timeout gracefully
        cache_manager.refresh_data()
        
        # Radarr should have failed due to timeout, but Sonarr should succeed
        assert cache_manager.radarr_loaded is False
        assert cache_manager.sonarr_loaded is True
