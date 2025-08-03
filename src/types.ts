export interface ServiceStatus {
  status: 'online' | 'offline' | 'error';
  lastCheck: Date;
  responseTime?: number;
  version?: string;
  error?: string;
}

export interface DownloadItem {
  id: number;
  title: string;
  progress: number;
  size: number;
  sizeLeft: number;
  timeLeft?: string;
  status: string;
  protocol: string;
  downloadClient: string;
  service: 'radarr' | 'sonarr';
  added?: string;
  errorMessage?: string;
}

export interface TVDownloadItem extends DownloadItem {
  series: string;
  season: number;
  episode: number;
  service: 'sonarr';
}

export interface MovieDownloadItem extends DownloadItem {
  service: 'radarr';
}

export interface HealthStatus {
  plex?: ServiceStatus;
  radarr?: ServiceStatus;
  sonarr?: ServiceStatus;
  lastUpdated: Date;
}

export type AnyDownloadItem = MovieDownloadItem | TVDownloadItem;