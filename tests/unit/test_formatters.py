"""
Tests for the Discord UI formatters module.
"""
import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime, timezone
import discord

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from discord_bot.ui.formatters import (
    create_progress_bar,
    format_movie_section,
    format_tv_section,
    format_summary_message,
    format_loading_message,
    format_error_message,
    format_partial_loading_message,
    format_health_status_message
)


class TestCreateProgressBar:
    """Test progress bar creation."""
    
    def test_create_progress_bar_zero_percent(self):
        """Test progress bar with 0% progress."""
        result = create_progress_bar(0)
        assert "░░░░░░░░░░` 0.0%" in result
        assert "█" not in result
    
    def test_create_progress_bar_fifty_percent(self):
        """Test progress bar with 50% progress."""
        result = create_progress_bar(50)
        assert "█████░░░░░` 50.0%" in result
    
    def test_create_progress_bar_hundred_percent(self):
        """Test progress bar with 100% progress."""
        result = create_progress_bar(100)
        assert "██████████` 100.0%" in result
        assert "░" not in result
    
    def test_create_progress_bar_custom_length(self):
        """Test progress bar with custom length."""
        result = create_progress_bar(50, length=20)
        assert len(result.split('`')[1].split('`')[0]) == 20
        assert "50.0%" in result
    
    def test_create_progress_bar_over_hundred(self):
        """Test progress bar with over 100% progress (should cap at 100)."""
        result = create_progress_bar(150)
        assert "██████████` 100.0%" in result
    
    def test_create_progress_bar_negative(self):
        """Test progress bar with negative progress (should cap at 0)."""
        result = create_progress_bar(-10)
        assert "░░░░░░░░░░` 0.0%" in result
    
    def test_create_progress_bar_decimal_progress(self):
        """Test progress bar with decimal progress."""
        result = create_progress_bar(33.7)
        assert "33.7%" in result


