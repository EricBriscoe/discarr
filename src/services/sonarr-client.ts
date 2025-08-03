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

  async getActiveDownloads(): Promise<TVDownloadItem[]> {
    try {
      // Use pagination to get ALL queue items
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

  async getStuckDownloads(): Promise<{id: number, title: string}[]> {
    try {
      const allRecords = await this.getAllPaginated<any>('/api/v3/queue', {
        includeUnknownSeriesItems: false,
        includeSeries: true,
        includeEpisode: true
      });

      const stuckItems = allRecords.filter(item => {
        // Check for infinite time remaining (no estimatedCompletionTime and no timeleft)
        const hasInfiniteTime = !item.estimatedCompletionTime && (!item.timeleft || item.timeleft === '∞');
        
        // Check if download has some progress (started but stuck)
        const progress = item.size && item.size > 0 && typeof item.sizeleft === 'number'
          ? 100 * (1 - item.sizeleft / item.size)
          : item.progress || 0;
        
        const hasProgress = progress > 0;
        
        // Only include items that are stuck (infinite time) but have started (have progress)
        return hasInfiniteTime && hasProgress;
      });

      // Get titles for stuck items
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
        console.error('Failed to fetch Sonarr calendar:', error);
      }
      return [];
    }
  }

  async searchSeries(query: string): Promise<SeriesSearchResult[]> {
    try {
      const results = await this.makeRequest<any[]>('/api/v3/series/lookup', 'GET', undefined, {
        term: query
      });

      return results.slice(0, 10).map(series => ({
        tvdbId: series.tvdbId,
        title: series.title,
        year: series.year,
        overview: series.overview,
        network: series.network,
        status: series.status,
        genres: series.genres || [],
        remotePoster: series.remotePoster,
        seasons: series.seasons?.length || 0
      }));
    } catch (error) {
      if (this.verbose) {
        console.error('Failed to search series:', error);
      }
      return [];
    }
  }

  async getMissingEpisodes(seriesId?: number): Promise<MissingEpisode[]> {
    try {
      const params: any = {
        page: 1,
        pageSize: 1000, // Increase page size to ensure we get all episodes for filtering
        sortKey: 'airDateUtc',
        sortDirection: 'descending',
        monitored: true
      };

      if (seriesId) {
        params.seriesId = seriesId;
      }

      const response = await this.makeRequest<{ records: any[] }>('/api/v3/wanted/missing', 'GET', undefined, params);

      // Filter by seriesId on our side since Sonarr API ignores the seriesId parameter 
      // when that series has no missing episodes and returns episodes from other series
      const filteredRecords = seriesId 
        ? response.records.filter(episode => episode.seriesId === seriesId)
        : response.records;

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
}