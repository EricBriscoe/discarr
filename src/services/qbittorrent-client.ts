import { ServiceStatus } from '../types.js';
import fetch from 'node-fetch';

export interface QBittorrentTorrent {
  hash: string;
  name: string;
  state: string;
  tags: string;
  category: string;
  progress: number;
  size: number;
  completed: number;
}

export interface QBittorrentTransferInfo {
  dl_info_speed: number;
  dl_info_data: number;
  up_info_speed: number;
  up_info_data: number;
  dl_rate_limit: number;
  up_rate_limit: number;
  dht_nodes: number;
  connection_status: string;
  queueing?: boolean;
  use_alt_speed_limits?: boolean;
  refresh_interval?: number;
}

export interface QBittorrentStats {
  totalTorrents: number;
  downloading: number;
  seeding: number;
  paused: number;
  stalled: number;
  error: number;
  queued: number;
}

interface QBittorrentConfig {
  baseUrl: string;
  username: string;
  password: string;
}

export class QBittorrentClient {
  private baseUrl: string;
  private username: string;
  private password: string;
  private sessionCookie?: string;

  constructor(config: QBittorrentConfig) {
    console.log('🔧 Initializing qBittorrent client with config:', {
      baseUrl: config.baseUrl,
      username: config.username,
      hasPassword: config.password ? 'yes' : 'no',
      passwordLength: config.password ? config.password.length : 0
    });
    
    this.baseUrl = config.baseUrl.replace(/\/$/, '');
    this.username = config.username;
    this.password = config.password;
    
    console.log(`✅ qBittorrent client initialized - baseUrl: ${this.baseUrl}`);
  }

  async checkHealth(): Promise<ServiceStatus> {
    console.log(`🔍 qBittorrent health check - connecting to: ${this.baseUrl}`);
    try {
      console.log('🔐 Attempting qBittorrent authentication...');
      await this.authenticate();
      console.log('✅ qBittorrent authentication successful');
      return {
        status: 'online',
        lastCheck: new Date(),
        version: 'Unknown'
      };
    } catch (error) {
      console.error('❌ qBittorrent health check failed with detailed error:', {
        message: error instanceof Error ? error.message : 'Unknown error',
        stack: error instanceof Error ? error.stack : 'No stack trace',
        name: error instanceof Error ? error.name : 'Unknown error type',
        cause: error instanceof Error && 'cause' in error ? error.cause : 'No cause',
        code: error instanceof Error && 'code' in error ? (error as any).code : 'No error code',
        errno: error instanceof Error && 'errno' in error ? (error as any).errno : 'No errno',
        syscall: error instanceof Error && 'syscall' in error ? (error as any).syscall : 'No syscall',
        address: error instanceof Error && 'address' in error ? (error as any).address : 'No address',
        port: error instanceof Error && 'port' in error ? (error as any).port : 'No port'
      });
      return {
        status: 'error',
        lastCheck: new Date(),
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  async authenticate(): Promise<void> {
    const formData = new URLSearchParams();
    formData.append('username', this.username);
    formData.append('password', this.password);

    const authUrl = `${this.baseUrl}/api/v2/auth/login`;
    console.log(`🔐 Making authentication request to: ${authUrl}`);
    console.log(`👤 Using username: ${this.username}`);

    try {
      const response = await fetch(authUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Referer': this.baseUrl,
          'User-Agent': 'Discarr-qBittorrent-Client/2.0.0'
        },
        body: formData,
        signal: AbortSignal.timeout(10000) // 10 second timeout
      });

      console.log(`📡 Authentication response status: ${response.status} ${response.statusText}`);
      
      if (!response.ok) {
        const responseText = await response.text();
        console.error(`❌ Authentication failed - Response: ${responseText}`);
        throw new Error(`qBittorrent authentication failed: ${response.status} ${response.statusText}`);
      }

      const responseText = await response.text();
      console.log(`📝 Authentication response body: "${responseText}"`);

      const setCookieHeader = response.headers.get('set-cookie');
      console.log(`🍪 Set-Cookie header: ${setCookieHeader}`);
      
      if (setCookieHeader) {
        this.sessionCookie = setCookieHeader.split(';')[0];
        console.log(`✅ Session cookie set: ${this.sessionCookie}`);
      } else {
        console.log('⚠️ No set-cookie header received');
      }
    } catch (fetchError) {
      console.error('❌ Fetch error during authentication:', {
        message: fetchError instanceof Error ? fetchError.message : 'Unknown fetch error',
        stack: fetchError instanceof Error ? fetchError.stack : 'No stack trace',
        name: fetchError instanceof Error ? fetchError.name : 'Unknown error type',
        cause: fetchError instanceof Error && 'cause' in fetchError ? fetchError.cause : 'No cause'
      });
      throw fetchError;
    }
  }

  private async authenticatedRequest<T>(
    endpoint: string, 
    method: 'GET' | 'POST' = 'GET',
    data?: any
  ): Promise<T> {
    if (!this.sessionCookie) {
      await this.authenticate();
    }

    const headers: Record<string, string> = {
      'Referer': this.baseUrl
    };

    if (this.sessionCookie) {
      headers['Cookie'] = this.sessionCookie;
    }

    let body: string | URLSearchParams | undefined;
    if (data && method === 'POST') {
      if (data instanceof URLSearchParams) {
        body = data;
        headers['Content-Type'] = 'application/x-www-form-urlencoded';
      } else {
        body = JSON.stringify(data);
        headers['Content-Type'] = 'application/json';
      }
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method,
      headers,
      body,
      signal: AbortSignal.timeout(10000)
    });

    if (!response.ok) {
      if (response.status === 403) {
        this.sessionCookie = undefined;
        await this.authenticate();
        return this.authenticatedRequest(endpoint, method, data);
      }
      throw new Error(`qBittorrent API error: ${response.status}`);
    }

    const text = await response.text();
    return text ? JSON.parse(text) : {} as T;
  }

