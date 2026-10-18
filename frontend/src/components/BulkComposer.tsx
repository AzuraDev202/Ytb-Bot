import { useEffect, useRef, useState } from 'react';
import { Check, ChevronRight, Mail, Send } from 'lucide-react';
import { call } from '../api';
import { LanguageSelect, useI18n } from '../i18n';

export type BulkSnapshot = {id: string; status: string; sender: string; account_id: string; subject: string; body: string; created: string; error?: string; recipients: {email: string; channels: {id: string; name: string}[]; status: string; error?: string}[]};
export type Sender = {id: string; email: string};
export const bulkLabels: Record<string, string> = {draft: 'Draft', running: 'Running', completed: 'Completed', stopped: 'Stopped', interrupted: 'Interrupted', error: 'Error', pending: 'Pending', sending: 'Sending / outcome uncertain', accepted: 'Gmail accepted the request', failed: 'Gmail rejected the request', unknown: 'Outcome uncertain · Check Gmail', skipped: 'Skipped', canceled: 'Canceled'};

export function BulkComposer({groupIds, accounts, initial, onClose}: {groupIds: string[]; accounts: Sender[]; initial: BulkSnapshot | null; onClose: () => void}) {
  const {t} = useI18n();
  const dialog = useRef<HTMLDialogElement>(null);
  const [form, setForm] = useState({account_id: accounts[0]?.id || '', subject: '', body: ''});
  const [snapshot, setSnapshot] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [closing, setClosing] = useState(false);
  const [attempted, setAttempted] = useState(false);
  const dirty = !snapshot && !!(form.subject || form.body);
  const awaitingResult = snapshot?.status === 'running' || snapshot?.recipients.some(item => item.status === 'sending');
  useEffect(() => {dialog.current?.showModal();}, []);
  useEffect(() => {void call('set_bulk_dirty', dirty).catch(() => {}); return () => {void call('set_bulk_dirty', false).catch(() => {});};}, [dirty]);
  useEffect(() => {
    if (!snapshot || !awaitingResult) return;
    let live = true;
    const timer = window.setInterval(() => {void call<BulkSnapshot>('get_bulk_mail', snapshot.id).then(value => {if (live && value) setSnapshot(value);}).catch(reason => {if (live) setError(String(reason));});}, 1000);
    return () => {live = false; clearInterval(timer);};
  }, [snapshot?.id, awaitingResult]);
  async function task(action: () => Promise<void>) {setBusy(true); setError(''); try {await action();} catch (reason) {setError(String(reason));} finally {setBusy(false);}}
  async function prepare() {const value = await call<BulkSnapshot>('prepare_bulk_mail', {group_ids: groupIds, ...form}); setSnapshot(value); return value;}
  function close() {if (dirty) setClosing(true); else onClose();}
  return <dialog ref={dialog} className="contact-composer bulk-composer" aria-label={t('Compose bulk email')} onCancel={event => {event.preventDefault(); if (!busy) close();}}>
    <header><h2>{t('Compose bulk email')}</h2><LanguageSelect/><button className="button secondary" disabled={busy} onClick={close}>{t('Close composer')}</button></header>
    <div className="composer-content">
      <ol className="bulk-stages" aria-label={t('Email workflow')}><li aria-current={!snapshot ? 'step' : undefined}><Mail size={16}/>{t('Compose bulk email')}<ChevronRight size={15} aria-hidden="true"/></li><li aria-current={snapshot?.status === 'draft' ? 'step' : undefined}>{snapshot && snapshot.status !== 'draft' ? <Check size={16}/> : <Send size={16}/>}{t('Review batch')}</li></ol>
      {error && <p role="alert" className="field-error">{error}</p>}
      {!snapshot ? <>
        <p className="bulk-intro">{t('{count} selected', {count: groupIds.length})} · {t('One email per unique address. Maximum 100 recipients.')}</p>
        <label className="composer-field">{t('Sender account')}<select disabled={busy} aria-label={t('Sender account')} value={form.account_id} onChange={event => setForm({...form, account_id: event.target.value})}>{accounts.map(account => <option key={account.id} value={account.id}>{account.email}</option>)}</select></label>
        <label className="composer-field">{t('Subject')}<input disabled={busy} aria-label={t('Email subject')} maxLength={200} value={form.subject} onChange={event => setForm({...form, subject: event.target.value})}/></label>
        <label className="composer-field">{t('Message')}<textarea disabled={busy} aria-label={t('Contact message')} rows={8} maxLength={50000} value={form.body} onChange={event => setForm({...form, body: event.target.value})}/></label>
      </> : <section aria-label={t('Review batch')}>
        <div className="bulk-review-heading"><h3>{t('Review before sending')}</h3><span className={`contact-status ${snapshot.status}`} role="status">{t(bulkLabels[snapshot.status] || snapshot.status)}</span></div><p className="bulk-sender">{t('From')}: <strong>{snapshot.sender}</strong></p><h4 className="bulk-subject">{snapshot.subject}</h4><div className="message-preview">{snapshot.body}</div>
        <p className="bulk-delivery-note">{t('Gmail acceptance does not confirm delivery. No automatic retries.')}</p>
        <div className="bulk-counts">{['pending', 'accepted', 'skipped'].map(status => <span key={status}>{t(bulkLabels[status])}<strong>{snapshot.recipients.filter(item => item.status === status).length}</strong></span>)}</div>
        <ul className="bulk-recipients">{snapshot.recipients.map(recipient => <li key={recipient.email}><strong>{recipient.email}</strong><span className="contact-channel-names">{recipient.channels.map(channel => channel.name).join(', ')}</span><span className={`contact-status ${recipient.status}`}>{t(bulkLabels[recipient.status] || recipient.status)}</span>{recipient.error && <span role="alert">{t(recipient.error)}</span>}</li>)}</ul>
        {snapshot.error && <p role="alert">{t(snapshot.error)}</p>}
        {snapshot.recipients.some(item => item.status === 'unknown' || item.status === 'sending') && <p role="status">{t('Check Sent in Gmail before creating another batch for uncertain recipients.')}</p>}
      </section>}
      {closing && <div className="composer-discard" role="alert"><p>{t('The draft has unsaved changes.')}</p><div className="sender-actions"><button className="button primary" disabled={busy || !form.account_id || !groupIds.length || groupIds.length > 100 || !form.subject.trim() || !form.body.trim()} onClick={() => void task(async () => {await prepare(); onClose();})}>{t('Save and close')}</button><button className="button secondary" disabled={busy} onClick={onClose}>{t('Discard changes')}</button><button className="button ghost" disabled={busy} onClick={() => setClosing(false)}>{t('Keep editing')}</button></div></div>}
    </div>
    <footer><div className="composer-actions">{!snapshot ? <button className="button primary" disabled={busy || !form.account_id || !form.subject.trim() || !form.body.trim() || !groupIds.length || groupIds.length > 100} onClick={() => void task(async () => {await prepare();})}>{t('Preview batch')}</button> : <>
      {snapshot.status === 'draft' && <>{!initial && <button className="button secondary" disabled={busy || attempted} onClick={() => {setForm({account_id: snapshot.account_id, subject: snapshot.subject, body: snapshot.body}); setSnapshot(null);}}>{t('Edit')}</button>}<button className="button primary" disabled={busy || attempted || snapshot.recipients.some(item => !['pending', 'skipped'].includes(item.status)) || !snapshot.recipients.some(item => item.status === 'pending')} onClick={() => {setAttempted(true); void task(async () => {try {setSnapshot(await call<BulkSnapshot>('start_bulk_mail', snapshot.id));} catch (reason) {const value = await call<BulkSnapshot>('get_bulk_mail', snapshot.id); if (value) setSnapshot(value); throw reason;}});}}>{t('Send batch')}</button></>}
      {snapshot.status === 'running' && <button className="button secondary" disabled={busy} onClick={() => void task(async () => {setSnapshot(await call<BulkSnapshot>('stop_bulk_mail', snapshot.id));})}>{t('Stop batch')}</button>}
      {snapshot.status === 'running' && <p>{t('Stopping cancels pending recipients after the current request finishes.')}</p>}
    </>}</div></footer>
  </dialog>;
}
