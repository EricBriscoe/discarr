"""
Tests for the main entry point module.
"""
import pytest
import sys
import logging
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Mock settings before importing main to avoid environment variable requirements
with patch.dict('os.environ', {
    'DISCORD_TOKEN': 'test_token',
    'DISCORD_CHANNEL_ID': '123456789',
    'RADARR_URL': 'http://test:7878',
    'RADARR_API_KEY': 'test_key',
    'SONARR_URL': 'http://test:8989',
    'SONARR_API_KEY': 'test_key'
}):
    from main import parse_arguments, configure_logging, main


class TestParseArguments:
    """Test command-line argument parsing."""
    
    def test_parse_arguments_no_flags(self):
        """Test parsing with no command-line flags."""
        with patch('sys.argv', ['main.py']):
            args = parse_arguments()
            assert args.verbose is False
    
    def test_parse_arguments_verbose_flag(self):
        """Test parsing with verbose flag."""
        with patch('sys.argv', ['main.py', '--verbose']):
            args = parse_arguments()
            assert args.verbose is True


class TestConfigureLogging:
    """Test logging configuration."""
    
    def test_configure_logging_default(self):
        """Test default logging configuration."""
        with patch('logging.basicConfig') as mock_config:
            logger = configure_logging()
            
            mock_config.assert_called_once_with(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            assert logger.name == 'main'
    
    def test_configure_logging_verbose(self):
        """Test verbose logging configuration."""
        with patch('logging.basicConfig') as mock_config:
            logger = configure_logging(verbose=True)
            
            mock_config.assert_called_once_with(
                level=logging.DEBUG,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            assert logger.name == 'main'


class TestMain:
    """Test the main function."""
    
    @patch('main.DiscordBot')
    @patch('main.settings')
    @patch('main.configure_logging')
    @patch('main.parse_arguments')
    def test_main_success(self, mock_parse_args, mock_configure_logging, mock_settings, mock_discord_bot):
        """Test successful main execution."""
        # Setup mocks
        mock_args = Mock()
        mock_args.verbose = False
        mock_parse_args.return_value = mock_args
        
        mock_logger = Mock()
        mock_configure_logging.return_value = mock_logger
        
        mock_settings.verbose = False
        mock_settings.log_config_status = Mock()
        
        mock_bot_instance = Mock()
        mock_discord_bot.return_value = mock_bot_instance
        
        # Execute main
        result = main()
        
        # Verify calls
        mock_parse_args.assert_called_once()
        mock_configure_logging.assert_called_once_with(False)
        mock_logger.info.assert_called_with("Starting Discarr bot...")
        mock_settings.log_config_status.assert_called_once()
        mock_discord_bot.assert_called_once_with(mock_settings)
        mock_bot_instance.start.assert_called_once()
        
        assert result == 0
    
    @patch('main.DiscordBot')
    @patch('main.settings')
    @patch('main.configure_logging')
    @patch('main.parse_arguments')
    def test_main_with_verbose_flag(self, mock_parse_args, mock_configure_logging, mock_settings, mock_discord_bot):
        """Test main execution with verbose flag."""
        # Setup mocks
        mock_args = Mock()
        mock_args.verbose = True
        mock_parse_args.return_value = mock_args
        
        mock_logger = Mock()
        mock_configure_logging.return_value = mock_logger
        
        mock_settings.verbose = False  # Initially false
        mock_settings.log_config_status = Mock()
        
        mock_bot_instance = Mock()
        mock_discord_bot.return_value = mock_bot_instance
        
        # Execute main
        result = main()
        
        # Verify verbose was set to True
        assert mock_settings.verbose is True
        mock_logger.debug.assert_called_with("Verbose mode enabled via command-line argument")
        
        assert result == 0
    
    @patch('main.DiscordBot')
    @patch('main.settings')
    @patch('main.configure_logging')
    @patch('main.parse_arguments')
    def test_main_keyboard_interrupt(self, mock_parse_args, mock_configure_logging, mock_settings, mock_discord_bot):
        """Test main execution with keyboard interrupt."""
        # Setup mocks
        mock_args = Mock()
        mock_args.verbose = False
        mock_parse_args.return_value = mock_args
        
        mock_logger = Mock()
        mock_configure_logging.return_value = mock_logger
        
        mock_settings.verbose = False
        mock_settings.log_config_status = Mock()
        
        mock_bot_instance = Mock()
        mock_bot_instance.start.side_effect = KeyboardInterrupt()
        mock_discord_bot.return_value = mock_bot_instance
        
        # Execute main
        result = main()
        
        # Verify keyboard interrupt handling
        mock_logger.info.assert_any_call("Bot stopped by user")
        assert result == 0
    
    @patch('main.DiscordBot')
    @patch('main.settings')
    @patch('main.configure_logging')
    @patch('main.parse_arguments')
    def test_main_exception(self, mock_parse_args, mock_configure_logging, mock_settings, mock_discord_bot):
        """Test main execution with exception."""
        # Setup mocks
        mock_args = Mock()
        mock_args.verbose = False
        mock_parse_args.return_value = mock_args
        
        mock_logger = Mock()
        mock_configure_logging.return_value = mock_logger
        
        mock_settings.verbose = False
        mock_settings.log_config_status = Mock()
        
        mock_bot_instance = Mock()
        test_error = Exception("Test error")
        mock_bot_instance.start.side_effect = test_error
        mock_discord_bot.return_value = mock_bot_instance
        
        # Execute main
        result = main()
        
        # Verify exception handling
        mock_logger.error.assert_called_with("Error running Discarr bot: Test error", exc_info=True)
        assert result == 1
    
    @patch('main.DiscordBot')
    @patch('main.settings')
    @patch('main.configure_logging')
    @patch('main.parse_arguments')
    def test_main_with_verbose_setting_already_true(self, mock_parse_args, mock_configure_logging, mock_settings, mock_discord_bot):
        """Test main execution when verbose setting is already True."""
        # Setup mocks
        mock_args = Mock()
        mock_args.verbose = False
        mock_parse_args.return_value = mock_args
        
        mock_logger = Mock()
        mock_configure_logging.return_value = mock_logger
        
        mock_settings.verbose = True  # Already true
        mock_settings.log_config_status = Mock()
        
        mock_bot_instance = Mock()
        mock_discord_bot.return_value = mock_bot_instance
        
        # Execute main
        result = main()
        
        # Verify verbose stays True and configure_logging is called with True
        assert mock_settings.verbose is True
        mock_configure_logging.assert_called_once_with(True)
        
        assert result == 0


class TestMainEntryPoint:
    """Test the main entry point when run as script."""
    
    @patch('main.main')
    @patch('builtins.exit')
    def test_main_entry_point(self, mock_exit, mock_main):
        """Test the main entry point execution."""
        mock_main.return_value = 0
        
        # Simulate running as main module
        with patch('__main__.__name__', '__main__'):
            # Import and execute the main block
            exec("""
if __name__ == "__main__":
    exit(main())
""", {'__name__': '__main__', 'exit': mock_exit, 'main': mock_main})
        
        mock_main.assert_called_once()
        mock_exit.assert_called_once_with(0)
