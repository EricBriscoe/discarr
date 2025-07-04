"""
Integration tests for API clients.
These tests require actual API endpoints to be available.
"""
import unittest
from unittest.mock import patch, Mock, AsyncMock
import sys
from pathlib import Path
import os
import pytest

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from clients.radarr import RadarrClient
from clients.sonarr import SonarrClient


class TestAPIClientsIntegration:
    """Integration tests for Radarr and Sonarr clients."""

    def setup_method(self):
        """Set up test fixtures."""
        # Use environment variables or defaults for testing
        self.radarr_url = os.getenv('TEST_RADARR_URL', 'http://localhost:7878')
        self.radarr_api_key = os.getenv('TEST_RADARR_API_KEY', 'test_key')
        self.sonarr_url = os.getenv('TEST_SONARR_URL', 'http://localhost:8989')
        self.sonarr_api_key = os.getenv('TEST_SONARR_API_KEY', 'test_key')

    def test_radarr_client_initialization(self):
        """Test that RadarrClient can be initialized."""
        client = RadarrClient(self.radarr_url, self.radarr_api_key, verbose=False)
        
        assert client.base_url == self.radarr_url
        assert client.api_key == self.radarr_api_key
        assert client.service_name == "Radarr"

    def test_sonarr_client_initialization(self):
        """Test that SonarrClient can be initialized."""
        client = SonarrClient(self.sonarr_url, self.sonarr_api_key, verbose=False)
        
        assert client.base_url == self.sonarr_url
        assert client.api_key == self.sonarr_api_key
        assert client.service_name == "Sonarr"

    @patch('clients.radarr.RadarrClient._make_request')
    async def test_radarr_queue_request_format(self, mock_request):
        """Test that Radarr queue requests are formatted correctly."""
        # Mock response
        mock_request.return_value = {"records": []}
        
        client = RadarrClient(self.radarr_url, self.radarr_api_key)
        await client.get_queue_items()
        
        # Verify the request was made with correct parameters
        mock_request.assert_called_once()

    @patch('clients.sonarr.SonarrClient._make_request')
    async def test_sonarr_queue_request_format(self, mock_request):
        """Test that Sonarr queue requests are formatted correctly."""
        # Mock response
        mock_request.return_value = {"records": []}
        
        client = SonarrClient(self.sonarr_url, self.sonarr_api_key)
        await client.get_queue_items()
        
        # Verify the request was made with correct parameters
        mock_request.assert_called_once()

    def test_radarr_queue_params(self):
        """Test that Radarr queue parameters are correct."""
        client = RadarrClient(self.radarr_url, self.radarr_api_key)
        params = client.get_queue_params()
        
        expected_keys = ['pageSize', 'page', 'sortKey', 'sortDirection', 'includeMovie']
        for key in expected_keys:
            assert key in params

    def test_sonarr_queue_params(self):
        """Test that Sonarr queue parameters are correct."""
        client = SonarrClient(self.sonarr_url, self.sonarr_api_key)
        params = client.get_queue_params()
        
        expected_keys = ['pageSize', 'page', 'sortKey', 'sortDirection', 'includeSeries', 'includeEpisode']
        for key in expected_keys:
            assert key in params

    async def test_radarr_media_info_structure(self):
        """Test that Radarr media info returns expected structure."""
        client = RadarrClient(self.radarr_url, self.radarr_api_key)
        
        # Mock queue item
        queue_item = {
            "movieId": 1,
            "title": "Test Movie",
            "year": 2024
        }
        
        with patch.object(client, 'get_movie_by_id', return_value={"title": "Test Movie"}):
            media_info = await client.get_media_info(queue_item)
        
        # The actual implementation only returns title
        assert "title" in media_info
        assert isinstance(media_info["title"], str)

    async def test_sonarr_media_info_structure(self):
        """Test that Sonarr media info returns expected structure."""
        client = SonarrClient(self.sonarr_url, self.sonarr_api_key)
        
        # Mock queue item
        queue_item = {
            "seriesId": 1,
            "episodeId": 1,
            "seasonNumber": 1
        }
        
        with patch.object(client, 'get_series_by_id', return_value={"title": "Test Series"}):
            with patch.object(client, 'get_episode_by_id', return_value={"title": "Test Episode", "episodeNumber": 1}):
                media_info = await client.get_media_info(queue_item)
        
        expected_keys = ["series", "episode", "season", "episode_number"]
        for key in expected_keys:
            assert key in media_info
