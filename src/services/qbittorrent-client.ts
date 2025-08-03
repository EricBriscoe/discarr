import { ServiceStatus } from '../types.js';

interface QBittorrentTorrent {
  hash: string;
  name: string;
  state: string;
  tags: string;
  category: string;
  progress: number;
  size: number;
  completed: number;
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
    this.baseUrl = config.baseUrl.replace(/\/$/, '');
    this.username = config.username;
    this.password = config.password;
  }

  async checkHealth(): Promise<ServiceStatus> {
    try {
      await this.authenticate();
      return {
        status: 'online',
        lastCheck: new Date(),
        version: 'Unknown'
      };
    } catch (error) {
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

    const response = await fetch(`${this.baseUrl}/api/v2/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': this.baseUrl
      },
      body: formData
    });

    if (!response.ok) {
      throw new Error(`qBittorrent authentication failed: ${response.status}`);
    }

    const setCookieHeader = response.headers.get('set-cookie');
    if (setCookieHeader) {
      this.sessionCookie = setCookieHeader.split(';')[0];
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
      body
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
}