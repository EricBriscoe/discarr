import { BaseClient } from './base-client';
import { ServiceStatus } from '../types';

export class PlexClient extends BaseClient {
  constructor(baseURL: string, verbose = false) {
    super(baseURL, undefined, verbose);
  }

  async checkHealth(): Promise<ServiceStatus> {
    const startTime = Date.now();
    
    try {
      await this.makeRequest<any>('/', {
        headers: { 'Accept': 'application/xml' }
      });
      
      const responseTime = Date.now() - startTime;
      
      return {
        status: 'online',
        lastCheck: new Date(),
        responseTime,
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
}