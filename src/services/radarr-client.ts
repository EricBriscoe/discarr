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

  async getActiveDownloads(): Promise<MovieDownloadItem[]> {
    try {
      // Use pagination to get ALL queue items
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
          // Check for infinite time remaining (no estimatedCompletionTime and no timeleft)
          const hasInfiniteTime = !item.estimatedCompletionTime && (!item.timeleft || item.timeleft === '∞');
          
          // Check if download has some progress (started but stuck)
          const progress = item.size && item.size > 0 && typeof item.sizeleft === 'number'
            ? 100 * (1 - item.sizeleft / item.size)
            : item.progress || 0;
          
          const hasProgress = progress > 0;
          
          // Only include items that are stuck (infinite time) but have started (have progress)
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

    const size = (item.size || 0) / (1024 * 1024 * 1024); // Convert to GB
    const timeLeft = item.estimatedCompletionTime 
      ? `<t:${Math.floor(new Date(item.estimatedCompletionTime).getTime() / 1000)}:R>`
      : this.parseTimeLeft(item.timeleft || '');

    // Get clean movie title
    const cleanTitle = await this.getCleanMovieTitle(item);

    return {
      id: item.id,
      title: cleanTitle,
      progress,
      size,
      sizeLeft: item.sizeleft || 0,
      timeLeft,
      status: item.trackedDownloadState || item.status,
      protocol: item.protocol || 'unknown',
      downloadClient: item.downloadClient || 'unknown',
      service: 'radarr',
      added: item.added,
      errorMessage: item.errorMessage,
    };
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
}