import { useEffect, useState } from 'react';
import { call } from '../api';
import { useI18n } from '../i18n';
import { BulkComposer, bulkLabels, type BulkSnapshot, type Sender } from './BulkComposer';

type Group = {id: string; kind: 'email' | 'social'; value: string; channels: {id: string; name: string}[]; last_status: string; last_created: string};
export function ContactGroups({active}: {active: boolean}) {
  const {t, locale} = useI18n();
  const [groups, setGroups] = useState<Group[]>([]);
  const [accounts, setAccounts] = useState<Sender[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [search, setSearch] = useState('');
  const [kind, setKind] = useState('all');
  const [error, setError] = useState('');
  const [history, setHistory] = useState<BulkSnapshot[]>([]);
  const [composer, setComposer] = useState<{initial: BulkSnapshot | null} | null>(null);
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    if (!active) return;
    let live = true;
    void Promise.all([call<Group[]>('contact_groups'), call<{accounts: Sender[]}>('get_mail_state'), call<BulkSnapshot[]>('list_bulk_mail')]).then(([rows, mail, batches]) => {if (live) {setGroups(rows); setAccounts(mail.accounts); setHistory(batches); setError('');}}).catch(reason => {if (live) setError(String(reason));});
    return () => {live = false;};
  }, [active, refresh]);
  const visible = groups.filter(group => (kind === 'all' || group.kind === kind) && `${group.value} ${group.channels.map(channel => channel.name).join(' ')}`.toLowerCase().includes(search.toLowerCase()));
  return <section className="panel grouped-contacts" aria-label={t('Grouped contacts')}>
    <div className="group-toolbar"><h2>{t('Grouped contacts')}</h2><button className="button secondary" onClick={() => setRefresh(value => value + 1)}>{t('Refresh contacts')}</button><button className="button primary" disabled={!accounts.length || !selected.length || selected.length > 100} onClick={() => setComposer({initial: null})}>{t('Compose bulk email')} ({selected.length}/100)</button></div>
    <p>{t('Shared addresses show all associated channels. Social contacts are read only.')}</p>
    {!accounts.length && <p>{t('Connect a sender account in a channel contact composer first.')}</p>}
    {error && <p role="alert" className="field-error">{error}</p>}
    <div className="group-toolbar"><label>{t('Search contacts')}<input aria-label={t('Search contacts')} value={search} onChange={event => setSearch(event.target.value)}/></label><label>{t('Contact type')}<select aria-label={t('Contact type')} value={kind} onChange={event => setKind(event.target.value)}><option value="all">{t('All contacts')}</option><option value="email">{t('Email')}</option><option value="social">{t('Social contacts')}</option></select></label></div>
    <ul className="contact-group-list">{visible.map(group => <li key={group.id}><div>{group.kind === 'email' && <input type="checkbox" aria-label={group.value} checked={selected.includes(group.id)} disabled={!selected.includes(group.id) && selected.length >= 100} onChange={event => setSelected(previous => event.target.checked ? [...new Set([...previous, group.id])] : previous.filter(id => id !== group.id))}/>}<strong>{group.value}</strong></div><span>{group.channels.map(channel => channel.name).join(', ')}</span><span>{t(bulkLabels[group.last_status] || group.last_status || 'No previous attempt')}{group.last_created && ` · ${new Date(group.last_created).toLocaleString(locale)}`}</span></li>)}</ul>
    {!visible.length && <p>{t('No matching contacts')}</p>}
    <h3>{t('Batch history')}</h3><ul className="bulk-history">{history.map(batch => <li key={batch.id}><button className="button secondary" onClick={() => setComposer({initial: batch})}>{batch.subject} · {t(bulkLabels[batch.status] || batch.status)} · {new Date(batch.created).toLocaleString(locale)}</button></li>)}</ul>
    {composer && <BulkComposer groupIds={selected} accounts={accounts} initial={composer.initial} onClose={() => {setComposer(null); setRefresh(value => value + 1);}}/>}
  </section>;
}
