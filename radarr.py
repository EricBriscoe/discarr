import requests
import logging
from config import RADARR_URL, RADARR_API_KEY, VERBOSE
from arr_client import ArrClient

logger = logging.getLogger(__name__)

class RadarrClient(ArrClient):
    def __init__(self):
        super().__init__(RADARR_URL, RADARR_API_KEY, VERBOSE)
        self.movie_cache = {}

    def get_queue_params(self):
        """Return parameters for queue API call"""
        return {
            "pageSize": 1000,
            "page": 1,
            "sortKey": "timeleft",
            "sortDirection": "ascending",
            "includeMovie": True
        }
            
    def get_movie_by_id(self, movie_id):
        """Get movie details by ID"""
        if movie_id in self.movie_cache:
            return self.movie_cache[movie_id]
            
        try:
            url = f"{self.base_url}/api/v3/movie/{movie_id}"
            if self.verbose:
                logger.debug(f"Making request to Radarr movie API: {url}")
                
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            movie_data = response.json()
            
            self.movie_cache[movie_id] = movie_data
            return movie_data
            
        except requests.RequestException as e:
            logger.error(f"Error fetching Radarr movie {movie_id}: {e}")
            if self.verbose and hasattr(e, 'response') and e.response:
                logger.debug(f"Response: {e.response.status_code} - {e.response.text[:200]}...")
            return None

    def get_media_info(self, item):
        """Extract movie specific information from the queue item"""
        movie_id = item.get("movieId")
        movie_title = "Unknown Movie"
        
        if movie_id:
            movie_data = self.get_movie_by_id(movie_id)
            if movie_data:
                movie_title = movie_data.get("title", movie_title)
        else:
            movie_title = item.get("title", movie_title)
        
        if self.verbose:
            logger.debug(f"Queue item: {movie_title} ({item.get('trackedDownloadState', 'status not found')})")
        
        return {
            "title": movie_title
        }

    def get_download_updates(self):
        """Get updates for downloads that need to be reported to Discord"""
        current_downloads = self.get_active_downloads()
        updates = []
        
        # Check for new downloads or progress updates
        for download in current_downloads:
            dl_id = download["id"]
            if dl_id not in self.previous_status or abs(self.previous_status[dl_id]["progress"] - download["progress"]) >= 10:
                updates.append({
                    "type": "movie",
                    "title": download["title"],
                    "progress": download["progress"],
                    "size": download["size"],
                    "time_left": download["time_left"],
                    "is_new": dl_id not in self.previous_status
                })
                self.previous_status[dl_id] = download
        
        # Check for completed downloads
        for dl_id in list(self.previous_status.keys()):
            if not any(d["id"] == dl_id for d in current_downloads):
                completed_download = self.previous_status[dl_id]
                updates.append({
                    "type": "movie",
                    "title": completed_download["title"],
                    "progress": 100,
                    "size": completed_download["size"],
                    "status": "completed"
                })
                if self.verbose:
                    logger.debug(f"Completed movie: {completed_download['title']}")
                del self.previous_status[dl_id]
            
        return updates
