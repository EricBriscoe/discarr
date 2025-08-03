import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { ServiceStatus } from '../types';

export abstract class BaseClient {
  protected client: AxiosInstance;
  protected verbose: boolean;

  constructor(baseURL: string, apiKey?: string, verbose = false) {
    this.verbose = verbose;
    this.client = axios.create({
      baseURL: baseURL.replace(/\/$/, ''),
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
        ...(apiKey && { 'X-Api-Key': apiKey }),
      },
    });
  }

  protected async makeRequest<T>(endpoint: string, params?: Record<string, any>): Promise<T> {
    try {
      const response: AxiosResponse<T> = await this.client.get(endpoint, { params });
      return response.data;
    } catch (error) {
      if (this.verbose) {
        console.error(`Request failed for ${endpoint}:`, error);
      }
      throw error;
    }
  }

  protected parseTimeLeft(timeStr: string): string {
    if (!timeStr || timeStr === '00:00:00') return '∞';
    
    const parts = timeStr.split(':');
    if (parts.length !== 3) return timeStr;
    
    const hours = parseInt(parts[0]);
    const minutes = parseInt(parts[1]);
    
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else if (minutes > 0) {
      return `${minutes}m`;
    } else {
      return '< 1m';
    }
  }

  abstract checkHealth(): Promise<ServiceStatus>;
}