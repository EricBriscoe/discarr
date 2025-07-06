"""
Unit tests for the HealthChecker class.
"""
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime
import httpx

from src.monitoring.health_checker import HealthChecker

@pytest.fixture
def mock_config():
    """Create a mock configuration object."""
    config = Mock()
    config.radarr_api_key = "test_radarr_key"
    config.radarr_url = "http://localhost:7878"
    config.sonarr_api_key = "test_sonarr_key"
    config.sonarr_url = "http://localhost:8989"
    config.plex_url = "http://localhost:32400"
    return config

@pytest.fixture
def health_checker(mock_config):
    """Create a HealthChecker instance with mock config."""
    return HealthChecker(mock_config)

@pytest.fixture
def mock_async_client():
    """Create a mock httpx.AsyncClient."""
    return AsyncMock(spec=httpx.AsyncClient)

@pytest.mark.asyncio
class TestHealthChecker:
    """Test cases for HealthChecker class."""

    async def test_init(self, health_checker, mock_config):
        """Test HealthChecker initialization."""
        assert health_checker.config == mock_config
        assert 'radarr' in health_checker.health_status
        assert health_checker.health_status['radarr']['status'] == 'unknown'

    async def test_check_radarr_health_success(self, health_checker, mock_async_client):
        """Test successful Radarr health check."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={'version': '4.0.0'})
        mock_async_client.get.return_value = mock_response

        await health_checker.check_radarr_health(mock_async_client)

        assert health_checker.health_status['radarr']['status'] == 'online'
        assert health_checker.health_status['radarr']['version'] == '4.0.0'
        mock_async_client.get.assert_awaited_once_with(
            "http://localhost:7878/api/v3/system/status",
            headers={'X-Api-Key': 'test_radarr_key'},
            timeout=10
        )

    async def test_check_radarr_health_error_status(self, health_checker, mock_async_client):
        """Test Radarr health check with error status code."""
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_async_client.get.return_value = mock_response

        await health_checker.check_radarr_health(mock_async_client)

        assert health_checker.health_status['radarr']['status'] == 'error'
        assert health_checker.health_status['radarr']['error'] == 'Status code: 500'

    async def test_check_radarr_health_request_error(self, health_checker, mock_async_client):
        """Test Radarr health check with request error."""
        mock_async_client.get.side_effect = httpx.RequestError("Connection failed")

        await health_checker.check_radarr_health(mock_async_client)

        assert health_checker.health_status['radarr']['status'] == 'offline'

    async def test_check_radarr_health_disabled(self, health_checker, mock_async_client, mock_config):
        """Test Radarr health check when API key is not configured."""
        mock_config.radarr_api_key = None
        
        await health_checker.check_radarr_health(mock_async_client)
        
        assert health_checker.health_status['radarr']['status'] == 'disabled'
        mock_async_client.get.assert_not_awaited()

    async def test_check_sonarr_health_success(self, health_checker, mock_async_client):
        """Test successful Sonarr health check."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={'version': '3.0.0'})
        mock_async_client.get.return_value = mock_response

        await health_checker.check_sonarr_health(mock_async_client)

        assert health_checker.health_status['sonarr']['status'] == 'online'
        assert health_checker.health_status['sonarr']['version'] == '3.0.0'

    async def test_check_plex_health_success(self, health_checker, mock_async_client):
        """Test successful Plex health check."""
        xml_response = '<?xml version="1.0" encoding="UTF-8"?><MediaContainer version="1.30.0.6486" />'
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = xml_response
        mock_async_client.get.return_value = mock_response

        await health_checker.check_plex_health(mock_async_client)

        assert health_checker.health_status['plex']['status'] == 'online'
        assert health_checker.health_status['plex']['version'] == '1.30.0.6486'

    async def test_check_all_services(self, health_checker):
        """Test checking all services at once."""
        health_checker.check_radarr_health = AsyncMock()
        health_checker.check_sonarr_health = AsyncMock()
        health_checker.check_plex_health = AsyncMock()

        await health_checker.check_all_services()

        health_checker.check_radarr_health.assert_awaited_once()
        health_checker.check_sonarr_health.assert_awaited_once()
        health_checker.check_plex_health.assert_awaited_once()

    def test_get_health_status(self, health_checker):
        """Test getting health status returns a copy."""
        health_checker.health_status['radarr']['status'] = 'test_status'
        
        result = health_checker.get_health_status()
        
        assert result == health_checker.health_status
        assert result is not health_checker.health_status
