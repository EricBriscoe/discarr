import { AnyDownloadItem, MovieDownloadItem, TVDownloadItem } from '../types';
import { HealthMonitor } from './health-monitor';
import config from '../config';

export class DownloadMonitor {
  private healthMonitor: HealthMonitor;
  private checkInterval?: NodeJS.Timeout;

  constructor(healthMonitor: HealthMonitor) {
    this.healthMonitor = healthMonitor;
  }

  async getActiveDownloads(): Promise<{
    movies: MovieDownloadItem[];
    tv: TVDownloadItem[];
    total: number;
  }> {
    const promises: Promise<AnyDownloadItem[]>[] = [];

    const radarrClient = this.healthMonitor.getRadarrClient();
    const sonarrClient = this.healthMonitor.getSonarrClient();

    if (radarrClient) {
      promises.push(radarrClient.getActiveDownloads());
    }

    if (sonarrClient) {
      promises.push(sonarrClient.getActiveDownloads());
    }

    if (promises.length === 0) {
      return { movies: [], tv: [], total: 0 };
    }

    try {
      const results = await Promise.allSettled(promises);
      const allDownloads: AnyDownloadItem[] = [];

      results.forEach(result => {
        if (result.status === 'fulfilled') {
          allDownloads.push(...result.value);
        }
      });

      // Sort by time left (shortest first) - no limiting for pagination
      const sortedDownloads = allDownloads
        .sort((a, b) => {
          // Parse time left for sorting (handle special cases)
          const parseTimeLeft = (timeLeft: string): number => {
            if (!timeLeft || timeLeft === '∞' || timeLeft.includes('∞')) return Infinity;
            if (timeLeft.startsWith('<t:')) {
              // Discord timestamp format - extract timestamp and calculate difference
              const timestamp = parseInt(timeLeft.match(/<t:(\d+):/)?.[1] || '0');
              const now = Math.floor(Date.now() / 1000);
              const secondsLeft = timestamp - now;
              return timestamp > 0 ? Math.max(0, secondsLeft) : Infinity;
            }
            // Handle special case for "< 1m"
            if (timeLeft.includes('< 1m')) {
              return 30; // 30 seconds for items finishing very soon
            }
            
            // Parse time strings like "1h 30m", "45m", "2h"
            const hours = (timeLeft.match(/(\d+)h/) || [])[1];
            const minutes = (timeLeft.match(/(\d+)m/) || [])[1];
            const seconds = (timeLeft.match(/(\d+)s/) || [])[1];
            return (parseInt(hours || '0') * 3600) + (parseInt(minutes || '0') * 60) + parseInt(seconds || '0');
          };

          const aTime = parseTimeLeft(a.timeLeft || '');
          const bTime = parseTimeLeft(b.timeLeft || '');
          
          // Sort by time left ascending (shortest time first)
          return aTime - bTime;
        });

      const movies = sortedDownloads.filter(item => item.service === 'radarr') as MovieDownloadItem[];
      const tv = sortedDownloads.filter(item => item.service === 'sonarr') as TVDownloadItem[];

      return {
        movies,
        tv,
        total: allDownloads.length,
      };
    } catch (error) {
      if (config.monitoring.verbose) {
        console.error('Error fetching downloads:', error);
      }
      return { movies: [], tv: [], total: 0 };
    }
  }

  startMonitoring(callback: (data: { movies: MovieDownloadItem[]; tv: TVDownloadItem[]; total: number }) => void): void {
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
    }

    this.checkInterval = setInterval(async () => {
      try {
        const downloads = await this.getActiveDownloads();
        callback(downloads);
      } catch (error) {
        if (config.monitoring.verbose) {
          console.error('Error in download monitoring:', error);
        }
      }
    }, config.monitoring.checkInterval);

    // Run immediately
    this.getActiveDownloads().then(callback).catch(error => {
      if (config.monitoring.verbose) {
        console.error('Error in initial download check:', error);
      }
    });
  }

  stopMonitoring(): void {
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = undefined;
    }
  }
}