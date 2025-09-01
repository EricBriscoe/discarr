import { ServiceStatus } from '../types';

declare const fetch: typeof globalThis.fetch;

export interface QBittorrentTorrent {
  hash: string;
  name: string;
  state: string;
  tags: string;
  category: string;
  progress: number;
  size: number;
  completed: number;
  // epoch seconds when torrent was added (as returned by qBittorrent API)
  added_on?: number;
  save_path?: string;
  content_path?: string;
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
    this.baseUrl = config.baseUrl.replace(/\/$/, '');
    this.username = config.username;
    this.password = config.password;
  }

  static formatSpeed(bytesPerSec: number): string {
    if (!bytesPerSec || bytesPerSec <= 0) return '0 B/s';
    const units = ['B/s', 'KB/s', 'MB/s', 'GB/s'];
    let value = bytesPerSec;
    let unitIndex = 0;
    while (value >= 1024 && unitIndex < units.length - 1) {
      value /= 1024;
      unitIndex++;
    }
    return `${value.toFixed(1)} ${units[unitIndex]}`;
  }

  static formatBytes(bytes: number): string {
    if (!bytes || bytes <= 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let value = bytes;
    let unitIndex = 0;
    while (value >= 1024 && unitIndex < units.length - 1) {
      value /= 1024;
      unitIndex++;
    }
    return `${value.toFixed(1)} ${units[unitIndex]}`;
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
    const authUrl = `${this.baseUrl}/api/v2/auth/login`;
    const response = await fetch(authUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': this.baseUrl,
        'User-Agent': 'Discarr-qBittorrent-Client/2.0.0'
      },
      body: formData,
      signal: AbortSignal.timeout(10000)
    });
    if (!response.ok) {
      const responseText = await response.text();
      throw new Error(`qBittorrent authentication failed: ${response.status} ${response.statusText} - ${responseText}`);
    }
    const setCookieHeader = response.headers.get('set-cookie');
    if (setCookieHeader) {
      this.sessionCookie = setCookieHeader.split(';')[0];
    }
  }

  private async authenticatedRequest<T>(endpoint: string, method: 'GET' | 'POST' = 'GET', data?: any): Promise<T> {
    if (!this.sessionCookie) {
      await this.authenticate();
    }
    const headers: Record<string, string> = { 'Referer': this.baseUrl };
    if (this.sessionCookie) headers['Cookie'] = this.sessionCookie;

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

  async getTorrentFiles(hash: string): Promise<Array<{ name: string; size: number }>> {
    const params = new URLSearchParams();
    params.append('hash', hash);
    return this.authenticatedRequest(`/api/v2/torrents/files?${params.toString()}`);
  }

  async getErroredTorrents(): Promise<Array<Pick<QBittorrentTorrent, 'hash' | 'name' | 'state' | 'category'>>> {
    const torrents = await this.getTorrents();
    return torrents
      .filter(t => t.state === 'error' || t.state === 'missingFiles')
      .map(t => ({ hash: t.hash, name: t.name, state: t.state, category: t.category }));
  }

  async recheckTorrents(hashes: string[]): Promise<{ success: boolean; hash: string }[]> {
    if (!hashes || hashes.length === 0) return [];
    const formData = new URLSearchParams();
    formData.append('hashes', hashes.join('|'));
    try {
      await this.authenticatedRequest('/api/v2/torrents/recheck', 'POST', formData);
      return hashes.map(hash => ({ success: true, hash }));
    } catch (_e) {
      return hashes.map(hash => ({ success: false, hash }));
    }
  }

  async getSeedinOrStalledTorrentsWithLabels(): Promise<{hash: string, name: string, category: string, state: string}[]> {
    const torrents = await this.getTorrents();
    return torrents
      .filter(torrent => {
        const cat = (torrent.category || '').toLowerCase();
        const tags = (torrent.tags || '').toLowerCase();
        const hasRequiredCategory = /sonarr|radarr/.test(cat) || /sonarr|radarr/.test(tags);
        const isTargetState = torrent.state === 'stalledUP' || torrent.state === 'stalledDL' || torrent.state === 'metaDL' || torrent.state === 'uploading' || torrent.state === 'queuedUP';
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
      return hashes.map(hash => ({ success: false, hash }));
    }
  }

  async getTransferInfo(): Promise<QBittorrentTransferInfo> {
    return this.authenticatedRequest<QBittorrentTransferInfo>('/api/v2/transfer/info');
  }

  // Set qBittorrent application preferences. Only include keys you want to change.
  // Example keys: queueing_max_active_downloads, queueing_max_active_uploads, queueing_max_active_torrents
  async setPreferences(prefs: Record<string, any>): Promise<void> {
    const formData = new URLSearchParams();
    formData.append('json', JSON.stringify(prefs));
    await this.authenticatedRequest('/api/v2/app/setPreferences', 'POST', formData);
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
    } as QBittorrentStats;

    for (const t of torrents) {
      switch (t.state) {
        case 'downloading':
        case 'stalledDL':
        case 'metaDL':
        case 'forcedDL':
        case 'queuedDL':
          stats.downloading++;
          break;
        case 'uploading':
        case 'stalledUP':
        case 'queuedUP':
        case 'forcedUP':
          stats.seeding++;
          break;
        case 'pausedDL':
        case 'pausedUP':
          stats.paused++;
          break;
        case 'error':
          stats.error++;
          break;
        case 'queued':
          stats.queued++;
          break;
        default:
          break;
      }
    }

    return stats;
  }
}

// Types are already exported via their interface declarations above.
