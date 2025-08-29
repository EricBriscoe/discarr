import fs from 'fs';
import path from 'path';
import type { Config } from '@discarr/core';
import { coreConfig } from '@discarr/core';

type DiscordSettings = { enabled?: boolean; token?: string; clientId?: string; channelId?: string };
type ServicesSettings = {
  radarr?: { url?: string; apiKey?: string };
  sonarr?: { url?: string; apiKey?: string };
  plex?: { url?: string };
  qbittorrent?: { url?: string; username?: string; password?: string };
};
type MonitoringSettings = {
  checkInterval?: number; // ms
  healthCheckInterval?: number; // ms
  verbose?: boolean;
  minRefreshInterval?: number; // ms
  maxRefreshInterval?: number; // ms
};
type FeatureSettings = {
  stalledDownloadCleanup?: {
    enabled?: boolean;
    // how often to run, in minutes (default 15)
    intervalMinutes?: number;
    // min age threshold for stalled downloads, in minutes (default 60)
    minAgeMinutes?: number;
    // cumulative number of torrents removed by this feature
    totalRemoved?: number;
  }
  orphanedMonitor?: {
    enabled?: boolean;
    intervalMinutes?: number; // default 60
    connection?: {
      host?: string;
      port?: number; // default 22
      username?: string;
      password?: string;
    };
    directories?: string[]; // absolute paths to scan
    deleteEmptyDirs?: boolean; // default false
    totalDeleted?: number; // cumulative files deleted
  }
};
type SettingsFile = { discord?: DiscordSettings; services?: ServicesSettings; monitoring?: MonitoringSettings; features?: FeatureSettings };

export class ConfigRepo {
  private settingsPath: string;
  constructor(baseDir = '/app/config') {
    this.settingsPath = path.join(baseDir, 'settings.json');
  }

  readSettings(): SettingsFile {
    try {
      const raw = fs.readFileSync(this.settingsPath, 'utf-8');
      return JSON.parse(raw);
    } catch {
      return {};
    }
  }

  writeSettings(settings: SettingsFile): void {
    const dir = path.dirname(this.settingsPath);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(this.settingsPath, JSON.stringify(settings, null, 2));
  }

  getEffectiveConfig(): Config {
    const envCfg = coreConfig; // from env
    const settings = this.readSettings();
    const d = settings.discord || {};
    const s = settings.services || {};
    const m = settings.monitoring || {};
    const services = {
      radarr: envCfg.services.radarr ? { ...envCfg.services.radarr } : undefined,
      sonarr: envCfg.services.sonarr ? { ...envCfg.services.sonarr } : undefined,
      plex: envCfg.services.plex ? { ...envCfg.services.plex } : undefined,
      qbittorrent: envCfg.services.qbittorrent ? { ...envCfg.services.qbittorrent } : undefined,
    } as Config['services'];

    if (s.radarr) services.radarr = { ...(services.radarr || {} as any), ...s.radarr } as any;
    if (s.sonarr) services.sonarr = { ...(services.sonarr || {} as any), ...s.sonarr } as any;
    if (s.plex) services.plex = { ...(services.plex || {} as any), ...s.plex } as any;
    if (s.qbittorrent) services.qbittorrent = { ...(services.qbittorrent || {} as any), ...s.qbittorrent } as any;

    return {
      discord: {
        token: (d.token || envCfg.discord.token) || '',
        clientId: (d.clientId || envCfg.discord.clientId) || '',
        channelId: (d.channelId || envCfg.discord.channelId) || '',
      },
      services,
      monitoring: {
        checkInterval: m.checkInterval ?? envCfg.monitoring.checkInterval,
        healthCheckInterval: m.healthCheckInterval ?? envCfg.monitoring.healthCheckInterval,
        verbose: m.verbose ?? envCfg.monitoring.verbose,
        minRefreshInterval: m.minRefreshInterval ?? envCfg.monitoring.minRefreshInterval,
        maxRefreshInterval: m.maxRefreshInterval ?? envCfg.monitoring.maxRefreshInterval,
      }
    } as Config;
  }