  async getTorrents(): Promise<QBittorrentTorrent[]> {
    return this.authenticatedRequest<QBittorrentTorrent[]>('/api/v2/torrents/info');
  }

  async getSeedinOrStalledTorrentsWithLabels(): Promise<{hash: string, name: string, category: string, state: string}[]> {
    const torrents = await this.getTorrents();
    
    return torrents
      .filter(torrent => {
        const hasRequiredCategory = torrent.category && 
          (torrent.category === 'sonarr' || torrent.category === 'radarr');
        const isTargetState = torrent.state === 'stalledUP' || 
                             torrent.state === 'stalledDL' ||
                             torrent.state === 'metaDL' ||
                             torrent.state === 'uploading' || 
                             torrent.state === 'queuedUP';
        
        return hasRequiredCategory && isTargetState;
      })
      .map(torrent => ({
        hash: torrent.hash,
        name: torrent.name,
        category: torrent.category,
        state: torrent.state
      }));
  }

  async deleteTorrents(hashes: string[], deleteFiles: boolean = true): Promise<{success: boolean, hash: string}[]> {
    const formData = new URLSearchParams();
    formData.append('hashes', hashes.join('|'));
    formData.append('deleteFiles', deleteFiles.toString());

    try {
      await this.authenticatedRequest('/api/v2/torrents/delete', 'POST', formData);
      return hashes.map(hash => ({ success: true, hash }));
    } catch (error) {
      console.error('Failed to delete torrents:', error);
      return hashes.map(hash => ({ success: false, hash }));
    }
  }

  async getTransferInfo(): Promise<QBittorrentTransferInfo> {
    return this.authenticatedRequest<QBittorrentTransferInfo>('/api/v2/transfer/info');
  }

  async getTorrentStats(): Promise<QBittorrentStats> {
    const torrents = await this.getTorrents();
    
    const stats = {
      totalTorrents: torrents.length,
      downloading: 0,
      seeding: 0,
      paused: 0,
      stalled: 0,
      error: 0,
      queued: 0
    };

    torrents.forEach(torrent => {
      switch (torrent.state) {
        case 'downloading':
        case 'metaDL':
        case 'allocating':
          stats.downloading++;
          break;
        case 'uploading':
        case 'stalledUP':
          stats.seeding++;
          break;
        case 'pausedDL':
        case 'pausedUP':
          stats.paused++;
          break;
        case 'stalledDL':
          stats.stalled++;
          break;
        case 'error':
        case 'missingFiles':
          stats.error++;
          break;
        case 'queuedDL':
        case 'queuedUP':
          stats.queued++;
          break;
      }
    });

    return stats;
  }

  static formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  static formatSpeed(bytesPerSecond: number): string {
    if (bytesPerSecond === 0) return '0 B/s';
    return this.formatBytes(bytesPerSecond) + '/s';
  }
}