import { BaseClient } from './base-client';
import { ServiceStatus } from '../types';
import { parseString } from 'xml2js';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export class PlexClient extends BaseClient {
  private baseURL: string;

  constructor(baseURL: string, verbose = false) {
    super(baseURL, undefined, verbose);
    this.baseURL = baseURL;
  }

  async checkHealth(): Promise<ServiceStatus> {
    const startTime = Date.now();
    
    try {
      // First try the normal axios request
      try {
        const xmlResponse = await this.makeRequest<string>('/identity');
        const responseTime = Date.now() - startTime;
        
        // Parse XML response
        const parsedData = await new Promise<any>((resolve, reject) => {
          parseString(xmlResponse, (err, result) => {
            if (err) reject(err);
            else resolve(result);
          });
        });

        const mediaContainer = parsedData?.MediaContainer?.$;
        const version = mediaContainer?.version || 'Unknown';
        
        return {
          status: 'online',
          lastCheck: new Date(),
          responseTime,
          version,
        };
      } catch (axiosError: any) {
        // If axios fails with EHOSTUNREACH, try curl as fallback
        if (axiosError.code === 'EHOSTUNREACH') {
          if (this.verbose) {
            console.log('Axios failed, attempting curl fallback for Plex...');
          }
          return await this.checkHealthWithCurl(startTime);
        }
        throw axiosError;
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

  private async checkHealthWithCurl(startTime: number): Promise<ServiceStatus> {
    try {
      const curlCommand = `curl -s --max-time 10 "${this.baseURL}/identity"`;
      const { stdout, stderr } = await execAsync(curlCommand);
      
      if (stderr && stderr.includes('connect')) {
        throw new Error('Curl connection failed: ' + stderr);
      }
      
      const responseTime = Date.now() - startTime;
      
      // Parse XML response from curl
      const parsedData = await new Promise<any>((resolve, reject) => {
        parseString(stdout, (err, result) => {
          if (err) reject(err);
          else resolve(result);
        });
      });

      const mediaContainer = parsedData?.MediaContainer?.$;
      const version = mediaContainer?.version || 'Unknown';
      
      if (this.verbose) {
        console.log('✅ Plex health check successful via curl fallback');
      }
      
      return {
        status: 'online',
        lastCheck: new Date(),
        responseTime,
        version,
      };
    } catch (curlError: any) {
      if (this.verbose) {
        console.log('❌ Curl fallback also failed:', curlError.message);
      }
      throw curlError;
    }
  }
}