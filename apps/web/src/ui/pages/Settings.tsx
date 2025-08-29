import { useEffect, useState } from 'react';
import { getAdminConfig, updateAdminConfig } from '../api';

export default function Settings() {
  const SECRET_MASK = '********';
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Discord bot credentials (enable/disable moved to Features)
  const [clientId, setClientId] = useState('');
  const [channelId, setChannelId] = useState('');
  const [token, setToken] = useState('');

  // Services config state
  const [radarrUrl, setRadarrUrl] = useState('');
  const [sonarrUrl, setSonarrUrl] = useState('');
  const [plexUrl, setPlexUrl] = useState('');
  const [qbUrl, setQbUrl] = useState('');
  const [qbUser, setQbUser] = useState('');
  const [radarrKey, setRadarrKey] = useState('');
  const [sonarrKey, setSonarrKey] = useState('');
  const [qbPass, setQbPass] = useState('');

  // Monitoring config state (seconds in UI)
  const [checkInterval, setCheckInterval] = useState<number | ''>('');
  const [healthInterval, setHealthInterval] = useState<number | ''>('');
  const [minRefresh, setMinRefresh] = useState<number | ''>('');
  const [maxRefresh, setMaxRefresh] = useState<number | ''>('');
  const [verbose, setVerbose] = useState(false);

  async function load() {
    try {
      setLoading(true);
      setError(null);
      const cfg = await getAdminConfig();
      // enable/disable and running are handled in Features
      setClientId(cfg.discord.clientId || '');
      setChannelId(cfg.discord.channelId || '');
      setToken(cfg.discord.tokenSet ? SECRET_MASK : '');

      // Services
      setRadarrUrl(cfg.services.radarr?.url || '');
      setSonarrUrl(cfg.services.sonarr?.url || '');
      setPlexUrl(cfg.services.plex?.url || '');
      setQbUrl(cfg.services.qbittorrent?.url || '');
      setQbUser(cfg.services.qbittorrent?.username || '');
      setRadarrKey(cfg.services.radarr?.apiKeySet ? SECRET_MASK : '');
      setSonarrKey(cfg.services.sonarr?.apiKeySet ? SECRET_MASK : '');
      setQbPass(cfg.services.qbittorrent?.passwordSet ? SECRET_MASK : '');

      // Monitoring (convert ms to s if present)
      setCheckInterval(typeof cfg.monitoring.checkInterval === 'number' ? Math.round(cfg.monitoring.checkInterval/1000) : '');
      setHealthInterval(typeof cfg.monitoring.healthCheckInterval === 'number' ? Math.round(cfg.monitoring.healthCheckInterval/1000) : '');
      setMinRefresh(typeof cfg.monitoring.minRefreshInterval === 'number' ? Math.round(cfg.monitoring.minRefreshInterval/1000) : '');
      setMaxRefresh(typeof cfg.monitoring.maxRefreshInterval === 'number' ? Math.round(cfg.monitoring.maxRefreshInterval/1000) : '');
      setVerbose(!!cfg.monitoring.verbose);
    } catch (e:any) {
      setError(e.message || 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  function noop() {}

  async function saveDiscord() {
    try {
      setLoading(true);
      setError(null);
      const payload: any = { discord: { clientId: clientId.trim(), channelId: channelId.trim() } };
      const t = token.trim();
      if (t && t !== SECRET_MASK) payload.discord.token = t;
      await updateAdminConfig(payload);
      await load();
      setSaved(true); setTimeout(()=>setSaved(false), 1500);
    } catch (e:any) {
      setError(e.message || 'Failed to save Discord settings');
    } finally {
      setLoading(false);
    }
  }

  async function saveRadarr() {
    try {
      setLoading(true); setError(null);
      const services: any = { radarr: { url: radarrUrl.trim() } };
      const k = radarrKey.trim();
      if (k && k !== SECRET_MASK) services.radarr.apiKey = k;
      await updateAdminConfig({ services }); await load(); setSaved(true); setTimeout(()=>setSaved(false), 1500);
    } catch (e:any) { setError(e.message || 'Failed to save Radarr'); } finally { setLoading(false); }
  }

  async function saveSonarr() {
    try {
      setLoading(true); setError(null);
      const services: any = { sonarr: { url: sonarrUrl.trim() } };
      const k = sonarrKey.trim();
      if (k && k !== SECRET_MASK) services.sonarr.apiKey = k;
      await updateAdminConfig({ services }); await load(); setSaved(true); setTimeout(()=>setSaved(false), 1500);
    } catch (e:any) { setError(e.message || 'Failed to save Sonarr'); } finally { setLoading(false); }
  }

  async function savePlex() {
    try {
      setLoading(true); setError(null);
      const services: any = { plex: { url: plexUrl.trim() } };
      await updateAdminConfig({ services }); await load(); setSaved(true); setTimeout(()=>setSaved(false), 1500);
    } catch (e:any) { setError(e.message || 'Failed to save Plex'); } finally { setLoading(false); }
  }

  async function saveQb() {
    try {
      setLoading(true); setError(null);
      const services: any = { qbittorrent: { url: qbUrl.trim(), username: qbUser.trim() } };
      const p = qbPass.trim();
      if (p && p !== SECRET_MASK) services.qbittorrent.password = p;
      await updateAdminConfig({ services }); await load(); setSaved(true); setTimeout(()=>setSaved(false), 1500);
    } catch (e:any) { setError(e.message || 'Failed to save qBittorrent'); } finally { setLoading(false); }
  }

  async function saveMonitoring() {
    try {
      setLoading(true);
      setError(null);
      const toMs = (v: number | '') => typeof v === 'number' ? v*1000 : undefined;
      const monitoring: any = {
        checkInterval: toMs(checkInterval),
        healthCheckInterval: toMs(healthInterval),
        minRefreshInterval: toMs(minRefresh),
        maxRefreshInterval: toMs(maxRefresh),
        verbose
      };
      await updateAdminConfig({ monitoring });
      await load();
      setSaved(true); setTimeout(()=>setSaved(false), 1500);
    } catch (e:any) {
      setError(e.message || 'Failed to save monitoring settings');
    } finally { setLoading(false); }
  }

  return (
    <div>
      <h2>Settings</h2>
      {error && <div className="card" style={{borderColor:'var(--danger)'}}>{error}</div>}
      {/* API Access removed - SSO provides protection */}
      <section className="card" style={{marginTop:'1rem'}}>
        <h3>Discord Bot Credentials</h3>
        <input className="input" placeholder="Client ID" value={clientId} onChange={(e: React.ChangeEvent<HTMLInputElement>)=>setClientId(e.target.value)} style={{marginTop:'.5rem'}} />
        <input className="input" placeholder="Channel ID" value={channelId} onChange={(e: React.ChangeEvent<HTMLInputElement>)=>setChannelId(e.target.value)} style={{marginTop:'.5rem'}} />
        <input className="input" placeholder="Bot Token" value={token} onChange={(e: React.ChangeEvent<HTMLInputElement>)=>setToken(e.target.value)} style={{marginTop:'.5rem'}} />
        <div className="row" style={{marginTop:'.5rem'}}>
          <button className="primary" onClick={saveDiscord} disabled={loading}>Save Discord Settings</button>
          {saved && <span className="pill ok">Saved</span>}
        </div>
      </section>

      <section className="card" style={{marginTop:'1rem'}}>
        <h3>Radarr</h3>
        <input className="input" placeholder="Radarr URL" value={radarrUrl} onChange={(e: React.ChangeEvent<HTMLInputElement>)=>setRadarrUrl(e.target.value)} />
        <input className="input" placeholder="Radarr API Key" value={radarrKey} onChange={(e: React.ChangeEvent<HTMLInputElement>)=>setRadarrKey(e.target.value)} style={{marginTop:'.3rem'}} />
        <div className="row" style={{marginTop:'.5rem'}}>
          <button className="primary" onClick={saveRadarr} disabled={loading}>Save Radarr</button>
          {saved && <span className="pill ok">Saved</span>}
        </div>
      </section>

      <section className="card" style={{marginTop:'1rem'}}>
        <h3>Sonarr</h3>
        <input className="input" placeholder="Sonarr URL" value={sonarrUrl} onChange={(e: React.ChangeEvent<HTMLInputElement>)=>setSonarrUrl(e.target.value)} />
        <input className="input" placeholder="Sonarr API Key" value={sonarrKey} onChange={(e: React.ChangeEvent<HTMLInputElement>)=>setSonarrKey(e.target.value)} style={{marginTop:'.3rem'}} />
        <div className="row" style={{marginTop:'.5rem'}}>
          <button className="primary" onClick={saveSonarr} disabled={loading}>Save Sonarr</button>
          {saved && <span className="pill ok">Saved</span>}
        </div>
      </section>

      <section className="card" style={{marginTop:'1rem'}}>
        <h3>qBittorrent</h3>
        <input className="input" placeholder="WebUI URL" value={qbUrl} onChange={(e: React.ChangeEvent<HTMLInputElement>)=>setQbUrl(e.target.value)} />
        <input className="input" placeholder="Username" value={qbUser} onChange={(e: React.ChangeEvent<HTMLInputElement>)=>setQbUser(e.target.value)} style={{marginTop:'.3rem'}} />
        <input className="input" placeholder="Password" type="password" value={qbPass} onChange={(e: React.ChangeEvent<HTMLInputElement>)=>setQbPass(e.target.value)} style={{marginTop:'.3rem'}} />
        <div className="row" style={{marginTop:'.5rem'}}>
          <button className="primary" onClick={saveQb} disabled={loading}>Save qBittorrent</button>
          {saved && <span className="pill ok">Saved</span>}
        </div>
      </section>

      <section className="card" style={{marginTop:'1rem'}}>
        <h3>Plex</h3>
        <input className="input" placeholder="Plex URL" value={plexUrl} onChange={(e: React.ChangeEvent<HTMLInputElement>)=>setPlexUrl(e.target.value)} />
        <div className="row" style={{marginTop:'.5rem'}}>
          <button className="primary" onClick={savePlex} disabled={loading}>Save Plex</button>
          {saved && <span className="pill ok">Saved</span>}
        </div>
      </section>

      <section className="card" style={{marginTop:'1rem'}}>
        <h3>Monitoring</h3>
        <div className="grid">
          <div>
            <label>Check Interval (s)</label>
            <input className="input" type="number" min={5} placeholder="300" value={checkInterval} onChange={(e: any)=>setCheckInterval(e.target.value ? parseInt(e.target.value) : '')} />
          </div>
          <div>
            <label>Health Interval (s)</label>
            <input className="input" type="number" min={5} placeholder="60" value={healthInterval} onChange={(e: any)=>setHealthInterval(e.target.value ? parseInt(e.target.value) : '')} />
          </div>
          <div>
            <label>Min Refresh (s)</label>
            <input className="input" type="number" min={5} placeholder="30" value={minRefresh} onChange={(e: any)=>setMinRefresh(e.target.value ? parseInt(e.target.value) : '')} />
          </div>
          <div>
            <label>Max Refresh (s)</label>
            <input className="input" type="number" min={10} placeholder="600" value={maxRefresh} onChange={(e: any)=>setMaxRefresh(e.target.value ? parseInt(e.target.value) : '')} />
          </div>
        </div>
        <div className="row" style={{marginTop:'.5rem'}}>
          <label><input type="checkbox" checked={verbose} onChange={e=>setVerbose(e.target.checked)} /> Verbose logging</label>
        </div>
        <div className="row" style={{marginTop:'.5rem'}}>
          <button className="primary" onClick={saveMonitoring} disabled={loading}>Save Monitoring Settings</button>
          {saved && <span className="pill ok">Saved</span>}
        </div>
      </section>
      {/* About section removed as requested */}
    </div>
  );
}
