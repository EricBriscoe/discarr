"""
Configuration module for Discarr application.
Loads environment variables from .env file and provides application settings.
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Determine config directory
CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")

# Create config directory if it doesn't exist
os.makedirs(CONFIG_DIR, exist_ok=True)

# Check for .env file in the config directory first
config_env_path = os.path.join(CONFIG_DIR, ".env")
if os.path.isfile(config_env_path):
    load_dotenv(config_env_path)
else:
    # Fallback to regular .env in the project root
    load_dotenv()

# Discord settings
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DISCORD_CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID', 0))

# Radarr settings (movie collection manager)
RADARR_URL = os.getenv('RADARR_URL', 'http://localhost:7878')
RADARR_API_KEY = os.getenv('RADARR_API_KEY')

# Sonarr settings (TV series collection manager)
SONARR_URL = os.getenv('SONARR_URL', 'http://localhost:8989')
SONARR_API_KEY = os.getenv('SONARR_API_KEY')

# Plex settings (media server)
PLEX_URL = os.getenv('PLEX_URL', 'http://localhost:32400')

# General application settings
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 300))  # Default: check every 5 minutes
HEALTH_CHECK_INTERVAL = int(os.getenv('HEALTH_CHECK_INTERVAL', 60))  # Default: check health every minute
VERBOSE = os.getenv('VERBOSE', 'false').lower() == 'true'

# Create a logger
logger = logging.getLogger(__name__)

def log_config_status():
    """Log configuration status (excluding sensitive info)"""
    logger.info(f"Discord channel ID: {DISCORD_CHANNEL_ID}")
    logger.info(f"Using Radarr URL: {RADARR_URL}")
    logger.info(f"Using Sonarr URL: {SONARR_URL}")
    logger.info(f"Using Plex URL: {PLEX_URL}")
    logger.info(f"Check interval: {CHECK_INTERVAL} seconds")
    logger.info(f"Health check interval: {HEALTH_CHECK_INTERVAL} seconds")
    logger.info(f"Verbose mode: {VERBOSE}")
