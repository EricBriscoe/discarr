import { QBittorrentClient } from '@discarr/core';
import { ConfigRepo } from './config-repo';
import SftpClient from 'ssh2-sftp-client';
import path from 'path';

type CleanupResult = { attempted: number; removed: number; error?: string };

export class FeaturesService {
  private configRepo: ConfigRepo;
  private cleanupTimer?: NodeJS.Timeout;
  private orphanTimer?: NodeJS.Timeout;

  // runtime status
  private lastCleanupRunAt?: string; // ISO
  private lastCleanupResult?: CleanupResult;
  private lastOrphanRunAt?: string;
  private lastOrphanResult?: { scanned: number; orphaned: number; deleted: number; errors?: string[] };

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
  }

  async updateSettings(p: { stalledDownloadCleanup?: { enabled?: boolean; intervalMinutes?: number; minAgeMinutes?: number } }) {
    this.configRepo.updateFeatures({ stalledDownloadCleanup: p.stalledDownloadCleanup });
    this.applyScheduling();
  }

  async updateOrphanSettings(p: { orphanedMonitor?: { enabled?: boolean; intervalMinutes?: number; connection?: { host?: string; port?: number; username?: string; password?: string }; directories?: string[]; deleteEmptyDirs?: boolean } }) {
    this.configRepo.updateFeatures({ orphanedMonitor: p.orphanedMonitor });
    this.applyScheduling();
  }

  async runStalledCleanup(): Promise<CleanupResult> {
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
        totalDeleted: f.orphanedMonitor.totalDeleted,
        lastRunAt: this.lastOrphanRunAt,
        lastRunResult: this.lastOrphanResult,
      }
    };
  }

  async runOrphanedMonitor(): Promise<{ scanned: number; orphaned: number; deleted: number; errors?: string[] }> {
    const cfg = this.configRepo.getEffectiveConfig();
    const f = this.configRepo.getFeatures();
    const settings = f.orphanedMonitor;
    const conn = (settings as any).connection || {};
    const errors: string[] = [];
    if (!cfg.services.qbittorrent) {
      const out = { scanned: 0, orphaned: 0, deleted: 0, errors: ['qBittorrent not configured'] };
      this.recordOrphan(out);
      return out;
    }
    if (!conn.host || !conn.username || !conn.password) {
      const out = { scanned: 0, orphaned: 0, deleted: 0, errors: ['SSH connection not fully configured'] };
      this.recordOrphan(out);
      return out;
    }
    if (!settings.directories || settings.directories.length === 0) {
      const out = { scanned: 0, orphaned: 0, deleted: 0, errors: ['No directories configured'] };
      this.recordOrphan(out);
      return out;
    }

    try {
      const qb = new QBittorrentClient({ baseUrl: cfg.services.qbittorrent.url, username: cfg.services.qbittorrent.username, password: cfg.services.qbittorrent.password });
      const torrents = await qb.getTorrents();
      const expected = new Set<string>();
      // Build expected absolute file paths using save_path/content_path and files list
      for (const t of torrents) {
        const files = await qb.getTorrentFiles(t.hash).catch((_e:any)=>[] as any[]);
        const base = (t.save_path && t.save_path.trim().length>0) ? t.save_path! : (t.content_path ? path.dirname(t.content_path) : '');
        if (!base) continue;
        for (const f of files as any[]) {
          const abs = path.posix.normalize(path.posix.join(base.replaceAll('\\','/'), (f.name || '').replaceAll('\\','/')));
          expected.add(abs);
        }
        // If no files returned (rare), include content_path itself
        if ((files as any[]).length === 0 && t.content_path) {
          expected.add(path.posix.normalize(t.content_path.replaceAll('\\','/')));
        }
      }

      const sftp = new SftpClient();
      await sftp.connect({
        host: conn.host,
        port: conn.port || 22,
        username: conn.username,
        password: conn.password,
        readyTimeout: 20000,
      });

      let scanned = 0;
      let orphaned = 0;
      let deleted = 0;

      // Normalize directories in case any were saved with literal "\n"
      const rawDirs = settings.directories || [];
      const dirs = rawDirs
        .flatMap(d => (d || '').split(/\r?\n|\\n/g))
        .map(d => d.trim())
        .filter(d => d.length > 0);
      console.log(`[OrphanedMonitor] Starting scan of ${dirs.length} directories on ${conn.host}:${conn.port} as ${conn.username}`);

      const listRecursive = async (dir: string): Promise<Array<{path:string; type:'file'|'dir'}>> => {
        const out: Array<{path:string; type:'file'|'dir'}> = [];
        const items = await sftp.list(dir);
        for (const it of items) {
          const p = path.posix.join(dir, it.name);
          if (it.type === 'd') {
            out.push({ path: p, type: 'dir' });
            const sub = await listRecursive(p);
            out.push(...sub);
          } else if (it.type === '-') {
            out.push({ path: p, type: 'file' });
          }
        }
        return out;
      };

      // Scan configured directories
      for (const dir of dirs) {
        try {
          const items = await listRecursive(dir);
          const filesInDir: string[] = [];
          for (const it of items) {
            if (it.type === 'file') {
              scanned++;
              const norm = path.posix.normalize(it.path);
              filesInDir.push(norm);
              if (!expected.has(norm)) {
                orphaned++;
                try {
                  console.log(`[OrphanedMonitor] Orphan file (to delete): ${norm}`);
                  await sftp.delete(norm);
                  deleted++;
                  console.log(`[OrphanedMonitor] Deleted: ${norm}`);
                } catch (e:any) {
                  const msg = `Delete failed: ${norm}: ${e?.message||e}`;
                  console.warn(`[OrphanedMonitor] ${msg}`);
                  errors.push(msg);
                }
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
          if (settings.deleteEmptyDirs) {
            // remove empty directories bottom-up
            const dirs = items.filter(i=>i.type==='dir').map(i=>i.path).sort((a,b)=>b.length-a.length);
            for (const d of dirs) {
              try {
                const ls = await sftp.list(d);
                if (ls.length === 0) await sftp.rmdir(d);
              } catch {}
            }
          }
        } catch (e:any) {
          errors.push(`Scan failed: ${dir}: ${e?.message||e}`);
        }
      }

      await sftp.end();
      const out = { scanned, orphaned, deleted, ...(errors.length ? { errors } : {}) };
      console.log(`[OrphanedMonitor] Summary: scanned=${scanned}, orphaned=${orphaned}, deleted=${deleted}${errors.length ? `, errors=${errors.length}` : ''}`);
      this.recordOrphan(out);
      try {
        const current = this.configRepo.getFeatures().orphanedMonitor.totalDeleted || 0;
        this.configRepo.updateFeatures({ orphanedMonitor: { totalDeleted: current + deleted } });
      } catch {}
      return out;
    } catch (e:any) {
      const out = { scanned: 0, orphaned: 0, deleted: 0, errors: [e?.message || 'Unknown error'] };
      this.recordOrphan(out);
      return out;
    }
  }

  private recordOrphan(result: { scanned: number; orphaned: number; deleted: number; errors?: string[] }) {
    this.lastOrphanRunAt = new Date().toISOString();
    this.lastOrphanResult = result;
  }
}
