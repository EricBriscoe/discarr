"""
Unified configuration management for Discarr application.
Loads environment variables and provides validated application settings.
"""
import os
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class Settings:
    """Centralized configuration management with validation."""
    
    def __init__(self):
        """Initialize settings by loading environment variables."""
        self._load_environment()
        self._validate_required_settings()
        
    def _load_environment(self):
        """Load environment variables from .env files."""
        # Determine config directory
        self.config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config")
        
        # Create config directory if it doesn't exist
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Check for .env file in the config directory first
        config_env_path = os.path.join(self.config_dir, ".env")
        if os.path.isfile(config_env_path):
            load_dotenv(config_env_path)
        else:
            # Fallback to regular .env in the project root
            load_dotenv()
    
    def _validate_required_settings(self):
        """Validate that required settings are present."""
        missing_config = []
        
        # Check required config values
        if not self.discord_token:
            missing_config.append("DISCORD_TOKEN")
            
        if not self.discord_channel_id:
            missing_config.append("DISCORD_CHANNEL_ID")
        
        # Report all missing configs at once
        if missing_config:
            logger.error(f"Missing required configuration: {', '.join(missing_config)}")
            raise ValueError(f"Missing required configuration: {', '.join(missing_config)}")
            
        # Check optional configs with warnings
        if not self.radarr_api_key and not self.sonarr_api_key:
            logger.warning("Both Radarr and Sonarr API keys are missing. Bot will not monitor any downloads.")
        elif not self.radarr_api_key:
            logger.warning("Radarr API key is missing. Movie monitoring will be disabled.")
        elif not self.sonarr_api_key:
            logger.warning("Sonarr API key is missing. TV show monitoring will be disabled.")
    
    # Discord settings
    @property
    def discord_token(self) -> Optional[str]:
        """Discord bot token."""
        return os.getenv('DISCORD_TOKEN')
    
    @property
    def discord_channel_id(self) -> int:
        """Discord channel ID for posting updates."""
        return int(os.getenv('DISCORD_CHANNEL_ID', 0))
    
    # Radarr settings (movie collection manager)
    @property
    def radarr_url(self) -> str:
        """Radarr server URL."""
        return os.getenv('RADARR_URL', 'http://localhost:7878')
    
    @property
    def radarr_api_key(self) -> Optional[str]:
        """Radarr API key."""
        return os.getenv('RADARR_API_KEY')
    
    @property
    def radarr_enabled(self) -> bool:
        """Whether Radarr monitoring is enabled."""
        return bool(self.radarr_api_key)
    
    # Sonarr settings (TV series collection manager)
    @property
    def sonarr_url(self) -> str:
        """Sonarr server URL."""
        return os.getenv('SONARR_URL', 'http://localhost:8989')
    
    @property
    def sonarr_api_key(self) -> Optional[str]:
        """Sonarr API key."""
        return os.getenv('SONARR_API_KEY')
    
    @property
    def sonarr_enabled(self) -> bool:
        """Whether Sonarr monitoring is enabled."""
        return bool(self.sonarr_api_key)
    
    # Plex settings (media server)
    @property
    def plex_url(self) -> str:
        """Plex server URL."""
        return os.getenv('PLEX_URL', 'http://localhost:32400')
    
    # General application settings
    @property
    def check_interval(self) -> int:
        """Interval between download checks in seconds."""
        return int(os.getenv('CHECK_INTERVAL', 300))  # Default: 5 minutes
    
    @property
    def health_check_interval(self) -> int:
        """Interval between health checks in seconds."""
        return int(os.getenv('HEALTH_CHECK_INTERVAL', 60))  # Default: 1 minute
    
    @property
    def verbose(self) -> bool:
        """Whether verbose logging is enabled."""
        return os.getenv('VERBOSE', 'false').lower() == 'true'
    
    @verbose.setter
    def verbose(self, value: bool):
        """Set verbose logging mode."""
        os.environ['VERBOSE'] = 'true' if value else 'false'
    
    # Progress tracking settings for stuck download detection
    @property
    def stuck_threshold_minutes(self) -> int:
        """Minutes without progress before download is considered stuck."""
        return int(os.getenv('STUCK_THRESHOLD_MINUTES', 120))  # Default: 2 hours
    
    @property
    def min_progress_change(self) -> float:
        """Minimum percentage progress change required."""
        return float(os.getenv('MIN_PROGRESS_CHANGE', 1.0))  # Default: 1%
    
    @property
    def min_size_change(self) -> int:
        """Minimum bytes downloaded required."""
        return int(os.getenv('MIN_SIZE_CHANGE', 104857600))  # Default: 100MB
    
    @property
    def progress_history_hours(self) -> int:
        """Hours of progress history to keep."""
        return int(os.getenv('PROGRESS_HISTORY_HOURS', 4))  # Default: 4 hours
    
    @property
    def max_snapshots_per_download(self) -> int:
        """Maximum snapshots per download."""
        return int(os.getenv('MAX_SNAPSHOTS_PER_DOWNLOAD', 50))  # Default: 50 snapshots
    
    def log_config_status(self):
        """Log configuration status (excluding sensitive info)."""
        logger.info(f"Discord channel ID: {self.discord_channel_id}")
        logger.info(f"Using Radarr URL: {self.radarr_url} (enabled: {self.radarr_enabled})")
        logger.info(f"Using Sonarr URL: {self.sonarr_url} (enabled: {self.sonarr_enabled})")
        logger.info(f"Using Plex URL: {self.plex_url}")
        logger.info(f"Check interval: {self.check_interval} seconds")
        logger.info(f"Health check interval: {self.health_check_interval} seconds")
        logger.info(f"Verbose mode: {self.verbose}")
        logger.info(f"Stuck threshold: {self.stuck_threshold_minutes} minutes")


# Global settings instance
settings = Settings()
