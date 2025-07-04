"""
Integration tests for API clients.
These tests require actual API endpoints to be available.
"""
import unittest
from unittest.mock import patch, Mock
import sys
from pathlib import Path
import os

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from clients.radarr import RadarrClient
from clients.sonarr import SonarrClient


class TestAPIClientsIntegration(unittest.TestCase):
    """Integration tests for Radarr and Sonarr clients."""

    def setUp(self):
        """Set up test fixtures."""
        # Use environment variables or defaults for testing
        self.radarr_url = os.getenv('TEST_RADARR_URL', 'http://localhost:7878')
        self.radarr_api_key = os.getenv('TEST_RADARR_API_KEY', 'test_key')
        self.sonarr_url = os.getenv('TEST_SONARR_URL', 'http://localhost:8989')
        self.sonarr_api_key = os.getenv('TEST_SONARR_API_KEY', 'test_key')

    def test_radarr_client_initialization(self):
        """Test that RadarrClient can be initialized."""
        client = RadarrClient(self.radarr_url, self.radarr_api_key, verbose=False)
        
        self.assertEqual(client.base_url, self.radarr_url)
        self.assertEqual(client.api_key, self.radarr_api_key)
        self.assertEqual(client.service_name, "Radarr")

    def test_sonarr_client_initialization(self):
        """Test that SonarrClient can be initialized."""
        client = SonarrClient(self.sonarr_url, self.sonarr_api_key, verbose=False)
        
        self.assertEqual(client.base_url, self.sonarr_url)
        self.assertEqual(client.api_key, self.sonarr_api_key)
        self.assertEqual(client.service_name, "Sonarr")

    @patch('clients.base.httpx.Client.request')
    def test_radarr_queue_request_format(self, mock_request):
        """Test that Radarr queue requests are formatted correctly."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"records": []}
        mock_request.return_value = mock_response
        
        client = RadarrClient(self.radarr_url, self.radarr_api_key)
        client.get_queue_items()
        
        # Verify the request was made with correct parameters
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        
        self.assertIn('/api/v3/queue', kwargs['url'])
        self.assertEqual(kwargs['method'], 'GET')
        self.assertIn('pageSize', kwargs['params'])
        self.assertIn('includeMovie', kwargs['params'])

    @patch('clients.base.httpx.Client.request')
    def test_sonarr_queue_request_format(self, mock_request):
        """Test that Sonarr queue requests are formatted correctly."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"records": []}
        mock_request.return_value = mock_response
        
        client = SonarrClient(self.sonarr_url, self.sonarr_api_key)
        client.get_queue_items()
        
        # Verify the request was made with correct parameters
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        
        self.assertIn('/api/v3/queue', kwargs['url'])
        self.assertEqual(kwargs['method'], 'GET')
        self.assertIn('pageSize', kwargs['params'])
        self.assertIn('includeSeries', kwargs['params'])

    def test_radarr_queue_params(self):
        """Test that Radarr queue parameters are correct."""
        client = RadarrClient(self.radarr_url, self.radarr_api_key)
        params = client.get_queue_params()
        
        expected_keys = ['pageSize', 'page', 'sortKey', 'sortDirection', 'includeMovie']
        for key in expected_keys:
            self.assertIn(key, params)

    def test_sonarr_queue_params(self):
        """Test that Sonarr queue parameters are correct."""
        client = SonarrClient(self.sonarr_url, self.sonarr_api_key)
        params = client.get_queue_params()
        
        expected_keys = ['pageSize', 'page', 'sortKey', 'sortDirection', 'includeSeries', 'includeEpisode']
        for key in expected_keys:
            self.assertIn(key, params)

    def test_radarr_media_info_structure(self):
        """Test that Radarr media info returns expected structure."""
        client = RadarrClient(self.radarr_url, self.radarr_api_key)
        
        # Mock queue item
        queue_item = {
            "movieId": 1,
            "title": "Test Movie",
            "year": 2024
        }
        
        media_info = client.get_media_info(queue_item)
        
        # The actual implementation only returns title
        self.assertIn("title", media_info)
        self.assertIsInstance(media_info["title"], str)

    def test_sonarr_media_info_structure(self):
        """Test that Sonarr media info returns expected structure."""
        client = SonarrClient(self.sonarr_url, self.sonarr_api_key)
        
        # Mock queue item
        queue_item = {
            "seriesId": 1,
            "episodeId": 1,
            "seasonNumber": 1
        }
        
        media_info = client.get_media_info(queue_item)
        
        expected_keys = ["series", "episode", "season", "episode_number"]
        for key in expected_keys:
            self.assertIn(key, media_info)


if __name__ == '__main__':
    unittest.main()
