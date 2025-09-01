import { QBittorrentClient } from '@discarr/core';
import { ConfigRepo } from './config-repo';
import { orphanEvents } from './orphaned-monitor-events';
import SftpClient from 'ssh2-sftp-client';
import path from 'path';

type CleanupResult = { attempted: number; removed: number; error?: string };

export class FeaturesService {
  private configRepo: ConfigRepo;
  private cleanupTimer?: NodeJS.Timeout;
  private orphanTimer?: NodeJS.Timeout;
  private recheckTimer?: NodeJS.Timeout;
  private aqmTimer?: NodeJS.Timeout;

  // runtime status
  private lastCleanupRunAt?: string; // ISO
  private lastCleanupResult?: CleanupResult;
  private lastOrphanRunAt?: string;
  private lastOrphanResult?: { scanned: number; orphaned: number; deleted: number; expected?: number; torrents?: number; qbFiles?: number; dirCounts?: Array<{ dir: string; files: number; sizeBytes?: number }>; errors?: string[] };
  private lastRecheckRunAt?: string;
  private lastRecheckResult?: { attempted: number; rechecked: number; error?: string };
  private lastAqmRunAt?: string;
  private lastAqmResult?: { usedBytes: number; queuedBytes: number; queuedCount: number; canStart: number; setDownloads: number; setUploads: number; setTorrents: number; error?: string };

  constructor(configRepo: ConfigRepo) {
    this.configRepo = configRepo;
  }

  start() {
    this.applyScheduling();
  }

  stop() {
    if (this.cleanupTimer) clearInterval(this.cleanupTimer);
    this.cleanupTimer = undefined;
  }

