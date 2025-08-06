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
    items: AnyDownloadItem[];
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
      return { items: [], total: 0 };
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

      return {
        items: sortedDownloads,
        total: allDownloads.length,
      };
    } catch (error) {
      if (config.monitoring.verbose) {
        console.error('Error fetching downloads:', error);
      }
      return { items: [], total: 0 };
    }
  }

  startMonitoring(callback: (data: { items: AnyDownloadItem[]; total: number }) => void): void {
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

  calculateNextRefreshInterval(downloads: { items: AnyDownloadItem[]; total: number }): number {
    let shortestTimeSeconds = Infinity;

    for (const item of downloads.items) {
      const timeSeconds = this.parseTimeLeftToSeconds(item.timeLeft || '');
      if (timeSeconds < shortestTimeSeconds) {
        shortestTimeSeconds = timeSeconds;
      }
    }

    // Apply smart interval rules
    let interval: number;
    if (shortestTimeSeconds < 2 * 60) { // < 2 minutes
      interval = 30 * 1000; // 30 seconds
    } else if (shortestTimeSeconds < 10 * 60) { // < 10 minutes
      interval = 60 * 1000; // 1 minute
    } else if (shortestTimeSeconds < 30 * 60) { // < 30 minutes
      interval = 2 * 60 * 1000; // 2 minutes
    } else if (shortestTimeSeconds < 2 * 60 * 60) { // < 2 hours
      interval = 5 * 60 * 1000; // 5 minutes
    } else {
      interval = 10 * 60 * 1000; // 10 minutes for > 2 hours
    }

    // Enforce bounds
    return Math.max(config.monitoring.minRefreshInterval, 
                   Math.min(config.monitoring.maxRefreshInterval, interval));
  }

  private parseTimeLeftToSeconds(timeLeft: string): number {
    if (!timeLeft || timeLeft === '∞' || timeLeft.includes('∞')) {
      return Infinity;
    }

    // Handle import blocked items - treat as infinite since they need manual action
    if (timeLeft.includes('Manual action required')) {
      return Infinity;
    }

    // Handle Discord timestamp format
    if (timeLeft.startsWith('<t:')) {
      const match = timeLeft.match(/<t:(\d+):/);
      const timestamp = parseInt(match![1]);
      const now = Math.floor(Date.now() / 1000);
      return Math.max(0, timestamp - now);
    }

    // Handle special case for "< 1m"
    if (timeLeft.includes('< 1m')) {
      return 30;
    }
    
    // Parse time strings like "1h 30m", "45m", "2h", "30s"
    const hours = parseInt((timeLeft.match(/(\d+)h/) || [])[1] || '0');
    const minutes = parseInt((timeLeft.match(/(\d+)m/) || [])[1] || '0');
    const seconds = parseInt((timeLeft.match(/(\d+)s/) || [])[1] || '0');
    
    return (hours * 3600) + (minutes * 60) + seconds;
  }
}