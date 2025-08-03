import { BaseClient } from './base-client';
import { ServiceStatus } from '../types';

export class PlexClient extends BaseClient {
  private baseURL: string;

  constructor(baseURL: string, verbose = false) {
    super(baseURL, undefined, verbose);
    this.baseURL = baseURL;
  }

  async checkHealth(): Promise<ServiceStatus> {
    const startTime = Date.now();
    
    try {
      const htmlResponse = await this.makeRequest<string>('/web/index.html');
      const responseTime = Date.now() - startTime;
      
      // Check if response contains Plex identifier
      if (htmlResponse && htmlResponse.includes('Plex')) {
        return {
          status: 'online',
          lastCheck: new Date(),
          responseTime,
          version: 'Running',
        };
      } else {
        throw new Error('Invalid Plex response');
      }
    } catch (error: any) {
      let errorMessage = error.message;
      if (error.code === 'EHOSTUNREACH') {
        errorMessage = 'Host unreachable - check network configuration';
      } else if (error.code === 'ECONNREFUSED') {
        errorMessage = 'Connection refused - Plex may be down';
      } else if (error.code === 'ETIMEDOUT') {
        errorMessage = 'Connection timed out';
      }
      
      return {
        status: 'offline',
        lastCheck: new Date(),
        responseTime: Date.now() - startTime,
        error: errorMessage,
      };
    }
  }
}