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

      // Sort by progress (highest first) - no limiting for pagination
      const sortedDownloads = allDownloads
        .sort((a, b) => b.progress - a.progress);

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