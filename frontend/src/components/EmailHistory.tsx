import {useEffect, useState} from 'react';
import {call} from '../api';
import {useI18n} from '../i18n';

type Record = {id: string; channel_id: string; name: string; recipient: string; created: string; status: string};
const statuses: {[key: string]: string} = {accepted: 'Gmail accepted the request', unknown: 'Outcome uncertain · Check Gmail', sending: 'Sending / outcome uncertain', failed: 'Gmail rejected the request'};

export function EmailHistory() {
  const {t, locale} = useI18n();
  const [rows, setRows] = useState<Record[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [refresh, setRefresh] = useState(0);
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(0);
  useEffect(() => {
    let canceled = false;
    setLoading(true); setError('');
    void call<Record[]>('email_contact_history').then(value => {if (!canceled) setRows(value);})
      .catch(reason => {if (!canceled) setError(String(reason));})
      .finally(() => {if (!canceled) setLoading(false);});
    return () => {canceled = true;};
  }, [refresh]);
  const filtered = rows.filter(row => `${row.name} ${row.channel_id} ${row.recipient}`.toLowerCase().includes(query.toLowerCase()));
  const current = Math.min(page, Math.max(0, Math.ceil(filtered.length / 50) - 1));
  return <section className="panel" style={{padding: 20}}>
    <h2>{t('Email contact history')}</h2>
    <p>{t('Accepted and uncertain email attempts block another send to this channel, even after clearing scan history.')}</p>
    <label>{t('Search email history')} <input value={query} onChange={event => {setQuery(event.target.value); setPage(0);}}/></label>
    <button className="button secondary" disabled={loading} onClick={() => setRefresh(value => value + 1)}>{t('Refresh')}</button>
    {error && <p role="alert">{error}</p>}
    {loading ? <p role="status">{t('Loading email history…')}</p> : !filtered.length ? <p>{t('No email history found.')}</p> : <>
      <div className="table-scroll"><table><thead><tr><th>{t('YouTube channel')}</th><th>{t('Channel ID')}</th><th>{t('Email')}</th><th>{t('Email attempt time')}</th><th>{t('Email status')}</th></tr></thead><tbody>
        {filtered.slice(current * 50, current * 50 + 50).map((row, index) => <tr key={`${row.id}-${row.channel_id}-${index}`}><td>{row.name}</td><td>{row.channel_id}</td><td>{row.recipient}</td><td>{new Date(row.created).toLocaleString(locale)}</td><td>{t(statuses[row.status] || row.status)}</td></tr>)}
      </tbody></table></div>
      <button className="button secondary" disabled={current === 0} onClick={() => setPage(current - 1)}>←</button> {current + 1} / {Math.ceil(filtered.length / 50)} <button className="button secondary" disabled={(current + 1) * 50 >= filtered.length} onClick={() => setPage(current + 1)}>→</button>
    </>}
  </section>;
}
