import { HealthStatus, ServiceStatus, QBittorrentStatus } from '../types';
import { RadarrClient } from '../services/radarr-client';
import { SonarrClient } from '../services/sonarr-client';
import { PlexClient } from '../services/plex-client';
import { QBittorrentClient } from '../services/qbittorrent-client';
import config from '../config';

export class HealthMonitor {
  private radarrClient?: RadarrClient;
  private sonarrClient?: SonarrClient;
  private plexClient?: PlexClient;
  private qbittorrentClient?: QBittorrentClient;

  constructor() {
    if (config.services.radarr) {
      this.radarrClient = new RadarrClient(
        config.services.radarr.url,
        config.services.radarr.apiKey,
        config.monitoring.verbose
      );
    }

    if (config.services.sonarr) {
      this.sonarrClient = new SonarrClient(
        config.services.sonarr.url,
        config.services.sonarr.apiKey,
        config.monitoring.verbose
      );
    }

    if (config.services.plex) {
      this.plexClient = new PlexClient(
        config.services.plex.url,
        config.monitoring.verbose
      );
    }

    if (config.services.qbittorrent) {
      this.qbittorrentClient = new QBittorrentClient({
        baseUrl: config.services.qbittorrent.url,
        username: config.services.qbittorrent.username,
        password: config.services.qbittorrent.password
      });
    }
  }

  async checkAllServices(): Promise<HealthStatus> {
    console.log('🏥 Starting health check for all services...');
    const checks: Promise<[string, ServiceStatus | QBittorrentStatus]>[] = [];

    if (this.radarrClient) {
      console.log('📹 Adding Radarr health check');
      checks.push(
        this.radarrClient.checkHealth().then(status => ['radarr', status] as [string, ServiceStatus])
      );
    }

    if (this.sonarrClient) {
      console.log('📺 Adding Sonarr health check');
      checks.push(
        this.sonarrClient.checkHealth().then(status => ['sonarr', status] as [string, ServiceStatus])
      );
    }

    if (this.plexClient) {
      console.log('🎞️ Adding Plex health check');
      checks.push(
        this.plexClient.checkHealth().then(status => ['plex', status] as [string, ServiceStatus])
      );
    }

    if (this.qbittorrentClient) {
      console.log('🏴‍☠️ Adding qBittorrent health check');
      checks.push(
        this.checkQBittorrentHealth().then(status => ['qbittorrent', status] as [string, QBittorrentStatus])
      );
    }

    console.log(`⚡ Running ${checks.length} health checks...`);
    const results = await Promise.allSettled(checks);
    const healthStatus: HealthStatus = {
      lastUpdated: new Date(),
    };

    results.forEach((result, index) => {
      if (result.status === 'fulfilled') {
        const [service, status] = result.value;
        console.log(`✅ ${service} health check completed: ${status.status}`);
        (healthStatus as any)[service] = status;
      } else {
        console.error(`❌ Health check ${index} failed:`, result.reason);
        // Handle failed health checks
        const serviceNames = [];
        if (this.radarrClient) serviceNames.push('radarr');
        if (this.sonarrClient) serviceNames.push('sonarr');
        if (this.plexClient) serviceNames.push('plex');
        if (this.qbittorrentClient) serviceNames.push('qbittorrent');
        
        const service = serviceNames[index];
        if (service) {
          console.log(`⚠️ Setting ${service} to error status`);
          (healthStatus as any)[service] = {
            status: 'error' as const,
            lastCheck: new Date(),
            error: 'Health check failed',
          };
        }
      }
    });

    console.log('🏥 Health check summary:');
    console.log(`- Plex: ${healthStatus.plex?.status || 'not configured'}`);
    console.log(`- Radarr: ${healthStatus.radarr?.status || 'not configured'}`);
    console.log(`- Sonarr: ${healthStatus.sonarr?.status || 'not configured'}`);
    console.log(`- qBittorrent: ${healthStatus.qbittorrent?.status || 'not configured'}`);

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
    console.log('🔍 Starting qBittorrent health check...');
    const startTime = Date.now();
    
    try {
      console.log('🔐 Checking qBittorrent basic health...');
      const basicHealth = await this.qbittorrentClient!.checkHealth();
      const responseTime = Date.now() - startTime;
      console.log(`✅ qBittorrent basic health: ${basicHealth.status} (${responseTime}ms)`);

      if (basicHealth.status === 'online') {
        console.log('📊 Fetching qBittorrent transfer info and torrent stats...');
        const [transferInfo, torrentStats] = await Promise.allSettled([
          this.qbittorrentClient!.getTransferInfo(),
          this.qbittorrentClient!.getTorrentStats()
        ]);

        console.log(`📈 Transfer info result: ${transferInfo.status}`);
        console.log(`🎯 Torrent stats result: ${torrentStats.status}`);

        if (transferInfo.status === 'rejected') {
          console.error('❌ Transfer info failed:', transferInfo.reason);
        } else {
          const info = transferInfo.value;
          console.log(`📊 Transfer info: DL ${info.dl_info_speed} B/s, UL ${info.up_info_speed} B/s, DHT ${info.dht_nodes}`);
        }

        if (torrentStats.status === 'rejected') {
          console.error('❌ Torrent stats failed:', torrentStats.reason);
        } else {
          const stats = torrentStats.value;
          console.log(`🎯 Torrent stats: ${stats.totalTorrents} total, ${stats.downloading} downloading, ${stats.seeding} seeding`);
        }

        const result = {
          status: 'online' as const,
          lastCheck: new Date(),
          responseTime,
          transferInfo: transferInfo.status === 'fulfilled' ? transferInfo.value : undefined,
          torrentStats: torrentStats.status === 'fulfilled' ? torrentStats.value : undefined,
        };

        console.log('✅ qBittorrent health check completed successfully');
        return result;
      } else {
        console.log(`⚠️ qBittorrent not online: ${basicHealth.status} - ${basicHealth.error}`);
        return {
          status: basicHealth.status as 'online' | 'offline' | 'error',
          lastCheck: new Date(),
          responseTime,
          error: basicHealth.error,
        };
      }
    } catch (error: any) {
      console.error('❌ qBittorrent health check failed:', error);
      return {
        status: 'error' as const,
        lastCheck: new Date(),
        responseTime: Date.now() - startTime,
        error: error.message,
      };
    }
  }
}