class TestFormatMovieSection:
    """Test movie section formatting."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_pagination = Mock()
        self.mock_pagination.get_pagination_info.return_value = (1, 1)
        self.mock_pagination.get_page_indices.return_value = (0, 3)
    
    def test_format_movie_section_empty(self):
        """Test formatting with no movies."""
        fields, message = format_movie_section([], self.mock_pagination)
        assert fields == []
        assert message == "No movies in queue."
    
    @patch('discord_bot.ui.formatters.get_status_emoji')
    @patch('discord_bot.ui.formatters.truncate_title')
    def test_format_movie_section_single_movie(self, mock_truncate, mock_emoji):
        """Test formatting with a single movie."""
        mock_truncate.return_value = "Test Movie"
        mock_emoji.return_value = "🎬"
        
        movies = [{
            'title': 'Test Movie (2023)',
            'progress': 75.5,
            'status': 'downloading',
            'size': 4.2,
            'time_left': '2h 30m'
        }]
        
        fields, message = format_movie_section(movies, self.mock_pagination)
        
        assert message is None
        assert len(fields) == 3  # Title, Status & Size, ETA
        assert "🎬 Test Movie" in fields[0]['name']
        assert "75.5%" in fields[0]['value']
        assert "downloading" in fields[1]['value']
        assert "4.20 GB" in fields[1]['value']
        assert "2h 30m" in fields[2]['value']
    
    @patch('discord_bot.ui.formatters.get_status_emoji')
    @patch('discord_bot.ui.formatters.truncate_title')
    def test_format_movie_section_with_error(self, mock_truncate, mock_emoji):
        """Test formatting movie with error message."""
        mock_truncate.return_value = "Error Movie"
        mock_emoji.return_value = "⚠️"
        
        movies = [{
            'title': 'Error Movie',
            'progress': 0,
            'status': 'warning',
            'size': 1.5,
            'time_left': 'N/A',
            'errorMessage': 'Download failed: Connection timeout'
        }]
        
        fields, message = format_movie_section(movies, self.mock_pagination)
        
        assert message is None
        assert "warning: Connection timeout" in fields[1]['value']
    
    @patch('discord_bot.ui.formatters.get_status_emoji')
    @patch('discord_bot.ui.formatters.truncate_title')
    def test_format_movie_section_pagination(self, mock_truncate, mock_emoji):
        """Test formatting with pagination."""
        mock_truncate.return_value = "Movie"
        mock_emoji.return_value = "🎬"
        
        # Set up pagination to show items 3-6 (second page)
        self.mock_pagination.get_page_indices.return_value = (3, 6)
        
        movies = [
            {'title': f'Movie {i}', 'progress': 50, 'status': 'downloading', 'size': 2.0, 'time_left': '1h'}
            for i in range(10)
        ]
        
        fields, message = format_movie_section(movies, self.mock_pagination)
        
        # Should process movies 3, 4, 5 (indices 3-6, but only 3 movies per page)
        assert len(fields) == 9  # 3 movies × 3 fields each


class TestFormatTvSection:
    """Test TV section formatting."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_pagination = Mock()
        self.mock_pagination.get_pagination_info.return_value = (1, 1)
        self.mock_pagination.get_page_indices.return_value = (0, 3)
    
    def test_format_tv_section_empty(self):
        """Test formatting with no TV shows."""
        fields, message = format_tv_section([], self.mock_pagination)
        assert fields == []
        assert message == "No TV shows in queue."
    
    @patch('discord_bot.ui.formatters.get_status_emoji')
    @patch('discord_bot.ui.formatters.truncate_title')
    def test_format_tv_section_single_show(self, mock_truncate, mock_emoji):
        """Test formatting with a single TV show."""
        mock_truncate.return_value = "Test Series"
        mock_emoji.return_value = "📺"
        
        tv_shows = [{
            'series': 'Test Series',
            'season': 1,
            'episode_number': 5,
            'progress': 60.0,
            'status': 'downloading',
            'size': 1.8,
            'time_left': '45m'
        }]
        
        fields, message = format_tv_section(tv_shows, self.mock_pagination)
        
        assert message is None
        assert len(fields) == 3  # Title, Status & Size, Time Left
        assert "📺 Test Series S01E05" in fields[0]['name']
        assert "60.0%" in fields[0]['value']
        assert "downloading" in fields[1]['value']
        assert "1.80 GB" in fields[1]['value']
        assert "45m" in fields[2]['value']
    
    @patch('discord_bot.ui.formatters.get_status_emoji')
    @patch('discord_bot.ui.formatters.truncate_title')
    def test_format_tv_section_with_error(self, mock_truncate, mock_emoji):
        """Test formatting TV show with error message."""
        mock_truncate.return_value = "Error Series"
        mock_emoji.return_value = "⚠️"
        
        tv_shows = [{
            'series': 'Error Series',
            'season': 2,
            'episode_number': 10,
            'progress': 25,
            'status': 'warning',
            'size': 0.9,
            'time_left': 'N/A',
            'errorMessage': 'Quality: No files found'
        }]
        
        fields, message = format_tv_section(tv_shows, self.mock_pagination)
        
        assert message is None
        assert "warning: No files found" in fields[1]['value']


