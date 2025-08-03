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

export interface CalendarEpisode {
  id: number;
  title: string;
  seriesTitle: string;
  seasonNumber: number;
  episodeNumber: number;
  airDateUtc?: string;
  hasFile: boolean;
  monitored: boolean;
  overview?: string;
  seriesType?: string;
  network?: string;
  status?: string;
}

export interface SeriesSearchResult {
  tvdbId: number;
  title: string;
  year?: number;
  overview?: string;
  network?: string;
  status?: string;
  genres: string[];
  remotePoster?: string;
  seasons: number;
}

export interface MissingEpisode {
  id: number;
  title: string;
  seriesTitle: string;
  seriesId: number;
  seasonNumber: number;
  episodeNumber: number;
  airDateUtc?: string;
  monitored: boolean;
  overview?: string;
}

export interface SeriesInfo {
  id: number;
  title: string;
  year?: number;
  status: string;
  monitored: boolean;
  seasonCount: number;
  episodeFileCount: number;
  episodeCount: number;
  network?: string;
}

export type AnyDownloadItem = MovieDownloadItem | TVDownloadItem;