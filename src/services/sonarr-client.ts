import { BaseClient } from './base-client';
import { ServiceStatus, TVDownloadItem } from '../types';

export class SonarrClient extends BaseClient {
  private seriesCache = new Map<number, any>();
  private episodeCache = new Map<number, any>();

  async checkHealth(): Promise<ServiceStatus> {
    const startTime = Date.now();
    
    try {
      const response = await this.makeRequest<{ version: string }>('/api/v3/system/status');
      const responseTime = Date.now() - startTime;
      
      return {
        status: 'online',
        lastCheck: new Date(),
        responseTime,
        version: response.version,
      };
    } catch (error: any) {
      return {
        status: 'offline',
        lastCheck: new Date(),
        responseTime: Date.now() - startTime,
        error: error.message,
      };
    }
  }

  async getActiveDownloads(): Promise<TVDownloadItem[]> {
    try {
      const response = await this.makeRequest<{ records: any[] }>('/api/v3/queue', {
        pageSize: 50,
        includeUnknownSeriesItems: false,
      });

      const downloads = await Promise.all(
        response.records
          .filter(item => item.status === 'downloading' || item.status === 'queued')
          .map(item => this.processQueueItem(item))
      );

      return downloads.sort((a, b) => b.progress - a.progress);
    } catch (error) {
      if (this.verbose) {
        console.error('Failed to fetch Sonarr queue:', error);
      }
      return [];
    }
  }

  private async processQueueItem(item: any): Promise<TVDownloadItem> {
    const progress = item.sizeleft && item.size && item.size > 0
      ? 100 * (1 - item.sizeleft / item.size)
      : item.progress || 0;

    const size = (item.size || 0) / (1024 * 1024 * 1024); // Convert to GB
    const timeLeft = item.estimatedCompletionTime 
      ? `<t:${Math.floor(new Date(item.estimatedCompletionTime).getTime() / 1000)}:R>`
      : this.parseTimeLeft(item.timeleft || '');

    // Get series and episode info
    const mediaInfo = await this.getMediaInfo(item);

    return {
      id: item.id,
      title: `${mediaInfo.series} - S${mediaInfo.season.toString().padStart(2, '0')}E${mediaInfo.episode.toString().padStart(2, '0')}`,
      series: mediaInfo.series,
      season: mediaInfo.season,
      episode: mediaInfo.episode,
      progress,
      size,
      sizeLeft: item.sizeleft || 0,
      timeLeft,
      status: item.trackedDownloadState || item.status,
      protocol: item.protocol || 'unknown',
      downloadClient: item.downloadClient || 'unknown',
      service: 'sonarr',
      added: item.added,
      errorMessage: item.errorMessage,
    };
  }

  private async getMediaInfo(queueItem: any): Promise<{ series: string; season: number; episode: number }> {
    const seriesId = queueItem.seriesId;
    const episodeId = queueItem.episodeId;

    let seriesTitle = 'Unknown Series';
    let seasonNumber = 0;
    let episodeNumber = 0;

    if (seriesId) {
      if (!this.seriesCache.has(seriesId)) {
        try {
          const series = await this.makeRequest<any>(`/api/v3/series/${seriesId}`);
          this.seriesCache.set(seriesId, series);
        } catch (error) {
          // Cache miss, use default
        }
      }
      const series = this.seriesCache.get(seriesId);
      if (series) {
        seriesTitle = series.title;
      }
    }

    if (episodeId) {
      if (!this.episodeCache.has(episodeId)) {
        try {
          const episode = await this.makeRequest<any>(`/api/v3/episode/${episodeId}`);
          this.episodeCache.set(episodeId, episode);
        } catch (error) {
          // Cache miss, use default
        }
      }
      const episode = this.episodeCache.get(episodeId);
      if (episode) {
        seasonNumber = episode.seasonNumber || 0;
        episodeNumber = episode.episodeNumber || 0;
      }
    }

    return {
      series: seriesTitle,
      season: seasonNumber,
      episode: episodeNumber,
    };
  }
}