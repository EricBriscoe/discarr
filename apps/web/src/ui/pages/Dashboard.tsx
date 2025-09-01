import { useEffect, useState } from 'react';
import { getHealth } from '../api';

export default function Dashboard() {
  const [health, setHealth] = useState<any>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const h = await getHealth();
      setHealth(h);
    } catch (e: any) { setError(e.message || 'Failed to load'); }
    finally { setLoading(false); }
  }

  useEffect(() => { refresh(); const t = setInterval(refresh, 30_000); return () => clearInterval(t); }, []);

  const serviceMeta: Record<string, {label:string; icon:string}> = {
    plex: { label: 'Plex', icon: '🎞️' },
    radarr: { label: 'Radarr', icon: '🎬' },
    sonarr: { label: 'Sonarr', icon: '📺' },
    lidarr: { label: 'Lidarr', icon: '🎵' },
    qbittorrent: { label: 'qBittorrent', icon: '⚡' }
  };

  function fmt(n: any) { return typeof n === 'number' ? n : 0; }

  return (
    <div>
      <div className="row" style={{justifyContent:'space-between'}}>
        <h2>Dashboard</h2>
        <div className="row">
          <button onClick={refresh} disabled={loading}>Refresh</button>
        </div>
      </div>
      {error && <div className="card" style={{borderColor:'var(--danger)'}}>{error}</div>}
      <section className="grid" style={{marginTop:'1rem'}}>
        {Object.keys(serviceMeta)
          .filter(k => health && (health as any)[k])
          .map(k => {
            const meta = serviceMeta[k];
            const s = (health as any)[k];
            const status = s?.status || 'n/a';
            const pillClass = status === 'online' ? 'ok' : status === 'error' ? 'warn' : 'err';
            return (
              <div key={k} className="card">
                <h3>{meta.icon} {meta.label}</h3>
                <div className={`pill ${pillClass}`}>{status}</div>
                {s?.responseTime != null && <div style={{marginTop:'.5rem',color:'var(--muted)'}}>rt: {s.responseTime}ms</div>}
                {k === 'qbittorrent' && s?.torrentStats && (
                  <div style={{marginTop:'.5rem'}}>
                    <div className="grid" style={{gridTemplateColumns:'repeat(3,1fr)'}}>
                      <div>Downloading: <b>{fmt(s.torrentStats.downloading)}</b></div>
                      <div>Seeding: <b>{fmt(s.torrentStats.seeding)}</b></div>
                      <div>Stalled: <b>{fmt(s.torrentStats.stalled)}</b></div>
                      <div>Paused: <b>{fmt(s.torrentStats.paused)}</b></div>
                      <div>Queued: <b>{fmt(s.torrentStats.queued)}</b></div>
                      <div>Error: <b>{fmt(s.torrentStats.error)}</b></div>
                    </div>
                    <div style={{marginTop:'.4rem',color:'var(--muted)'}}>Total: {fmt(s.torrentStats.totalTorrents)}</div>
                  </div>
                )}
                {(k === 'sonarr' || k === 'radarr' || k === 'lidarr') && s?.queueStats && (
                  <div style={{marginTop:'.5rem'}}>
                    <div className="grid" style={{gridTemplateColumns:'repeat(3,1fr)'}}>
                      <div>Downloading: <b>{fmt(s.queueStats.downloading)}</b></div>
                      <div>Queued: <b>{fmt(s.queueStats.queued)}</b></div>
                      <div>Completed: <b>{fmt(s.queueStats.completed)}</b></div>
                      <div>Import Blocked: <b>{fmt(s.queueStats.importBlocked)}</b></div>
                      <div>Stuck: <b>{fmt(s.queueStats.stuck)}</b></div>
                      <div>Failed: <b>{fmt(s.queueStats.failed)}</b></div>
                    </div>
                    <div style={{marginTop:'.4rem',color:'var(--muted)'}}>In Queue: {fmt(s.queueStats.total)}</div>
                  </div>
                )}
              </div>
            );
          })}
      </section>
    </div>
  );
}
