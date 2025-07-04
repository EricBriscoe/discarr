"""
Unit tests for discord utilities.
"""
import unittest
from unittest.mock import patch, Mock
import sys
from pathlib import Path
from datetime import datetime, timezone
import pytz

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from utils.discord_utils import (
    calculate_time_remaining,
    get_status_emoji,
    truncate_title,
    format_discord_timestamp
)


class TestDiscordUtils(unittest.TestCase):
    """Test cases for discord utility functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.sample_item = {
            "size": 1000000000,  # 1GB
            "sizeleft": 500000000,  # 500MB left
            "added": "2023-10-10T10:00:00Z"
        }

    @patch('utils.discord_utils.datetime')
    def test_calculate_time_remaining_normal_download(self, mock_datetime):
        """Test time calculation for normal download progress."""
        # Mock current time to be 1 hour after start
        mock_now = datetime(2023, 10, 10, 11, 0, 0, tzinfo=pytz.UTC)
        mock_datetime.now.return_value = mock_now
        mock_datetime.strptime.return_value = datetime(2023, 10, 10, 10, 0, 0)
        
        result = calculate_time_remaining(self.sample_item)
        
        # Should calculate based on download rate
        self.assertIsInstance(result, str)
        self.assertNotEqual(result, "unknown")

    def test_calculate_time_remaining_missing_data(self):
        """Test time calculation with missing required data."""
        # Test missing sizeleft
        item = {"size": 1000000000, "added": "2023-10-10T10:00:00Z"}
        result = calculate_time_remaining(item)
        self.assertEqual(result, "unknown")
        
        # Test missing size
        item = {"sizeleft": 500000000, "added": "2023-10-10T10:00:00Z"}
        result = calculate_time_remaining(item)
        self.assertEqual(result, "unknown")
        
        # Test zero size
        item = {"size": 0, "sizeleft": 0, "added": "2023-10-10T10:00:00Z"}
        result = calculate_time_remaining(item)
        self.assertEqual(result, "unknown")

    def test_calculate_time_remaining_missing_added_time(self):
        """Test time calculation with missing added time."""
        item = {"size": 1000000000, "sizeleft": 500000000}
        result = calculate_time_remaining(item)
        self.assertEqual(result, "unknown")

    def test_calculate_time_remaining_invalid_time_format(self):
        """Test time calculation with invalid time format."""
        item = {
            "size": 1000000000,
            "sizeleft": 500000000,
            "added": "invalid-time-format"
        }
        result = calculate_time_remaining(item)
        self.assertEqual(result, "unknown")

    @patch('utils.discord_utils.datetime')
    def test_calculate_time_remaining_no_progress(self, mock_datetime):
        """Test time calculation when no bytes downloaded."""
        mock_now = datetime(2023, 10, 10, 11, 0, 0, tzinfo=pytz.UTC)
        mock_datetime.now.return_value = mock_now
        mock_datetime.strptime.return_value = datetime(2023, 10, 10, 10, 0, 0)
        
        # No progress made
        item = {
            "size": 1000000000,
            "sizeleft": 1000000000,  # Same as size
            "added": "2023-10-10T10:00:00Z"
        }
        
        result = calculate_time_remaining(item)
        self.assertEqual(result, "unknown")

    @patch('utils.discord_utils.datetime')
    def test_calculate_time_remaining_fast_download(self, mock_datetime):
        """Test time calculation for very fast downloads."""
        mock_now = datetime(2023, 10, 10, 10, 0, 30, tzinfo=pytz.UTC)  # 30 seconds later
        mock_datetime.now.return_value = mock_now
        mock_datetime.strptime.return_value = datetime(2023, 10, 10, 10, 0, 0)
        
        # Almost complete download
        item = {
            "size": 1000000000,
            "sizeleft": 1000000,  # 1MB left
            "added": "2023-10-10T10:00:00Z"
        }
        
        result = calculate_time_remaining(item)
        self.assertEqual(result, "< 1 min")

    def test_get_status_emoji_known_statuses(self):
        """Test emoji mapping for known statuses."""
        test_cases = [
            ("downloading", "⬇️"),
            ("completed", "✅"),
            ("imported", "✅"),
            ("importing", "📤"),
            ("importpending", "📁⏳"),
            ("importblocked", "📁🔒"),
            ("failed", "❌"),
            ("failedpending", "⚠️❌"),
            ("ignored", "🔕"),
            ("warning", "⚠️"),
            ("online", "🟢"),
            ("offline", "🔴"),
            ("error", "🟠"),
            ("disabled", "⚫"),
            ("unknown", "❓"),
        ]
        
        for status, expected_emoji in test_cases:
            with self.subTest(status=status):
                result = get_status_emoji(status)
                self.assertEqual(result, expected_emoji)

    def test_get_status_emoji_case_insensitive(self):
        """Test that status emoji lookup is case insensitive."""
        test_cases = [
            ("DOWNLOADING", "⬇️"),
            ("Completed", "✅"),
            ("FAILED", "❌"),
            ("Warning", "⚠️"),
        ]
        
        for status, expected_emoji in test_cases:
            with self.subTest(status=status):
                result = get_status_emoji(status)
                self.assertEqual(result, expected_emoji)

    def test_get_status_emoji_unknown_status(self):
        """Test emoji for unknown status."""
        result = get_status_emoji("some_random_status")
        self.assertEqual(result, "🔄")

    def test_get_status_emoji_non_string_input(self):
        """Test emoji for non-string input."""
        test_cases = [None, 123, [], {}]
        
        for invalid_input in test_cases:
            with self.subTest(input=invalid_input):
                result = get_status_emoji(invalid_input)
                self.assertEqual(result, "❓")

    def test_truncate_title_short_title(self):
        """Test truncation of short titles."""
        title = "Short Movie"
        result = truncate_title(title)
        self.assertEqual(result, "Short Movie")

    def test_truncate_title_exact_length(self):
        """Test truncation of title at exact max length."""
        title = "A" * 50  # Exactly 50 characters
        result = truncate_title(title)
        self.assertEqual(result, title)

    def test_truncate_title_long_title(self):
        """Test truncation of long titles."""
        title = "A" * 60  # 60 characters
        result = truncate_title(title)
        self.assertEqual(result, "A" * 50 + "...")
        self.assertTrue(len(result) <= 53)  # 50 + "..."

    def test_truncate_title_with_year(self):
        """Test truncation that preserves year information."""
        title = "The Really Long Movie Title That Goes On Forever (2023) Extended Director's Cut"
        result = truncate_title(title)
        
        # Should truncate and end with "..."
        self.assertTrue(result.endswith("..."))
        # Length should be reasonable (the function may truncate after year if found)
        self.assertLessEqual(len(result), 60)  # Allow some flexibility

    def test_truncate_title_custom_max_length(self):
        """Test truncation with custom max length."""
        title = "A Long Movie Title"
        result = truncate_title(title, max_length=10)
        self.assertEqual(result, "A Long Mov...")

    def test_truncate_title_empty_or_none(self):
        """Test truncation of empty or None titles."""
        self.assertEqual(truncate_title(""), "Unknown")
        self.assertEqual(truncate_title(None), "Unknown")

    def test_format_discord_timestamp_valid_iso(self):
        """Test formatting valid ISO timestamp."""
        iso_time = "2023-10-10T15:30:45Z"
        result = format_discord_timestamp(iso_time)
        
        # Should return Discord timestamp format
        self.assertTrue(result.startswith("<t:"))
        self.assertTrue(result.endswith(":R>"))
        self.assertIn("1696951845", result)  # Unix timestamp for the given time

    def test_format_discord_timestamp_with_timezone(self):
        """Test formatting ISO timestamp with timezone."""
        iso_time = "2023-10-10T15:30:45+02:00"
        result = format_discord_timestamp(iso_time)
        
        self.assertTrue(result.startswith("<t:"))
        self.assertTrue(result.endswith(":R>"))

    def test_format_discord_timestamp_custom_format(self):
        """Test formatting with custom Discord format code."""
        iso_time = "2023-10-10T15:30:45Z"
        result = format_discord_timestamp(iso_time, format_code="F")
        
        self.assertTrue(result.startswith("<t:"))
        self.assertTrue(result.endswith(":F>"))

    def test_format_discord_timestamp_empty_input(self):
        """Test formatting empty timestamp."""
        result = format_discord_timestamp("")
        self.assertEqual(result, "∞")
        
        result = format_discord_timestamp(None)
        self.assertEqual(result, "∞")

    def test_format_discord_timestamp_invalid_format(self):
        """Test formatting invalid timestamp format."""
        invalid_times = [
            "not-a-timestamp",
            "2023-13-45T25:70:90Z",  # Invalid date/time
            "2023/10/10 15:30:45",   # Wrong format
        ]
        
        for invalid_time in invalid_times:
            with self.subTest(timestamp=invalid_time):
                result = format_discord_timestamp(invalid_time)
                self.assertEqual(result, "∞")

    def test_calculate_time_remaining_exception_handling(self):
        """Test that exceptions are handled gracefully in time calculation."""
        # Invalid item that will cause an exception
        invalid_item = {"invalid": "data"}
        
        result = calculate_time_remaining(invalid_item)
        
        self.assertEqual(result, "unknown")

    def test_format_discord_timestamp_exception_handling(self):
        """Test that exceptions are handled gracefully in timestamp formatting."""
        result = format_discord_timestamp("invalid-timestamp")
        
        self.assertEqual(result, "∞")


if __name__ == '__main__':
    unittest.main()
