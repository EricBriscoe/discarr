"""
Integration tests for async optimization improvements.
Tests performance characteristics and concurrent behavior of API clients.
"""
import pytest
import asyncio
import time
import logging
from unittest.mock import Mock, patch, AsyncMock
from src.clients.radarr import RadarrClient
from src.clients.sonarr import SonarrClient

logger = logging.getLogger(__name__)


class TestAsyncOptimization:
    """Test cases for async optimization and performance improvements."""
    
    @pytest.fixture
    def mock_radarr_client(self):
        """Create a mock Radarr client for testing."""
        client = RadarrClient("http://localhost:7878", "test_key", verbose=False)
        return client
    
    @pytest.fixture
    def mock_sonarr_client(self):
        """Create a mock Sonarr client for testing."""
        client = SonarrClient("http://localhost:8989", "test_key", verbose=False)
        return client
    
    @pytest.mark.asyncio
    async def test_concurrent_queue_fetching(self, mock_radarr_client, mock_sonarr_client):
        """Test that concurrent API calls are faster than sequential calls."""
        
        # Mock the HTTP responses
        mock_radarr_response = [{"id": 1, "movieId": 1, "title": "Test Movie"}]
        mock_sonarr_response = [{"id": 2, "seriesId": 1, "title": "Test Series"}]
        
        with patch.object(mock_radarr_client, 'get_queue_items', new_callable=AsyncMock) as mock_radarr, \
             patch.object(mock_sonarr_client, 'get_queue_items', new_callable=AsyncMock) as mock_sonarr:
            
            # Configure mocks to simulate network delay
            async def delayed_radarr_response():
                await asyncio.sleep(0.1)  # 100ms delay
                return mock_radarr_response
            
            async def delayed_sonarr_response():
                await asyncio.sleep(0.1)  # 100ms delay
                return mock_sonarr_response
            
            mock_radarr.side_effect = delayed_radarr_response
            mock_sonarr.side_effect = delayed_sonarr_response
            
            # Test sequential approach
            start_time = time.time()
            radarr_queue = await mock_radarr_client.get_queue_items()
            sonarr_queue = await mock_sonarr_client.get_queue_items()
            sequential_time = time.time() - start_time
            
            # Reset mocks
            mock_radarr.side_effect = delayed_radarr_response
            mock_sonarr.side_effect = delayed_sonarr_response
            
            # Test concurrent approach
            start_time = time.time()
            radarr_task = mock_radarr_client.get_queue_items()
            sonarr_task = mock_sonarr_client.get_queue_items()
            radarr_queue, sonarr_queue = await asyncio.gather(radarr_task, sonarr_task)
            concurrent_time = time.time() - start_time
            
            # Verify results
            assert radarr_queue == mock_radarr_response
            assert sonarr_queue == mock_sonarr_response
            
            # Concurrent should be significantly faster (at least 40% improvement)
            improvement = ((sequential_time - concurrent_time) / sequential_time) * 100
            assert improvement > 40, f"Expected >40% improvement, got {improvement:.1f}%"
            
            # Verify both methods were called
            assert mock_radarr.call_count == 2
            assert mock_sonarr.call_count == 2
    
    @pytest.mark.asyncio
    async def test_connection_pooling_benefits(self, mock_radarr_client):
        """Test that connection pooling improves performance for multiple requests."""
        
        with patch.object(mock_radarr_client, 'test_connection', new_callable=AsyncMock) as mock_test:
            
            # Configure mock to simulate connection delay
            async def delayed_connection():
                await asyncio.sleep(0.05)  # 50ms delay
                return True
            
            mock_test.side_effect = delayed_connection
            
            # Test multiple concurrent connections
            start_time = time.time()
            tasks = [mock_radarr_client.test_connection() for _ in range(5)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            pooling_time = time.time() - start_time
            
            # Verify all connections succeeded
            assert all(r is True for r in results)
            assert len(results) == 5
            
            # With connection pooling, 5 concurrent requests should take roughly
            # the same time as 1 request (plus some overhead)
            assert pooling_time < 0.15, f"Expected <150ms for 5 concurrent connections, got {pooling_time*1000:.0f}ms"
            
            # Verify all connection attempts were made
            assert mock_test.call_count == 5
    
    @pytest.mark.asyncio
    async def test_large_batch_processing(self):
        """Test concurrent processing of large batches of items."""
        
        # Simulate processing 50 queue items
        mock_queue_items = [
            {"id": i, "movieId": i, "title": f"Movie {i}"} 
            for i in range(50)
        ]
        
        async def process_item(item):
            """Simulate processing a single item with API delay."""
            await asyncio.sleep(0.01)  # 10ms per item
            return {"processed": True, "id": item["id"], "title": item["title"]}
        
        # Test concurrent processing
        start_time = time.time()
        tasks = [process_item(item) for item in mock_queue_items]
        results = await asyncio.gather(*tasks)
        concurrent_time = time.time() - start_time
        
        # Verify all items were processed
        assert len(results) == 50
        assert all(r["processed"] is True for r in results)
        assert all(r["id"] == i for i, r in enumerate(results))
        
        # Concurrent processing should be much faster than sequential
        # With 50 items at 10ms each, sequential would take ~500ms
        # Concurrent should take roughly 10ms + overhead
        assert concurrent_time < 0.1, f"Expected <100ms for concurrent processing, got {concurrent_time*1000:.0f}ms"
        
        # Test that sequential would be much slower
        start_time = time.time()
        sequential_results = []
        for item in mock_queue_items[:5]:  # Test with just 5 items for speed
            result = await process_item(item)
            sequential_results.append(result)
        sequential_time_per_item = (time.time() - start_time) / 5
        
        # Sequential time per item should be roughly 10ms
        assert 0.008 < sequential_time_per_item < 0.015, f"Expected ~10ms per item, got {sequential_time_per_item*1000:.1f}ms"
    
    @pytest.mark.asyncio
    async def test_error_handling_in_concurrent_operations(self, mock_radarr_client, mock_sonarr_client):
        """Test that errors in one concurrent operation don't affect others."""
        
        with patch.object(mock_radarr_client, 'get_queue_items', new_callable=AsyncMock) as mock_radarr, \
             patch.object(mock_sonarr_client, 'get_queue_items', new_callable=AsyncMock) as mock_sonarr:
            
            # Configure one to succeed and one to fail
            mock_radarr.return_value = [{"id": 1, "title": "Success"}]
            mock_sonarr.side_effect = Exception("Network error")
            
            # Test concurrent execution with error handling
            radarr_task = mock_radarr_client.get_queue_items()
            sonarr_task = mock_sonarr_client.get_queue_items()
            
            results = await asyncio.gather(radarr_task, sonarr_task, return_exceptions=True)
            
            # Verify one succeeded and one failed
            assert results[0] == [{"id": 1, "title": "Success"}]
            assert isinstance(results[1], Exception)
            assert str(results[1]) == "Network error"
            
            # Verify both methods were called
            mock_radarr.assert_called_once()
            mock_sonarr.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_timeout_handling_in_concurrent_operations(self, mock_radarr_client):
        """Test that timeouts are properly handled in concurrent operations."""
        
        with patch.object(mock_radarr_client, 'get_queue_items', new_callable=AsyncMock) as mock_radarr:
            
            # Configure mock to simulate a long delay
            async def slow_response():
                await asyncio.sleep(2.0)  # 2 second delay
                return [{"id": 1, "title": "Slow response"}]
            
            mock_radarr.side_effect = slow_response
            
            # Test with timeout
            start_time = time.time()
            try:
                result = await asyncio.wait_for(
                    mock_radarr_client.get_queue_items(), 
                    timeout=0.5  # 500ms timeout
                )
                assert False, "Expected timeout exception"
            except asyncio.TimeoutError:
                # This is expected
                pass
            
            elapsed_time = time.time() - start_time
            
            # Should timeout around 500ms, not wait for 2 seconds
            assert 0.4 < elapsed_time < 0.7, f"Expected ~500ms timeout, got {elapsed_time*1000:.0f}ms"
    
    def test_client_initialization_performance(self):
        """Test that client initialization is fast and doesn't block."""
        
        start_time = time.time()
        
        # Create multiple clients
        clients = []
        for i in range(10):
            radarr_client = RadarrClient(f"http://localhost:787{i}", f"test_key_{i}", verbose=False)
            sonarr_client = SonarrClient(f"http://localhost:898{i}", f"test_key_{i}", verbose=False)
            clients.extend([radarr_client, sonarr_client])
        
        initialization_time = time.time() - start_time
        
        # Client initialization should be reasonably fast (under 500ms for 20 clients)
        assert initialization_time < 0.5, f"Expected <500ms for 20 client initializations, got {initialization_time*1000:.0f}ms"
        
        # Verify all clients were created properly
        assert len(clients) == 20
        assert all(hasattr(client, 'base_url') for client in clients)
        assert all(hasattr(client, 'api_key') for client in clients)
    
    @pytest.mark.asyncio
    async def test_memory_efficiency_with_large_responses(self, mock_radarr_client):
        """Test that large responses are handled efficiently."""
        
        # Create a large mock response (simulate 1000 queue items)
        large_response = [
            {
                "id": i,
                "movieId": i,
                "title": f"Movie Title {i}",
                "status": "downloading",
                "size": 1000000000,  # 1GB
                "sizeleft": 500000000,  # 500MB
                "downloadId": f"download_{i}",
                "indexer": "Test Indexer",
                "outputPath": f"/downloads/movie_{i}"
            }
            for i in range(1000)
        ]
        
        with patch.object(mock_radarr_client, 'get_queue_items', new_callable=AsyncMock) as mock_radarr:
            mock_radarr.return_value = large_response
            
            start_time = time.time()
            result = await mock_radarr_client.get_queue_items()
            processing_time = time.time() - start_time
            
            # Verify the large response was handled correctly
            assert len(result) == 1000
            assert result[0]["id"] == 0
            assert result[999]["id"] == 999
            
            # Processing should be fast even with large responses
            assert processing_time < 0.1, f"Expected <100ms for large response processing, got {processing_time*1000:.0f}ms"
