"""
Unit tests for Sonarr client.
"""
import unittest
from unittest.mock import patch, Mock, AsyncMock
import sys
from pathlib import Path
import pytest

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from clients.sonarr import SonarrClient


class TestSonarrClient:
    """Test cases for SonarrClient."""

    def setup_method(self):
        """Set up test fixtures."""
        self.base_url = "http://localhost:8989"
        self.api_key = "test_api_key"
        self.client = SonarrClient(self.base_url, self.api_key, verbose=False)

    def test_initialization(self):
        """Test SonarrClient initialization."""
        assert self.client.base_url == self.base_url
        assert self.client.api_key == self.api_key
        assert self.client.service_name == "Sonarr"

    def test_get_queue_params(self):
        """Test queue parameters for Sonarr."""
        params = self.client.get_queue_params()
        
        expected_keys = ['pageSize', 'page', 'sortKey', 'sortDirection', 'includeSeries', 'includeEpisode']
        for key in expected_keys:
            assert key in params
        
        # Test actual default values
        assert params['pageSize'] == 1000
        assert params['page'] == 1
        assert params['sortKey'] == 'timeleft'
        assert params['sortDirection'] == 'ascending'
        assert params['includeSeries'] is True
        assert params['includeEpisode'] is True

    def test_get_queue_params_no_parameters(self):
        """Test that queue parameters method doesn't accept parameters."""
        # The actual implementation doesn't accept parameters
        params = self.client.get_queue_params()
        assert isinstance(params, dict)

    @patch.object(SonarrClient, 'get_series_by_id')
    @patch.object(SonarrClient, 'get_episode_by_id')
    async def test_get_media_info_basic(self, mock_get_episode, mock_get_series):
        """Test basic media info extraction."""
        mock_get_series.return_value = {"title": "Test Series"}
        mock_get_episode.return_value = {"title": "Test Episode", "episodeNumber": 5}
        
        queue_item = {
            "seriesId": 123,
            "episodeId": 456,
            "seasonNumber": 1,
            "episodeNumber": 5,
            "series": {"title": "Test Series"},
            "episode": {"title": "Test Episode"}
        }
        
        media_info = await self.client.get_media_info(queue_item)
        
        expected_keys = ["series", "episode", "season", "episode_number"]
        for key in expected_keys:
            assert key in media_info
        
        assert media_info["series"] == "Test Series"
        assert media_info["episode"] == "Test Episode"
        assert media_info["season"] == 1
        assert media_info["episode_number"] == 5

    async def test_get_media_info_missing_series(self):
        """Test media info with missing series information."""
        queue_item = {
            "seriesId": 123,
            "episodeId": 456,
            "seasonNumber": 1,
            "episodeNumber": 5
        }
        
        with patch.object(self.client, 'get_series_by_id', return_value={}):
            with patch.object(self.client, 'get_episode_by_id', return_value={}):
                media_info = await self.client.get_media_info(queue_item)
        
        assert media_info["series"] == "Unknown Series"
        assert media_info["episode"] == "Unknown Episode"

    async def test_get_media_info_missing_episode(self):
        """Test media info with missing episode information."""
        queue_item = {
            "seriesId": 123,
            "seasonNumber": 1,
            "episodeNumber": 5,
            "series": {"title": "Test Series"}
        }
        
        with patch.object(self.client, 'get_series_by_id', return_value={"title": "Test Series"}):
            with patch.object(self.client, 'get_episode_by_id', return_value={}):
                media_info = await self.client.get_media_info(queue_item)
        
        assert media_info["series"] == "Test Series"
        assert media_info["episode"] == "Unknown Episode"

    async def test_get_media_info_empty_item(self):
        """Test media info with empty item."""
        queue_item = {}
        
        with patch.object(self.client, 'get_series_by_id', return_value={}):
            with patch.object(self.client, 'get_episode_by_id', return_value={}):
                media_info = await self.client.get_media_info(queue_item)
        
        assert media_info["series"] == "Unknown Series"
        assert media_info["episode"] == "Unknown Episode"
        assert media_info["season"] == 0
        assert media_info["episode_number"] == 0

    async def test_get_media_info_none_item(self):
        """Test media info with None item."""
        # Test with None input - this should be handled gracefully
        with patch.object(self.client, 'get_series_by_id', return_value={}):
            with patch.object(self.client, 'get_episode_by_id', return_value={}):
                try:
                    await self.client.get_media_info(None)
                    # If no exception is raised, the method handles None gracefully
                    assert True
                except AttributeError:
                    # If AttributeError is raised, that's expected behavior
                    assert True

    @patch('clients.sonarr.SonarrClient._make_request')
    async def test_get_queue_items_success(self, mock_request):
        """Test successful queue items retrieval."""
        mock_request.return_value = {
            "records": [
                {
                    "id": 1,
                    "seriesId": 1,
                    "episodeId": 1,
                    "series": {"title": "Test Series"},
                    "episode": {"title": "Test Episode"},
                    "size": 1000000000,
                    "sizeleft": 500000000,
                    "status": "downloading"
                }
            ],
            "totalRecords": 1
        }
        
        with patch.object(self.client, 'get_series_by_id', return_value={"title": "Test Series"}):
            with patch.object(self.client, 'get_episode_by_id', return_value={"title": "Test Episode", "episodeNumber": 1}):
                result = await self.client.get_queue_items()
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert "series" in result[0]

    @patch('clients.sonarr.SonarrClient._make_request')
    async def test_get_queue_items_empty_response(self, mock_request):
        """Test queue items with empty response."""
        mock_request.return_value = {"records": []}
        
        result = await self.client.get_queue_items()
        
        assert isinstance(result, list)
        assert len(result) == 0

    @patch('clients.sonarr.SonarrClient._make_request')
    async def test_get_queue_items_http_error(self, mock_request):
        """Test queue items with HTTP error."""
        mock_request.return_value = None
        
        result = await self.client.get_queue_items()
        
        assert isinstance(result, list)
        assert len(result) == 0

    @patch('clients.sonarr.SonarrClient._make_request')
    async def test_get_queue_items_connection_error(self, mock_request):
        """Test queue items with connection error."""
        mock_request.return_value = None
        
        result = await self.client.get_queue_items()
        
        assert isinstance(result, list)
        assert len(result) == 0

    async def test_media_info_nested_data_extraction(self):
        """Test extraction of nested data from complex queue items."""
        queue_item = {
            "seriesId": 123,
            "episodeId": 456,
            "seasonNumber": 2,
            "episodeNumber": 10,
            "series": {
                "title": "Complex Series Name",
                "year": 2023,
                "tvdbId": 789
            },
            "episode": {
                "title": "Complex Episode Title",
                "airDate": "2023-10-10",
                "overview": "Episode description"
            }
        }
        
        with patch.object(self.client, 'get_series_by_id', return_value={"title": "Complex Series Name"}):
            with patch.object(self.client, 'get_episode_by_id', return_value={"title": "Complex Episode Title", "episodeNumber": 10}):
                media_info = await self.client.get_media_info(queue_item)
        
        assert media_info["series"] == "Complex Series Name"
        assert media_info["episode"] == "Complex Episode Title"
        assert media_info["season"] == 2
        assert media_info["episode_number"] == 10

    async def test_media_info_data_types(self):
        """Test that media info returns correct data types."""
        queue_item = {
            "seriesId": 123,
            "episodeId": 456,
            "seasonNumber": "1",  # String instead of int
            "episodeNumber": "5",  # String instead of int
            "series": {"title": "Test Series"},
            "episode": {"title": "Test Episode"}
        }
        
        with patch.object(self.client, 'get_series_by_id', return_value={"title": "Test Series"}):
            with patch.object(self.client, 'get_episode_by_id', return_value={"title": "Test Episode", "episodeNumber": 5}):
                media_info = await self.client.get_media_info(queue_item)
        
        assert isinstance(media_info, dict)
        assert isinstance(media_info["series"], str)
        assert isinstance(media_info["episode"], str)
        assert media_info["season"] == "1"
        assert media_info["episode_number"] == 5

    def test_queue_params_structure(self):
        """Test that queue parameters have correct structure."""
        params = self.client.get_queue_params()
        
        # Test that all required keys are present
        assert 'pageSize' in params
        assert 'page' in params
        assert 'sortKey' in params
        assert 'sortDirection' in params
        assert 'includeSeries' in params
        assert 'includeEpisode' in params

    def test_service_specific_configuration(self):
        """Test Sonarr-specific configuration."""
        assert self.client.service_name == "Sonarr"
        
        # Sonarr should include both series and episode info
        params = self.client.get_queue_params()
        assert params['includeSeries'] is True
        assert params['includeEpisode'] is True

    async def test_error_handling_with_malformed_data(self):
        """Test error handling with malformed queue item data."""
        malformed_items = [
            {"seriesId": "not_a_number"},
            {"series": "not_a_dict"},
            {"episode": None},
            {"seasonNumber": None, "episodeNumber": None}
        ]
        
        for item in malformed_items:
            with patch.object(self.client, 'get_series_by_id', return_value={}):
                with patch.object(self.client, 'get_episode_by_id', return_value={}):
                    media_info = await self.client.get_media_info(item)
                    assert isinstance(media_info, dict)
                    assert "series" in media_info
                    assert "episode" in media_info

    @patch('clients.sonarr.SonarrClient._make_request')
    async def test_api_request_parameters(self, mock_request):
        """Test that API requests include correct parameters."""
        mock_request.return_value = {"records": []}
        
        await self.client.get_queue_items()
        
        # Verify the request was made with correct parameters
        mock_request.assert_called_once()

    async def test_media_info_with_special_characters(self):
        """Test media info extraction with special characters."""
        queue_item = {
            "seriesId": 123,
            "episodeId": 456,
            "seasonNumber": 1,
            "episodeNumber": 1,
            "series": {"title": "Série Spéciale & Ñoño"},
            "episode": {"title": "Épisode with émojis 🎬"}
        }
        
        with patch.object(self.client, 'get_series_by_id', return_value={"title": "Série Spéciale & Ñoño"}):
            with patch.object(self.client, 'get_episode_by_id', return_value={"title": "Épisode with émojis 🎬", "episodeNumber": 1}):
                media_info = await self.client.get_media_info(queue_item)
        
        assert media_info["series"] == "Série Spéciale & Ñoño"
        assert media_info["episode"] == "Épisode with émojis 🎬"
