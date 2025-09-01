import { useEffect, useRef, useState } from 'react';
import { getFeatures, updateFeatures, runStalledCleanupNow, runOrphanedMonitorNow, FeaturesState, runRecheckErroredNow, openOrphanedMonitorStream, runAutoQueueManagerNow } from '../api';

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
  const [omIgnoredText, setOmIgnoredText] = useState('');
  const [rqEnabled, setRqEnabled] = useState(false);
  const [rqInterval, setRqInterval] = useState<number>(30);
  const [aqEnabled, setAqEnabled] = useState(false);
  const [aqInterval, setAqInterval] = useState<number>(10);
  const [aqMaxGb, setAqMaxGb] = useState<number>(0);
  const [aqMaxActive, setAqMaxActive] = useState<number>(5);
  const [omStreaming, setOmStreaming] = useState(false);
  const [omLog, setOmLog] = useState<string[]>([]);
  const esRef = useRef<EventSource | null>(null);
  function fmtBytes(n?: number): string {
    if (!n || n <= 0) return '0 B';
    const u = ['B','KB','MB','GB','TB'];
    let v = n; let i = 0;
    while (v >= 1024 && i < u.length-1) { v /= 1024; i++; }
    return `${v.toFixed(1)} ${u[i]}`;
  }

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
      setOmIgnoredText((s.orphanedMonitor?.ignored || []).join('\n'));
      setRqEnabled(!!s.qbittorrentRecheckErrored?.enabled);
      setRqInterval(s.qbittorrentRecheckErrored?.intervalMinutes ?? 30);
      setAqEnabled(!!s.autoQueueManager?.enabled);
      setAqInterval(s.autoQueueManager?.intervalMinutes ?? 10);
      setAqMaxActive(s.autoQueueManager?.maxActiveTorrents ?? 5);
      setAqMaxGb(Math.max(0, Math.floor((s.autoQueueManager?.maxStorageBytes || 0) / (1024*1024*1024))));
    }
    catch (e:any) { setError(e.message || 'Failed to load features'); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  useEffect(() => {
    if (!omStreaming) {
      if (esRef.current) { esRef.current.close(); esRef.current = null; }
      return;
    }
    if (esRef.current) return; // already open
    setOmLog([]);
    const es = openOrphanedMonitorStream((ev: MessageEvent) => {
      try {
        const payload = JSON.parse((ev as MessageEvent).data || '{}');
        const { type, data, runId, ts } = payload || {};
        const tsStr = ts ? new Date(ts).toLocaleTimeString() : new Date().toLocaleTimeString();
        let line = `[${tsStr}] ${type}`;
        if (type === 'start') line += ` host=${data?.host} user=${data?.username} dirs=${(data?.dirs||[]).length}`;
        else if (type === 'qbit-fetched') line += ` torrents=${data?.torrents} qbFiles=${data?.qbFiles} expected=${data?.expected}`;
        else if (type === 'sftp-connected') line += ` connected`;
        else if (type === 'scan-start') line += ` dirs=${(data?.dirs||[]).length}`;
        else if (type === 'dir-summary') line += ` dir=${data?.dir} files=${data?.files} size=${fmtBytes(data?.sizeBytes)} scanned=${data?.scanned} orphaned=${data?.orphaned} deleted=${data?.deleted}`;
        else if (type === 'deleted') line += ` ${data?.path}`;
        else if (type === 'summary') line += ` scanned=${data?.scanned} expected=${data?.expected} orphaned=${data?.orphaned} deleted=${data?.deleted}`;
        else if (type === 'error') line += ` ERROR: ${data?.message}`;
        else line += ` ${JSON.stringify(data)}`;
        setOmLog(prev => {
          const next = [...prev, line];
          if (next.length > 500) next.shift();
          return next;
        });
        if (type === 'summary') {
          // auto-close stream shortly after summary; keep log visible
          setTimeout(()=> setOmStreaming(false), 1500);
        }
      } catch {
        // ignore parse errors
      }
    });
    esRef.current = es;
    return () => { es.close(); esRef.current = null; };
  }, [omStreaming]);

  async function saveAll() {
    try {
      setSaving(true); setSaved(false); setError(null);
      // Split on real newlines or literal "\n" sequences to normalize existing data
      const dirs = omDirsText.split(/\r?\n|\\n/g).map(s=>s.trim()).filter(Boolean);
      const ignored = omIgnoredText.split(/\r?\n|\\n/g).map(s=>s.trim()).filter(Boolean);
      const payload: any = {
        botMonitoring: { enabled: botEnabled },
        stalledDownloadCleanup: { enabled: stEnabled, intervalMinutes: stInterval, minAgeMinutes: stMinAge },
        qbittorrentRecheckErrored: { enabled: rqEnabled, intervalMinutes: rqInterval },
        orphanedMonitor: {
          enabled: omEnabled,
          intervalMinutes: omInterval,
          deleteEmptyDirs: omDeleteEmpty,
          directories: dirs,
          ignored,
          connection: { host: omHost, port: omPort, username: omUser }
        },
        autoQueueManager: {
          enabled: aqEnabled,
          intervalMinutes: aqInterval,
          maxActiveTorrents: aqMaxActive,
          maxStorageBytes: Math.max(0, Math.floor(aqMaxGb) * 1024 * 1024 * 1024),
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
        <div style={{color:'var(--muted)', marginBottom:'.5rem'}}>Removes torrents stuck in stalled download or metadata state older than the minimum age.</div>
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
          <h3>qBittorrent: Recheck Errored Torrents</h3>
          <label>
            <input type="checkbox" checked={rqEnabled} onChange={(e)=>setRqEnabled(e.target.checked)} disabled={saving || loading} /> Enable
          </label>
        </div>
        <div style={{color:'var(--muted)', marginBottom:'.5rem'}}>Rechecks torrents in error/missing files state. Use Run Now for manual, or enable scheduling with an interval.</div>
        <div className="grid">
          <div>
            <label>Interval (minutes)</label>
            <input className="input" type="number" min={1} value={rqInterval} onChange={(e:any)=>setRqInterval(parseInt(e.target.value||'30',10))} />
          </div>
        </div>
        <div className="row" style={{marginTop:'.5rem'}}>
          <button className="primary" onClick={async ()=>{ setRunning(true); try { const r = await runRecheckErroredNow(); await load(); window.alert(`Rechecked ${r.rechecked}/${r.attempted}`); } catch (e:any) { window.alert(e.message||'Failed'); } finally { setRunning(false); } }} disabled={running || loading}>Run Now</button>
          {state?.qbittorrentRecheckErrored?.lastRunAt && <span className="pill ok">Last run: {new Date(state.qbittorrentRecheckErrored.lastRunAt).toLocaleString()}</span>}
          {state?.qbittorrentRecheckErrored?.lastRunResult && (
            state.qbittorrentRecheckErrored.lastRunResult.error
              ? <span className="pill err">Error: {state.qbittorrentRecheckErrored.lastRunResult.error}</span>
              : <span className="pill ok">Rechecked {state.qbittorrentRecheckErrored.lastRunResult.rechecked}/{state.qbittorrentRecheckErrored.lastRunResult.attempted}</span>
          )}
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
          <div style={{marginTop:'.5rem'}}>
            <label>Ignore names (one per line)</label>
            <textarea
              className="input"
              rows={4}
              placeholder={".stfolder\\n.DS_Store"}
              value={omIgnoredText}
              onChange={(e:any)=>setOmIgnoredText(e.target.value)}
              onKeyDown={(e:any)=>{
                if (e.key === 'Enter') {
                  e.preventDefault();
                  const el = e.target as HTMLTextAreaElement;
                  const start = el.selectionStart ?? omIgnoredText.length;
                  const end = el.selectionEnd ?? start;
                  const next = omIgnoredText.slice(0, start) + '\n' + omIgnoredText.slice(end);
                  setOmIgnoredText(next);
                }
              }}
            />
            <div style={{color:'var(--muted)', fontSize:'.9em', marginTop:'.25rem'}}>Basenames only (e.g., .stfolder). These files or directories are never deleted.</div>
          </div>
          <div className="row" style={{marginTop:'.5rem'}}>
            <button className="primary" onClick={async ()=>{ setRunning(true); setOmStreaming(true); try { await runOrphanedMonitorNow(); } catch (e:any) { window.alert(e.message); } finally { setRunning(false); } }} disabled={running || loading}>Run Now</button>
          </div>
          {(omStreaming || omLog.length>0) && (
            <div className="card" style={{marginTop:'.5rem', maxHeight: 240, overflow:'auto', background:'var(--bg)', fontFamily:'monospace', fontSize:'0.85em'}}>
              {omLog.length === 0 ? <div style={{color:'var(--muted)'}}>Waiting for events…</div> : omLog.map((l, i)=> <div key={i}>{l}</div>)}
            </div>
          )}
          </>
        )}
      </section>

      <section className="card" style={{marginTop:'1rem'}}>
        <div className="row" style={{justifyContent:'space-between'}}>
          <h3>Auto Queue Manager</h3>
          <label>
            <input type="checkbox" checked={aqEnabled} onChange={(e)=>setAqEnabled(e.target.checked)} disabled={saving || loading} /> Enable
          </label>
        </div>
        <div style={{color:'var(--muted)', marginBottom:'.5rem'}}>Adjusts qBittorrent queue limits to avoid exceeding your storage quota.</div>
        <div className="grid">
          <div>
            <label>Interval (minutes)</label>
            <input className="input" type="number" min={1} value={aqInterval} onChange={(e:any)=>setAqInterval(parseInt(e.target.value||'10',10))} />
          </div>
          <div>
            <label>Max storage space (GB)</label>
            <input className="input" type="number" min={0} value={aqMaxGb} onChange={(e:any)=>setAqMaxGb(parseInt(e.target.value||'0',10))} />
          </div>
          <div>
            <label>Max active torrents</label>
            <input className="input" type="number" min={0} value={aqMaxActive} onChange={(e:any)=>setAqMaxActive(parseInt(e.target.value||'5',10))} />
          </div>
        </div>
        <div className="row" style={{marginTop:'.5rem'}}>
          <button className="primary" onClick={async ()=>{ setRunning(true); try { const r = await runAutoQueueManagerNow(); await load(); window.alert(`Set downloads=${r.setDownloads}, uploads=${r.setUploads}, total=${r.setTorrents}`); } catch (e:any) { window.alert(e.message||'Failed'); } finally { setRunning(false); } }} disabled={running || loading}>Run Now</button>
          {state?.autoQueueManager?.lastRunAt && <span className="pill ok">Last run: {new Date(state.autoQueueManager.lastRunAt).toLocaleString()}</span>}
          {state?.autoQueueManager?.lastRunResult && (
            state.autoQueueManager.lastRunResult.error
              ? <span className="pill err">Error: {state.autoQueueManager.lastRunResult.error}</span>
              : <span className="pill ok">Can start: {state.autoQueueManager.lastRunResult.canStart} (used {Math.round((state.autoQueueManager.lastRunResult.usedBytes||0)/(1024*1024*1024))} GB)</span>
          )}
        </div>
      </section>

      <div className="row" style={{marginTop:'1rem', justifyContent:'flex-end'}}>
        <button className="primary" onClick={saveAll} disabled={saving || loading}>Save Features</button>
        {saved && <span className="pill ok">Saved</span>}
      </div>
    </div>
  );
}
