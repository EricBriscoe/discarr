import express from 'express';
import helmet from 'helmet';
import cors from 'cors';
import morgan from 'morgan';
import rateLimit from 'express-rate-limit';
import path from 'path';
import { HealthMonitor, DownloadMonitor, RadarrClient, SonarrClient, QBittorrentClient } from '@discarr/core';
import { ConfigRepo } from './services/config-repo';
import { BotController } from './services/bot-controller';
import { FeaturesService } from './services/features-service';
// SSO-protected deployment: no in-app auth middleware

// __dirname is available in CommonJS output; keep it simple

const app = express();
const port = parseInt(process.env.SERVER_PORT || '8080');

app.use(helmet());
app.use(cors({ origin: process.env.CORS_ORIGIN || '*'}));
app.use(express.json());
app.use(morgan('combined'));
app.use(rateLimit({ windowMs: 60_000, max: 300 }));

// Instantiate core services
const configRepo = new ConfigRepo(process.env.CONFIG_DIR || '/app/config');
const featuresService = new FeaturesService(configRepo);

// Bot controller with persistent settings
const botController = new BotController();
const discordEnabled = configRepo.getPublicConfig().discord.enabled;
if (discordEnabled) {
  const effectiveConfig = configRepo.getEffectiveConfig();
  botController.start(effectiveConfig).then(() => console.log('Discord bot started')).catch(err => console.error('Discord bot failed:', err));
}
// Start features scheduler(s)
featuresService.start();

// Routes
app.get('/api/health', async (_req, res) => {
  try {
    const hm = new HealthMonitor(configRepo.getEffectiveConfig());
    res.json(await hm.checkAllServices());
  } catch (e: any) { res.status(500).json({ error: e.message }); }
});

app.get('/api/downloads', async (_req, res) => {
  try {
    const hm = new HealthMonitor(configRepo.getEffectiveConfig());
    const dm = new DownloadMonitor(hm);
    res.json(await dm.getActiveDownloads());
  } catch (e: any) { res.status(500).json({ error: e.message }); }
});

app.get('/api/blocked', async (_req, res) => {
  try {
    const cfg = configRepo.getEffectiveConfig();
    const rc = cfg.services.radarr ? new RadarrClient(cfg.services.radarr.url, cfg.services.radarr.apiKey, cfg.monitoring.verbose) : undefined;
    const sc = cfg.services.sonarr ? new SonarrClient(cfg.services.sonarr.url, cfg.services.sonarr.apiKey, cfg.monitoring.verbose) : undefined;
    const radarr = rc ? await rc.getImportBlockedItems() : [];
    const sonarr = sc ? await sc.getImportBlockedItems() : [];
    res.json({ radarr, sonarr });
  } catch (e: any) { res.status(500).json({ error: e.message }); }
});

app.post('/api/blocked/:service/:id/approve', async (req, res) => {
  const { service, id } = req.params as { service: 'radarr' | 'sonarr'; id: string };
  try {
    const cfg = configRepo.getEffectiveConfig();
    if (service === 'radarr' && cfg.services.radarr) {
      await new RadarrClient(cfg.services.radarr.url, cfg.services.radarr.apiKey, cfg.monitoring.verbose).approveImport(parseInt(id));
    } else if (service === 'sonarr' && cfg.services.sonarr) {
      await new SonarrClient(cfg.services.sonarr.url, cfg.services.sonarr.apiKey, cfg.monitoring.verbose).approveImport(parseInt(id));
    }
    else return res.status(400).json({ error: 'Service not available' });
    res.json({ ok: true });
  } catch (e: any) { res.status(500).json({ error: e.message }); }
});

app.delete('/api/blocked/:service/:id', async (req, res) => {
  const { service, id } = req.params as { service: 'radarr' | 'sonarr'; id: string };
  try {
    const cfg = configRepo.getEffectiveConfig();
    if (service === 'radarr' && cfg.services.radarr) {
      await new RadarrClient(cfg.services.radarr.url, cfg.services.radarr.apiKey, cfg.monitoring.verbose).removeQueueItems([parseInt(id)]);
    } else if (service === 'sonarr' && cfg.services.sonarr) {
      await new SonarrClient(cfg.services.sonarr.url, cfg.services.sonarr.apiKey, cfg.monitoring.verbose).removeQueueItems([parseInt(id)]);
    }
    else return res.status(400).json({ error: 'Service not available' });
    res.json({ ok: true });
  } catch (e: any) { res.status(500).json({ error: e.message }); }
});

app.post('/api/actions/cleanup', async (_req, res) => {
  try {
    const cfg = configRepo.getEffectiveConfig();
    if (!cfg.services.qbittorrent) return res.status(400).json({ error: 'qBittorrent not configured' });
    const qb = new QBittorrentClient({ baseUrl: cfg.services.qbittorrent.url, username: cfg.services.qbittorrent.username, password: cfg.services.qbittorrent.password });
    const todos = await qb.getSeedinOrStalledTorrentsWithLabels();
    const result = await qb.deleteTorrents(todos.map(t => t.hash), true);
    res.json({ removed: result.filter(r => r.success).length, attempted: result.length });
  } catch (e: any) { res.status(500).json({ error: e.message }); }
});

