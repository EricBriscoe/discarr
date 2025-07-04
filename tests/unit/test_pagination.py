"""
Tests for the pagination management module.
"""
import pytest
import sys
from unittest.mock import Mock, patch
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from discord_bot.ui.pagination import (
    PaginationManager,
    FIRST_PAGE_ID,
    PREV_PAGE_ID,
    NEXT_PAGE_ID,
    LAST_PAGE_ID,
    FIRST_PAGE_LABEL,
    PREV_PAGE_LABEL,
    NEXT_PAGE_LABEL,
    LAST_PAGE_LABEL,
    BUTTON_CONTROLS
)


class TestPaginationConstants:
    """Test pagination constants."""
    
    def test_button_ids(self):
        """Test button ID constants."""
        assert FIRST_PAGE_ID == "pagination_first"
        assert PREV_PAGE_ID == "pagination_prev"
        assert NEXT_PAGE_ID == "pagination_next"
        assert LAST_PAGE_ID == "pagination_last"
    
    def test_button_labels(self):
        """Test button label constants."""
        assert FIRST_PAGE_LABEL == "First"
        assert PREV_PAGE_LABEL == "Previous"
        assert NEXT_PAGE_LABEL == "Next"
        assert LAST_PAGE_LABEL == "Last"
    
    def test_button_controls_structure(self):
        """Test button controls configuration."""
        assert len(BUTTON_CONTROLS) == 4
        
        # Check first button
        first_button = BUTTON_CONTROLS[0]
        assert first_button["id"] == FIRST_PAGE_ID
        assert first_button["emoji"] == FIRST_PAGE_LABEL
        assert first_button["style"] == "secondary"
        
        # Check last button
        last_button = BUTTON_CONTROLS[3]
        assert last_button["id"] == LAST_PAGE_ID
        assert last_button["emoji"] == LAST_PAGE_LABEL
        assert last_button["style"] == "secondary"