class TestFormatSummaryMessage:
    """Test complete summary message formatting."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_pagination = Mock()
        self.mock_pagination.update_page_limits = Mock()
        self.mock_pagination.get_pagination_info.side_effect = lambda is_movie: (1, 1)
    
    @patch('discord_bot.ui.formatters.format_movie_section')
    @patch('discord_bot.ui.formatters.format_tv_section')
    @patch('discord_bot.ui.formatters.calculate_elapsed_time')
    @patch('discord_bot.ui.formatters.format_elapsed_time')
    def test_format_summary_message_with_data(self, mock_format_elapsed, mock_calc_elapsed, 
                                            mock_format_tv, mock_format_movie):
        """Test formatting summary with movie and TV data."""
        # Setup mocks
        mock_format_movie.return_value = ([
            {"name": "Movie 1", "value": "Progress: 50%", "inline": False}
        ], None)
        mock_format_tv.return_value = ([
            {"name": "TV Show 1", "value": "Progress: 75%", "inline": False}
        ], None)
        mock_calc_elapsed.return_value = 300  # 5 minutes
        mock_format_elapsed.return_value = "Last updated 5 minutes ago"
        
        movies = [{'title': 'Test Movie'}]
        tv_shows = [{'series': 'Test Series'}]
        last_updated = datetime.now(timezone.utc)
        
        embed = format_summary_message(movies, tv_shows, self.mock_pagination, last_updated)
        
        # Verify embed properties
        assert isinstance(embed, discord.Embed)
        assert embed.title == "📊 Download Status"
        assert embed.color == discord.Color.blue()
        assert "Current download status" in embed.description
        
        # Verify pagination was updated
        self.mock_pagination.update_page_limits.assert_called_once_with(1, 1)
        
        # Verify footer
        assert embed.footer.text == "Last updated 5 minutes ago"
    
    @patch('discord_bot.ui.formatters.format_movie_section')
    @patch('discord_bot.ui.formatters.format_tv_section')
    @patch('discord_bot.ui.formatters.calculate_elapsed_time')
    @patch('discord_bot.ui.formatters.format_elapsed_time')
    def test_format_summary_message_empty_data(self, mock_format_elapsed, mock_calc_elapsed,
                                             mock_format_tv, mock_format_movie):
        """Test formatting summary with no data."""
        mock_format_movie.return_value = ([], "No movies in queue.")
        mock_format_tv.return_value = ([], "No TV shows in queue.")
        mock_calc_elapsed.return_value = 0
        mock_format_elapsed.return_value = "Just updated"
        
        embed = format_summary_message([], [], self.mock_pagination)
        
        assert isinstance(embed, discord.Embed)
        # Should still have movie and TV sections, but with empty messages
        movie_field = next((f for f in embed.fields if "Movies" in f.name), None)
        tv_field = next((f for f in embed.fields if "TV Shows" in f.name), None)
        
        assert movie_field is not None
        assert tv_field is not None


class TestFormatLoadingMessage:
    """Test loading message formatting."""
    
    def test_format_loading_message_basic(self):
        """Test basic loading message."""
        embed = format_loading_message()
        
        assert isinstance(embed, discord.Embed)
        assert embed.title == "📊 Download Status"
        assert embed.color == discord.Color.blue()
        assert "Loading download information" in embed.description
        
        # Check for movie and TV fields
        movie_field = next((f for f in embed.fields if "Movies" in f.name), None)
        tv_field = next((f for f in embed.fields if "TV Shows" in f.name), None)
        
        assert movie_field is not None
        assert tv_field is not None
        assert "Loading movie data" in movie_field.value
        assert "Loading TV show data" in tv_field.value
    
    def test_format_loading_message_stuck_warning(self):
        """Test loading message with stuck warning."""
        import time
        loading_start_time = time.time() - 150  # 2.5 minutes ago
        
        embed = format_loading_message(loading_start_time)
        
        assert embed.color == discord.Color.orange()
        movie_field = next((f for f in embed.fields if "Movies" in f.name), None)
        assert "taking longer than expected" in movie_field.value
        assert "API connectivity issues" in movie_field.value


class TestFormatErrorMessage:
    """Test error message formatting."""
    
    def test_format_error_message_both_errors(self):
        """Test error message with both Radarr and Sonarr errors."""
        embed = format_error_message("Radarr connection failed", "Sonarr timeout")
        
        assert isinstance(embed, discord.Embed)
        assert embed.title == "📊 Download Status"
        assert embed.color == discord.Color.red()
        assert "Error loading download information" in embed.description
        
        # Check error fields
        radarr_field = next((f for f in embed.fields if "Radarr" in f.name), None)
        sonarr_field = next((f for f in embed.fields if "Sonarr" in f.name), None)
        
        assert radarr_field is not None
        assert sonarr_field is not None
        assert "Radarr connection failed" in radarr_field.value
        assert "Sonarr timeout" in sonarr_field.value
    
    def test_format_error_message_radarr_only(self):
        """Test error message with only Radarr error."""
        embed = format_error_message(radarr_error="Radarr API error")
        
        radarr_field = next((f for f in embed.fields if "Radarr" in f.name), None)
        sonarr_field = next((f for f in embed.fields if "Sonarr" in f.name), None)
        
        assert "Radarr API error" in radarr_field.value
        assert "Connected" in sonarr_field.value
    
    def test_format_error_message_sonarr_only(self):
        """Test error message with only Sonarr error."""
        embed = format_error_message(sonarr_error="Sonarr network error")
        
        radarr_field = next((f for f in embed.fields if "Radarr" in f.name), None)
        sonarr_field = next((f for f in embed.fields if "Sonarr" in f.name), None)
        
        assert "Connected" in radarr_field.value
        assert "Sonarr network error" in sonarr_field.value
    
    def test_format_error_message_troubleshooting_section(self):
        """Test that troubleshooting section is included."""
        embed = format_error_message("Test error")
        
        troubleshooting_field = next((f for f in embed.fields if "Troubleshooting" in f.name), None)
        assert troubleshooting_field is not None
        assert "Check the health status" in troubleshooting_field.value
        assert "Verify your .env configuration" in troubleshooting_field.value


class TestFormatPartialLoadingMessage:
    """Test partial loading message formatting."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_pagination = Mock()
        self.mock_pagination.update_movie_page_limit = Mock()
        self.mock_pagination.update_tv_page_limit = Mock()
        self.mock_pagination.get_pagination_info.side_effect = lambda is_movie: (1, 1)
    
    @patch('discord_bot.ui.formatters.format_movie_section')
    @patch('discord_bot.ui.formatters.format_tv_section')
    @patch('discord_bot.ui.formatters.calculate_elapsed_time')
    @patch('discord_bot.ui.formatters.format_elapsed_time')
    def test_format_partial_loading_radarr_ready(self, mock_format_elapsed, mock_calc_elapsed,
                                                mock_format_tv, mock_format_movie):
        """Test partial loading with Radarr ready, Sonarr loading."""
        mock_format_movie.return_value = ([
            {"name": "Movie 1", "value": "Progress: 50%", "inline": False}
        ], None)
        mock_calc_elapsed.return_value = 60
        mock_format_elapsed.return_value = "1 minute ago"
        
        movies = [{'title': 'Test Movie'}]
        tv_shows = []
        
        embed = format_partial_loading_message(
            movies, tv_shows, self.mock_pagination, 
            radarr_ready=True, sonarr_ready=False
        )
        
        assert isinstance(embed, discord.Embed)
        
        # Verify movie pagination was updated
        self.mock_pagination.update_movie_page_limit.assert_called_once_with(1)
        
        # Check that movies show data but TV shows show loading
        movie_field = next((f for f in embed.fields if "Movies" in f.name), None)
        tv_field = next((f for f in embed.fields if "TV Shows" in f.name and "Loading" not in f.name), None)
        loading_tv_field = next((f for f in embed.fields if "TV Shows" in f.name and "Loading" not in f.name), None)
        
        # Should have movie data and TV loading message
        assert movie_field is not None
        # TV should show loading message
        tv_loading_field = next((f for f in embed.fields if "📺 TV Shows" == f.name), None)
        assert tv_loading_field is not None
        assert "Loading TV show data" in tv_loading_field.value
    
    @patch('discord_bot.ui.formatters.format_movie_section')
    @patch('discord_bot.ui.formatters.format_tv_section')
    @patch('discord_bot.ui.formatters.calculate_elapsed_time')
    @patch('discord_bot.ui.formatters.format_elapsed_time')
    def test_format_partial_loading_sonarr_ready(self, mock_format_elapsed, mock_calc_elapsed,
                                                mock_format_tv, mock_format_movie):
        """Test partial loading with Sonarr ready, Radarr loading."""
        mock_format_tv.return_value = ([
            {"name": "TV Show 1", "value": "Progress: 75%", "inline": False}
        ], None)
        mock_calc_elapsed.return_value = 30
        mock_format_elapsed.return_value = "30 seconds ago"
        
        movies = []
        tv_shows = [{'series': 'Test Series'}]
        
        embed = format_partial_loading_message(
            movies, tv_shows, self.mock_pagination,
            radarr_ready=False, sonarr_ready=True
        )
        
        # Verify TV pagination was updated
        self.mock_pagination.update_tv_page_limit.assert_called_once_with(1)
        
        # Movies should show loading, TV should show data
        movie_loading_field = next((f for f in embed.fields if "🎬 Movies" == f.name), None)
        assert movie_loading_field is not None
        assert "Loading movie data" in movie_loading_field.value


