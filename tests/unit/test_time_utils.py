"""
Unit tests for the time utilities module.
"""
import unittest
from unittest.mock import patch
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from utils.time_utils import format_discord_timestamp, format_timedelta, parse_time_string, calculate_time_remaining, calculate_elapsed_time, format_elapsed_time


class TestTimeUtils(unittest.TestCase):
    """Test cases for time utility functions."""

    def test_format_discord_timestamp_with_datetime_string(self):
        """Test formatting a datetime string to Discord timestamp."""
        # Test with ISO format datetime string
        datetime_str = "2024-01-15T14:30:00Z"
        result = format_discord_timestamp(datetime_str)
        
        # Should return a Discord relative timestamp format
        self.assertIsInstance(result, str)
        self.assertTrue(result.startswith('<t:'))
        self.assertTrue(result.endswith(':R>'))


    def test_format_discord_timestamp_with_invalid_input(self):
        """Test that invalid input returns the original value."""
        invalid_inputs = [None, "", "invalid_date", 12345]
        
        for invalid_input in invalid_inputs:
            result = format_discord_timestamp(invalid_input)
            self.assertEqual(result, invalid_input)

    def test_parse_time_string_hours_minutes_seconds(self):
        """Test parsing time string with hours, minutes, and seconds."""
        test_cases = [
            ("2:30:45", timedelta(hours=2, minutes=30, seconds=45)),
            ("1:00:00", timedelta(hours=1)),
            ("0:30:00", timedelta(minutes=30)),
            ("0:00:30", timedelta(seconds=30)),
            ("10:05:15", timedelta(hours=10, minutes=5, seconds=15)),
        ]
        
        for time_str, expected in test_cases:
            with self.subTest(time_str=time_str):
                result = parse_time_string(time_str)
                self.assertEqual(result, expected)

    def test_parse_time_string_minutes_seconds(self):
        """Test parsing time string with minutes and seconds only."""
        test_cases = [
            ("30:45", timedelta(minutes=30, seconds=45)),
            ("5:00", timedelta(minutes=5)),
            ("0:30", timedelta(seconds=30)),
            ("59:59", timedelta(minutes=59, seconds=59)),
        ]
        
        for time_str, expected in test_cases:
            with self.subTest(time_str=time_str):
                result = parse_time_string(time_str)
                self.assertEqual(result, expected)

    def test_parse_time_string_invalid_format(self):
        """Test that invalid time string format returns None."""
        invalid_inputs = [
            "invalid",
            "1",        # Single number
            "",         # Empty string
            None,       # None input
        ]
        
        for invalid_input in invalid_inputs:
            with self.subTest(invalid_input=invalid_input):
                result = parse_time_string(invalid_input)
                self.assertIsNone(result)

    def test_parse_time_string_edge_cases(self):
        """Test edge cases and how they're actually handled."""
        # Test cases showing actual behavior
        edge_cases = [
            ("1:2:3:4", None),  # Too many parts - returns None
            ("1:60:00", timedelta(hours=2)),  # 60 minutes = 1 hour, so 1+1=2 hours
            ("1:30:60", timedelta(hours=1, minutes=31)),  # 60 seconds = 1 minute, so 30+1=31 minutes
        ]
        
        for time_str, expected in edge_cases:
            with self.subTest(time_str=time_str):
                result = parse_time_string(time_str)
                if expected is None:
                    self.assertIsNone(result)
                else:
                    self.assertEqual(result, expected)

    def test_format_timedelta_seconds(self):
        """Test formatting timedelta in seconds."""
        test_cases = [
            (timedelta(seconds=30), "30s"),
            (timedelta(seconds=59), "59s"),
            (timedelta(seconds=0), "0s"),
        ]
        
        for td, expected in test_cases:
            with self.subTest(td=td):
                result = format_timedelta(td)
                self.assertEqual(result, expected)

    def test_format_timedelta_minutes(self):
        """Test formatting timedelta in minutes."""
        test_cases = [
            (timedelta(minutes=1), "1m"),
            (timedelta(minutes=30), "30m"),
            (timedelta(minutes=59), "59m"),
        ]
        
        for td, expected in test_cases:
            with self.subTest(td=td):
                result = format_timedelta(td)
                self.assertEqual(result, expected)

    def test_format_timedelta_hours(self):
        """Test formatting timedelta in hours."""
        test_cases = [
            (timedelta(hours=1), "1h"),
            (timedelta(hours=2, minutes=30), "2h 30m"),
            (timedelta(hours=23), "23h"),
        ]
        
        for td, expected in test_cases:
            with self.subTest(td=td):
                result = format_timedelta(td)
                self.assertEqual(result, expected)

    def test_format_timedelta_days(self):
        """Test formatting timedelta in days."""
        test_cases = [
            (timedelta(days=1), "1d"),
            (timedelta(days=2, hours=5), "2d 5h"),
            (timedelta(days=7), "7d"),
        ]
        
        for td, expected in test_cases:
            with self.subTest(td=td):
                result = format_timedelta(td)
                self.assertEqual(result, expected)

    def test_calculate_time_remaining_with_estimated_completion(self):
        """Test calculating time remaining with estimated completion time."""
        item = {
            "estimatedCompletionTime": "2024-01-15T14:30:00Z"
        }
        
        result = calculate_time_remaining(item)
        
        self.assertIsInstance(result, str)
        self.assertTrue(result.startswith('<t:'))

    def test_calculate_time_remaining_with_timeleft(self):
        """Test calculating time remaining with timeleft field."""
        item = {
            "timeleft": "2h 30m"
        }
        
        result = calculate_time_remaining(item)
        
        self.assertEqual(result, "2h 30m")

    def test_calculate_time_remaining_with_rate_calculation(self):
        """Test calculating time remaining from size and download rate."""
        item = {
            "size": 1000000000,  # 1GB
            "sizeleft": 500000000,  # 500MB remaining
            "downloadRate": 1000000  # 1MB/s
        }
        
        result = calculate_time_remaining(item)
        
        self.assertIsInstance(result, str)
        # Should be around 500 seconds = 8m 20s
        self.assertIn("m", result)

    def test_calculate_time_remaining_no_data(self):
        """Test calculating time remaining with no useful data."""
        item = {}
        
        result = calculate_time_remaining(item)
        
        self.assertIsNone(result)

    @patch('utils.time_utils.datetime')
    def test_format_discord_timestamp_timezone_handling(self, mock_datetime):
        """Test that timezone handling works correctly."""
        # Mock current time
        mock_now = datetime(2024, 1, 15, 12, 0, 0)
        mock_datetime.now.return_value = mock_now
        mock_datetime.fromisoformat.side_effect = datetime.fromisoformat
        
        # Test with timezone-aware string
        datetime_str = "2024-01-15T14:30:00+02:00"
        result = format_discord_timestamp(datetime_str)
        
        self.assertIsInstance(result, str)
        self.assertTrue(result.startswith('<t:'))
        self.assertTrue(result.endswith(':R>'))


if __name__ == '__main__':
    unittest.main()