  applyScheduling() {
    const features = this.configRepo.getFeatures();
    // clear any existing timers
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer);
      this.cleanupTimer = undefined;
    }
    if (this.orphanTimer) {
      clearInterval(this.orphanTimer);
      this.orphanTimer = undefined;
    }
    if (this.recheckTimer) {
      clearInterval(this.recheckTimer);
      this.recheckTimer = undefined;
    }
    if (this.aqmTimer) {
      clearInterval(this.aqmTimer);
      this.aqmTimer = undefined;
    }
    if (features.stalledDownloadCleanup.enabled) {
      const everyMs = Math.max(1, features.stalledDownloadCleanup.intervalMinutes || 15) * 60_000;
      this.cleanupTimer = setInterval(() => {
        this.runStalledCleanup().catch(() => void 0);
      }, everyMs);
      // Do not run immediately to avoid surprise; users can press Run Now from UI
    }
    if (features.orphanedMonitor.enabled) {
      const everyMs = Math.max(1, features.orphanedMonitor.intervalMinutes || 60) * 60_000;
      this.orphanTimer = setInterval(() => {
        this.runOrphanedMonitor().catch(() => void 0);
      }, everyMs);
    }
    if (features.qbittorrentRecheckErrored.enabled) {
      const everyMs = Math.max(1, features.qbittorrentRecheckErrored.intervalMinutes || 30) * 60_000;
      this.recheckTimer = setInterval(() => {
        this.runRecheckErrored().catch(() => void 0);
      }, everyMs);
    }
    if (features.autoQueueManager.enabled) {
      const everyMs = Math.max(1, features.autoQueueManager.intervalMinutes || 10) * 60_000;
      this.aqmTimer = setInterval(() => {
        this.runAutoQueueManager().catch(() => void 0);
      }, everyMs);
    }
  }

  async updateSettings(p: { stalledDownloadCleanup?: { enabled?: boolean; intervalMinutes?: number; minAgeMinutes?: number } }) {
    this.configRepo.updateFeatures({ stalledDownloadCleanup: p.stalledDownloadCleanup });
    this.applyScheduling();
  }

  async updateOrphanSettings(p: { orphanedMonitor?: { enabled?: boolean; intervalMinutes?: number; connection?: { host?: string; port?: number; username?: string; password?: string }; directories?: string[]; deleteEmptyDirs?: boolean } }) {
    this.configRepo.updateFeatures({ orphanedMonitor: p.orphanedMonitor });
    this.applyScheduling();
  }

  async updateRecheckSettings(p: { qbittorrentRecheckErrored?: { enabled?: boolean; intervalMinutes?: number } }) {
    this.configRepo.updateFeatures({ qbittorrentRecheckErrored: p.qbittorrentRecheckErrored });
    this.applyScheduling();
  }
  
  async updateAutoQueueSettings(p: { autoQueueManager?: { enabled?: boolean; intervalMinutes?: number; maxStorageBytes?: number; maxActiveTorrents?: number } }) {
    this.configRepo.updateFeatures({ autoQueueManager: p.autoQueueManager });
    this.applyScheduling();
  }

  async runStalledCleanup(p?: { ignoreMinAge?: boolean }): Promise<CleanupResult> {
    const cfg = this.configRepo.getEffectiveConfig();
    const f = this.configRepo.getFeatures();
    const minAgeMinutes = f.stalledDownloadCleanup.minAgeMinutes ?? 60;
    const thresholdSec = Math.max(1, minAgeMinutes) * 60;

    if (!cfg.services.qbittorrent) {
      const result: CleanupResult = { attempted: 0, removed: 0, error: 'qBittorrent not configured' };
      this.recordCleanup(result);
      return result;
    }
    try {
      const qb = new QBittorrentClient({ baseUrl: cfg.services.qbittorrent.url, username: cfg.services.qbittorrent.username, password: cfg.services.qbittorrent.password });
      const torrents = await qb.getTorrents();
      const nowSec = Math.floor(Date.now() / 1000);
      const stale = torrents.filter(t => {
        const isStalledDl = t.state === 'stalledDL';
        const isMetaDl = t.state === 'metaDL';
        const addedOn = (t as any).added_on as number | undefined;
        if (p?.ignoreMinAge) {
          return (isStalledDl || isMetaDl);
        }
        const ageOk = typeof addedOn === 'number' ? (nowSec - addedOn) >= thresholdSec : false;
        return (isStalledDl || isMetaDl) && ageOk;
      });
      const hashes = stale.map(t => t.hash);
      let removed = 0;
      if (hashes.length > 0) {
        const result = await qb.deleteTorrents(hashes, true);
        removed = result.filter(r => r.success).length;
      }
      const out: CleanupResult = { attempted: hashes.length, removed };
      this.recordCleanup(out);
      // persist cumulative counter
      try {
        const f = this.configRepo.getFeatures();
        const nextTotal = (f.stalledDownloadCleanup.totalRemoved || 0) + removed;
        this.configRepo.updateFeatures({ stalledDownloadCleanup: { totalRemoved: nextTotal } });
      } catch {}
      return out;
    } catch (e: any) {
      const out: CleanupResult = { attempted: 0, removed: 0, error: e?.message || 'Unknown error' };
      this.recordCleanup(out);
      return out;
    }
  }

  private recordCleanup(result: CleanupResult) {
    this.lastCleanupRunAt = new Date().toISOString();
    this.lastCleanupResult = result;
  }

  getPublicState() {
    const f = this.configRepo.getFeatures();
    const con = (f.orphanedMonitor as any).connection || {};
    return {
      stalledDownloadCleanup: {
        enabled: f.stalledDownloadCleanup.enabled,
        intervalMinutes: f.stalledDownloadCleanup.intervalMinutes,
        minAgeMinutes: f.stalledDownloadCleanup.minAgeMinutes,
        totalRemoved: f.stalledDownloadCleanup.totalRemoved,
        lastRunAt: this.lastCleanupRunAt,
        lastRunResult: this.lastCleanupResult,
      },
      qbittorrentRecheckErrored: {
        enabled: f.qbittorrentRecheckErrored.enabled,
        intervalMinutes: f.qbittorrentRecheckErrored.intervalMinutes,
        lastRunAt: this.lastRecheckRunAt,
        lastRunResult: this.lastRecheckResult,
      },
      orphanedMonitor: {
        enabled: f.orphanedMonitor.enabled,
        intervalMinutes: f.orphanedMonitor.intervalMinutes,
        connection: {
          host: con.host,
          port: con.port,
          username: con.username,
          passwordSet: !!con.password,
        },
        directories: f.orphanedMonitor.directories,
        deleteEmptyDirs: f.orphanedMonitor.deleteEmptyDirs,
        ignored: (f.orphanedMonitor as any).ignored,
        totalDeleted: f.orphanedMonitor.totalDeleted,
        lastRunAt: this.lastOrphanRunAt,
        lastRunResult: this.lastOrphanResult,
      },
      autoQueueManager: {
        enabled: f.autoQueueManager.enabled,
        intervalMinutes: f.autoQueueManager.intervalMinutes,
        maxStorageBytes: f.autoQueueManager.maxStorageBytes,
        maxActiveTorrents: f.autoQueueManager.maxActiveTorrents,
        lastRunAt: this.lastAqmRunAt,
        lastRunResult: this.lastAqmResult,
      }
    };
  }

  async runRecheckErrored(): Promise<{ attempted: number; rechecked: number; error?: string }> {
    const cfg = this.configRepo.getEffectiveConfig();
    if (!cfg.services.qbittorrent) {
      const out = { attempted: 0, rechecked: 0, error: 'qBittorrent not configured' };
      this.lastRecheckRunAt = new Date().toISOString();
      this.lastRecheckResult = out;
      return out;
    }
    try {
      const qb = new QBittorrentClient({ baseUrl: cfg.services.qbittorrent.url, username: cfg.services.qbittorrent.username, password: cfg.services.qbittorrent.password });
      const errored = await qb.getErroredTorrents();
      const hashes = errored.map(t => t.hash);
      const result = await qb.recheckTorrents(hashes);
      const out = { attempted: hashes.length, rechecked: result.filter(r => r.success).length };
      this.lastRecheckRunAt = new Date().toISOString();
      this.lastRecheckResult = out;
      // snapshot last result into settings for visibility across restarts (optional)
      try { this.configRepo.updateFeatures({ qbittorrentRecheckErrored: { lastAttempted: out.attempted, lastRechecked: out.rechecked } }); } catch {}
      return out;
    } catch (e:any) {
      const out = { attempted: 0, rechecked: 0, error: e?.message || 'Unknown error' };
      this.lastRecheckRunAt = new Date().toISOString();
      this.lastRecheckResult = out;
      return out;
    }
  }

  async runAutoQueueManager(): Promise<{ usedBytes: number; queuedBytes: number; queuedCount: number; canStart: number; setDownloads: number; setUploads: number; setTorrents: number; error?: string }> {
    const cfg = this.configRepo.getEffectiveConfig();
    const f = this.configRepo.getFeatures();
    const aq = f.autoQueueManager;
    if (!cfg.services.qbittorrent) {
      const out = { usedBytes: 0, queuedBytes: 0, queuedCount: 0, canStart: 0, setDownloads: 0, setUploads: 0, setTorrents: 0, error: 'qBittorrent not configured' };
      this.lastAqmRunAt = new Date().toISOString();
      this.lastAqmResult = out;
      return out;
    }
    try {
      const qb = new QBittorrentClient({ baseUrl: cfg.services.qbittorrent.url, username: cfg.services.qbittorrent.username, password: cfg.services.qbittorrent.password });
      const torrents = await qb.getTorrents();
      // Completed torrents use space
      const completed = torrents.filter(t => t.progress >= 0.9999 || /UP$/.test(t.state) || /(uploading|stalledUP|queuedUP|forcedUP)/.test(t.state));
      const usedBytes = completed.reduce((sum, t) => sum + (typeof t.size === 'number' ? t.size : 0), 0);
      const quota = Math.max(0, aq.maxStorageBytes || 0);
      const available = Math.max(0, quota - usedBytes);
      // Queued downloads in order of added time (oldest first)
      const queued = torrents
        .filter(t => t.state === 'queuedDL')
        .sort((a,b) => (a.added_on || 0) - (b.added_on || 0));
      let canStart = 0;
      let acc = 0;
      let queuedBytes = 0;
      for (const t of queued) {
        const sz = typeof t.size === 'number' ? t.size : 0;
        queuedBytes += sz;
        if (acc + sz <= available) {
          acc += sz;
          canStart++;
        } else {
          break;
        }
      }
      const setDownloads = Math.max(0, canStart);
      const setUploads = Math.max(0, aq.maxActiveTorrents || 0);
      const setTorrents = Math.max(0, aq.maxActiveTorrents || 0);
      await qb.setPreferences({
        'queueing_max_active_downloads': setDownloads,
        'queueing_max_active_uploads': setUploads,
        'queueing_max_active_torrents': setTorrents,
      });
      const out = { usedBytes, queuedBytes, queuedCount: queued.length, canStart, setDownloads, setUploads, setTorrents };
      this.lastAqmRunAt = new Date().toISOString();
      this.lastAqmResult = out;
      try {
        this.configRepo.updateFeatures({ autoQueueManager: { lastComputedDownloads: canStart } });
      } catch {}
      return out;
    } catch (e:any) {
      const out = { usedBytes: 0, queuedBytes: 0, queuedCount: 0, canStart: 0, setDownloads: 0, setUploads: 0, setTorrents: 0, error: e?.message || 'Unknown error' };
      this.lastAqmRunAt = new Date().toISOString();
      this.lastAqmResult = out;
      return out;
    }
  }

  async runOrphanedMonitor(): Promise<{ scanned: number; orphaned: number; deleted: number; expected?: number; torrents?: number; qbFiles?: number; dirCounts?: Array<{ dir: string; files: number; sizeBytes?: number }>; errors?: string[] }> {
    const cfg = this.configRepo.getEffectiveConfig();
    const f = this.configRepo.getFeatures();
    const settings = f.orphanedMonitor;
    const conn = (settings as any).connection || {};
    const ignoredNames: string[] = Array.isArray((settings as any).ignored) && (settings as any).ignored.length > 0
      ? ((settings as any).ignored as string[]).map(s => (s || '').trim()).filter(s => s.length > 0)
      : ['.stfolder'];
    const ignoredSet = new Set<string>(ignoredNames);
    const errors: string[] = [];
    const runId = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2,8)}`;
    orphanEvents.send({ type: 'start', runId, data: { host: conn.host, port: conn.port, username: conn.username, dirs: (settings.directories||[]).slice(0,50) } });
    if (!cfg.services.qbittorrent) {
      console.warn('[OrphanedMonitor] qBittorrent not configured; cannot build expected file set');
      orphanEvents.send({ type: 'error', runId, data: { message: 'qBittorrent not configured' } });
      const out = { scanned: 0, orphaned: 0, deleted: 0, errors: ['qBittorrent not configured'] };
      this.recordOrphan(out);
      return out;
    }
    if (!conn.host || !conn.username || !conn.password) {
      const missing: string[] = [];
      if (!conn.host) missing.push('host');
      if (!conn.username) missing.push('username');
      if (!conn.password) missing.push('password');
      console.warn(`[OrphanedMonitor] SSH connection not fully configured; missing: ${missing.join(', ')}`);
      orphanEvents.send({ type: 'error', runId, data: { message: 'SSH connection not fully configured', missing } });
      const out = { scanned: 0, orphaned: 0, deleted: 0, errors: ['SSH connection not fully configured'] };
      this.recordOrphan(out);
      return out;
    }
    if (!settings.directories || settings.directories.length === 0) {
      console.warn('[OrphanedMonitor] No directories configured to scan');
      orphanEvents.send({ type: 'error', runId, data: { message: 'No directories configured' } });
      const out = { scanned: 0, orphaned: 0, deleted: 0, errors: ['No directories configured'] };
      this.recordOrphan(out);
      return out;
    }

    try {
      const qb = new QBittorrentClient({ baseUrl: cfg.services.qbittorrent.url, username: cfg.services.qbittorrent.username, password: cfg.services.qbittorrent.password });
      const torrents = await qb.getTorrents();
      console.log(`[OrphanedMonitor] qBittorrent: fetched ${torrents.length} torrents`);
      const expected = new Set<string>();
      let qbFilesTotal = 0;
      // Build expected absolute file paths using save_path/content_path and files list.
      // Fetch file lists concurrently for efficiency.
      const fileLists = await Promise.allSettled(
        torrents.map(async (t) => {
          const files = await qb.getTorrentFiles(t.hash).catch((_e:any)=>[] as any[]);
          return { t, files };
        })
      );
      for (const res of fileLists) {
        if (res.status !== 'fulfilled') continue;
        const { t, files } = res.value as { t: any; files: any[] };
        qbFilesTotal += (files as any[]).length;
        const base = (t.save_path && t.save_path.trim().length>0) ? t.save_path as string : (t.content_path ? path.dirname(t.content_path as string) : '');
        if (!base) continue;
        const normBase = base.replaceAll('\\','/');
        for (const f of files) {
          const rel = (f.name || '').replaceAll('\\','/');
          const abs = path.posix.normalize(path.posix.join(normBase, rel));
          expected.add(abs);
          // Include in-progress variants so we don't mark them orphaned
          expected.add(`${abs}.!qB`);
          expected.add(`${abs}.!qb`);
        }
        // If no files returned (rare), include content_path itself
        if ((files as any[]).length === 0 && t.content_path) {
          const cp = path.posix.normalize((t.content_path as string).replaceAll('\\','/'));
          expected.add(cp);
          expected.add(`${cp}.!qB`);
          expected.add(`${cp}.!qb`);
        }
      }
      console.log(`[OrphanedMonitor] qBittorrent files total: ${qbFilesTotal}; expected unique paths (incl. in-progress markers): ${expected.size}`);
      orphanEvents.send({ type: 'qbit-fetched', runId, data: { torrents: torrents.length, qbFiles: qbFilesTotal, expected: expected.size } });

      const sftp = new SftpClient();
      console.log(`[OrphanedMonitor] Connecting via SFTP to ${conn.host}:${conn.port || 22} as ${conn.username}`);
      await sftp.connect({
        host: conn.host,
        port: conn.port || 22,
        username: conn.username,
        password: conn.password,
        readyTimeout: 20000,
      });
      console.log('[OrphanedMonitor] SFTP connection established');
      orphanEvents.send({ type: 'sftp-connected', runId });

      let scanned = 0;
      let orphaned = 0;
      let deleted = 0;
      const dirCounts: Array<{ dir: string; files: number; sizeBytes?: number }> = [];

      // Normalize directories in case any were saved with literal "\n"
      const rawDirs = settings.directories || [];
      const dirs = rawDirs
        .flatMap(d => (d || '').split(/\r?\n|\\n/g))
        .map(d => d.trim())
        .filter(d => d.length > 0);
      console.log(`[OrphanedMonitor] Starting scan of ${dirs.length} directories on ${conn.host}:${conn.port} as ${conn.username}`);
      for (const d of dirs) console.log(`[OrphanedMonitor] Directory to scan: ${d}`);
      orphanEvents.send({ type: 'scan-start', runId, data: { dirs } });

      const listRecursive = async (dir: string): Promise<Array<{path:string; type:'file'|'dir'; size?: number}>> => {
        const out: Array<{path:string; type:'file'|'dir'; size?: number}> = [];
        const items = await sftp.list(dir);
        for (const it of items) {
          const p = path.posix.join(dir, it.name);
          const base = path.posix.basename(p);
          // Skip ignored entries by base name
          if (ignoredSet.has(base)) {
            continue;
          }
          if (it.type === 'd') {
            out.push({ path: p, type: 'dir' });
            const sub = await listRecursive(p);
            out.push(...sub);
          } else if (it.type === '-') {
            out.push({ path: p, type: 'file', size: (it as any).size ?? 0 });
          }
        }
        return out;
      };

      // Scan configured directories
      for (const dir of dirs) {
        try {
          const items = await listRecursive(dir);
          const filesInDir: string[] = [];
          let dirSize = 0;
          for (const it of items) {
            if (it.type === 'file') {
              scanned++;
              const norm = path.posix.normalize(it.path);
              filesInDir.push(norm);
              // Skip files with qBittorrent in-progress markers (e.g., .!qB/.!qb)
              const base = path.posix.basename(norm);
              const lower = base.toLowerCase();
              const isQbInProgress = lower.endsWith('.!qb');
              if (isQbInProgress) { dirSize += it.size || 0; continue; }
              // Never delete ignored files
              if (ignoredSet.has(base)) { dirSize += it.size || 0; continue; }
              if (!expected.has(norm)) {
                orphaned++;
                try {
                  console.log(`[OrphanedMonitor] Orphan file (to delete): ${norm}`);
                  await sftp.delete(norm);
                  deleted++;
                  console.log(`[OrphanedMonitor] Deleted: ${norm}`);
                  orphanEvents.send({ type: 'deleted', runId, data: { path: norm } });
                } catch (e:any) {
                  const msg = `Delete failed: ${norm}: ${e?.message||e}`;
                  console.warn(`[OrphanedMonitor] ${msg}`);
                  errors.push(msg);
                  orphanEvents.send({ type: 'error', runId, data: { message: msg } });
                  dirSize += it.size || 0;
                }
              } else {
                dirSize += it.size || 0;
              }
            }
          }
          // Log all files found in this directory and the diff
          try {
            if (filesInDir.length > 0) {
              console.log(`[OrphanedMonitor] Files in ${dir} (${filesInDir.length}):`);
              for (const fp of filesInDir) console.log(` - ${fp}`);
              const diffs = filesInDir.filter(fp => !expected.has(path.posix.normalize(fp)));
              console.log(`[OrphanedMonitor] Diff (not in qBittorrent) in ${dir}: ${diffs.length}`);
              for (const dfn of diffs) console.log(`   * ${dfn}`);
            } else {
              console.log(`[OrphanedMonitor] No files found in ${dir}`);
            }
          } catch {}
          dirCounts.push({ dir, files: filesInDir.length, sizeBytes: dirSize });
          orphanEvents.send({ type: 'dir-summary', runId, data: { dir, files: filesInDir.length, sizeBytes: dirSize, scanned, orphaned, deleted } });
          if (settings.deleteEmptyDirs) {
            // remove empty directories bottom-up
            const dirs = items.filter(i=>i.type==='dir').map(i=>i.path).sort((a,b)=>b.length-a.length);
            for (const d of dirs) {
              try {
                // Skip removal of ignored directories
                const b = path.posix.basename(d);
                if (ignoredSet.has(b)) continue;
                const ls = await sftp.list(d);
                if (ls.length === 0) await sftp.rmdir(d);
              } catch {}
            }
          }
        } catch (e:any) {
          errors.push(`Scan failed: ${dir}: ${e?.message||e}`);
          orphanEvents.send({ type: 'error', runId, data: { message: `Scan failed: ${dir}: ${e?.message||e}` } });
        }
      }

      await sftp.end();
      const out = { scanned, orphaned, deleted, expected: expected.size, torrents: torrents.length, qbFiles: qbFilesTotal, dirCounts, ...(errors.length ? { errors } : {}) };
      console.log(`[OrphanedMonitor] Summary: scanned=${scanned}, expected=${expected.size}, orphaned=${orphaned}, deleted=${deleted}, torrents=${torrents.length}, qbFiles=${qbFilesTotal}${errors.length ? `, errors=${errors.length}` : ''}`);
      this.recordOrphan(out);
      orphanEvents.send({ type: 'summary', runId, data: out });
      try {
        const current = this.configRepo.getFeatures().orphanedMonitor.totalDeleted || 0;
        this.configRepo.updateFeatures({ orphanedMonitor: { totalDeleted: current + deleted } });
      } catch {}
      return out;
    } catch (e:any) {
      console.warn('[OrphanedMonitor] Fatal error during run:', e?.message || e);
      const out = { scanned: 0, orphaned: 0, deleted: 0, errors: [e?.message || 'Unknown error'] };
      this.recordOrphan(out);
      orphanEvents.send({ type: 'error', runId, data: { message: e?.message || 'Unknown error' } });
      return out;
    }
  }

  private recordOrphan(result: { scanned: number; orphaned: number; deleted: number; errors?: string[] }) {
    this.lastOrphanRunAt = new Date().toISOString();
    this.lastOrphanResult = result;
  }
}