  getPublicConfig() {
    const s = this.readSettings();
    const enabled = (s.discord?.enabled) ?? (process.env.ENABLE_DISCORD_BOT !== 'false');
    return {
      discord: {
        enabled,
        clientId: s.discord?.clientId || '',
        channelId: s.discord?.channelId || '',
        tokenSet: !!s.discord?.token
      },
      services: {
        radarr: { url: s.services?.radarr?.url || '', apiKeySet: !!s.services?.radarr?.apiKey },
        sonarr: { url: s.services?.sonarr?.url || '', apiKeySet: !!s.services?.sonarr?.apiKey },
        plex: { url: s.services?.plex?.url || '' },
        qbittorrent: { url: s.services?.qbittorrent?.url || '', username: s.services?.qbittorrent?.username || '', passwordSet: !!s.services?.qbittorrent?.password }
      },
      monitoring: {
        checkInterval: s.monitoring?.checkInterval,
        healthCheckInterval: s.monitoring?.healthCheckInterval,
        verbose: s.monitoring?.verbose,
        minRefreshInterval: s.monitoring?.minRefreshInterval,
        maxRefreshInterval: s.monitoring?.maxRefreshInterval,
      }
    };
  }

  updateAll(payload: { discord?: DiscordSettings; services?: ServicesSettings; monitoring?: MonitoringSettings }) {
    const settings = this.readSettings();
    if (payload.discord) {
      settings.discord = settings.discord || {};
      const d = payload.discord;
      if (typeof d.enabled === 'boolean') settings.discord.enabled = d.enabled;
      if (typeof d.clientId === 'string') settings.discord.clientId = d.clientId.trim();
      if (typeof d.channelId === 'string') settings.discord.channelId = d.channelId.trim();
      if (d.token !== undefined) {
        const t = (d.token || '').trim();
        if (t.length > 0) settings.discord.token = t;
      }
    }
    if (payload.services) {
      settings.services = settings.services || {};
      settings.services.radarr = { ...(settings.services.radarr || {}), ...(payload.services.radarr || {}) };
      settings.services.sonarr = { ...(settings.services.sonarr || {}), ...(payload.services.sonarr || {}) };
      settings.services.plex = { ...(settings.services.plex || {}), ...(payload.services.plex || {}) };
      settings.services.qbittorrent = { ...(settings.services.qbittorrent || {}), ...(payload.services.qbittorrent || {}) };
      // Trim strings
      const strTrim = (v: any) => typeof v === 'string' ? v.trim() : v;
      for (const svc of ['radarr','sonarr','plex','qbittorrent'] as const) {
        const obj: any = (settings.services as any)[svc];
        if (obj) Object.keys(obj).forEach(k => obj[k] = strTrim(obj[k]));
      }
    }
    if (payload.monitoring) {
      settings.monitoring = { ...(settings.monitoring || {}), ...payload.monitoring };
    }
    this.writeSettings(settings);
  }

  // Feature settings
  getFeatures(): Required<FeatureSettings> {
    const s = this.readSettings();
    const f = s.features || {};
    return {
      stalledDownloadCleanup: {
        enabled: f.stalledDownloadCleanup?.enabled ?? false,
        intervalMinutes: f.stalledDownloadCleanup?.intervalMinutes ?? 15,
        minAgeMinutes: f.stalledDownloadCleanup?.minAgeMinutes ?? 60,
        totalRemoved: f.stalledDownloadCleanup?.totalRemoved ?? 0,
      },
      orphanedMonitor: {
        enabled: f.orphanedMonitor?.enabled ?? false,
        intervalMinutes: f.orphanedMonitor?.intervalMinutes ?? 60,
        connection: {
          host: f.orphanedMonitor?.connection?.host || '',
          port: f.orphanedMonitor?.connection?.port ?? 22,
          username: f.orphanedMonitor?.connection?.username || '',
          password: f.orphanedMonitor?.connection?.password || '',
        },
        directories: Array.isArray(f.orphanedMonitor?.directories) ? f.orphanedMonitor!.directories! : [],
        deleteEmptyDirs: f.orphanedMonitor?.deleteEmptyDirs ?? false,
        totalDeleted: f.orphanedMonitor?.totalDeleted ?? 0,
      },
    };
  }

  updateFeatures(payload: FeatureSettings) {
    const settings = this.readSettings();
    settings.features = settings.features || {};
    if (payload.stalledDownloadCleanup) {
      settings.features.stalledDownloadCleanup = {
        ...(settings.features.stalledDownloadCleanup || {}),
        ...payload.stalledDownloadCleanup
      };
    }
    if (payload.orphanedMonitor) {
      settings.features.orphanedMonitor = {
        ...(settings.features.orphanedMonitor || {}),
        ...payload.orphanedMonitor
      } as any;
      // normalize directories (trim, drop empty)
      const dirs = (settings.features.orphanedMonitor as any).directories;
      if (Array.isArray(dirs)) {
        (settings.features.orphanedMonitor as any).directories = dirs.map((d: string)=> (d||'').trim()).filter((d: string)=>d.length>0);
      }
    }
    this.writeSettings(settings);
  }
}
