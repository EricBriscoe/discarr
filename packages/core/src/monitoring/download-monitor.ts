import { AnyDownloadItem } from '../types';
import { HealthMonitor } from './health-monitor';
import config from '../config';

export class DownloadMonitor {
  private healthMonitor: HealthMonitor;
  private checkInterval?: NodeJS.Timeout;

  constructor(healthMonitor: HealthMonitor) {
    this.healthMonitor = healthMonitor;
  }

  async getActiveDownloads(): Promise<{ items: AnyDownloadItem[]; total: number; }> {
    const promises: Promise<AnyDownloadItem[]>[] = [];

    const radarrClient = this.healthMonitor.getRadarrClient();
    const sonarrClient = this.healthMonitor.getSonarrClient();

    if (radarrClient) promises.push(radarrClient.getActiveDownloads());
    if (sonarrClient) promises.push(sonarrClient.getActiveDownloads());

    if (promises.length === 0) return { items: [], total: 0 };

    try {
      const results = await Promise.allSettled(promises);
      const allDownloads: AnyDownloadItem[] = [];
      results.forEach(result => { if (result.status === 'fulfilled') allDownloads.push(...result.value); });

      const sortedDownloads = allDownloads.sort((a, b) => {
        const parseTimeLeft = (timeLeft: string): number => {
          if (!timeLeft || timeLeft === '∞' || timeLeft.includes('∞')) return Infinity;
          if (timeLeft.startsWith('<t:')) {
            const timestamp = parseInt(timeLeft.match(/<t:(\d+):/)?.[1] || '0');
            const now = Math.floor(Date.now() / 1000);
            return timestamp > 0 ? Math.max(0, timestamp - now) : Infinity;
          }
          if (timeLeft.includes('< 1m')) return 30;
          const hours = (timeLeft.match(/(\d+)h/) || [])[1];
          const minutes = (timeLeft.match(/(\d+)m/) || [])[1];
          const seconds = (timeLeft.match(/(\d+)s/) || [])[1];
          return (parseInt(hours || '0') * 3600) + (parseInt(minutes || '0') * 60) + parseInt(seconds || '0');
        };
        return parseTimeLeft(a.timeLeft || '') - parseTimeLeft(b.timeLeft || '');
      });

      return { items: sortedDownloads, total: allDownloads.length };
    } catch (error) {
      if (config.monitoring.verbose) console.error('Error fetching downloads:', error);
      return { items: [], total: 0 };
    }
  }

  calculateNextRefreshInterval(downloads: { items: AnyDownloadItem[]; total: number }): number {
    let shortestTimeSeconds = Infinity;
    for (const item of downloads.items) {
      const seconds = this.parseTimeLeftToSeconds(item.timeLeft || '');
      if (seconds < shortestTimeSeconds) shortestTimeSeconds = seconds;
    }
    let interval: number;
    if (shortestTimeSeconds < 2 * 60) interval = 30 * 1000;
    else if (shortestTimeSeconds < 10 * 60) interval = 60 * 1000;
    else if (shortestTimeSeconds < 30 * 60) interval = 2 * 60 * 1000;
    else if (shortestTimeSeconds < 2 * 60 * 60) interval = 5 * 60 * 1000;
    else interval = 10 * 60 * 1000;
    return Math.max(config.monitoring.minRefreshInterval, Math.min(config.monitoring.maxRefreshInterval, interval));
  }

  startMonitoring(callback: (data: { items: AnyDownloadItem[]; total: number }) => void): void {
    if (this.checkInterval) clearInterval(this.checkInterval);
    this.checkInterval = setInterval(async () => {
      try { callback(await this.getActiveDownloads()); } catch (e) { if (config.monitoring.verbose) console.error('Error in download monitoring:', e); }
    }, config.monitoring.checkInterval);
    this.getActiveDownloads().then(callback).catch(e => { if (config.monitoring.verbose) console.error('Error in initial download check:', e); });
  }

  stopMonitoring(): void { if (this.checkInterval) clearInterval(this.checkInterval); }

  private parseTimeLeftToSeconds(timeLeft: string): number {
    if (!timeLeft || timeLeft === '∞' || timeLeft.includes('∞')) return Infinity;
    if (timeLeft.includes('Manual action required')) return Infinity;
    if (timeLeft.startsWith('<t:')) {
      const match = timeLeft.match(/<t:(\d+):/);
      const timestamp = parseInt(match![1]);
      const now = Math.floor(Date.now() / 1000);
      return Math.max(0, timestamp - now);
    }
    if (timeLeft.includes('< 1m')) return 30;
    const hours = parseInt((timeLeft.match(/(\d+)h/) || [])[1] || '0');
    const minutes = parseInt((timeLeft.match(/(\d+)m/) || [])[1] || '0');
    const seconds = parseInt((timeLeft.match(/(\d+)s/) || [])[1] || '0');
    return (hours * 3600) + (minutes * 60) + seconds;
  }
}

