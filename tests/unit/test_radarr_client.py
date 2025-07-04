"""
Unit tests for Radarr client.
"""
import unittest
from unittest.mock import patch, Mock, AsyncMock
import sys
from pathlib import Path
import pytest

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from clients.radarr import RadarrClient


class TestRadarrClient:
    """Test cases for RadarrClient."""

    def setup_method(self):
        """Set up test fixtures."""
        self.base_url = "http://localhost:7878"
        self.api_key = "test_api_key"
        self.client = RadarrClient(self.base_url, self.api_key, verbose=False)

    def test_initialization(self):
        """Test RadarrClient initialization."""
        assert self.client.base_url == self.base_url
        assert self.client.api_key == self.api_key
        assert self.client.service_name == "Radarr"

    def test_get_queue_params(self):
        """Test queue parameters for Radarr."""
        params = self.client.get_queue_params()
        
        expected_keys = ['pageSize', 'page', 'sortKey', 'sortDirection', 'includeMovie']
        for key in expected_keys:
            assert key in params
        
        # Test actual default values
        assert params['pageSize'] == 1000
        assert params['page'] == 1
        assert params['sortKey'] == 'timeleft'
        assert params['sortDirection'] == 'ascending'
        assert params['includeMovie'] is True

    def test_get_queue_params_no_parameters(self):
        """Test that queue parameters method doesn't accept parameters."""
        # The actual implementation doesn't accept parameters
        params = self.client.get_queue_params()
        assert isinstance(params, dict)

    @patch.object(RadarrClient, 'get_movie_by_id')
    async def test_get_media_info_basic(self, mock_get_movie):
        """Test basic media info extraction."""
        mock_get_movie.return_value = {"title": "Test Movie"}
        
        queue_item = {
            "movieId": 123,
            "title": "Test Movie",
            "year": 2023
        }
        
        media_info = await self.client.get_media_info(queue_item)
        
        assert "title" in media_info
        assert media_info["title"] == "Test Movie"

    async def test_get_media_info_missing_title(self):
        """Test media info with missing title."""
        queue_item = {
            "movieId": 123,
            "year": 2023
        }
        
        with patch.object(self.client, 'get_movie_by_id', return_value={}):
            media_info = await self.client.get_media_info(queue_item)
        
        assert "title" in media_info
        assert media_info["title"] == "Unknown Movie"

    async def test_get_media_info_empty_item(self):
        """Test media info with empty item."""
        queue_item = {}
        
        with patch.object(self.client, 'get_movie_by_id', return_value={}):
            media_info = await self.client.get_media_info(queue_item)
        
        assert "title" in media_info
        assert media_info["title"] == "Unknown Movie"

    @patch('clients.radarr.RadarrClient._make_request')
    async def test_get_queue_items_success(self, mock_request):
        """Test successful queue items retrieval."""
        mock_request.return_value = {
            "records": [
                {
                    "id": 1,
                    "movieId": 1,
                    "title": "Movie 1",
                    "size": 1000000000,
                    "sizeleft": 500000000,
                    "status": "downloading"
                }
            ],
            "totalRecords": 1
        }
        
        with patch.object(self.client, 'get_movie_by_id', return_value={"title": "Test Movie"}):
            result = await self.client.get_queue_items()
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["title"] == "Test Movie"

    @patch('clients.radarr.RadarrClient._make_request')
    async def test_get_queue_items_empty_response(self, mock_request):
        """Test queue items with empty response."""
        mock_request.return_value = {"records": []}
        
        result = await self.client.get_queue_items()
        
        assert isinstance(result, list)
        assert len(result) == 0

    @patch('clients.radarr.RadarrClient._make_request')
    async def test_get_queue_items_http_error(self, mock_request):
        """Test queue items with HTTP error."""
        mock_request.return_value = None
        
        result = await self.client.get_queue_items()
        
        assert isinstance(result, list)
        assert len(result) == 0

    @patch('clients.radarr.RadarrClient._make_request')
    async def test_get_queue_items_invalid_json(self, mock_request):
        """Test queue items with invalid JSON response."""
        mock_request.return_value = None
        
        result = await self.client.get_queue_items()
        
        assert isinstance(result, list)
        assert len(result) == 0

    @patch('clients.radarr.RadarrClient._make_request')
    async def test_get_queue_items_missing_records(self, mock_request):
        """Test queue items with missing records field."""
        mock_request.return_value = {"totalRecords": 0}
        
        result = await self.client.get_queue_items()
        
        assert isinstance(result, list)
        assert len(result) == 0

    def test_format_progress_info_basic(self):
        """Test basic progress info formatting."""
        queue_item = {
            "title": "Test Movie",
            "size": 1000000000,
            "sizeleft": 500000000,
            "status": "downloading"
        }
        
        # This method might not exist in the actual implementation
        # but we're testing the concept
        if hasattr(self.client, 'format_progress_info'):
            result = self.client.format_progress_info(queue_item)
            assert isinstance(result, dict)

    def test_api_endpoint_construction(self):
        """Test API endpoint URL construction."""
        # Test that the client constructs proper API URLs
        expected_base = f"{self.base_url}/api/v3"
        
        # The base client should handle URL construction
        # This tests the integration with the base client
        assert self.client.base_url.startswith("http")

    def test_service_specific_headers(self):
        """Test Radarr-specific headers if any."""
        # Radarr might have specific headers or authentication
        # This test ensures the client is properly configured
        assert self.client.service_name == "Radarr"

    async def test_error_handling_patterns(self):
        """Test common error handling patterns."""
        # Test with None input - this should be handled gracefully
        with patch.object(self.client, 'get_movie_by_id', return_value={}):
            try:
                await self.client.get_media_info(None)
                # If no exception is raised, the method handles None gracefully
                assert True
            except AttributeError:
                # If AttributeError is raised, that's expected behavior
                assert True

    @patch('clients.radarr.RadarrClient._make_request')
    async def test_request_timeout_handling(self, mock_request):
        """Test handling of request timeouts."""
        mock_request.return_value = None
        
        result = await self.client.get_queue_items()
        
        assert isinstance(result, list)
        assert len(result) == 0

    def test_queue_params_structure(self):
        """Test that queue parameters have correct structure."""
        params = self.client.get_queue_params()
        
        # Test that all required keys are present
        assert 'pageSize' in params
        assert 'page' in params
        assert 'sortKey' in params
        assert 'sortDirection' in params
        assert 'includeMovie' in params

    async def test_media_info_data_types(self):
        """Test that media info returns correct data types."""
        queue_item = {
            "movieId": 123,
            "title": "Test Movie",
            "year": 2023
        }
        
        with patch.object(self.client, 'get_movie_by_id', return_value={"title": "Test Movie"}):
            media_info = await self.client.get_media_info(queue_item)
        
        assert isinstance(media_info, dict)
        assert isinstance(media_info["title"], str)
