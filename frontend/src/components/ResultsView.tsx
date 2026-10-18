import { useEffect, useState } from 'react';
import { CheckCircle2, History, RefreshCw } from 'lucide-react';
import { call, type WorkbookMeta, type ScanStatus } from '../api';
import { WorkbookView } from './WorkbookView';
import { ContactComposer } from './ContactComposer';
import { TableLoading } from './TableLoading';
import type { Notice } from './ConfirmDialog';

type Run = {id: number; created: string; status: string; count: number; error: string};
const labels: Record<string, string> = {
  running: 'Scanning / unfinished',
  complete: 'Completed',
  stopped: 'Stopped',
  error: 'Error',
};

export function ResultsView({status, notify, onDiscover}: {
  status: ScanStatus;
  notify: (notice: Notice) => void;
  onDiscover: () => void;
}) {
  const [runs, setRuns] = useState<Run[]>([]);
  const [selected, setSelected] = useState('');
  const [meta, setMeta] = useState<WorkbookMeta | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(true);
  const [opening, setOpening] = useState(false);
  const [listError, setListError] = useState('');
  const [openError, setOpenError] = useState('');
  // Keep drafts mounted across automatic history/table refreshes.
  const [contactChannel, setContactChannel] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setListError('');
    void call<Run[]>('list_results')
      .then(rows => {
        if (!cancelled) {
          setRuns(rows);
          setSelected(value => value || String(rows[0]?.id || ''));
        }
      })
      .catch(error => {
        if (!cancelled) {
          setListError('Could not read the history. Click Refresh to try again.');
          notify({text: String(error), error: true});
        }
      })
      .finally(() => {if (!cancelled) setLoading(false);});
    return () => {cancelled = true;};
  }, [status, refresh, notify]);

  useEffect(() => {
    let cancelled = false;
    setMeta(null);
    setOpenError('');
    if (!selected) return;
    setOpening(true);
    void call<WorkbookMeta>('open_results', Number(selected))
      .then(value => {if (!cancelled) setMeta(value);})
      .catch(error => {
        if (!cancelled) {
          setOpenError('Could not open this scan. Click Refresh to try again.');
          notify({text: String(error), error: true});
        }
      })
      .finally(() => {if (!cancelled) setOpening(false);});
    return () => {cancelled = true;};
  }, [selected, status, refresh, notify]);

  const run = runs.find(item => String(item.id) === selected);
  const failure = listError || openError;

  return <div className="results-workspace">
    <section className="panel history-toolbar">
      <div><span className="eyebrow">YOUR HISTORY</span><h2>Choose a scan</h2></div>
      <div className="history-select">
        <label>Scan<select aria-label="Scan" value={selected} disabled={loading && !runs.length} onChange={event => setSelected(event.target.value)}>
          <option value="" disabled>Select scan</option>
          {runs.map(item => <option key={item.id} value={item.id}>#{item.id} · {new Date(item.created).toLocaleString('en-US')} · {item.count} channels · {labels[item.status] || item.status}</option>)}
        </select></label>
        <button className="button secondary" disabled={loading || opening} onClick={() => setRefresh(value => value + 1)}><RefreshCw size={15} className={loading ? 'spin' : ''}/> Refresh</button>
      </div>
      {run && <span className={`history-status ${run.status}`}><CheckCircle2 size={14}/>{labels[run.status] || run.status} · {run.count.toLocaleString('en-US')} saved channels</span>}
      {run?.error && <p role="alert" className="field-error">Scan failed: {run.error}. Previously collected channels are preserved.</p>}
    </section>
    {failure ? <section className="panel table-empty" role="alert">{failure}</section>
      : meta ? <WorkbookView meta={meta} onOpen={() => {}} onImport={() => {}} notify={notify} readOnly onContact={setContactChannel}/>
      : loading || opening || selected ? <section className="panel"><TableLoading label="Loading discovery history…"/></section>
      : <section className="panel empty-state"><div className="empty-illustration"><History size={32}/></div><h3>No discovery scans yet</h3><p>Choose a few keywords to start. Discovered channels will be saved here for you to revisit.</p><button className="button primary" onClick={onDiscover}>Start your first scan</button></section>}
    <ContactComposer channelId={contactChannel} onClose={() => setContactChannel(null)} notify={notify}/>
  </div>;
}