class TestFormatHealthStatusMessage:
    """Test health status message formatting."""
    
    @patch('discord_bot.ui.formatters.get_status_emoji')
    def test_format_health_status_all_online(self, mock_emoji):
        """Test health status with all services online."""
        mock_emoji.return_value = "✅"
        
        health_status = {
            'plex': {'status': 'online'},
            'radarr': {'status': 'online'},
            'sonarr': {'status': 'online'}
        }
        
        embed = format_health_status_message(health_status)
        
        assert isinstance(embed, discord.Embed)
        assert embed.title == "🏥 Service Health Status"
        assert embed.color == discord.Color.green()
        
        # Check all service fields
        plex_field = next((f for f in embed.fields if "Plex" in f.name), None)
        radarr_field = next((f for f in embed.fields if "Radarr" in f.name), None)
        sonarr_field = next((f for f in embed.fields if "Sonarr" in f.name), None)
        
        assert plex_field is not None
        assert radarr_field is not None
        assert sonarr_field is not None
        
        assert "online" in plex_field.value
        assert "online" in radarr_field.value
        assert "online" in sonarr_field.value
    
    @patch('discord_bot.ui.formatters.get_status_emoji')
    def test_format_health_status_with_offline_service(self, mock_emoji):
        """Test health status with one service offline."""
        mock_emoji.side_effect = lambda status: "❌" if status == "offline" else "✅"
        
        health_status = {
            'plex': {'status': 'online'},
            'radarr': {'status': 'offline'},
            'sonarr': {'status': 'online'}
        }
        
        embed = format_health_status_message(health_status)
        
        # Should be red due to offline service
        assert embed.color == discord.Color.red()
    
    @patch('discord_bot.ui.formatters.get_status_emoji')
    def test_format_health_status_with_error_service(self, mock_emoji):
        """Test health status with one service in error state."""
        mock_emoji.side_effect = lambda status: "⚠️" if status == "error" else "✅"
        
        health_status = {
            'plex': {'status': 'online'},
            'radarr': {'status': 'error'},
            'sonarr': {'status': 'online'}
        }
        
        embed = format_health_status_message(health_status)
        
        # Should be orange due to error service
        assert embed.color == discord.Color.orange()
    
    @patch('discord_bot.ui.formatters.get_status_emoji')
    def test_format_health_status_unknown_service(self, mock_emoji):
        """Test health status with unknown service status."""
        mock_emoji.return_value = "❓"
        
        health_status = {
            'plex': {'status': 'unknown'},
            'radarr': {'status': 'unknown'},
            'sonarr': {'status': 'unknown'}
        }
        
        embed = format_health_status_message(health_status)
        
        # Should be orange due to unknown status
        assert embed.color == discord.Color.orange()
    
    def test_format_health_status_missing_services(self):
        """Test health status with missing service data."""
        health_status = {}
        
        embed = format_health_status_message(health_status)
        
        # Should still create fields for all services with unknown status
        plex_field = next((f for f in embed.fields if "Plex" in f.name), None)
        radarr_field = next((f for f in embed.fields if "Radarr" in f.name), None)
        sonarr_field = next((f for f in embed.fields if "Sonarr" in f.name), None)
        
        assert plex_field is not None
        assert radarr_field is not None
        assert sonarr_field is not None
        
        assert "unknown" in plex_field.value
        assert "unknown" in radarr_field.value
        assert "unknown" in sonarr_field.value
