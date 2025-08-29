import { BaseClient } from './base-client';
import { ServiceStatus, TVDownloadItem, CalendarEpisode, SeriesSearchResult, MissingEpisode, SeriesInfo } from '../types';

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

  async getQueueSummary(): Promise<import('../types').QueueStats> {
    try {
      const items = await this.getAllPaginated<any>('/api/v3/queue', {
        includeUnknownSeriesItems: false,
        includeSeries: true,
        includeEpisode: true
      });
      const summary = {
        total: items.length,
        downloading: 0,
        queued: 0,
        completed: 0,
        importBlocked: 0,
        stuck: 0,
        failed: 0,
      };
      for (const it of items) {
        const status = (it.status || '').toLowerCase();
        const tracked = (it.trackedDownloadState || '').toLowerCase();
        if (status === 'downloading' || status === 'paused' || status === 'resuming') summary.downloading++;
        if (status === 'queued' || status === 'pending') summary.queued++;
        if (status === 'completed') summary.completed++;
        if (tracked === 'importblocked' || status === 'importblocked') summary.importBlocked++;
        const size = it.size || 0; const sizeleft = typeof it.sizeleft === 'number' ? it.sizeleft : 0;
        const progress = size > 0 ? 100 * (1 - sizeleft / size) : (it.progress || 0);
        const timeleft = it.timeleft || '';
        if ((!it.estimatedCompletionTime && (!timeleft || timeleft === '∞')) && progress > 0 && status !== 'completed') summary.stuck++;
        if (status === 'failed' || tracked === 'failed') summary.failed++;
      }
      return summary;
    } catch {
      return { total: 0, downloading: 0, queued: 0, completed: 0, importBlocked: 0, stuck: 0, failed: 0 };
    }
  }

  async getActiveDownloads(): Promise<TVDownloadItem[]> {
    try {
      const allRecords = await this.getAllPaginated<any>('/api/v3/queue', {
        includeUnknownSeriesItems: false,
        includeSeries: true,
        includeEpisode: true
      });

      if (this.verbose) {
        console.log(`Processing ${allRecords.length} Sonarr queue items`);
      }

      return await Promise.all(
        allRecords.map(item => this.processQueueItem(item))
      );
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

    const size = (item.size || 0) / (1024 * 1024 * 1024);
    
    let timeLeft: string;
    if (item.estimatedCompletionTime && (item.status === 'downloading' || item.status === 'queued')) {
      timeLeft = `<t:${Math.floor(new Date(item.estimatedCompletionTime).getTime() / 1000)}:R>`;
    } else if (item.trackedDownloadState === 'importBlocked' && item.status === 'completed') {
      timeLeft = 'Manual action required';
    } else if (item.status === 'completed') {
      timeLeft = 'Processing...';
    } else if (item.estimatedCompletionTime) {
      timeLeft = `<t:${Math.floor(new Date(item.estimatedCompletionTime).getTime() / 1000)}:R>`;
    } else {
      timeLeft = this.parseTimeLeft(item.timeleft || '');
    }

    const mediaInfo = await this.getMediaInfo(item);

    let title = `${mediaInfo.series} - S${mediaInfo.season.toString().padStart(2, '0')}E${mediaInfo.episode.toString().padStart(2, '0')}`;
    if (mediaInfo.episodeTitle) {
      title += `: ${mediaInfo.episodeTitle}`;
    }

    const result = {
      id: item.id,
      title,
      series: mediaInfo.series,
      season: mediaInfo.season,
      episode: mediaInfo.episode,
      progress,
      size,
      sizeLeft: item.sizeleft || 0,
      timeLeft,
      status: item.status,
      protocol: item.protocol || 'unknown',
      downloadClient: item.downloadClient || 'unknown',
      service: 'sonarr' as const,
      added: item.added,
      errorMessage: item.errorMessage,
    };

    return result;
  }

  private async getMediaInfo(queueItem: any): Promise<{ series: string; season: number; episode: number; episodeTitle?: string }> {
    const seriesId = queueItem.seriesId;
    const episodeId = queueItem.episodeId;

    if (!this.seriesCache.has(seriesId)) {
      const series = await this.makeRequest<any>(`/api/v3/series/${seriesId}`);
      this.seriesCache.set(seriesId, series);
    }
    const series = this.seriesCache.get(seriesId);

    if (!this.episodeCache.has(episodeId)) {
      const episode = await this.makeRequest<any>(`/api/v3/episode/${episodeId}`);
      this.episodeCache.set(episodeId, episode);
    }
    const episode = this.episodeCache.get(episodeId);

    return {
      series: series.title,
      season: episode.seasonNumber,
      episode: episode.episodeNumber,
      episodeTitle: episode.title && episode.title !== 'TBA' ? episode.title : undefined,
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

  async getStuckDownloads(): Promise<{id: number, title: string}[]> {
    try {
      const allRecords = await this.getAllPaginated<any>('/api/v3/queue', {
        includeUnknownSeriesItems: false,
        includeSeries: true,
        includeEpisode: true
      });

    const stuckItems = allRecords.filter(item => {
        const hasInfiniteTime = !item.estimatedCompletionTime && (!item.timeleft || item.timeleft === '∞');
        const progress = item.size && item.size > 0 && typeof item.sizeleft === 'number'
          ? 100 * (1 - item.sizeleft / item.size)
          : item.progress || 0;
        const hasProgress = progress > 0;
        return hasInfiniteTime && hasProgress;
      });

      const itemsWithTitles = await Promise.all(
        stuckItems.map(async (item) => {
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
        console.error('Failed to fetch Sonarr stuck downloads:', error);
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

  async getCalendarEpisodes(days: number = 7): Promise<CalendarEpisode[]> {
    try {
      const startDate = new Date();
      const endDate = new Date();
      endDate.setDate(startDate.getDate() + days);

      const episodes = await this.makeRequest<any[]>('/api/v3/calendar', 'GET', undefined, {
        start: startDate.toISOString().split('T')[0],
        end: endDate.toISOString().split('T')[0],
        includeSeries: true
      });

      return episodes.map(episode => ({
        id: episode.id,
        title: episode.title,
        seriesTitle: episode.series?.title || 'Unknown Series',
        seasonNumber: episode.seasonNumber,
        episodeNumber: episode.episodeNumber,
        airDateUtc: episode.airDateUtc,
        hasFile: episode.hasFile,
        monitored: episode.monitored,
        overview: episode.overview,
        seriesType: episode.series?.seriesType,
        network: episode.series?.network,
        status: episode.series?.status
      }));
    } catch (error) {
      if (this.verbose) {
        console.error('Failed to fetch calendar:', error);
      }
      return [];
    }
  }

  async getMissingEpisodes(seriesId: number): Promise<MissingEpisode[]> {
    try {
      const episodes = await this.makeRequest<any[]>(`/api/v3/episode`, 'GET', undefined, {
        seriesId,
        includeImages: false
      });

      const filteredRecords = episodes.filter(ep => !ep.hasFile && ep.monitored);

      return filteredRecords.map(episode => ({
        id: episode.id,
        title: episode.title,
        seriesTitle: episode.series?.title || 'Unknown Series',
        seriesId: episode.seriesId,
        seasonNumber: episode.seasonNumber,
        episodeNumber: episode.episodeNumber,
        airDateUtc: episode.airDateUtc,
        monitored: episode.monitored,
        overview: episode.overview
      }));
    } catch (error) {
      if (this.verbose) {
        console.error('Failed to fetch missing episodes:', error);
      }
      return [];
    }
  }

  async getSeriesList(): Promise<SeriesInfo[]> {
    try {
      const series = await this.makeRequest<any[]>('/api/v3/series');
      
      return series.map(s => ({
        id: s.id,
        title: s.title,
        year: s.year,
        status: s.status,
        monitored: s.monitored,
        seasonCount: s.statistics?.seasonCount || 0,
        episodeFileCount: s.statistics?.episodeFileCount || 0,
        episodeCount: s.statistics?.episodeCount || 0,
        network: s.network
      }));
    } catch (error) {
      if (this.verbose) {
        console.error('Failed to fetch series list:', error);
      }
      return [];
    }
  }

  async getSeriesById(seriesId: number): Promise<SeriesInfo | null> {
    try {
      const series = await this.makeRequest<any>(`/api/v3/series/${seriesId}`);
      
      return {
        id: series.id,
        title: series.title,
        year: series.year,
        status: series.status,
        monitored: series.monitored,
        seasonCount: series.statistics?.seasonCount || 0,
        episodeFileCount: series.statistics?.episodeFileCount || 0,
        episodeCount: series.statistics?.episodeCount || 0,
        network: series.network
      };
    } catch (error) {
      if (this.verbose) {
        console.error('Failed to fetch series by ID:', error);
      }
      return null;
    }
  }

  async searchForMissingEpisodes(seriesId: number): Promise<boolean> {
    try {
      await this.makeRequest('/api/v3/command', 'POST', {
        name: 'SeriesSearch',
        seriesId: seriesId
      });
      return true;
    } catch (error) {
      if (this.verbose) {
        console.error('Failed to trigger series search:', error);
      }
      return false;
    }
  }

  async getDetailedBlockedItem(id: number): Promise<any> {
    const allRecords = await this.getAllPaginated<any>('/api/v3/queue', {
      includeUnknownSeriesItems: false,
      includeSeries: true,
      includeEpisode: true
    });

    const item = allRecords.find(record => record.id === id && 
      (record.trackedDownloadState === 'importBlocked' || record.status === 'importBlocked'));
    
    if (!item) {
      throw new Error(`Import blocked item with ID ${id} not found`);
    }

    return item;
  }

  async approveImport(id: number): Promise<boolean> {
    const item = await this.getDetailedBlockedItem(id);
    await this.makeRequest('/api/v3/manualimport', 'PUT', undefined, [{
      id: item.downloadId,
      seriesId: item.seriesId,
      episodeIds: [item.episodeId],
      series: item.series,
      episodes: [item.episode],
      quality: item.quality,
      languages: item.languages,
      downloadId: item.downloadId
    }]);
    return true;
  }
}
