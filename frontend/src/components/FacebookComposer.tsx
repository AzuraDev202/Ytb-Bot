import {useEffect, useRef, useState} from 'react';
import {call} from '../api';
import {useI18n} from '../i18n';
import type {PageAccount} from './LinkedAccounts';

type Conversation = {id: string; recipient_id: string; name: string; eligible: boolean};
type Review = {id: string; page_name: string; recipient_name: string; body: string};
type Attempt = {id: string; status: string; created: string; payload: {body: string; recipient_name: string}};

export function FacebookComposer({channel, onClose}: {channel: {id: string; name: string}; onClose: () => void}) {
  const {t, locale} = useI18n();
  const dialog = useRef<HTMLDialogElement>(null);
  const [pages, setPages] = useState<PageAccount[]>([]);
  const [pageId, setPageId] = useState('');
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationId, setConversationId] = useState('');
  const [body, setBody] = useState('');
  const [review, setReview] = useState<Review | null>(null);
  const [history, setHistory] = useState<Attempt[]>([]);
  const [result, setResult] = useState<{status: string; message: string} | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [discard, setDiscard] = useState(false);
  const selected = conversations.find(item => item.id === conversationId);
  useEffect(() => {
    dialog.current?.showModal();
    let live = true;
    void Promise.all([call<{accounts: PageAccount[]}>('facebook_state'), call<Attempt[]>('facebook_history', channel.id)])
      .then(([state, attempts]) => {if (live) {setPages(state.accounts); setPageId(state.accounts[0]?.id || ''); setHistory(attempts);}})
      .catch(reason => {if (live) setError(String(reason));});
    return () => {live = false; void call('set_facebook_dirty', false).catch(() => {});};
  }, [channel.id]);
  useEffect(() => {
    if (!pageId) return;
    let live = true;
    setLoading(true); setConversations([]); setConversationId(''); setError('');
    void call<Conversation[]>('facebook_conversations', pageId)
      .then(items => {if (live) setConversations(items);})
      .catch(reason => {if (live) setError(String(reason));})
      .finally(() => {if (live) setLoading(false);});
    return () => {live = false;};
  }, [pageId]);
  useEffect(() => {void call('set_facebook_dirty', !!body.trim() && !result).catch(reason => setError(String(reason)));}, [body, result]);
  function close() {if (busy) return; if (body.trim() && !result) setDiscard(true); else onClose();}
  async function prepare() {
    if (!selected || busy) return;
    setBusy(true); setError('');
    try {
      await call('bind_facebook_contact', channel.id, pageId, selected.id, selected.recipient_id);
      setReview(await call<Review>('prepare_facebook_message', channel.id, {page_id: pageId, body}));
    } catch (reason) {setError(String(reason));}
    finally {setBusy(false);}
  }
  async function send() {
    if (!review || busy || result) return;
    setBusy(true); setError('');
    try {setResult(await call<{status: string; message: string}>('send_facebook_message', review.id));}
    catch (reason) {
      setError(String(reason));
      // A bridge failure may happen after submission. Do not offer a blind retry.
      setResult({status: 'unknown', message: 'Messenger outcome is uncertain. Check the Page inbox before further contact.'});
    } finally {
      setBusy(false);
      void call<Attempt[]>('facebook_history', channel.id).then(setHistory).catch(() => {});
    }
  }
  return <dialog ref={dialog} className="contact-composer facebook-composer" aria-labelledby="facebook-composer-title" onCancel={event => {event.preventDefault(); close();}}>
    <header><div><h2 id="facebook-composer-title">{t('Messenger message')}</h2><p>{channel.name}</p></div><button className="icon-button" aria-label={t('Close Messenger composer')} disabled={busy} onClick={close}>×</button></header>
    <div className="composer-content">
      <p className="composer-message">{t('Choose the conversation that belongs to this channel. The recipient must have messaged your Page within 24 hours.')}</p>
      {error && <p role="alert" className="field-error">{t(error.replace(/^Error: /, ''))}</p>}
      {!pages.length && <p>{t('Connect a Fanpage in Linked accounts first.')}</p>}
      {!review ? <>
        <label className="composer-field">{t('Sending Fanpage')}<select aria-label={t('Sending Fanpage')} value={pageId} disabled={busy || !pages.length} onChange={event => setPageId(event.target.value)}>{pages.map(page => <option key={page.id} value={page.id}>{page.name}</option>)}</select></label>
        <label className="composer-field">{t('Page conversation')}<select aria-label={t('Page conversation')} value={conversationId} disabled={busy || loading} onChange={event => setConversationId(event.target.value)}><option value="">{loading ? t('Loading conversations…') : t('Select a conversation')}</option>{conversations.map(item => <option key={item.id} value={item.id} disabled={!item.eligible}>{item.name} · {item.recipient_id}{!item.eligible ? ` · ${t('Messaging unavailable')}` : ''}</option>)}</select></label>
        {!loading && !!pageId && !conversations.length && <p>{t('No verified conversations. Ask the recipient to message your Page first, then reopen this composer.')}</p>}
        <label className="composer-field">{t('Messenger message')}<textarea aria-label={t('Messenger message')} rows={7} maxLength={2000} value={body} disabled={busy} onChange={event => setBody(event.target.value)}/><small>{body.length} / 2,000</small></label>
      </> : <section className="messenger-review" aria-label={t('Messenger review')}><p><strong>{t('Sending Fanpage')}: </strong>{review.page_name}</p><p><strong>{t('Recipient')}: </strong>{review.recipient_name}</p><p className="message-preview">{review.body}</p></section>}
      {result && <p className={`composer-message ${result.status === 'accepted' ? 'success' : 'error'}`} role="status">{t(result.message)}</p>}
      {!!history.length && <details className="contact-history"><summary>{t('Messenger send history')}</summary><ul>{history.map(attempt => <li key={attempt.id}><strong>{t(attempt.status === 'sending' ? 'Outcome uncertain' : attempt.status)}</strong><span>{attempt.payload.recipient_name} · {new Date(attempt.created).toLocaleString(locale)}</span><span>{attempt.payload.body}</span></li>)}</ul></details>}
      {discard && <div role="alert"><p>{t('Discard the unsent Messenger draft?')}</p><button className="button secondary" onClick={onClose}>{t('Discard changes')}</button><button className="button ghost" onClick={() => setDiscard(false)}>{t('Keep editing')}</button></div>}
    </div>
    <footer><div className="composer-actions">{!result && (review ? <><button className="button secondary" disabled={busy} onClick={() => setReview(null)}>{t('Edit')}</button><button className="button primary" disabled={busy} onClick={() => void send()}>{busy ? t('Processing…') : t('Send Messenger message')}</button></> : <button className="button primary" disabled={busy || loading || !selected?.eligible || !body.trim()} onClick={() => void prepare()}>{t('Review Messenger message')}</button>)}</div></footer>
  </dialog>;
}
