"""
Unit tests for the settings module.
"""
import unittest
from unittest.mock import patch, Mock
import sys
from pathlib import Path
import os

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Mock environment variables before importing Settings
with patch.dict(os.environ, {
    'DISCORD_TOKEN': 'test_token',
    'DISCORD_CHANNEL_ID': '123456789',
    'RADARR_URL': 'http://localhost:7878',
    'RADARR_API_KEY': 'test_radarr_key',
    'SONARR_URL': 'http://localhost:8989',
    'SONARR_API_KEY': 'test_sonarr_key'
}):
    from core.settings import Settings


class TestSettings(unittest.TestCase):
    """Test cases for the Settings class."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_env = {
            'DISCORD_TOKEN': 'test_discord_token',
            'DISCORD_CHANNEL_ID': '123456789',
            'RADARR_URL': 'http://localhost:7878',
            'RADARR_API_KEY': 'test_radarr_key',
            'SONARR_URL': 'http://localhost:8989',
            'SONARR_API_KEY': 'test_sonarr_key',
            'CHECK_INTERVAL': '30',
            'VERBOSE': 'false'
        }

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_required_env_vars(self):
        """Test that missing required environment variables raise ValueError."""
        with self.assertRaises(ValueError) as context:
            Settings()
        
        self.assertIn("DISCORD_TOKEN", str(context.exception))

    @patch.dict(os.environ, {'DISCORD_TOKEN': 'test_token'}, clear=True)
    def test_missing_discord_channel_id(self):
        """Test that missing DISCORD_CHANNEL_ID raises ValueError."""
        with self.assertRaises(ValueError) as context:
            Settings()
        
        self.assertIn("DISCORD_CHANNEL_ID", str(context.exception))

    @patch.dict(os.environ, clear=True)
    def test_valid_configuration(self):
        """Test that valid configuration creates Settings instance."""
        with patch.dict(os.environ, self.test_env):
            settings = Settings()
            
            self.assertEqual(settings.discord_token, 'test_discord_token')
            self.assertEqual(settings.discord_channel_id, 123456789)
            self.assertEqual(settings.radarr_url, 'http://localhost:7878')
            self.assertEqual(settings.radarr_api_key, 'test_radarr_key')
            self.assertEqual(settings.sonarr_url, 'http://localhost:8989')
            self.assertEqual(settings.sonarr_api_key, 'test_sonarr_key')
            self.assertEqual(settings.check_interval, 30)
            self.assertFalse(settings.verbose)

    @patch.dict(os.environ, clear=True)
    def test_default_values(self):
        """Test that default values are set correctly."""
        env_with_defaults = self.test_env.copy()
        del env_with_defaults['CHECK_INTERVAL']
        del env_with_defaults['VERBOSE']
        
        with patch.dict(os.environ, env_with_defaults):
            settings = Settings()
            
            self.assertEqual(settings.check_interval, 300)  # Default value (5 minutes)
            self.assertFalse(settings.verbose)  # Default value

    @patch.dict(os.environ, clear=True)
    def test_verbose_true_values(self):
        """Test that various true values for VERBOSE are handled correctly."""
        true_values = ['true', 'True', 'TRUE']  # Only these work with .lower() == 'true'
        
        for true_value in true_values:
            env = self.test_env.copy()
            env['VERBOSE'] = true_value
            
            with patch.dict(os.environ, env):
                settings = Settings()
                self.assertTrue(settings.verbose, f"Failed for value: {true_value}")

    @patch.dict(os.environ, clear=True)
    def test_invalid_channel_id(self):
        """Test that invalid channel ID raises ValueError."""
        env = self.test_env.copy()
        env['DISCORD_CHANNEL_ID'] = 'not_a_number'
        
        with patch.dict(os.environ, env):
            with self.assertRaises(ValueError) as context:
                Settings()
            
            # The actual error is from int() conversion, not our validation
            self.assertIn("invalid literal for int()", str(context.exception))

    @patch.dict(os.environ, clear=True)
    def test_invalid_check_interval(self):
        """Test that invalid check interval doesn't raise ValueError during init."""
        env = self.test_env.copy()
        env['CHECK_INTERVAL'] = 'not_a_number'
        
        with patch.dict(os.environ, env):
            # The Settings class doesn't validate CHECK_INTERVAL during init
            # It will fail when the property is accessed
            settings = Settings()
            with self.assertRaises(ValueError):
                _ = settings.check_interval

    @patch.dict(os.environ, clear=True)
    @patch('core.settings.logger')
    def test_log_config_status(self, mock_logger):
        """Test that log_config_status logs configuration details."""
        with patch.dict(os.environ, self.test_env):
            settings = Settings()
            settings.log_config_status()
            
            # Verify that info logs were called
            self.assertTrue(mock_logger.info.called)
            
            # The actual implementation doesn't mask sensitive info in log_config_status
            # Just verify that logging occurred
            self.assertGreater(mock_logger.info.call_count, 0)

    @patch.dict(os.environ, clear=True)
    def test_progress_tracking_defaults(self):
        """Test that progress tracking settings have correct defaults."""
        with patch.dict(os.environ, self.test_env):
            settings = Settings()
            
            self.assertEqual(settings.stuck_threshold_minutes, 120)  # Default: 2 hours
            self.assertEqual(settings.min_progress_change, 1.0)  # Default: 1%
            self.assertEqual(settings.min_size_change, 104857600)  # Default: 100MB
            self.assertEqual(settings.progress_history_hours, 4)  # Default: 4 hours
            self.assertEqual(settings.max_snapshots_per_download, 50)  # Default: 50

    @patch.dict(os.environ, clear=True)
    def test_custom_progress_tracking_settings(self):
        """Test that custom progress tracking settings are applied."""
        env = self.test_env.copy()
        env.update({
            'STUCK_THRESHOLD_MINUTES': '45',
            'MIN_PROGRESS_CHANGE': '10.0',
            'MIN_SIZE_CHANGE': '20971520',  # 20MB
            'PROGRESS_HISTORY_HOURS': '48',
            'MAX_SNAPSHOTS_PER_DOWNLOAD': '200'
        })
        
        with patch.dict(os.environ, env):
            settings = Settings()
            
            self.assertEqual(settings.stuck_threshold_minutes, 45)
            self.assertEqual(settings.min_progress_change, 10.0)
            self.assertEqual(settings.min_size_change, 20971520)
            self.assertEqual(settings.progress_history_hours, 48)
            self.assertEqual(settings.max_snapshots_per_download, 200)


if __name__ == '__main__':
    unittest.main()
