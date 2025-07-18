"""
Unit tests for the base media client.
"""
import unittest
from unittest.mock import patch, MagicMock, Mock, AsyncMock
import sys
from pathlib import Path
import httpx
from datetime import timedelta
import pytest

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from clients.base import MediaClient


class TestMediaClient:
    """Test cases for the MediaClient base class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.base_url = "http://localhost:8080"
        self.api_key = "test_api_key"
        self.service_name = "TestService"
        self.verbose = False
        
        # Create a concrete implementation for testing
        class TestClient(MediaClient):
            def get_queue_params(self):
                return {"pageSize": 100, "page": 1}
            
            async def get_queue_items(self):
                return []
            
            async def get_media_info(self, queue_item):
                return {"title": "Test Item"}
        
        self.TestClient = TestClient

    def test_initialization(self):
        """Test that MediaClient initializes correctly."""
        client = self.TestClient(self.base_url, self.api_key, self.service_name, self.verbose)
        
        assert client.base_url == self.base_url
        assert client.api_key == self.api_key
        assert client.service_name == self.service_name
        assert client.verbose == self.verbose
        assert client.session is not None
        assert client.session.headers['X-Api-Key'] == self.api_key

    def test_initialization_with_trailing_slash(self):
        """Test that trailing slash is removed from base URL."""
        url_with_slash = "http://localhost:8080/"
        client = self.TestClient(url_with_slash, self.api_key, self.service_name)
        
        assert client.base_url == self.base_url

    @patch('clients.base.httpx.AsyncClient.request')
    async def test_make_request_success(self, mock_request):
        """Test successful API request."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"test": "data"}
        mock_request.return_value = mock_response
        
        client = self.TestClient(self.base_url, self.api_key, self.service_name)
        result = await client._make_request("test/endpoint")
        
        assert result == {"test": "data"}
        mock_request.assert_called_once()

    @patch('clients.base.httpx.AsyncClient.request')
    async def test_make_request_with_params(self, mock_request):
        """Test API request with parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"test": "data"}
        mock_request.return_value = mock_response
        
        client = self.TestClient(self.base_url, self.api_key, self.service_name)
        params = {"page": 1, "size": 10}
        result = await client._make_request("test/endpoint", params=params)
        
        mock_request.assert_called_once()

    @patch('clients.base.httpx.AsyncClient.request')
    @patch('clients.base.logger')
    async def test_make_request_http_error(self, mock_logger, mock_request):
        """Test API request with HTTP error."""
        # Mock HTTP error
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_request.return_value = mock_response
        
        client = self.TestClient(self.base_url, self.api_key, self.service_name, verbose=True)
        result = await client._make_request("test/endpoint")
        
        assert result is None
        mock_logger.warning.assert_called()

    @patch('clients.base.httpx.AsyncClient.request')
    @patch('clients.base.logger')
    async def test_make_request_connection_error(self, mock_logger, mock_request):
        """Test API request with connection error."""
        # Mock connection error
        mock_request.side_effect = httpx.ConnectError("Connection failed")
        
        client = self.TestClient(self.base_url, self.api_key, self.service_name)
        result = await client._make_request("test/endpoint")
        
        assert result is None
        mock_logger.error.assert_called()

    async def test_get_queue_success(self):
        """Test successful queue retrieval."""
        client = self.TestClient(self.base_url, self.api_key, self.service_name)
        
        # Mock get_queue_items to return test data
        test_items = [{"id": 1}, {"id": 2}]
        with patch.object(client, 'get_queue_items', return_value=test_items):
            with patch.object(client, 'get_media_info', return_value={"title": "Test"}):
                result = await client.get_queue()
        
        assert len(result) == 2
        assert result[0]["title"] == "Test"

    async def test_get_queue_failure(self):
        """Test queue retrieval failure."""
        client = self.TestClient(self.base_url, self.api_key, self.service_name)
        
        # Mock get_queue_items to raise an exception
        with patch.object(client, 'get_queue_items', side_effect=Exception("Connection failed")):
            result = await client.get_queue()
        
        assert result == []

    async def test_get_active_downloads(self):
        """Test filtering active downloads."""
        client = self.TestClient(self.base_url, self.api_key, self.service_name)
        
        test_queue = [
            {"id": 1, "status": "downloading", "progress": 50},
            {"id": 2, "status": "completed", "progress": 100},
            {"id": 3, "status": "queued", "progress": 0},
            {"id": 4, "status": "failed", "progress": 25},
        ]
        
        with patch.object(client, 'get_queue', return_value=test_queue):
            active = await client.get_active_downloads()
        
        # Should only return downloading and queued items
        assert len(active) == 2
        assert active[0]["id"] == 1
        assert active[1]["id"] == 3

    def test_parse_time_left_valid_formats(self):
        """Test parsing various time left formats."""
        client = self.TestClient(self.base_url, self.api_key, self.service_name)
        
        test_cases = [
            ("2:30:45", timedelta(hours=2, minutes=30, seconds=45)),
            ("1:00:00", timedelta(hours=1, minutes=0, seconds=0)),
            ("0:30:00", timedelta(hours=0, minutes=30, seconds=0)),
            ("0:00:30", timedelta(hours=0, minutes=0, seconds=30)),
            ("30:45", timedelta(minutes=30, seconds=45)),
            ("5:00", timedelta(minutes=5, seconds=0)),
        ]
        
        for time_str, expected in test_cases:
            result = client.parse_time_left(time_str)
            assert result == expected

    def test_parse_time_left_invalid_formats(self):
        """Test parsing invalid time left formats."""
        client = self.TestClient(self.base_url, self.api_key, self.service_name)
        
        invalid_inputs = ["invalid", "", None, "1:2:3:4"]
        
        for invalid_input in invalid_inputs:
            result = client.parse_time_left(invalid_input)
            assert result is None

    @patch('clients.base.MediaClient._remove_queue_item')
    async def test_remove_stuck_downloads_success(self, mock_remove):
        """Test successful removal of stuck downloads."""
        mock_remove.return_value = True
        
        client = self.TestClient(self.base_url, self.api_key, self.service_name)
        stuck_ids = ["1", "2", "3"]
        
        result = await client.remove_stuck_downloads(stuck_ids)
        
        assert result == 3
        assert mock_remove.call_count == 3

    @patch('clients.base.MediaClient._remove_queue_item')
    async def test_remove_stuck_downloads_partial_failure(self, mock_remove):
        """Test partial failure when removing stuck downloads."""
        # First call succeeds, second fails, third succeeds
        mock_remove.side_effect = [True, False, True]
        
        client = self.TestClient(self.base_url, self.api_key, self.service_name)
        stuck_ids = ["1", "2", "3"]
        
        result = await client.remove_stuck_downloads(stuck_ids)
        
        assert result == 2  # Only 2 successful removals
        assert mock_remove.call_count == 3

    async def test_remove_stuck_downloads_empty_list(self):
        """Test removing stuck downloads with empty list."""
        client = self.TestClient(self.base_url, self.api_key, self.service_name)
        
        result = await client.remove_stuck_downloads([])
        
        assert result == 0

    @patch('clients.base.MediaClient._remove_queue_item')
    @patch('clients.base.MediaClient._make_request')
    async def test_remove_inactive_items_success(self, mock_request, mock_remove):
        """Test successful removal of inactive items."""
        # Mock _make_request to return test data
        queue_data = {
            "records": [
                {"id": 1, "status": "completed"},
                {"id": 2, "status": "failed"},
                {"id": 3, "status": "downloading"},
                {"id": 4, "status": "warning"},
            ]
        }
        mock_request.return_value = queue_data
        mock_remove.return_value = True
        
        client = self.TestClient(self.base_url, self.api_key, self.service_name)
        result = await client.remove_inactive_items()
        
        # Should remove items 1, 2, and 4 (completed, failed, warning)
        assert result == 3
        assert mock_remove.call_count == 3

    @patch('clients.base.MediaClient._make_request')
    async def test_test_connection_success(self, mock_request):
        """Test successful connection test."""
        mock_request.return_value = {"status": "ok"}
        
        client = self.TestClient(self.base_url, self.api_key, self.service_name)
        result = await client.test_connection()
        
        assert result is True
        mock_request.assert_called_once_with('system/status')

    @patch('clients.base.MediaClient._make_request')
    async def test_test_connection_failure(self, mock_request):
        """Test failed connection test."""
        mock_request.return_value = None
        
        client = self.TestClient(self.base_url, self.api_key, self.service_name)
        result = await client.test_connection()
        
        assert result is False

    async def test_get_download_updates(self):
        """Test getting download updates."""
        client = self.TestClient(self.base_url, self.api_key, self.service_name)
        
        test_active = [{"id": 1, "status": "downloading"}]
        with patch.object(client, 'get_active_downloads', return_value=test_active):
            result = await client.get_download_updates()
        
        assert result == test_active
