const BASE: string = (import.meta as any).env?.VITE_API_BASE_URL || '';

export async function getHealth() {
  const res = await fetch(`${BASE}/api/health`);
  if (!res.ok) throw new Error('Failed to load health');
  return res.json();
}

export async function getDownloads() {
  const res = await fetch(`${BASE}/api/downloads`);
  if (!res.ok) throw new Error('Failed to load downloads');
  return res.json();
}

export interface BlockedResponse { radarr: Array<{id:number; title:string}>; sonarr: Array<{id:number; title:string}>; lidarr: Array<{id:number; title:string}> }

export async function getBlocked(): Promise<BlockedResponse> {
  const res = await fetch(`${BASE}/api/blocked`);
  if (!res.ok) throw new Error('Failed to load blocked items');
  return res.json();
}

export async function approveBlocked(service: 'radarr'|'sonarr', id: number) {
  const res = await fetch(`${BASE}/api/blocked/${service}/${id}/approve`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to approve');
  return res.json();
}

export async function rejectBlocked(service: 'radarr'|'sonarr'|'lidarr', id: number) {
  const res = await fetch(`${BASE}/api/blocked/${service}/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to reject');
  return res.json();
}

export async function cleanupTorrents() {
  const res = await fetch(`${BASE}/api/actions/cleanup`, { method: 'POST' });
  if (!res.ok) throw new Error('Cleanup failed');
  return res.json();
}

export async function seriesSearch(seriesId: number) {
  const res = await fetch(`${BASE}/api/actions/series-search`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ seriesId }) });
  if (!res.ok) throw new Error('Series search failed');
  return res.json();
}

// Admin config
export interface AdminConfig {
  discord: { enabled: boolean; clientId: string; channelId: string; tokenSet: boolean };
  services: {
    radarr: { url: string; apiKeySet: boolean };
    sonarr: { url: string; apiKeySet: boolean };
    plex: { url: string };
    qbittorrent: { url: string; username: string; passwordSet: boolean };
  };
  monitoring: { checkInterval?: number; healthCheckInterval?: number; verbose?: boolean; minRefreshInterval?: number; maxRefreshInterval?: number };
  running: boolean;
}

export async function getAdminConfig(): Promise<AdminConfig> {
  const res = await fetch(`${BASE}/api/admin/config`, { headers: { 'Content-Type': 'application/json' } });
  if (!res.ok) throw new Error('Failed to load configuration');
  return res.json();
}

export async function updateAdminConfig(payload: { discord?: { enabled?: boolean; clientId?: string; channelId?: string; token?: string | null }, services?: any, monitoring?: any }) {
  const res = await fetch(`${BASE}/api/admin/config`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  if (!res.ok) throw new Error('Failed to update configuration');
  return res.json();
}

// Features
export interface FeaturesState {
  stalledDownloadCleanup: {
    enabled: boolean;
    intervalMinutes: number;
    minAgeMinutes: number;
    totalRemoved: number;
    lastRunAt?: string;
    lastRunResult?: { attempted: number; removed: number; error?: string };
  };
  qbittorrentRecheckErrored: {
    enabled: boolean;
    intervalMinutes: number;
    lastRunAt?: string;
    lastRunResult?: { attempted: number; rechecked: number; error?: string };
  };
  botMonitoring: {
    enabled: boolean;
    running: boolean;
  };
  orphanedMonitor: {
    enabled: boolean;
    intervalMinutes: number;
    connection: { host?: string; port?: number; username?: string; passwordSet?: boolean };
    directories: string[];
    deleteEmptyDirs: boolean;
    ignored: string[];
    totalDeleted: number;
    lastRunAt?: string;
    lastRunResult?: { scanned: number; orphaned: number; deleted: number; expected?: number; torrents?: number; qbFiles?: number; dirCounts?: Array<{ dir: string; files: number; sizeBytes?: number }>; errors?: string[] };
  };
  autoQueueManager: {
    enabled: boolean;
    intervalMinutes: number;
    maxStorageBytes: number;
    maxActiveTorrents: number;
    lastRunAt?: string;
    lastRunResult?: { usedBytes: number; queuedBytes: number; queuedCount: number; canStart: number; setDownloads: number; setUploads: number; setTorrents: number; error?: string };
  };
}

export async function getFeatures(): Promise<FeaturesState> {
  const res = await fetch(`${BASE}/api/features`);
  if (!res.ok) throw new Error('Failed to load features');
  return res.json();
}

export async function updateFeatures(payload: { stalledDownloadCleanup?: Partial<FeaturesState['stalledDownloadCleanup']>; botMonitoring?: { enabled?: boolean }; orphanedMonitor?: Partial<FeaturesState['orphanedMonitor']> & { connection?: { host?: string; port?: number; username?: string; password?: string } } }) {
  const res = await fetch(`${BASE}/api/features`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  if (!res.ok) throw new Error('Failed to update features');
  return res.json();
}

export async function runStalledCleanupNow() {
  const res = await fetch(`${BASE}/api/features/stalled-cleanup/run`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to run cleanup');
  return res.json();
}

export async function runOrphanedMonitorNow() {
  const res = await fetch(`${BASE}/api/features/orphaned-monitor/run`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to run orphaned monitor');
  return res.json();
}

// SSE: Orphaned monitor progress
export function openOrphanedMonitorStream(onMessage: (ev: MessageEvent) => void): EventSource {
  const es = new EventSource(`${BASE}/api/features/orphaned-monitor/stream`);
  es.addEventListener('om', onMessage);
  return es;
}

export async function runRecheckErroredNow() {
  const res = await fetch(`${BASE}/api/features/recheck-errored/run`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to run recheck');
  return res.json();
}

export async function runAutoQueueManagerNow() {
  const res = await fetch(`${BASE}/api/features/auto-queue/run`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to run auto queue manager');
  return res.json();
}

// SSE: Auto Queue Manager progress
export function openAutoQueueStream(onMessage: (ev: MessageEvent) => void): EventSource {
  const es = new EventSource(`${BASE}/api/features/auto-queue/stream`);
  es.addEventListener('aqm', onMessage);
  return es;
}
