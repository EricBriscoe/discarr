"""
Health check service for monitoring Plex, Radarr, and Sonarr.
"""
import logging
import httpx
import time
import asyncio
from datetime import datetime

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
        
    async def check_radarr_health(self, client: httpx.AsyncClient):
        """Check Radarr service health."""
        if not self.config.radarr_api_key:
            self.health_status['radarr']['status'] = 'disabled'
            self.health_status['radarr']['last_check'] = datetime.now()
            return
            
        try:
            start_time = time.time()
            url = f"{self.config.radarr_url}/api/v3/system/status"
            headers = {'X-Api-Key': self.config.radarr_api_key}
            
            response = await client.get(url, headers=headers, timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                self.health_status['radarr'] = {
                    'status': 'online',
                    'last_check': datetime.now(),
                    'response_time': round(response_time * 1000, 2),  # Convert to ms
                    'version': data.get('version', 'unknown')
                }
            else:
                self.health_status['radarr'] = {
                    'status': 'error',
                    'last_check': datetime.now(),
                    'response_time': round(response_time * 1000, 2),
                    'error': f"Status code: {response.status_code}"
                }
        except httpx.RequestError:
            self.health_status['radarr'] = {
                'status': 'offline',
                'last_check': datetime.now()
            }
            
    async def check_sonarr_health(self, client: httpx.AsyncClient):
        """Check Sonarr service health."""
        if not self.config.sonarr_api_key:
            self.health_status['sonarr']['status'] = 'disabled'
            self.health_status['sonarr']['last_check'] = datetime.now()
            return
            
        try:
            start_time = time.time()
            url = f"{self.config.sonarr_url}/api/v3/system/status"
            headers = {'X-Api-Key': self.config.sonarr_api_key}
            
            response = await client.get(url, headers=headers, timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                self.health_status['sonarr'] = {
                    'status': 'online',
                    'last_check': datetime.now(),
                    'response_time': round(response_time * 1000, 2),  # Convert to ms
                    'version': data.get('version', 'unknown')
                }
            else:
                self.health_status['sonarr'] = {
                    'status': 'error',
                    'last_check': datetime.now(),
                    'response_time': round(response_time * 1000, 2),
                    'error': f"Status code: {response.status_code}"
                }
        except httpx.RequestError:
            self.health_status['sonarr'] = {
                'status': 'offline',
                'last_check': datetime.now()
            }
    
    async def check_plex_health(self, client: httpx.AsyncClient):
        """Check Plex service health using the identity endpoint without authentication."""
        if not self.config.plex_url:
            self.health_status['plex']['status'] = 'disabled'
            self.health_status['plex']['last_check'] = datetime.now()
            return
            
        try:
            start_time = time.time()
            url = f"{self.config.plex_url}/identity"
            
            headers = {'Accept': 'application/xml'}
                
            response = await client.get(url, headers=headers, timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                version = 'unknown'
                try:
                    if 'MediaContainer' in response.text:
                        import xml.etree.ElementTree as ET
                        root = ET.fromstring(response.text)
                        if 'version' in root.attrib:
                            version = root.attrib['version']
                except Exception:
                    pass
                        
                self.health_status['plex'] = {
                    'status': 'online',
                    'last_check': datetime.now(),
                    'response_time': round(response_time * 1000, 2),
                    'version': version
                }
            else:
                self.health_status['plex'] = {
                    'status': 'error',
                    'last_check': datetime.now(),
                    'response_time': round(response_time * 1000, 2),
                    'error': f"Status code: {response.status_code}"
                }
        except httpx.RequestError:
            self.health_status['plex'] = {
                'status': 'offline',
                'last_check': datetime.now()
            }
    
    async def check_all_services(self):
        """Check health of all configured services asynchronously."""
        async with httpx.AsyncClient() as client:
            await asyncio.gather(
                self.check_radarr_health(client),
                self.check_sonarr_health(client),
                self.check_plex_health(client)
            )
        return self.get_health_status()
    
    def get_health_status(self):
        """Get the current health status of all services."""
        return self.health_status.copy()
