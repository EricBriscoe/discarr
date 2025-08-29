import { useEffect, useState } from 'react';
import { getFeatures, updateFeatures, runStalledCleanupNow, runOrphanedMonitorNow, FeaturesState } from '../api';

export default function Features() {
  const [state, setState] = useState<FeaturesState | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Local draft state (edit without auto-saving)
  const [botEnabled, setBotEnabled] = useState(false);
  const [stEnabled, setStEnabled] = useState(false);
  const [stInterval, setStInterval] = useState<number>(15);
  const [stMinAge, setStMinAge] = useState<number>(60);
  const [omEnabled, setOmEnabled] = useState(false);
  const [omHost, setOmHost] = useState('');
  const [omPort, setOmPort] = useState<number>(22);
  const [omUser, setOmUser] = useState('');
  const [omPass, setOmPass] = useState('');
  const [omInterval, setOmInterval] = useState<number>(60);
  const [omDeleteEmpty, setOmDeleteEmpty] = useState(false);
  const [omDirsText, setOmDirsText] = useState('');

  async function load() {
    setLoading(true); setError(null);
    try {
      const s = await getFeatures();
      setState(s);
      // populate local drafts
      setBotEnabled(!!s.botMonitoring?.enabled);
      setStEnabled(!!s.stalledDownloadCleanup?.enabled);
      setStInterval(s.stalledDownloadCleanup?.intervalMinutes ?? 15);
      setStMinAge(s.stalledDownloadCleanup?.minAgeMinutes ?? 60);
      setOmEnabled(!!s.orphanedMonitor?.enabled);
      setOmHost(s.orphanedMonitor?.connection?.host || '');
      setOmPort(s.orphanedMonitor?.connection?.port ?? 22);
      setOmUser(s.orphanedMonitor?.connection?.username || '');
      setOmPass('');
      setOmInterval(s.orphanedMonitor?.intervalMinutes ?? 60);
      setOmDeleteEmpty(!!s.orphanedMonitor?.deleteEmptyDirs);
      setOmDirsText((s.orphanedMonitor?.directories || []).join('\n'));
    }
    catch (e:any) { setError(e.message || 'Failed to load features'); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  async function saveAll() {
    try {
      setSaving(true); setSaved(false); setError(null);
      // Split on real newlines or literal "\n" sequences to normalize existing data
      const dirs = omDirsText.split(/\r?\n|\\n/g).map(s=>s.trim()).filter(Boolean);
      const payload: any = {
        botMonitoring: { enabled: botEnabled },
        stalledDownloadCleanup: { enabled: stEnabled, intervalMinutes: stInterval, minAgeMinutes: stMinAge },
        orphanedMonitor: {
          enabled: omEnabled,
          intervalMinutes: omInterval,
          deleteEmptyDirs: omDeleteEmpty,
          directories: dirs,
          connection: { host: omHost, port: omPort, username: omUser }
        }
      };
      if (omPass && omPass.trim()) payload.orphanedMonitor.connection.password = omPass.trim();
      const next = await updateFeatures(payload);
      setState(next);
      setSaved(true); setTimeout(()=>setSaved(false), 1500);
    } catch (e:any) {
      setError(e.message || 'Failed to save features');
    } finally {
      setSaving(false);
    }
  }

  async function runNow() {
    setRunning(true); setError(null);
    try { await runStalledCleanupNow(); await load(); }
    catch (e:any) { setError(e.message || 'Failed to run'); }
    finally { setRunning(false); }
  }

  const s = state?.stalledDownloadCleanup;
  const om = state?.orphanedMonitor;

  return (
    <div>
      <div className="row" style={{justifyContent:'space-between'}}>
        <h2>Features</h2>
        <button onClick={load} disabled={loading}>Refresh</button>
      </div>
      {error && <div className="card" style={{borderColor:'var(--danger)'}}>{error}</div>}

      <section className="card" style={{marginTop:'1rem'}}>
        <div className="row" style={{justifyContent:'space-between'}}>
          <h3>Discord Bot Monitoring</h3>
          <label>
            <input type="checkbox" checked={botEnabled} onChange={(e)=>setBotEnabled(e.target.checked)} disabled={saving || loading} /> Enable
          </label>
        </div>
        <div style={{color:'var(--muted)'}}>Starts/stops the Discord bot. Configure token and IDs under Settings.</div>
        {state?.botMonitoring && (
          <div style={{marginTop:'.5rem'}}>
            <span className={`pill ${state.botMonitoring.running ? 'ok' : 'warn'}`}>{state.botMonitoring.running ? 'running' : 'stopped'}</span>
          </div>
        )}
      </section>

      <section className="card" style={{marginTop:'1rem'}}>
        <div className="row" style={{justifyContent:'space-between'}}>
          <h3>Stalled Download Cleanup</h3>
          <label>
            <input type="checkbox" checked={stEnabled} onChange={(e)=>setStEnabled(e.target.checked)} disabled={saving || loading} /> Enable
          </label>
        </div>
        <div style={{color:'var(--muted)', marginBottom:'.5rem'}}>Removes Sonarr/Radarr torrents stuck in stalled download state older than the minimum age.</div>
        {s && (
          <div className="grid">
            <div>
              <label>Interval (minutes)</label>
              <input className="input" type="number" min={1} value={stInterval} onChange={(e:any)=>setStInterval(parseInt(e.target.value||'1'))} />
            </div>
            <div>
              <label>Minimum Age (minutes)</label>
              <input className="input" type="number" min={1} value={stMinAge} onChange={(e:any)=>setStMinAge(parseInt(e.target.value||'1'))} />
            </div>
          </div>
        )}
        <div className="row" style={{marginTop:'.5rem'}}>
          <button className="primary" onClick={runNow} disabled={running || loading}>Run Now</button>
          {s?.lastRunAt && <span className="pill ok">Last run: {new Date(s.lastRunAt).toLocaleString()}</span>}
          {s?.lastRunResult && (
            s.lastRunResult.error ? <span className="pill err">Error: {s.lastRunResult.error}</span> : <span className="pill ok">Removed {s.lastRunResult.removed}/{s.lastRunResult.attempted}</span>
          )}
          {typeof s?.totalRemoved === 'number' && <span className="pill ok">Total cleaned up: {s.totalRemoved}</span>}
        </div>
      </section>

      <section className="card" style={{marginTop:'1rem'}}>
        <div className="row" style={{justifyContent:'space-between'}}>
          <h3>Orphaned Download Monitor</h3>
          <label>
            <input type="checkbox" checked={omEnabled} onChange={(e)=>setOmEnabled(e.target.checked)} disabled={saving || loading} /> Enable
          </label>
        </div>
        <div style={{color:'var(--muted)', marginBottom:'.5rem'}}>Scans remote qBittorrent directories over SFTP and deletes files not associated with any active torrent.</div>
        {om && (
          <>
          <div className="grid">
            <div>
              <label>Host</label>
              <input className="input" placeholder="hostname or IP" value={omHost} onChange={(e:any)=>setOmHost(e.target.value)} />
            </div>
            <div>
              <label>Port</label>
              <input className="input" type="number" placeholder="22" value={omPort} onChange={(e:any)=>setOmPort(parseInt(e.target.value||'22',10))} />
            </div>
            <div>
              <label>Username</label>
              <input className="input" placeholder="username" value={omUser} onChange={(e:any)=>setOmUser(e.target.value)} />
            </div>
            <div>
              <label>Password</label>
              <input className="input" type="password" placeholder={om.connection?.passwordSet ? '********' : ''} value={omPass} onChange={(e:any)=>setOmPass(e.target.value)} />
            </div>
          </div>
          <div className="grid" style={{marginTop:'.5rem'}}>
            <div>
              <label>Interval (minutes)</label>
              <input className="input" type="number" min={1} value={omInterval} onChange={(e:any)=>setOmInterval(parseInt(e.target.value||'60',10))} />
            </div>
            <div>
              <label>Delete empty directories</label>
              <div className="row"><input type="checkbox" checked={omDeleteEmpty} onChange={(e:any)=>setOmDeleteEmpty(e.target.checked)} /></div>
            </div>
          </div>
          <div style={{marginTop:'.5rem'}}>
            <label>Directories (one per line)</label>
            <textarea
              className="input"
              rows={6}
              placeholder={"/path/to/downloads\n/path/to/incomplete"}
              value={omDirsText}
              onChange={(e:any)=>setOmDirsText(e.target.value)}
              onKeyDown={(e:any)=>{
                if (e.key === 'Enter') {
                  // Ensure newline is inserted even if a parent handler prevents default
                  // Insert at caret position for controlled component
                  e.preventDefault();
                  const el = e.target as HTMLTextAreaElement;
                  const start = el.selectionStart ?? omDirsText.length;
                  const end = el.selectionEnd ?? start;
                  const next = omDirsText.slice(0, start) + '\n' + omDirsText.slice(end);
                  setOmDirsText(next);
                }
              }}
            />
          </div>
          <div className="row" style={{marginTop:'.5rem'}}>
            <button className="primary" onClick={async ()=>{ setRunning(true); try { await runOrphanedMonitorNow(); await load(); } catch (e:any) { window.alert(e.message); } finally { setRunning(false); } }} disabled={running || loading}>Run Now</button>
            {om.lastRunAt && <span className="pill ok">Last run: {new Date(om.lastRunAt).toLocaleString()}</span>}
            {om.lastRunResult && (
              om.lastRunResult.errors && om.lastRunResult.errors.length > 0
                ? <span className="pill err">Errors: {om.lastRunResult.errors.length}</span>
                : <span className="pill ok">Deleted {om.lastRunResult.deleted} / Orphaned {om.lastRunResult.orphaned}</span>
            )}
            <span className="pill ok">Total deleted: {om.totalDeleted}</span>
          </div>
          </>
        )}
      </section>

      <div className="row" style={{marginTop:'1rem', justifyContent:'flex-end'}}>
        <button className="primary" onClick={saveAll} disabled={saving || loading}>Save Features</button>
        {saved && <span className="pill ok">Saved</span>}
      </div>
    </div>
  );
}
