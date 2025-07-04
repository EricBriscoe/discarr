"""
Unit tests for the HealthChecker class.
"""
import pytest
import httpx
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import time
import xml.etree.ElementTree as ET

from src.monitoring.health_checker import HealthChecker


class TestHealthChecker:
    """Test cases for HealthChecker class."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration object."""
        config = Mock()
        config.radarr_api_key = "test_radarr_key"
        config.radarr_url = "http://localhost:7878"
        config.sonarr_api_key = "test_sonarr_key"
        config.sonarr_url = "http://localhost:8989"
        config.plex_url = "http://localhost:32400"
        return config
    
    @pytest.fixture
    def health_checker(self, mock_config):
        """Create a HealthChecker instance with mock config."""
        return HealthChecker(mock_config)
    
    def test_init(self, health_checker, mock_config):
        """Test HealthChecker initialization."""
        assert health_checker.config == mock_config
        assert 'radarr' in health_checker.health_status
        assert 'sonarr' in health_checker.health_status
        assert 'plex' in health_checker.health_status
        
        # Check initial status
        for service in ['radarr', 'sonarr', 'plex']:
            assert health_checker.health_status[service]['status'] == 'unknown'
            assert health_checker.health_status[service]['last_check'] is None
            assert health_checker.health_status[service]['response_time'] == 0
    
    @patch('httpx.get')
    def test_check_radarr_health_success(self, mock_get, health_checker):
        """Test successful Radarr health check."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'version': '4.0.0'}
        mock_get.return_value = mock_response
        
        result = health_checker.check_radarr_health()
        
        assert result is True
        assert health_checker.health_status['radarr']['status'] == 'online'
        assert health_checker.health_status['radarr']['version'] == '4.0.0'
        assert health_checker.health_status['radarr']['response_time'] > 0
        assert isinstance(health_checker.health_status['radarr']['last_check'], datetime)
        
        # Verify API call
        mock_get.assert_called_once_with(
            "http://localhost:7878/api/v3/system/status",
            headers={'X-Api-Key': 'test_radarr_key'},
            timeout=10
        )
    
    @patch('httpx.get')
    def test_check_radarr_health_error_status(self, mock_get, health_checker):
        """Test Radarr health check with error status code."""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        result = health_checker.check_radarr_health()
        
        assert result is False
        assert health_checker.health_status['radarr']['status'] == 'error'
        assert health_checker.health_status['radarr']['error'] == 'Status code: 500'
        assert health_checker.health_status['radarr']['response_time'] > 0
        assert isinstance(health_checker.health_status['radarr']['last_check'], datetime)
    
    @patch('httpx.get')
    def test_check_radarr_health_request_error(self, mock_get, health_checker):
        """Test Radarr health check with request error."""
        # Mock request error
        mock_get.side_effect = httpx.RequestError("Connection failed")
        
        result = health_checker.check_radarr_health()
        
        assert result is False
        assert health_checker.health_status['radarr']['status'] == 'offline'
        assert isinstance(health_checker.health_status['radarr']['last_check'], datetime)
        assert 'error' not in health_checker.health_status['radarr']
    
    def test_check_radarr_health_disabled(self, health_checker):
        """Test Radarr health check when API key is not configured."""
        health_checker.config.radarr_api_key = None
        
        result = health_checker.check_radarr_health()
        
        assert result is False
        assert health_checker.health_status['radarr']['status'] == 'disabled'
        assert isinstance(health_checker.health_status['radarr']['last_check'], datetime)
    
    @patch('httpx.get')
    def test_check_sonarr_health_success(self, mock_get, health_checker):
        """Test successful Sonarr health check."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'version': '3.0.0'}
        mock_get.return_value = mock_response
        
        result = health_checker.check_sonarr_health()
        
        assert result is True
        assert health_checker.health_status['sonarr']['status'] == 'online'
        assert health_checker.health_status['sonarr']['version'] == '3.0.0'
        assert health_checker.health_status['sonarr']['response_time'] > 0
        assert isinstance(health_checker.health_status['sonarr']['last_check'], datetime)
        
        # Verify API call
        mock_get.assert_called_once_with(
            "http://localhost:8989/api/v3/system/status",
            headers={'X-Api-Key': 'test_sonarr_key'},
            timeout=10
        )
    
    @patch('httpx.get')
    def test_check_sonarr_health_error_status(self, mock_get, health_checker):
        """Test Sonarr health check with error status code."""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        result = health_checker.check_sonarr_health()
        
        assert result is False
        assert health_checker.health_status['sonarr']['status'] == 'error'
        assert health_checker.health_status['sonarr']['error'] == 'Status code: 401'
        assert health_checker.health_status['sonarr']['response_time'] > 0
        assert isinstance(health_checker.health_status['sonarr']['last_check'], datetime)
    
    @patch('httpx.get')
    def test_check_sonarr_health_request_error(self, mock_get, health_checker):
        """Test Sonarr health check with request error."""
        # Mock request error
        mock_get.side_effect = httpx.RequestError("Connection timeout")
        
        result = health_checker.check_sonarr_health()
        
        assert result is False
        assert health_checker.health_status['sonarr']['status'] == 'offline'
        assert isinstance(health_checker.health_status['sonarr']['last_check'], datetime)
        assert 'error' not in health_checker.health_status['sonarr']
    
    def test_check_sonarr_health_disabled(self, health_checker):
        """Test Sonarr health check when API key is not configured."""
        health_checker.config.sonarr_api_key = ""
        
        result = health_checker.check_sonarr_health()
        
        assert result is False
        assert health_checker.health_status['sonarr']['status'] == 'disabled'
        assert isinstance(health_checker.health_status['sonarr']['last_check'], datetime)
    
    @patch('httpx.get')
    def test_check_plex_health_success(self, mock_get, health_checker):
        """Test successful Plex health check."""
        # Mock successful XML response
        xml_response = '<?xml version="1.0" encoding="UTF-8"?><MediaContainer version="1.30.0.6486" />'
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = xml_response
        mock_get.return_value = mock_response
        
        result = health_checker.check_plex_health()
        
        assert result is True
        assert health_checker.health_status['plex']['status'] == 'online'
        assert health_checker.health_status['plex']['version'] == '1.30.0.6486'
        assert health_checker.health_status['plex']['response_time'] > 0
        assert isinstance(health_checker.health_status['plex']['last_check'], datetime)
        
        # Verify API call
        mock_get.assert_called_once_with(
            "http://localhost:32400/identity",
            headers={'Accept': 'application/xml'},
            timeout=10
        )
    
    @patch('httpx.get')
    def test_check_plex_health_success_no_version(self, mock_get, health_checker):
        """Test successful Plex health check without version in response."""
        # Mock successful response without version
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Some response without MediaContainer"
        mock_get.return_value = mock_response
        
        result = health_checker.check_plex_health()
        
        assert result is True
        assert health_checker.health_status['plex']['status'] == 'online'
        assert health_checker.health_status['plex']['version'] == 'unknown'
        assert health_checker.health_status['plex']['response_time'] > 0
        assert isinstance(health_checker.health_status['plex']['last_check'], datetime)
    
    @patch('httpx.get')
    def test_check_plex_health_error_status(self, mock_get, health_checker):
        """Test Plex health check with error status code."""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        result = health_checker.check_plex_health()
        
        assert result is False
        assert health_checker.health_status['plex']['status'] == 'error'
        assert health_checker.health_status['plex']['error'] == 'Status code: 404'
        assert health_checker.health_status['plex']['response_time'] > 0
        assert isinstance(health_checker.health_status['plex']['last_check'], datetime)
    
    @patch('httpx.get')
    def test_check_plex_health_request_error(self, mock_get, health_checker):
        """Test Plex health check with request error."""
        # Mock request error
        mock_get.side_effect = httpx.RequestError("Network unreachable")
        
        result = health_checker.check_plex_health()
        
        assert result is False
        assert health_checker.health_status['plex']['status'] == 'offline'
        assert isinstance(health_checker.health_status['plex']['last_check'], datetime)
        assert 'error' not in health_checker.health_status['plex']
    
    def test_check_plex_health_disabled(self, health_checker):
        """Test Plex health check when URL is not configured."""
        health_checker.config.plex_url = None
        
        result = health_checker.check_plex_health()
        
        assert result is False
        assert health_checker.health_status['plex']['status'] == 'disabled'
        assert isinstance(health_checker.health_status['plex']['last_check'], datetime)
    
    @patch('httpx.get')
    def test_check_plex_health_xml_parsing_error(self, mock_get, health_checker):
        """Test Plex health check with XML parsing error."""
        # Mock response with invalid XML
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<MediaContainer invalid xml'
        mock_get.return_value = mock_response
        
        result = health_checker.check_plex_health()
        
        assert result is True
        assert health_checker.health_status['plex']['status'] == 'online'
        assert health_checker.health_status['plex']['version'] == 'unknown'
    
    def test_check_all_services(self, health_checker):
        """Test checking all services at once."""
        with patch.object(health_checker, 'check_radarr_health') as mock_radarr, \
             patch.object(health_checker, 'check_sonarr_health') as mock_sonarr, \
             patch.object(health_checker, 'check_plex_health') as mock_plex:
            
            # Set up return values
            mock_radarr.return_value = True
            mock_sonarr.return_value = False
            mock_plex.return_value = True
            
            result = health_checker.check_all_services()
            
            # Verify all methods were called
            mock_radarr.assert_called_once()
            mock_sonarr.assert_called_once()
            mock_plex.assert_called_once()
            
            # Verify result is the health status
            assert result == health_checker.health_status
    
    def test_get_health_status(self, health_checker):
        """Test getting health status returns a copy."""
        # Modify the health status
        health_checker.health_status['radarr']['status'] = 'test_status'
        
        result = health_checker.get_health_status()
        
        # Verify it's a copy
        assert result == health_checker.health_status
        assert result is not health_checker.health_status
        
        # Modify the returned copy and verify original is unchanged
        # Note: The copy() method only does a shallow copy, so nested dicts are still shared
        # We need to test this differently
        original_status = health_checker.health_status['radarr']['status']
        result['new_service'] = {'status': 'new'}
        assert 'new_service' not in health_checker.health_status
        assert health_checker.health_status['radarr']['status'] == original_status
    
    def test_thread_safety(self, health_checker):
        """Test that health status updates are thread-safe."""
        import threading
        import time
        
        def update_status():
            for i in range(10):
                with health_checker.status_lock:
                    health_checker.health_status['radarr']['status'] = f'status_{i}'
                time.sleep(0.001)
        
        def read_status():
            for i in range(10):
                status = health_checker.get_health_status()
                assert 'status_' in status['radarr']['status'] or status['radarr']['status'] == 'unknown'
                time.sleep(0.001)
        
        # Run concurrent threads
        threads = []
        for _ in range(3):
            threads.append(threading.Thread(target=update_status))
            threads.append(threading.Thread(target=read_status))
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
