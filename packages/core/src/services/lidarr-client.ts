import { BaseClient } from './base-client';
import { ServiceStatus } from '../types';

export class LidarrClient extends BaseClient {
  async checkHealth(): Promise<ServiceStatus> {
    const startTime = Date.now();
    try {
      const response = await this.makeRequest<{ version: string }>('/api/v1/system/status');
      const responseTime = Date.now() - startTime;
      return { status: 'online', lastCheck: new Date(), responseTime, version: (response as any).version };
    } catch (error: any) {
      return { status: 'offline', lastCheck: new Date(), responseTime: Date.now() - startTime, error: error.message };
    }
  }

  async getQueueSummary(): Promise<import('../types').QueueStats> {
    try {
      const items = await this.getAllPaginated<any>('/api/v1/queue', {});
      const summary = { total: items.length, downloading: 0, queued: 0, completed: 0, importBlocked: 0, stuck: 0, failed: 0 };
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

  async getQueueItems(): Promise<any[]> {
    return this.getAllPaginated<any>('/api/v1/queue', {});
  }

  async removeQueueItems(itemIds: number[], blocklist: boolean): Promise<{id:number; success:boolean; error?:string}[]> {
    const results = await Promise.allSettled(itemIds.map(async (id)=>{
      try {
        await this.makeRequest(`/api/v1/queue/${id}`, 'DELETE', undefined, { removeFromClient: true, blocklist });
        return { id, success: true };
      } catch (e:any) {
        return { id, success: false, error: e?.message || 'Unknown error' };
      }
    }));
    return results.map(r=> r.status==='fulfilled'? r.value : {id:0, success:false, error:'Promise rejected'});
  }
}

