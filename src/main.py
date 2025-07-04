"""
Main entry point for Discarr Discord bot.
Simplified and reorganized for better maintainability.
"""
import logging
import argparse
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from core.settings import settings
from discord.bot import DiscordBot


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Discarr Discord bot for Radarr and Sonarr")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    return parser.parse_args()


def configure_logging(verbose: bool = False):
    """Configure the logging system."""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def main():
    """Main function to start the bot."""
    # Parse command-line arguments
    args = parse_arguments()
    
    # Override verbose setting if --verbose flag is used
    if args.verbose:
        settings.verbose = True
    
    # Configure logging
    logger = configure_logging(settings.verbose)
    logger.info("Starting Discarr bot...")
    
    if args.verbose:
        logger.debug("Verbose mode enabled via command-line argument")
    
    # Log configuration details
    settings.log_config_status()
    
    try:
        # Initialize and start the Discord bot
        bot = DiscordBot(settings)
        bot.start()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error running Discarr bot: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
