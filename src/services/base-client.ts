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
      family: 4, // Force IPv4
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'Discarr/2.0.0',
        ...(apiKey && { 'X-Api-Key': apiKey }),
      },
    });
  }

  protected async makeRequest<T>(
    endpoint: string, 
    method: 'GET' | 'POST' | 'PUT' | 'DELETE' = 'GET',
    data?: any,
    params?: Record<string, any>, 
    headers?: Record<string, string>
  ): Promise<T> {
    try {
      const config = {
        ...(params && { params }),
        ...(headers && { headers }),
        ...(data && { data })
      };

      let response: AxiosResponse<T>;
      
      switch (method) {
        case 'GET':
          response = await this.client.get(endpoint, config);
          break;
        case 'POST':
          response = await this.client.post(endpoint, data, config);
          break;
        case 'PUT':
          response = await this.client.put(endpoint, data, config);
          break;
        case 'DELETE':
          response = await this.client.delete(endpoint, config);
          break;
        default:
          throw new Error(`Unsupported HTTP method: ${method}`);
      }
      
      return response.data;
    } catch (error) {
      if (this.verbose) {
        console.error(`${method} request failed for ${endpoint}:`, error);
      }
      throw error;
    }
  }

  protected async getAllPaginated<T>(
    endpoint: string, 
    baseParams: Record<string, any> = {},
    pageSize: number = 100
  ): Promise<T[]> {
    const allItems: T[] = [];
    let page = 1;
    let totalRecords: number | null = null;

    while (true) {
      const params = { 
        ...baseParams, 
        page, 
        pageSize 
      };

      if (this.verbose) {
        console.log(`Fetching page ${page} for ${endpoint}`);
      }

      try {
        const response = await this.makeRequest<{ records: T[]; totalRecords: number }>(
          endpoint, 
          'GET',
          undefined,
          params
        );

        const records = response.records || [];
        if (records.length === 0) {
          break; // No more records
        }

        allItems.push(...records);

        // Get total on first page
        if (totalRecords === null) {
          totalRecords = response.totalRecords || 0;
          if (this.verbose) {
            console.log(`Total records available: ${totalRecords}`);
          }
        }

        // Check if we've got all items or if this page wasn't full
        if (allItems.length >= totalRecords || records.length < pageSize) {
          break;
        }

        page++;
      } catch (error) {
        if (this.verbose) {
          console.error(`Failed to fetch page ${page} for ${endpoint}:`, error);
        }
        break;
      }
    }

    if (this.verbose) {
      console.log(`Fetched ${allItems.length} total items from ${endpoint}`);
    }

    return allItems;
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