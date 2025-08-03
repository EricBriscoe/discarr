import { HealthStatus, ServiceStatus } from '../types';
import { RadarrClient } from '../services/radarr-client';
import { SonarrClient } from '../services/sonarr-client';
import { PlexClient } from '../services/plex-client';
import config from '../config';

export class HealthMonitor {
  private radarrClient?: RadarrClient;
  private sonarrClient?: SonarrClient;
  private plexClient?: PlexClient;

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
  }

  async checkAllServices(): Promise<HealthStatus> {
    const checks: Promise<[string, ServiceStatus]>[] = [];

    if (this.radarrClient) {
      checks.push(
        this.radarrClient.checkHealth().then(status => ['radarr', status] as [string, ServiceStatus])
      );
    }

    if (this.sonarrClient) {
      checks.push(
        this.sonarrClient.checkHealth().then(status => ['sonarr', status] as [string, ServiceStatus])
      );
    }

    if (this.plexClient) {
      checks.push(
        this.plexClient.checkHealth().then(status => ['plex', status] as [string, ServiceStatus])
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
        // Handle failed health checks
        const serviceNames = [];
        if (this.radarrClient) serviceNames.push('radarr');
        if (this.sonarrClient) serviceNames.push('sonarr');
        if (this.plexClient) serviceNames.push('plex');
        
        const service = serviceNames[index];
        if (service) {
          (healthStatus as any)[service] = {
            status: 'error',
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
}