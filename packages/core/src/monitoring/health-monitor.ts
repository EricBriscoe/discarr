import { HealthStatus, ServiceStatus, QBittorrentStatus, RadarrStatus, SonarrStatus } from '../types';
import { RadarrClient } from '../services/radarr-client';
import { SonarrClient } from '../services/sonarr-client';
import { PlexClient } from '../services/plex-client';
import { QBittorrentClient } from '../services/qbittorrent-client';
import defaultConfig, { type Config } from '../config';

export class HealthMonitor {
  private config: Config;
  private radarrClient?: RadarrClient;
  private sonarrClient?: SonarrClient;
  private plexClient?: PlexClient;
  private qbittorrentClient?: QBittorrentClient;

  constructor(configOverride?: Config) {
    this.config = configOverride ?? defaultConfig;

    if (this.config.services.radarr) {
      this.radarrClient = new RadarrClient(
        this.config.services.radarr.url,
        this.config.services.radarr.apiKey,
        this.config.monitoring.verbose
      );
    }

    if (this.config.services.sonarr) {
      this.sonarrClient = new SonarrClient(
        this.config.services.sonarr.url,
        this.config.services.sonarr.apiKey,
        this.config.monitoring.verbose
      );
    }

    if (this.config.services.plex) {
      this.plexClient = new PlexClient(
        this.config.services.plex.url,
        this.config.monitoring.verbose
      );
    }

    if (this.config.services.qbittorrent) {
      this.qbittorrentClient = new QBittorrentClient({
        baseUrl: this.config.services.qbittorrent.url,
        username: this.config.services.qbittorrent.username,
        password: this.config.services.qbittorrent.password
      });
    }
  }

  async checkAllServices(): Promise<HealthStatus> {
    const checks: Promise<[string, ServiceStatus | QBittorrentStatus]>[] = [];

    if (this.radarrClient) {
      checks.push(
        this.radarrClient.checkHealth().then(async status => {
          const s: RadarrStatus = { ...status };
          try { s.queueStats = await this.radarrClient!.getQueueSummary(); } catch {}
          return ['radarr', s] as [string, RadarrStatus];
        })
      );
    }

    if (this.sonarrClient) {
      checks.push(
        this.sonarrClient.checkHealth().then(async status => {
          const s: SonarrStatus = { ...status };
          try { s.queueStats = await this.sonarrClient!.getQueueSummary(); } catch {}
          return ['sonarr', s] as [string, SonarrStatus];
        })
      );
    }

    if (this.plexClient) {
      checks.push(
        this.plexClient.checkHealth().then(status => ['plex', status] as [string, ServiceStatus])
      );
    }

    if (this.qbittorrentClient) {
      checks.push(
        this.checkQBittorrentHealth().then(status => ['qbittorrent', status] as [string, QBittorrentStatus])
      );
    }

    const results = await Promise.allSettled(checks);
    const healthStatus: HealthStatus = {
      lastUpdated: new Date(),
    };

    results.forEach((result, index) => {
      if (result.status === 'fulfilled') {
        const [service, status] = result.value;
        (healthStatus as any)[service] = status;
      } else {
        const serviceNames = [] as string[];
        if (this.radarrClient) serviceNames.push('radarr');
        if (this.sonarrClient) serviceNames.push('sonarr');
        if (this.plexClient) serviceNames.push('plex');
        if (this.qbittorrentClient) serviceNames.push('qbittorrent');
        const service = serviceNames[index];
        if (service) {
          (healthStatus as any)[service] = {
            status: 'error' as const,
            lastCheck: new Date(),
            error: 'Health check failed',
          };
        }
      }
    });

    return healthStatus;
  }

  getRadarrClient(): RadarrClient | undefined {
    return this.radarrClient;
  }

  getSonarrClient(): SonarrClient | undefined {
    return this.sonarrClient;
  }

  getQBittorrentClient(): QBittorrentClient | undefined {
    return this.qbittorrentClient;
  }

  private async checkQBittorrentHealth(): Promise<QBittorrentStatus> {
    const startTime = Date.now();
    try {
      const basicHealth = await this.qbittorrentClient!.checkHealth();
      const responseTime = Date.now() - startTime;
      if (basicHealth.status === 'online') {
        const [transferInfo, torrentStats] = await Promise.allSettled([
          this.qbittorrentClient!.getTransferInfo(),
          this.qbittorrentClient!.getTorrentStats()
        ]);
        return {
          status: 'online',
          lastCheck: new Date(),
          responseTime,
          transferInfo: transferInfo.status === 'fulfilled' ? transferInfo.value : undefined,
          torrentStats: torrentStats.status === 'fulfilled' ? torrentStats.value : undefined,
        };
      } else {
        return {
          status: basicHealth.status as 'online' | 'offline' | 'error',
          lastCheck: new Date(),
          responseTime,
          error: (basicHealth as any).error,
        };
      }
    } catch (error: any) {
      return {
        status: 'error',
        lastCheck: new Date(),
        responseTime: Date.now() - startTime,
        error: error.message,
      };
    }
  }
}
