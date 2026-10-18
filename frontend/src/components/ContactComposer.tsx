import { useI18n, LanguageSelect } from '../i18n';
import { useEffect, useId, useRef, useState } from 'react';
import { ArrowLeft, Check, Copy, ExternalLink, Loader2, Mail, Save, Send, UserPlus, X } from 'lucide-react';
import { call } from '../api';
import type { Notice } from './ConfirmDialog';

type Draft = {recipient: string; account_id: string; subject: string; body: string; revision?: number};
type MailState = {configured: boolean; connecting: boolean; error: string; accounts: {id: string; email: string}[]};
type Attempt = {id: string; revision: number; created: string; status: string; payload: Draft; message_id: string};
type Context = {channel_id: string; name: string; contacts: {kind: 'email' | 'social'; label: string; value: string}[]; draft: Draft | null; history: Attempt[]};
const emptyMail: MailState = {configured: false, connecting: false, error: '', accounts: []};
const statusLabels: Record<string, string> = {sending: 'Sending / outcome uncertain', accepted: 'Gmail accepted the request', failed: 'Gmail rejected the request', unknown: 'Outcome uncertain · Check Gmail'};

export function ContactComposer({channelId, onClose, notify}: {channelId: string | null; onClose: () => void; notify: (notice: Notice) => void}) {
  const { t, locale } = useI18n();
  const dialog = useRef<HTMLDialogElement>(null);
  const id = useId();
  const [context, setContext] = useState<Context | null>(null);
  const [mail, setMail] = useState(emptyMail);
  const [form, setForm] = useState<Draft>({recipient: '', account_id: '', subject: '', body: ''});
  const [saved, setSaved] = useState('');
  const [revision, setRevision] = useState(0);
  const [error, setError] = useState('');
  const [working, setWorking] = useState(false);
  const [review, setReview] = useState(false);
  const [closing, setClosing] = useState(false);
  const [result, setResult] = useState<{status: string; message: string} | null>(null);
  const [retry, setRetry] = useState(0);
  const dirty = !!context && JSON.stringify(form) !== saved;
  const email = context?.contacts.find(contact => contact.value === form.recipient)?.kind === 'email';
  const account = mail.accounts.find(item => item.id === form.account_id);
  const attempted = context?.history.some(item => item.revision === revision);
  const resultMessage = result?.status === 'accepted'
    ? 'Gmail accepted the send request. This status does not confirm delivery to the recipient.'
    : result?.status === 'unknown'
      ? 'It is unknown whether Gmail accepted the email. Check Sent in Gmail before sending again.'
      : result?.message || '';

  useEffect(() => {
    if (!channelId) {dialog.current?.close(); return;}
    let cancelled = false;
    setContext(null); setError(''); setMail(emptyMail); setReview(false); setClosing(false); setResult(null); setRevision(0);
    if (!dialog.current?.open) dialog.current?.showModal();
    void Promise.all([call<Context>('contact_context', channelId), call<MailState>('get_mail_state')]).then(([value, state]) => {
      if (cancelled) return;
      const initial = value.draft ? {recipient: value.draft.recipient, account_id: value.draft.account_id, subject: value.draft.subject, body: value.draft.body}
        : {recipient: value.contacts.find(contact => contact.kind === 'email')?.value || value.contacts[0]?.value || '', account_id: state.accounts[0]?.id || '', subject: '', body: ''};
      setContext(value); setMail(state); setForm(initial); setSaved(JSON.stringify(initial)); setRevision(value.draft?.revision || 0);
    }).catch(reason => {if (!cancelled) setError(String(reason));});
    return () => {cancelled = true;};
  }, [channelId, retry]);

  useEffect(() => {
    if (!channelId || !context) return;
    void call('set_contact_dirty', dirty).catch(() => {});
  }, [channelId, context, dirty]);
  useEffect(() => () => {void call('set_contact_dirty', false).catch(() => {});}, []);
  useEffect(() => {
    if (!channelId || !mail.connecting) return;
    let cancelled = false;
    const timer = window.setInterval(() => {
      void call<MailState>('get_mail_state').then(value => {if (!cancelled) setMail(value);}).catch(reason => {if (!cancelled) setError(String(reason));});
    }, 1200);
    return () => {cancelled = true; window.clearInterval(timer);};
  }, [channelId, mail.connecting]);

  function change(key: keyof Draft, value: string) {setForm(previous => ({...previous, [key]: value})); setResult(null); setError('');}
  async function save() {
    const value = await call<Draft>('save_contact_draft', channelId, form);
    setSaved(JSON.stringify(form)); setRevision(value.revision || 0);
    return value;
  }
  async function task(action: () => Promise<void>) {
    setWorking(true); setError('');
    try {await action();} catch (reason) {setError(String(reason));}
    finally {setWorking(false);}
  }
  function finishClose() {dialog.current?.close(); onClose();}
  function close() {if (!working) {if (dirty) setClosing(true); else finishClose();}}
  async function preview() {
    if (!account || !email || !form.subject.trim() || !form.body.trim()) {setError('Choose a sender account and recipient, then enter a subject and message.'); return;}
    await task(async () => {await save(); setReview(true);});
  }
  async function send() {
    await task(async () => {
      const value = await call<{status: string; message: string}>('send_contact_mail', channelId, revision);
      setResult(value);
      const refreshed = await call<Context>('contact_context', channelId);
      setContext(refreshed);
    });
  }
  if (!channelId) return null;
  return <dialog ref={dialog} className="contact-composer" aria-labelledby={id + '-title'} onCancel={event => {event.preventDefault(); close();}}>
    <header><div><h2 id={id + '-title'}>{t("Compose contact")}</h2><p>{context?.name || t("Opening channel details…")}</p></div><LanguageSelect/><button className="icon-button" aria-label={t("Close composer")} disabled={working} onClick={close}><X size={20}/></button></header>
    <div className="composer-content">
      {error && <div className="composer-message error" role="alert">{t(error)}{!context && <button className="button secondary" onClick={() => setRetry(value => value + 1)}>{t("Try again")}</button>}</div>}
      {!context && !error && <p role="status"><Loader2 size={18} className="spin"/> {t("Loading contacts and draft…")}</p>}
      {context && !context.contacts.length && <div className="composer-message">{t("This channel has no supported email or contact link in its saved data. Choose another channel or visit its page to contact it manually.")}</div>}
      {context && !!context.contacts.length && <>
        {review ? <section className="mail-review" aria-label={t("Review email")}><div className="review-heading"><Check size={18}/><strong>{t("Review before sending")}</strong></div><dl><div><dt>{t("From")}</dt><dd>{account?.email}</dd></div><div><dt>{t("To")}</dt><dd>{form.recipient}</dd></div><div><dt>{t("Subject")}</dt><dd>{form.subject}</dd></div></dl><div className="message-preview">{form.body}</div></section> : <>
          <label className="composer-field">{t("Recipient contact")}<select aria-label={t("Recipient contact")} value={form.recipient} disabled={working} onChange={event => change('recipient', event.target.value)}>{context.contacts.map(contact => <option key={contact.value} value={contact.value}>{t(contact.label)} · {contact.value}</option>)}</select></label>
          {email && <section className="sender-section" aria-label={t("Sender account")}><div className="sender-heading"><Mail size={18}/><strong>Gmail / Google Workspace</strong><span className="pill neutral">OAUTH</span></div>
            <label className="composer-field">{t("Sender account")}<select aria-label={t("Sender account")} value={form.account_id} disabled={working} onChange={event => change('account_id', event.target.value)}><option value="">{t("Choose a connected account")}</option>{mail.accounts.map(item => <option key={item.id} value={item.id}>{item.email}</option>)}</select></label>
            <div className="sender-actions"><button className="button secondary" disabled={working || mail.connecting || !mail.configured} onClick={() => void task(async () => {await call('connect_gmail'); setMail(await call<MailState>('get_mail_state'));})}>{mail.connecting ? <Loader2 size={15} className="spin"/> : <UserPlus size={15}/>} {mail.connecting ? t("Waiting for Google sign-in…") : t("Connect Gmail")}</button>{account && <button className="button ghost" disabled={working || mail.connecting} onClick={() => void task(async () => {setMail(await call<MailState>('disconnect_gmail', account.id)); change('account_id', '');})}>{t("Remove account from the bot")}</button>}</div>
            {mail.connecting && <p role="status" className="composer-hint">{t("Complete sign-in and grant access in your browser. The session waits up to 3 minutes.")}</p>}{mail.error && <p className="field-error" role="alert">{t(mail.error)}</p>}
            <details className="gmail-setup" open={!mail.configured}><summary>{mail.configured ? t("OAuth configuration is ready") : t("Set up your first connection")}</summary><p>{t("In Google Cloud: enable the Gmail API, configure Google Auth Platform, add the gmail.send and email scopes, create a Desktop app OAuth client, and download its JSON file. In Testing mode, add your email to Test users.")}</p><div className="sender-actions"><button className="button secondary" disabled={working || mail.connecting} onClick={() => void task(async () => {const value = await call<MailState | null>('configure_gmail'); if (value) setMail(value);})}>{mail.configured ? t("Change OAuth JSON file") : t("Import OAuth JSON file")}</button><button className="button ghost" onClick={() => void task(async () => {await call('open_gmail_setup');})}><ExternalLink size={14}/> {t("Open Google instructions")}</button></div></details>
          </section>}
          {!email && <div className="composer-message"><ExternalLink size={17}/><span>{t("Copy the message and open the profile to send manually. To send from a Fanpage, use Grouped contacts.")}</span></div>}
          {email && <label className="composer-field">{t("Subject")}<input aria-label={t("Email subject")} maxLength={200} value={form.subject} disabled={working} onChange={event => change('subject', event.target.value)} placeholder={t("Example: Content collaboration proposal")}/></label>}
          <label className="composer-field">{t("Message")}<textarea aria-label={t("Contact message")} maxLength={50000} rows={8} value={form.body} disabled={working} onChange={event => change('body', event.target.value)} placeholder={t("Introduce yourself and explain what you would like to discuss with the channel…")}/><span className="composer-hint">{form.body.length.toLocaleString(locale)} {t("/ 50,000 characters ·")} {dirty ? t("Unsaved changes") : t("The draft matches the open content")}</span></label>
        </>}
        {result && <div className={`composer-message ${result.status === 'accepted' ? 'success' : 'error'}`} role="status">{t(resultMessage)}</div>}
        {!!context.history.length && <details className="contact-history"><summary>{t("Channel send history ·")} {context.history.length} {t("most recent attempts")}</summary><ul>{context.history.map(item => <li key={item.id}><strong>{t(statusLabels[item.status] || item.status)}</strong><span>{new Date(item.created).toLocaleString(locale)} · {item.payload.recipient}</span><span>{item.payload.subject}</span></li>)}</ul><p>{t("Delivery is uncertain: check Sent mail in Gmail before trying again. To create a new send attempt, edit the content and save a new version.")}</p></details>}
      </>}
    </div>
    {closing && <div className="composer-discard" role="alert"><p>{t("The draft has unsaved changes.")}</p><div className="sender-actions"><button className="button primary" disabled={working} onClick={() => void task(async () => {await save(); finishClose();})}>{t("Save and close")}</button><button className="button secondary" disabled={working} onClick={() => {void call('set_contact_dirty', false).catch(() => {}); finishClose();}}>{t("Discard changes")}</button><button className="button ghost" onClick={() => setClosing(false)}>{t("Keep editing")}</button></div></div>}
    <footer><span>{working ? t("Processing…") : t("Draft saved in the bot")}</span><div className="composer-actions">{context && !!context.contacts.length && (review ? <><button className="button secondary" disabled={working} onClick={() => {setReview(false); setResult(null);}}><ArrowLeft size={15}/> {t("Edit")}</button><button className="button primary" disabled={working || !!attempted || result?.status === 'accepted' || result?.status === 'unknown' || result?.status === 'failed'} onClick={() => void send()}>{working ? <Loader2 size={16} className="spin"/> : <Send size={16}/>} {t("Send email")}</button></> : <><button className="button secondary" disabled={working} onClick={() => void task(async () => {await save(); notify({text: "Contact draft saved in the bot."});})}><Save size={15}/> {t("Save draft")}</button>{email ? <button className="button primary" disabled={working || mail.connecting || !account || !form.subject.trim() || !form.body.trim()} onClick={() => void preview()}><Send size={16}/> {t("Review email")}</button> : <><button className="button secondary" disabled={working || !form.body.trim()} onClick={() => void task(async () => {await navigator.clipboard.writeText(form.body); notify({text: "Message copied. You can paste it into the conversation."});})}><Copy size={15}/> {t("Copy message")}</button><button className="button primary" disabled={working} onClick={() => void task(async () => {await save(); await call('open_social_contact', channelId, form.recipient); notify({text: "Contact opened. Send your message on that platform."});})}><ExternalLink size={15}/> {t("Open contact")}</button></> }</> )}</div></footer>
  </dialog>;
}
