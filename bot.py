"""
Main entry point for Discarr Discord bot.
Handles initialization and configuration of the bot components.
"""
import logging
from discord_client import DiscordClient
import config

def configure_logging():
    """Configure the logging system."""
    log_level = logging.DEBUG if config.VERBOSE else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def validate_config():
    """Validate critical configuration parameters."""
    logger = logging.getLogger(__name__)
    
    missing_config = []
    
    # Check required config values
    if not config.DISCORD_TOKEN:
        missing_config.append("DISCORD_TOKEN")
        
    if not config.DISCORD_CHANNEL_ID:
        missing_config.append("DISCORD_CHANNEL_ID")
    
    # Report all missing configs at once
    if missing_config:
        logger.error(f"Missing required configuration: {', '.join(missing_config)}")
        return False
        
    # Check optional configs with warnings
    if not config.RADARR_API_KEY and not config.SONARR_API_KEY:
        logger.warning("Both Radarr and Sonarr API keys are missing. Bot will not monitor any downloads.")
    elif not config.RADARR_API_KEY:
        logger.warning("Radarr API key is missing. Movie monitoring will be disabled.")
    elif not config.SONARR_API_KEY:
        logger.warning("Sonarr API key is missing. TV show monitoring will be disabled.")
        
    return True

def main():
    """Main function to start the bot."""
    # Configure logging
    logger = configure_logging()
    logger.info("Starting Discarr bot...")
    
    # Validate configuration
    if not validate_config():
        return 1
    
    # Log configuration details
    config.log_config_status()
    
    try:
        # Initialize and start the Discord client
        client = DiscordClient()
        client.start()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error running Discarr bot: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
