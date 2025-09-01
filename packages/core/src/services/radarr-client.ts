import { BaseClient } from './base-client';
import { ServiceStatus, MovieDownloadItem } from '../types';

export class RadarrClient extends BaseClient {
  private movieCache = new Map<number, any>();
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

  async getQueueItems(): Promise<any[]> {
    return this.getAllPaginated<any>('/api/v3/queue', { includeUnknownMovieItems: false, includeMovie: true });
  }

  async removeQueueItemsWithBlocklist(itemIds: number[], blocklist: boolean): Promise<{id:number; success:boolean; error?:string}[]> {
    const results = await Promise.allSettled(
      itemIds.map(async (id) => {
        try {
          await this.makeRequest(`/api/v3/queue/${id}`, 'DELETE', undefined, {
            removeFromClient: true,
            blocklist
          });
          return { id, success: true };
        } catch (error:any) {
          return { id, success: false, error: error?.message || 'Unknown error' };
        }
      })
    );
    return results.map(r=> r.status==='fulfilled'? r.value : { id:0, success:false, error:'Promise rejected' });
  }

  async getQueueSummary(): Promise<import('../types').QueueStats> {
    try {
      const items = await this.getAllPaginated<any>('/api/v3/queue', {
        includeUnknownMovieItems: false,
        includeMovie: true
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

  async getActiveDownloads(): Promise<MovieDownloadItem[]> {
    try {
      const allRecords = await this.getAllPaginated<any>('/api/v3/queue', {
        includeUnknownMovieItems: false,
        includeMovie: true
      });

      if (this.verbose) {
        console.log(`Processing ${allRecords.length} Radarr queue items`);
      }

      return await Promise.all(
        allRecords.map(item => this.processQueueItem(item))
      );
    } catch (error) {
      if (this.verbose) {
        console.error('Failed to fetch Radarr queue:', error);
      }
      return [];
    }
  }

  async getImportBlockedItems(): Promise<{id: number, title: string}[]> {
    try {
      const allRecords = await this.getAllPaginated<any>('/api/v3/queue', {
        includeUnknownMovieItems: false,
        includeMovie: true
      });

      return allRecords
        .filter(item => (item.trackedDownloadState || item.status) === 'importBlocked')
        .map(item => ({
          id: item.id,
          title: item.title || 'Unknown Movie'
        }));
    } catch (error) {
      if (this.verbose) {
        console.error('Failed to fetch Radarr importBlocked items:', error);
      }
      return [];
    }
  }

  async getStuckDownloads(): Promise<{id: number, title: string}[]> {
    try {
      const allRecords = await this.getAllPaginated<any>('/api/v3/queue', {
        includeUnknownMovieItems: false,
        includeMovie: true
      });

      return allRecords
        .filter(item => {
          const hasInfiniteTime = !item.estimatedCompletionTime && (!item.timeleft || item.timeleft === '∞');
          const progress = item.size && item.size > 0 && typeof item.sizeleft === 'number'
            ? 100 * (1 - item.sizeleft / item.size)
            : item.progress || 0;
          const hasProgress = progress > 0;
          return hasInfiniteTime && hasProgress;
        })
        .map(item => ({
          id: item.id,
          title: item.title || 'Unknown Movie'
        }));
    } catch (error) {
      if (this.verbose) {
        console.error('Failed to fetch Radarr stuck downloads:', error);
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

  private async processQueueItem(item: any): Promise<MovieDownloadItem> {
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

    const cleanTitle = await this.getCleanMovieTitle(item);

    const result = {
      id: item.id,
      title: cleanTitle,
      progress,
      size,
      sizeLeft: item.sizeleft || 0,
      timeLeft,
      status: item.status,
      protocol: item.protocol || 'unknown',
      downloadClient: item.downloadClient || 'unknown',
      service: 'radarr' as const,
      added: item.added,
      errorMessage: item.errorMessage,
    };

    return result;
  }

  private async getCleanMovieTitle(queueItem: any): Promise<string> {
    const movieId = queueItem.movieId;
    
    if (!movieId) {
      return queueItem.title;
    }

    if (!this.movieCache.has(movieId)) {
      const movie = await this.makeRequest<any>(`/api/v3/movie/${movieId}`);
      this.movieCache.set(movieId, movie);
    }

    const movie = this.movieCache.get(movieId);
    const year = movie.year ? ` (${movie.year})` : '';
    return `${movie.title}${year}`;
  }

  async getDetailedBlockedItem(id: number): Promise<any> {
    const allRecords = await this.getAllPaginated<any>('/api/v3/queue', {
      includeUnknownMovieItems: false,
      includeMovie: true
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
      movieId: item.movieId,
      movie: item.movie,
      quality: item.quality,
      languages: item.languages,
      downloadId: item.downloadId
    }]);
    return true;
  }
}