// qBittorrent: Recheck all errored torrents
app.post('/api/actions/qbit/recheck-errored', async (_req, res) => {
  try {
    const cfg = configRepo.getEffectiveConfig();
    if (!cfg.services.qbittorrent) return res.status(400).json({ error: 'qBittorrent not configured' });
    const qb = new QBittorrentClient({ baseUrl: cfg.services.qbittorrent.url, username: cfg.services.qbittorrent.username, password: cfg.services.qbittorrent.password });
    const errored = await qb.getErroredTorrents();
    const hashes = errored.map(t => t.hash);
    const result = await qb.recheckTorrents(hashes);
    res.json({ attempted: hashes.length, rechecked: result.filter(r => r.success).length });
  } catch (e: any) { res.status(500).json({ error: e.message }); }
});

app.post('/api/actions/series-search', async (req, res) => {
  try {
    const seriesId = parseInt(req.body?.seriesId);
    const cfg = configRepo.getEffectiveConfig();
    if (!cfg.services.sonarr) return res.status(400).json({ error: 'Sonarr not configured' });
    if (!seriesId) return res.status(400).json({ error: 'seriesId required' });
    const ok = await new SonarrClient(cfg.services.sonarr.url, cfg.services.sonarr.apiKey, cfg.monitoring.verbose).searchForMissingEpisodes(seriesId);
    res.json({ ok });
  } catch (e: any) { res.status(500).json({ error: e.message }); }
});

// Features routes
app.get('/api/features', async (_req, res) => {
  try {
    const state = featuresService.getPublicState();
    const bot = configRepo.getPublicConfig().discord;
    res.json({
      ...state,
      botMonitoring: { enabled: bot.enabled, running: botController.running }
    });
  }
  catch (e:any) { res.status(500).json({ error: e.message }); }
});

app.put('/api/features', async (req, res) => {
  try {
    const payload = req.body || {};
    // update scheduled features
    await featuresService.updateSettings({
      stalledDownloadCleanup: payload?.stalledDownloadCleanup,
    });
    if (payload?.qbittorrentRecheckErrored) {
      await featuresService.updateRecheckSettings({ qbittorrentRecheckErrored: payload.qbittorrentRecheckErrored });
    }
    if (payload?.orphanedMonitor) {
      await featuresService.updateOrphanSettings({ orphanedMonitor: payload.orphanedMonitor });
    }
    // handle bot monitoring toggle if present
    if (payload?.botMonitoring && typeof payload.botMonitoring.enabled === 'boolean') {
      const enabled: boolean = !!payload.botMonitoring.enabled;
      const current = configRepo.getPublicConfig().discord.enabled;
      if (enabled !== current) {
        configRepo.updateAll({ discord: { enabled } });
        const effective = configRepo.getEffectiveConfig();
        if (enabled) await botController.restart(effective); else await botController.stop();
      }
    }
    const state = featuresService.getPublicState();
    const bot = configRepo.getPublicConfig().discord;
    res.json({ ...state, botMonitoring: { enabled: bot.enabled, running: botController.running } });
  } catch (e:any) { res.status(500).json({ error: e.message }); }
});

app.post('/api/features/stalled-cleanup/run', async (_req, res) => {
  try {
    const result = await featuresService.runStalledCleanup({ ignoreMinAge: true });
    res.json(result);
  } catch (e:any) { res.status(500).json({ error: e.message }); }
});

app.post('/api/features/orphaned-monitor/run', async (_req, res) => {
  try {
    const result = await featuresService.runOrphanedMonitor();
    res.json(result);
  } catch (e:any) { res.status(500).json({ error: e.message }); }
});

// qBittorrent: scheduled recheck run-now
app.post('/api/features/recheck-errored/run', async (_req, res) => {
  try {
    const result = await featuresService.runRecheckErrored();
    res.json(result);
  } catch (e:any) { res.status(500).json({ error: e.message }); }
});

// Admin config routes (all settings via JSON file)
app.get('/api/admin/config', async (_req, res) => {
  try { res.json({ ...configRepo.getPublicConfig(), running: botController.running }); }
  catch (e:any) { res.status(500).json({ error: e.message }); }
});

app.put('/api/admin/config', async (req, res) => {
  try {
    const { discord, services, monitoring } = req.body || {};
    configRepo.updateAll({ discord, services, monitoring });
    const effective = configRepo.getEffectiveConfig();
    // Restart bot when settings change to apply new config
    if ((discord && discord.enabled === false) || (discord && discord.enabled === true)) {
      if (discord.enabled) await botController.restart(effective); else await botController.stop();
    } else {
      // Service/monitoring updates may impact bot behavior; restart to apply
      await botController.restart(effective);
    }
    res.json({ ok: true, running: botController.running });
  } catch (e:any) { res.status(500).json({ error: e.message }); }
});

// Static assets (built web app)
const staticDir = path.resolve(__dirname, '../../web/dist');
app.use(express.static(staticDir));
app.get('*', (_req, res) => { res.sendFile(path.join(staticDir, 'index.html')); });

app.listen(port, () => { console.log(`Discarr server listening on :${port} (bot: ${botController.running ? 'on' : 'off'})`); });
