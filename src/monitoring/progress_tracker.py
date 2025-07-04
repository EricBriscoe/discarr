"""
Progress tracking module for Discarr bot.
Handles in-memory tracking of download progress over time to identify stuck downloads.
"""
import time
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional
from src.core.settings import settings

logger = logging.getLogger(__name__)

@dataclass
class ProgressSnapshot:
    """Represents a point-in-time snapshot of download progress."""
    timestamp: float
    progress_percent: float
    size_left: int
    status: str
    title: str
    download_client: str = ""
    protocol: str = ""

class ProgressTracker:
    """Tracks download progress over time to identify stuck downloads."""
    
    def __init__(self):
        """Initialize the progress tracker."""
        # Dictionary mapping download_id to list of ProgressSnapshots
        self.progress_history: Dict[str, List[ProgressSnapshot]] = {}
        
        # Configuration from settings
        self.stuck_threshold_minutes = settings.stuck_threshold_minutes
        self.min_progress_change = settings.min_progress_change
        self.min_size_change = settings.min_size_change
        self.progress_history_hours = settings.progress_history_hours
        self.max_snapshots_per_download = settings.max_snapshots_per_download
        
        logger.info(f"ProgressTracker initialized with {self.stuck_threshold_minutes}min stuck threshold")
    
    def record_progress_snapshot(self, download_items: List[Dict], service_type: str):
        """Record progress snapshots for all current download items.
        
        Args:
            download_items: List of download items from Radarr/Sonarr
            service_type: 'radarr' or 'sonarr'
        """
        current_time = time.time()
        
        # Track which downloads are still active
        active_download_ids = set()
        
        for item in download_items:
            download_id = f"{service_type}_{item.get('id', 0)}"
            active_download_ids.add(download_id)
            
            # Create progress snapshot
            snapshot = ProgressSnapshot(
                timestamp=current_time,
                progress_percent=item.get('progress', 0),
                size_left=item.get('sizeleft', 0),
                status=item.get('status', 'unknown'),
                title=item.get('title', 'Unknown'),
                download_client=item.get('download_client', ''),
                protocol=item.get('protocol', '')
            )
            
            # Add to history
            if download_id not in self.progress_history:
                self.progress_history[download_id] = []
            
            self.progress_history[download_id].append(snapshot)
            
            # Limit snapshots per download to prevent memory bloat
            if len(self.progress_history[download_id]) > self.max_snapshots_per_download:
                self.progress_history[download_id] = self.progress_history[download_id][-self.max_snapshots_per_download:]
        
        # Clean up history for downloads that are no longer active
        self._cleanup_inactive_downloads(active_download_ids)
        
        # Clean up old snapshots beyond time window
        self._cleanup_old_snapshots(current_time)
        
        if settings.verbose:
            logger.debug(f"Recorded progress for {len(download_items)} {service_type} items. "
                        f"Total tracked downloads: {len(self.progress_history)}")
    
    def _cleanup_inactive_downloads(self, active_download_ids: set):
        """Remove progress history for downloads that are no longer in the queue."""
        inactive_ids = set(self.progress_history.keys()) - active_download_ids
        for download_id in inactive_ids:
            del self.progress_history[download_id]
            if settings.verbose:
                logger.debug(f"Cleaned up progress history for inactive download: {download_id}")
    
    def _cleanup_old_snapshots(self, current_time: float):
        """Remove snapshots older than the configured time window."""
        cutoff_time = current_time - (self.progress_history_hours * 3600)
        
        for download_id, snapshots in self.progress_history.items():
            # Keep only snapshots within the time window
            recent_snapshots = [s for s in snapshots if s.timestamp >= cutoff_time]
            
            # Always keep at least the last 2 snapshots for comparison
            if len(recent_snapshots) < 2 and len(snapshots) >= 2:
                recent_snapshots = snapshots[-2:]
            
            self.progress_history[download_id] = recent_snapshots
    
    def analyze_stuck_downloads(self) -> List[Dict]:
        """Analyze progress history to identify stuck downloads.
        
        Returns:
            List of dictionaries containing stuck download information
        """
        stuck_downloads = []
        current_time = time.time()
        
        for download_id, snapshots in self.progress_history.items():
            if len(snapshots) < 2:
                continue  # Need at least 2 snapshots to analyze progress
            
            stuck_info = self._analyze_download_progress(download_id, snapshots, current_time)
            if stuck_info:
                stuck_downloads.append(stuck_info)
        
        if settings.verbose:
            logger.debug(f"Found {len(stuck_downloads)} stuck downloads out of {len(self.progress_history)} tracked")
        
        return stuck_downloads
    
    def _analyze_download_progress(self, download_id: str, snapshots: List[ProgressSnapshot], current_time: float) -> Optional[Dict]:
        """Analyze progress for a single download to determine if it's stuck.
        
        Args:
            download_id: Unique identifier for the download
            snapshots: List of progress snapshots for this download
            current_time: Current timestamp
            
        Returns:
            Dictionary with stuck download info if stuck, None otherwise
        """
        # Get snapshots within the stuck threshold window
        threshold_time = current_time - (self.stuck_threshold_minutes * 60)
        recent_snapshots = [s for s in snapshots if s.timestamp >= threshold_time]
        
        if len(recent_snapshots) < 2:
            return None  # Not enough recent data
        
        # Compare oldest and newest snapshots in the threshold window
        oldest_snapshot = recent_snapshots[0]
        newest_snapshot = recent_snapshots[-1]
        
        # Calculate changes over the threshold period
        progress_change = abs(newest_snapshot.progress_percent - oldest_snapshot.progress_percent)
        size_change = abs(oldest_snapshot.size_left - newest_snapshot.size_left)
        time_span_minutes = (newest_snapshot.timestamp - oldest_snapshot.timestamp) / 60
        
        # Determine if download is stuck
        is_stuck = (
            time_span_minutes >= self.stuck_threshold_minutes and
            progress_change < self.min_progress_change and
            size_change < self.min_size_change and
            newest_snapshot.status in ['downloading', 'queued']  # Only consider active statuses as potentially stuck
        )
        
        if is_stuck:
            # Extract service and ID from download_id
            service_type, item_id = download_id.split('_', 1)
            
            return {
                'download_id': download_id,
                'service': service_type,
                'id': int(item_id),
                'title': newest_snapshot.title,
                'status': newest_snapshot.status,
                'progress_percent': newest_snapshot.progress_percent,
                'size_left': newest_snapshot.size_left,
                'stuck_duration_minutes': time_span_minutes,
                'progress_change': progress_change,
                'size_change': size_change,
                'download_client': newest_snapshot.download_client,
                'protocol': newest_snapshot.protocol
            }
        
        return None
    
    def get_download_progress_summary(self, download_id: str) -> Optional[Dict]:
        """Get a summary of progress for a specific download.
        
        Args:
            download_id: Unique identifier for the download
            
        Returns:
            Dictionary with progress summary or None if not found
        """
        if download_id not in self.progress_history:
            return None
        
        snapshots = self.progress_history[download_id]
        if not snapshots:
            return None
        
        latest = snapshots[-1]
        oldest = snapshots[0]
        
        return {
            'download_id': download_id,
            'title': latest.title,
            'current_progress': latest.progress_percent,
            'current_status': latest.status,
            'snapshots_count': len(snapshots),
            'tracking_duration_hours': (latest.timestamp - oldest.timestamp) / 3600,
            'total_progress_change': latest.progress_percent - oldest.progress_percent,
            'total_size_change': oldest.size_left - latest.size_left
        }
    
    def get_statistics(self) -> Dict:
        """Get overall statistics about tracked downloads.
        
        Returns:
            Dictionary with tracking statistics
        """
        total_downloads = len(self.progress_history)
        total_snapshots = sum(len(snapshots) for snapshots in self.progress_history.values())
        
        if total_downloads == 0:
            return {
                'total_downloads': 0,
                'total_snapshots': 0,
                'avg_snapshots_per_download': 0,
                'memory_usage_estimate_kb': 0,
                'min_download_speed_mbps': 0,
                'max_download_speed_mbps': 0
            }
        
        avg_snapshots = total_snapshots / total_downloads
        # Rough estimate: ~100 bytes per snapshot
        memory_estimate_kb = (total_snapshots * 100) / 1024
        
        # Calculate download speeds
        speeds = self._calculate_download_speeds()
        min_speed = min(speeds) if speeds else 0
        max_speed = max(speeds) if speeds else 0
        
        return {
            'total_downloads': total_downloads,
            'total_snapshots': total_snapshots,
            'avg_snapshots_per_download': round(avg_snapshots, 1),
            'memory_usage_estimate_kb': round(memory_estimate_kb, 1),
            'min_download_speed_mbps': round(min_speed, 1),
            'max_download_speed_mbps': round(max_speed, 1)
        }
    
    def _calculate_download_speeds(self) -> List[float]:
        """Calculate download speeds for all tracked downloads.
        
        Returns:
            List of download speeds in MB/s
        """
        speeds = []
        
        for download_id, snapshots in self.progress_history.items():
            if len(snapshots) < 2:
                continue
            
            # Calculate speed between consecutive snapshots
            for i in range(1, len(snapshots)):
                prev_snapshot = snapshots[i-1]
                curr_snapshot = snapshots[i]
                
                # Calculate time difference in seconds
                time_diff = curr_snapshot.timestamp - prev_snapshot.timestamp
                if time_diff <= 0:
                    continue
                
                # Calculate bytes downloaded (size_left decreased)
                bytes_downloaded = prev_snapshot.size_left - curr_snapshot.size_left
                if bytes_downloaded <= 0:
                    continue
                
                # Convert to MB/s
                speed_mbps = (bytes_downloaded / (1024 * 1024)) / time_diff
                if speed_mbps > 0:
                    speeds.append(speed_mbps)
        
        return speeds
