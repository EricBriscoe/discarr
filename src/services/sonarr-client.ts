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
      // Use pagination to get ALL queue items
      const allRecords = await this.getAllPaginated<any>('/api/v3/queue', {
        includeUnknownSeriesItems: false,
        sortKey: 'timeleft',
        sortDirection: 'ascending',
        includeSeries: true,
        includeEpisode: true
      });

      if (this.verbose) {
        console.log(`Processing ${allRecords.length} Sonarr queue items`);
      }

      const downloads = await Promise.all(
        allRecords.map(item => this.processQueueItem(item))
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
    const progress = item.size && item.size > 0 && typeof item.sizeleft === 'number'
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

  async getImportBlockedItems(): Promise<{id: number, title: string}[]> {
    try {
      const allRecords = await this.getAllPaginated<any>('/api/v3/queue', {
        includeUnknownSeriesItems: false,
        includeSeries: true,
        includeEpisode: true
      });

      const blockedItems = allRecords.filter(item => 
        (item.trackedDownloadState || item.status) === 'importBlocked'
      );

      // Get titles for blocked items
      const itemsWithTitles = await Promise.all(
        blockedItems.map(async (item) => {
          const mediaInfo = await this.getMediaInfo(item);
          return {
            id: item.id,
            title: `${mediaInfo.series} - S${mediaInfo.season.toString().padStart(2, '0')}E${mediaInfo.episode.toString().padStart(2, '0')}`
          };
        })
      );

      return itemsWithTitles;
    } catch (error) {
      if (this.verbose) {
        console.error('Failed to fetch Sonarr importBlocked items:', error);
      }
      return [];
    }
  }

  async removeQueueItems(itemIds: number[]): Promise<{id: number, success: boolean, error?: string}[]> {
    const results = await Promise.allSettled(
      itemIds.map(async (id) => {
        try {
          await this.makeRequest(`/api/v3/queue/${id}`, 'DELETE', undefined, {
            removeFromClient: true,
            blocklist: false
          });
          return { id, success: true };
        } catch (error) {
          return { 
            id, 
            success: false, 
            error: error instanceof Error ? error.message : 'Unknown error' 
          };
        }
      })
    );

    return results.map(result => 
      result.status === 'fulfilled' ? result.value : { 
        id: 0, 
        success: false, 
        error: 'Promise rejected' 
      }
    );
  }
}