"""
Pagination management for Discarr bot.
Handles state and controls for navigating pages of download information.
"""
import math

# Button control IDs for pagination
FIRST_PAGE_ID = "pagination_first"
PREV_PAGE_ID = "pagination_prev"
NEXT_PAGE_ID = "pagination_next"
LAST_PAGE_ID = "pagination_last"

# Button labels for navigation
FIRST_PAGE_LABEL = "First"
PREV_PAGE_LABEL = "Previous"
NEXT_PAGE_LABEL = "Next"
LAST_PAGE_LABEL = "Last"

# Button definitions for view creation
BUTTON_CONTROLS = [
    {"id": FIRST_PAGE_ID, "emoji": FIRST_PAGE_LABEL, "style": "secondary"},
    {"id": PREV_PAGE_ID, "emoji": PREV_PAGE_LABEL, "style": "primary"},
    {"id": NEXT_PAGE_ID, "emoji": NEXT_PAGE_LABEL, "style": "primary"},
    {"id": LAST_PAGE_ID, "emoji": LAST_PAGE_LABEL, "style": "secondary"}
]

class PaginationManager:
    """Manages pagination state for movies and TV shows."""
    
    def __init__(self, items_per_page=3):  # Reduced from 5 to 3 to stay under field limit
        """Initialize pagination state."""
        self.items_per_page = items_per_page
        # Separate page counters for movies and TV
        self.movie_current_page = 1
        self.tv_current_page = 1
        self.last_movie_page = 1
        self.last_tv_page = 1
    
    def handle_button(self, button_id):
        """Handle a pagination button click and update the state.
        
        Returns True if state was changed, False otherwise.
        """
        changed = False
        
        if button_id == FIRST_PAGE_ID:
            if self.movie_current_page != 1 or self.tv_current_page != 1:
                self.movie_current_page = 1
                self.tv_current_page = 1
                changed = True
                
        elif button_id == PREV_PAGE_ID:
            if self.movie_current_page > 1:
                self.movie_current_page -= 1
                changed = True
            if self.tv_current_page > 1:
                self.tv_current_page -= 1
                changed = True
                
        elif button_id == NEXT_PAGE_ID:
            if self.movie_current_page < self.last_movie_page:
                self.movie_current_page += 1
                changed = True
            if self.tv_current_page < self.last_tv_page:
                self.tv_current_page += 1
                changed = True
                
        elif button_id == LAST_PAGE_ID:
            if self.movie_current_page != self.last_movie_page or self.tv_current_page != self.last_tv_page:
                self.movie_current_page = self.last_movie_page
                self.tv_current_page = self.last_tv_page
                changed = True
                
        return changed
        
    # For backward compatibility
    def handle_reaction(self, reaction_emoji):
        """Legacy method for handling reactions - maps to button handling."""
        if reaction_emoji == FIRST_PAGE_LABEL:
            return self.handle_button(FIRST_PAGE_ID)
        elif reaction_emoji == PREV_PAGE_LABEL:
            return self.handle_button(PREV_PAGE_ID)
        elif reaction_emoji == NEXT_PAGE_LABEL:
            return self.handle_button(NEXT_PAGE_ID)
        elif reaction_emoji == LAST_PAGE_LABEL:
            return self.handle_button(LAST_PAGE_ID)
        return False
    
    def update_page_limits(self, movie_count, tv_count):
        """Update the last page numbers based on item counts."""
        self.update_movie_page_limit(movie_count)
        self.update_tv_page_limit(tv_count)
    
    def update_movie_page_limit(self, movie_count):
        """Update just the movie page limit."""
        self.last_movie_page = max(1, math.ceil(movie_count / self.items_per_page))
        # Ensure current page is within valid range
        if self.movie_current_page > self.last_movie_page:
            self.movie_current_page = self.last_movie_page
    
    def update_tv_page_limit(self, tv_count):
        """Update just the TV page limit."""
        self.last_tv_page = max(1, math.ceil(tv_count / self.items_per_page))
        # Ensure current page is within valid range
        if self.tv_current_page > self.last_tv_page:
            self.tv_current_page = self.last_tv_page
    
    def get_page_indices(self, is_movie=True):
        """Get the start and end indices for the current page."""
        if is_movie:
            start_idx = (self.movie_current_page - 1) * self.items_per_page
        else:
            start_idx = (self.tv_current_page - 1) * self.items_per_page
            
        end_idx = start_idx + self.items_per_page
        return start_idx, end_idx
        
    def get_pagination_info(self, is_movie=True):
        """Get the current page number and total pages."""
        if is_movie:
            return self.movie_current_page, self.last_movie_page
        else:
            return self.tv_current_page, self.last_tv_page
