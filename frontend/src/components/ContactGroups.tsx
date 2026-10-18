import { useEffect, useRef, useState } from 'react';
import { Mail, Search, RefreshCw, Users, ArrowUpRight, Inbox } from 'lucide-react';
import { call } from '../api';
import { useI18n } from '../i18n';
import { BulkComposer, bulkLabels, type BulkSnapshot, type Sender } from './BulkComposer';
import {LinkedAccounts} from './LinkedAccounts';
import {FacebookComposer} from './FacebookComposer';

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
  const [loading, setLoading] = useState(true);
  const selectAll = useRef<HTMLInputElement>(null);
  const [facebookChannel, setFacebookChannel] = useState<{id: string; name: string} | null>(null);
  useEffect(() => {
    if (!active) return;
    let live = true;
    setLoading(true);
    void Promise.all([call<Group[]>('contact_groups'), call<{accounts: Sender[]}>('get_mail_state'), call<BulkSnapshot[]>('list_bulk_mail')]).then(([rows, mail, batches]) => {if (live) {setGroups(rows); setAccounts(mail.accounts); setHistory(batches); setSelected(previous => previous.filter(id => rows.some(row => row.id === id && row.kind === 'email'))); setError('');}}).catch(reason => {if (live) setError(String(reason));}).finally(() => {if (live) setLoading(false);});
    return () => {live = false;};
  }, [active, refresh]);
  const visible = groups.filter(group => (kind === 'all' || group.kind === kind) && `${group.value} ${group.channels.map(channel => channel.name).join(' ')}`.toLowerCase().includes(search.toLowerCase()));
  const visibleEmails = visible.filter(group => group.kind === 'email').map(group => group.id);
  const visibleSelected = visibleEmails.filter(id => selected.includes(id)).length;
  const allChecked = visibleEmails.length > 0 && visibleSelected === visibleEmails.length;
  useEffect(() => {if (selectAll.current) selectAll.current.indeterminate = visibleSelected > 0 && !allChecked;}, [visibleSelected, allChecked]);
  return <section className="panel grouped-contacts" aria-label={t('Grouped contacts')}>
    <header className="contacts-heading"><div><h2>{t('Grouped contacts')}</h2><p>{t('Contact channels by Gmail or a linked Fanpage. Accepted sends remove channels and their other contacts from this list.')}</p></div><button className="button secondary" disabled={loading} onClick={() => setRefresh(value => value + 1)}><RefreshCw size={16} className={loading ? 'spin' : ''}/>{t('Refresh contacts')}</button></header>
    <LinkedAccounts onChanged={() => setRefresh(value => value + 1)}/>
    {!loading && !accounts.length && <p className="composer-message"><Mail size={18}/>{t('Connect a Gmail sender in Linked accounts first.')}</p>}
    {error && <p role="alert" className="field-error">{error}</p>}
    <div className="group-toolbar contacts-filters"><label>{t('Search contacts')}<div className="search-field"><Search size={17} aria-hidden="true"/><input aria-label={t('Search contacts')} value={search} onChange={event => setSearch(event.target.value)}/></div></label><label>{t('Contact type')}<select aria-label={t('Contact type')} value={kind} onChange={event => setKind(event.target.value)}><option value="all">{t('All contacts')}</option><option value="email">{t('Email')}</option><option value="social">{t('Social contacts')}</option></select></label></div>
    <label className="select-all-contacts"><input ref={selectAll} type="checkbox" aria-label={t('Select all visible email groups')} checked={allChecked} disabled={loading || !!error || !visibleEmails.length} onChange={() => setSelected(previous => allChecked ? previous.filter(id => !visibleEmails.includes(id)) : [...new Set([...previous, ...visibleEmails])].slice(0, 100))}/>{t('Select all visible email groups')}</label>
    {selected.length >= 100 && !allChecked && <p role="status">{t('Selection limit reached. Send up to 100 email groups per batch.')}</p>}
    <div className="contact-selection-bar"><span role="status">{t('{count} selected', {count: selected.length})}<span className="selection-limit"> / 100</span></span><div><button className="button ghost" disabled={!selected.length} onClick={() => setSelected([])}>{t('Clear selection')}</button><button className="button primary" disabled={loading || !!error || !accounts.length || !selected.length || selected.length > 100} onClick={() => setComposer({initial: null})}><Mail size={16}/>{t('Compose bulk email')}</button></div></div>
    <ul className="contact-group-list" aria-busy={loading}>{visible.map(group => <li key={group.id} className={selected.includes(group.id) ? 'is-selected' : ''}><div className="contact-group-identity">{group.kind === 'email' ? <label className="contact-group-label"><input type="checkbox" aria-label={group.value} checked={selected.includes(group.id)} disabled={loading || (!selected.includes(group.id) && selected.length >= 100)} onChange={event => setSelected(previous => event.target.checked ? [...new Set([...previous, group.id])] : previous.filter(id => id !== group.id))}/><Mail size={17} aria-hidden="true"/><strong>{group.value}</strong></label> : <div className="contact-group-label"><ArrowUpRight size={18} aria-hidden="true"/><strong>{group.value}</strong></div>}<span className="contact-kind">{t(group.kind === 'email' ? 'Email' : 'Social contacts')}</span></div><span className="contact-channel-names"><Users size={15} aria-hidden="true"/>{group.channels.map(channel => channel.name).join(', ')}{group.kind === 'social' && /^https:\/\/(?:www\.)?(?:facebook\.com|fb\.com|fb\.me)\//i.test(group.value) && <span className="facebook-channel-actions">{group.channels.map(channel => <button key={channel.id} className="button secondary" aria-label={t('Message {name}', {name: channel.name})} onClick={() => setFacebookChannel(channel)}>{t('Message {name}', {name: channel.name})}</button>)}</span>}</span><span className={`contact-status ${group.last_status}`}>{t(bulkLabels[group.last_status] || group.last_status || 'No previous attempt')}{group.last_created && ` · ${new Date(group.last_created).toLocaleString(locale)}`}</span></li>)}</ul>
    {loading && <p className="contacts-empty" role="status">{t('Loading contacts…')}</p>}
    {!loading && !error && !visible.length && <div className="contacts-empty"><Search size={24}/><h3>{t('No matching contacts')}</h3><p>{t(groups.length ? 'Try another search or contact type.' : 'Saved channel contacts will appear here after a scan.')}</p>{groups.length > 0 && <button className="button secondary" onClick={() => {setSearch(''); setKind('all');}}>{t('Reset filters')}</button>}</div>}
    <section className="batch-history-section" aria-label={t('Batch history')}><h3>{t('Batch history')}<span className="count-badge">{history.length}</span></h3>{!loading && !history.length && <div className="history-empty"><Inbox size={20}/><p>{t('Your reviewed batches and send results will appear here.')}</p></div>}<ul className="bulk-history">{history.map(batch => <li key={batch.id}><button className="button secondary" onClick={() => setComposer({initial: batch})}><span className="batch-history-title">{batch.subject}<small>{batch.sender} · {new Date(batch.created).toLocaleString(locale)}</small></span><span className={`contact-status ${batch.status}`}>{t(bulkLabels[batch.status] || batch.status)}</span><ArrowUpRight size={16}/></button></li>)}</ul></section>
    {composer && <BulkComposer groupIds={selected} accounts={accounts} initial={composer.initial} onClose={() => {setComposer(null); setRefresh(value => value + 1);}}/>}
    {facebookChannel && <FacebookComposer channel={facebookChannel} onClose={() => {setFacebookChannel(null); setRefresh(value => value + 1);}}/>}
  </section>;
}