class TestPaginationManager:
    """Test pagination manager functionality."""
    
    def test_initialization_default(self):
        """Test default initialization."""
        manager = PaginationManager()
        
        assert manager.items_per_page == 3
        assert manager.movie_current_page == 1
        assert manager.tv_current_page == 1
        assert manager.last_movie_page == 1
        assert manager.last_tv_page == 1
    
    def test_initialization_custom_items_per_page(self):
        """Test initialization with custom items per page."""
        manager = PaginationManager(items_per_page=5)
        
        assert manager.items_per_page == 5
        assert manager.movie_current_page == 1
        assert manager.tv_current_page == 1
    
    def test_handle_button_first_page(self):
        """Test handling first page button."""
        manager = PaginationManager()
        manager.movie_current_page = 3
        manager.tv_current_page = 2
        
        changed = manager.handle_button(FIRST_PAGE_ID)
        
        assert changed is True
        assert manager.movie_current_page == 1
        assert manager.tv_current_page == 1
    
    def test_handle_button_first_page_already_first(self):
        """Test handling first page button when already on first page."""
        manager = PaginationManager()
        
        changed = manager.handle_button(FIRST_PAGE_ID)
        
        assert changed is False
        assert manager.movie_current_page == 1
        assert manager.tv_current_page == 1
    
    def test_handle_button_previous_page(self):
        """Test handling previous page button."""
        manager = PaginationManager()
        manager.movie_current_page = 3
        manager.tv_current_page = 2
        
        changed = manager.handle_button(PREV_PAGE_ID)
        
        assert changed is True
        assert manager.movie_current_page == 2
        assert manager.tv_current_page == 1
    
    def test_handle_button_previous_page_at_first(self):
        """Test handling previous page button when at first page."""
        manager = PaginationManager()
        
        changed = manager.handle_button(PREV_PAGE_ID)
        
        assert changed is False
        assert manager.movie_current_page == 1
        assert manager.tv_current_page == 1
    
    def test_handle_button_next_page(self):
        """Test handling next page button."""
        manager = PaginationManager()
        manager.last_movie_page = 3
        manager.last_tv_page = 2
        
        changed = manager.handle_button(NEXT_PAGE_ID)
        
        assert changed is True
        assert manager.movie_current_page == 2
        assert manager.tv_current_page == 2
    
    def test_handle_button_next_page_at_last(self):
        """Test handling next page button when at last page."""
        manager = PaginationManager()
        manager.movie_current_page = 1
        manager.tv_current_page = 1
        manager.last_movie_page = 1
        manager.last_tv_page = 1
        
        changed = manager.handle_button(NEXT_PAGE_ID)
        
        assert changed is False
        assert manager.movie_current_page == 1
        assert manager.tv_current_page == 1
    
    def test_handle_button_last_page(self):
        """Test handling last page button."""
        manager = PaginationManager()
        manager.last_movie_page = 5
        manager.last_tv_page = 3
        
        changed = manager.handle_button(LAST_PAGE_ID)
        
        assert changed is True
        assert manager.movie_current_page == 5
        assert manager.tv_current_page == 3
    
    def test_handle_button_last_page_already_last(self):
        """Test handling last page button when already on last page."""
        manager = PaginationManager()
        manager.movie_current_page = 2
        manager.tv_current_page = 2
        manager.last_movie_page = 2
        manager.last_tv_page = 2
        
        changed = manager.handle_button(LAST_PAGE_ID)
        
        assert changed is False
        assert manager.movie_current_page == 2
        assert manager.tv_current_page == 2
    
    def test_handle_button_unknown_button(self):
        """Test handling unknown button ID."""
        manager = PaginationManager()
        
        changed = manager.handle_button("unknown_button")
        
        assert changed is False
        assert manager.movie_current_page == 1
        assert manager.tv_current_page == 1
    
    def test_handle_reaction_legacy_compatibility(self):
        """Test legacy reaction handling."""
        manager = PaginationManager()
        manager.last_movie_page = 3
        manager.last_tv_page = 3
        
        # Test first page reaction
        changed = manager.handle_reaction(FIRST_PAGE_LABEL)
        assert changed is False  # Already on first page
        
        # Move to page 2 and test previous
        manager.movie_current_page = 2
        manager.tv_current_page = 2
        changed = manager.handle_reaction(PREV_PAGE_LABEL)
        assert changed is True
        assert manager.movie_current_page == 1
        assert manager.tv_current_page == 1
        
        # Test next page reaction
        changed = manager.handle_reaction(NEXT_PAGE_LABEL)
        assert changed is True
        assert manager.movie_current_page == 2
        assert manager.tv_current_page == 2
        
        # Test last page reaction
        changed = manager.handle_reaction(LAST_PAGE_LABEL)
        assert changed is True
        assert manager.movie_current_page == 3
        assert manager.tv_current_page == 3
    
    def test_handle_reaction_unknown_emoji(self):
        """Test handling unknown reaction emoji."""
        manager = PaginationManager()
        
        changed = manager.handle_reaction("🤔")
        
        assert changed is False
    
    def test_update_page_limits(self):
        """Test updating page limits for both movies and TV."""
        manager = PaginationManager(items_per_page=2)
        
        manager.update_page_limits(movie_count=5, tv_count=7)
        
        # 5 movies / 2 per page = 3 pages (ceil)
        assert manager.last_movie_page == 3
        # 7 TV shows / 2 per page = 4 pages (ceil)
        assert manager.last_tv_page == 4
    
    def test_update_movie_page_limit(self):
        """Test updating only movie page limit."""
        manager = PaginationManager(items_per_page=3)
        
        manager.update_movie_page_limit(10)
        
        # 10 movies / 3 per page = 4 pages (ceil)
        assert manager.last_movie_page == 4
        assert manager.last_tv_page == 1  # Should remain unchanged
    
    def test_update_tv_page_limit(self):
        """Test updating only TV page limit."""
        manager = PaginationManager(items_per_page=3)
        
        manager.update_tv_page_limit(8)
        
        # 8 TV shows / 3 per page = 3 pages (ceil)
        assert manager.last_tv_page == 3
        assert manager.last_movie_page == 1  # Should remain unchanged
    
    def test_update_page_limit_zero_items(self):
        """Test updating page limits with zero items."""
        manager = PaginationManager()
        
        manager.update_page_limits(movie_count=0, tv_count=0)
        
        # Should have at least 1 page even with 0 items
        assert manager.last_movie_page == 1
        assert manager.last_tv_page == 1
    
    def test_update_page_limit_current_page_adjustment(self):
        """Test that current page is adjusted when it exceeds new limit."""
        manager = PaginationManager(items_per_page=3)
        manager.movie_current_page = 5
        manager.tv_current_page = 4
        
        # Update limits to smaller values
        manager.update_page_limits(movie_count=6, tv_count=3)  # 2 pages for movies, 1 for TV
        
        assert manager.last_movie_page == 2
        assert manager.last_tv_page == 1
        assert manager.movie_current_page == 2  # Adjusted down from 5
        assert manager.tv_current_page == 1     # Adjusted down from 4
    
    def test_get_page_indices_movies_first_page(self):
        """Test getting page indices for movies on first page."""
        manager = PaginationManager(items_per_page=3)
        
        start_idx, end_idx = manager.get_page_indices(is_movie=True)
        
        assert start_idx == 0
        assert end_idx == 3
    
    def test_get_page_indices_movies_second_page(self):
        """Test getting page indices for movies on second page."""
        manager = PaginationManager(items_per_page=3)
        manager.movie_current_page = 2
        
        start_idx, end_idx = manager.get_page_indices(is_movie=True)
        
        assert start_idx == 3
        assert end_idx == 6
    
    def test_get_page_indices_tv_first_page(self):
        """Test getting page indices for TV shows on first page."""
        manager = PaginationManager(items_per_page=5)
        
        start_idx, end_idx = manager.get_page_indices(is_movie=False)
        
        assert start_idx == 0
        assert end_idx == 5
    
    def test_get_page_indices_tv_third_page(self):
        """Test getting page indices for TV shows on third page."""
        manager = PaginationManager(items_per_page=4)
        manager.tv_current_page = 3
        
        start_idx, end_idx = manager.get_page_indices(is_movie=False)
        
        assert start_idx == 8  # (3-1) * 4
        assert end_idx == 12   # 8 + 4
    
    def test_get_pagination_info_movies(self):
        """Test getting pagination info for movies."""
        manager = PaginationManager()
        manager.movie_current_page = 2
        manager.last_movie_page = 5
        
        current_page, total_pages = manager.get_pagination_info(is_movie=True)
        
        assert current_page == 2
        assert total_pages == 5
    
    def test_get_pagination_info_tv(self):
        """Test getting pagination info for TV shows."""
        manager = PaginationManager()
        manager.tv_current_page = 3
        manager.last_tv_page = 4
        
        current_page, total_pages = manager.get_pagination_info(is_movie=False)
        
        assert current_page == 3
        assert total_pages == 4
    
    def test_complex_pagination_scenario(self):
        """Test a complex pagination scenario with multiple operations."""
        manager = PaginationManager(items_per_page=2)
        
        # Set up initial data
        manager.update_page_limits(movie_count=10, tv_count=6)  # 5 movie pages, 3 TV pages
        
        # Navigate to middle pages
        manager.handle_button(NEXT_PAGE_ID)  # Page 2
        manager.handle_button(NEXT_PAGE_ID)  # Page 3
        
        assert manager.movie_current_page == 3
        assert manager.tv_current_page == 3
        
        # Go to last page
        manager.handle_button(LAST_PAGE_ID)
        
        assert manager.movie_current_page == 5
        assert manager.tv_current_page == 3  # TV only has 3 pages
        
        # Try to go beyond last page (should not change)
        changed = manager.handle_button(NEXT_PAGE_ID)
        assert changed is False
        assert manager.movie_current_page == 5
        assert manager.tv_current_page == 3
        
        # Go back to first page
        manager.handle_button(FIRST_PAGE_ID)
        
        assert manager.movie_current_page == 1
        assert manager.tv_current_page == 1
        
        # Test page indices for different pages
        start_idx, end_idx = manager.get_page_indices(is_movie=True)
        assert start_idx == 0
        assert end_idx == 2
        
        manager.movie_current_page = 3
        start_idx, end_idx = manager.get_page_indices(is_movie=True)
        assert start_idx == 4  # (3-1) * 2
        assert end_idx == 6    # 4 + 2
    
    def test_edge_case_single_item(self):
        """Test pagination with single item."""
        manager = PaginationManager(items_per_page=3)
        
        manager.update_page_limits(movie_count=1, tv_count=1)
        
        assert manager.last_movie_page == 1
        assert manager.last_tv_page == 1
        
        # Should not be able to navigate anywhere
        changed = manager.handle_button(NEXT_PAGE_ID)
        assert changed is False
        
        changed = manager.handle_button(PREV_PAGE_ID)
        assert changed is False
        
        # Page indices should be correct
        start_idx, end_idx = manager.get_page_indices(is_movie=True)
        assert start_idx == 0
        assert end_idx == 3  # Still returns items_per_page, caller handles bounds
    
    def test_edge_case_exact_page_boundary(self):
        """Test pagination when item count is exactly divisible by items per page."""
        manager = PaginationManager(items_per_page=3)
        
        manager.update_page_limits(movie_count=6, tv_count=9)  # Exactly 2 and 3 pages
        
        assert manager.last_movie_page == 2
        assert manager.last_tv_page == 3
        
        # Navigate to last pages
        manager.handle_button(LAST_PAGE_ID)
        
        assert manager.movie_current_page == 2
        assert manager.tv_current_page == 3
        
        # Check indices for last pages
        start_idx, end_idx = manager.get_page_indices(is_movie=True)
        assert start_idx == 3  # (2-1) * 3
        assert end_idx == 6    # 3 + 3
        
        start_idx, end_idx = manager.get_page_indices(is_movie=False)
        assert start_idx == 6  # (3-1) * 3
        assert end_idx == 9    # 6 + 3
