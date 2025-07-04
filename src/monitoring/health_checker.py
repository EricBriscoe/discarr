"""
Health check service for monitoring Plex, Radarr, and Sonarr.
"""
import logging
import httpx
import time
from datetime import datetime
from threading import Lock

logger = logging.getLogger(__name__)

class HealthChecker:
    """Checks and reports on the health status of media services."""
    
    def __init__(self, config):
        """Initialize the health checker with configuration."""
        self.config = config
        self.health_status = {
            'radarr': {'status': 'unknown', 'last_check': None, 'response_time': 0},
            'sonarr': {'status': 'unknown', 'last_check': None, 'response_time': 0},
            'plex': {'status': 'unknown', 'last_check': None, 'response_time': 0}
        }
        self.status_lock = Lock()
        
    def check_radarr_health(self):
        """Check Radarr service health."""
        if not self.config.radarr_api_key:
            with self.status_lock:
                self.health_status['radarr']['status'] = 'disabled'
                self.health_status['radarr']['last_check'] = datetime.now()
            return False
            
        try:
            start_time = time.time()
            url = f"{self.config.radarr_url}/api/v3/system/status"
            headers = {'X-Api-Key': self.config.radarr_api_key}
            
            response = httpx.get(url, headers=headers, timeout=10)
            response_time = time.time() - start_time
            
            with self.status_lock:
                if response.status_code == 200:
                    data = response.json()
                    self.health_status['radarr'] = {
                        'status': 'online',
                        'last_check': datetime.now(),
                        'response_time': round(response_time * 1000, 2),  # Convert to ms
                        'version': data.get('version', 'unknown')
                    }
                    return True
                else:
                    self.health_status['radarr'] = {
                        'status': 'error',
                        'last_check': datetime.now(),
                        'response_time': round(response_time * 1000, 2),
                        'error': f"Status code: {response.status_code}"
                    }
                    return False
        except httpx.RequestError:
            with self.status_lock:
                self.health_status['radarr'] = {
                    'status': 'offline',
                    'last_check': datetime.now()
                    # No error details included for offline status
                }
            return False
            
    def check_sonarr_health(self):
        """Check Sonarr service health."""
        if not self.config.sonarr_api_key:
            with self.status_lock:
                self.health_status['sonarr']['status'] = 'disabled'
                self.health_status['sonarr']['last_check'] = datetime.now()
            return False
            
        try:
            start_time = time.time()
            url = f"{self.config.sonarr_url}/api/v3/system/status"
            headers = {'X-Api-Key': self.config.sonarr_api_key}
            
            response = httpx.get(url, headers=headers, timeout=10)
            response_time = time.time() - start_time
            
            with self.status_lock:
                if response.status_code == 200:
                    data = response.json()
                    self.health_status['sonarr'] = {
                        'status': 'online',
                        'last_check': datetime.now(),
                        'response_time': round(response_time * 1000, 2),  # Convert to ms
                        'version': data.get('version', 'unknown')
                    }
                    return True
                else:
                    self.health_status['sonarr'] = {
                        'status': 'error',
                        'last_check': datetime.now(),
                        'response_time': round(response_time * 1000, 2),
                        'error': f"Status code: {response.status_code}"
                    }
                    return False
        except httpx.RequestError:
            with self.status_lock:
                self.health_status['sonarr'] = {
                    'status': 'offline',
                    'last_check': datetime.now()
                    # No error details included for offline status
                }
            return False
    
    def check_plex_health(self):
        """Check Plex service health using the identity endpoint without authentication."""
        if not self.config.plex_url:
            with self.status_lock:
                self.health_status['plex']['status'] = 'disabled'
                self.health_status['plex']['last_check'] = datetime.now()
            return False
            
        try:
            start_time = time.time()
            url = f"{self.config.plex_url}/identity"
            
            # No auth headers needed for identity endpoint
            headers = {'Accept': 'application/xml'}
                
            response = httpx.get(url, headers=headers, timeout=10)
            response_time = time.time() - start_time
            
            with self.status_lock:
                if response.status_code == 200:
                    # Try to extract version from response
                    version = 'unknown'
                    try:
                        if 'MediaContainer' in response.text:
                            # Likely XML response
                            import xml.etree.ElementTree as ET
                            root = ET.fromstring(response.text)
                            if 'version' in root.attrib:
                                version = root.attrib['version']
                    except Exception:
                        pass  # Keep unknown version if parsing fails
                        
                    self.health_status['plex'] = {
                        'status': 'online',
                        'last_check': datetime.now(),
                        'response_time': round(response_time * 1000, 2),
                        'version': version
                    }
                    return True
                else:
                    self.health_status['plex'] = {
                        'status': 'error',
                        'last_check': datetime.now(),
                        'response_time': round(response_time * 1000, 2),
                        'error': f"Status code: {response.status_code}"
                    }
                    return False
        except httpx.RequestError:
            with self.status_lock:
                self.health_status['plex'] = {
                    'status': 'offline',
                    'last_check': datetime.now()
                    # No error details included for offline status
                }
            return False
    
    def check_all_services(self):
        """Check health of all configured services."""
        self.check_radarr_health()
        self.check_sonarr_health()
        self.check_plex_health()
        return self.get_health_status()
    
    def get_health_status(self):
        """Get the current health status of all services."""
        with self.status_lock:
            return self.health_status.copy()
