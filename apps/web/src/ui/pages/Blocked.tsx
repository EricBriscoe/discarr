import { useEffect, useState } from 'react';
import { getBlocked, approveBlocked, rejectBlocked } from '../api';

type Block = { id:number; title:string };

export default function Blocked() {
  const [radarr, setRadarr] = useState<Block[]>([]);
  const [sonarr, setSonarr] = useState<Block[]>([]);
  const [lidarr, setLidarr] = useState<Block[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setLoading(true); setError(null);
    try { const data = await getBlocked(); setRadarr(data.radarr || []); setSonarr(data.sonarr || []); setLidarr((data as any).lidarr || []); }
    catch (e:any) { setError(e.message || 'Failed to load blocked items'); }
    finally { setLoading(false); }
  }

  useEffect(() => { refresh(); }, []);

  async function handleApprove(service:'radarr'|'sonarr', id:number) {
    try { await approveBlocked(service, id); await refresh(); } catch (e:any) { window.alert(e.message); }
  }
  async function handleReject(service:'radarr'|'sonarr'|'lidarr', id:number) {
    try { await rejectBlocked(service, id); await refresh(); } catch (e:any) { window.alert(e.message); }
  }

  const Section = ({name, items, service}:{name:string; items:Block[]; service:'radarr'|'sonarr'|'lidarr'}) => (
    <section className="card">
      <h3>{name} ({items.length})</h3>
      {items.length === 0 ? <div style={{color:'var(--muted)'}}>None</div> : (
        <table className="table">
          <thead><tr><th>Title</th><th style={{width:220}}>Actions</th></tr></thead>
          <tbody>
            {items.map(i => (
              <tr key={`${service}-${i.id}`}>
                <td>{i.title}</td>
                <td>
                  <div className="row">
                    {service !== 'lidarr' && <button className="primary" onClick={()=>handleApprove(service as 'radarr'|'sonarr',i.id)}>Approve</button>}
                    <button className="danger" onClick={()=>handleReject(service,i.id)}>Reject</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );

  return (
    <div>
      <div className="row" style={{justifyContent:'space-between'}}>
        <h2>Import Blocked</h2>
        <button onClick={refresh} disabled={loading}>Refresh</button>
      </div>
      {error && <div className="card" style={{borderColor:'var(--danger)'}}>{error}</div>}
      <div className="grid" style={{marginTop:'1rem'}}>
        <Section name="Radarr" items={radarr} service="radarr" />
        <Section name="Sonarr" items={sonarr} service="sonarr" />
        <Section name="Lidarr" items={lidarr} service="lidarr" />
      </div>
      <div className="card" style={{marginTop:'1rem'}}>
        <div className="pill warn">Note: Approve uses the services' manual import API and may require proper indexer/quality metadata present on the queue item.</div>
      </div>
    </div>
  );
}
