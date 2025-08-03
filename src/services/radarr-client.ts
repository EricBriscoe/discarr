import { BaseClient } from './base-client';
import { ServiceStatus, MovieDownloadItem } from '../types';

export class RadarrClient extends BaseClient {
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
      const response = await this.makeRequest<{ records: any[] }>('/api/v3/queue', {
        pageSize: 50,
        includeUnknownMovieItems: false,
      });

      return response.records
        .filter(item => item.status === 'downloading' || item.status === 'queued')
        .map(item => this.processQueueItem(item))
        .sort((a, b) => b.progress - a.progress);
    } catch (error) {
      if (this.verbose) {
        console.error('Failed to fetch Radarr queue:', error);
      }
      return [];
    }
  }

  private processQueueItem(item: any): MovieDownloadItem {
    const progress = item.sizeleft && item.size && item.size > 0
      ? 100 * (1 - item.sizeleft / item.size)
      : item.progress || 0;

    const size = (item.size || 0) / (1024 * 1024 * 1024); // Convert to GB
    const timeLeft = item.estimatedCompletionTime 
      ? `<t:${Math.floor(new Date(item.estimatedCompletionTime).getTime() / 1000)}:R>`
      : this.parseTimeLeft(item.timeleft || '');

    return {
      id: item.id,
      title: item.title || 'Unknown Movie',
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
}