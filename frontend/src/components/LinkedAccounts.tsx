import {useEffect, useState} from 'react';
import {call} from '../api';
import {useI18n} from '../i18n';

export type PageAccount = {id: string; name: string};
type MailState = {configured: boolean; connecting: boolean; error: string; accounts: {id: string; email: string}[]};

export function LinkedAccounts({onChanged}: {onChanged: () => void}) {
  const {t} = useI18n();
  const [open, setOpen] = useState(false);
  const [mail, setMail] = useState<MailState | null>(null);
  const [pages, setPages] = useState<PageAccount[]>([]);
  const [token, setToken] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function refresh() {
    const [gmail, facebook] = await Promise.all([call<MailState>('get_mail_state'), call<{accounts: PageAccount[]}>('facebook_state')]);
    setMail(gmail); setPages(facebook.accounts);
  }
  useEffect(() => {
    if (!open) return;
    let live = true;
    void Promise.all([call<MailState>('get_mail_state'), call<{accounts: PageAccount[]}>('facebook_state')])
      .then(([gmail, facebook]) => {if (live) {setMail(gmail); setPages(facebook.accounts);}})
      .catch(reason => {if (live) setError(String(reason));});
    return () => {live = false;};
  }, [open]);
  useEffect(() => {
    if (!open || !mail?.connecting) return;
    let live = true;
    const timer = window.setInterval(() => {
      void call<MailState>('get_mail_state').then(state => {if (live) {setMail(state); if (!state.connecting) onChanged();}})
        .catch(reason => {if (live) setError(String(reason));});
    }, 1200);
    return () => {live = false; window.clearInterval(timer);};
  }, [open, mail?.connecting, onChanged]);
  async function task(action: () => Promise<void>) {
    if (busy) return;
    setBusy(true); setError('');
    try {await action(); await refresh(); onChanged();}
    catch (reason) {setError(String(reason));}
    finally {setBusy(false);}
  }
  return <details className="linked-accounts" onToggle={event => {setOpen(event.currentTarget.open); if (!event.currentTarget.open) setToken('');}}>
    <summary>{t('Linked accounts')}</summary>
    {open && <div className="linked-account-content">
      <p>{t('Connect your Gmail sender accounts and Facebook Fanpages here.')}</p>
      {error && <p role="alert" className="field-error">{t(error.replace(/^Error: /, ''))}</p>}
      <section aria-label={t('Gmail accounts')}><h3>Gmail</h3>
        {mail?.error && <p role="alert" className="field-error">{t(mail.error)}</p>}
        <ul>{mail?.accounts.map(account => <li key={account.id}><span>{account.email}</span><button className="button secondary" disabled={busy || mail.connecting} onClick={() => void task(async () => {await call('disconnect_gmail', account.id);})}>{t('Disconnect')}</button></li>)}</ul>
        <div className="sender-actions"><button className="button secondary" disabled={busy || mail?.connecting} onClick={() => void task(async () => {await call('configure_gmail');})}>{t('Import Google OAuth file')}</button><button className="button primary" disabled={busy || !mail?.configured || mail.connecting} onClick={() => void task(async () => {await call('connect_gmail');})}>{mail?.connecting ? t('Connecting…') : t('Connect Gmail')}</button></div>
      </section>
      <section aria-label={t('Facebook Fanpages')}><h3>{t('Facebook Fanpages')}</h3>
        <p>{t('Use a Page access token with Messenger permissions. Public profile links alone cannot receive API messages.')}</p>
        <ul>{pages.map(page => <li key={page.id}><span>{page.name}</span><button className="button secondary" disabled={busy} onClick={() => void task(async () => {await call('disconnect_facebook', page.id);})}>{t('Disconnect')}</button></li>)}</ul>
        <form className="page-connect-form" onSubmit={event => {event.preventDefault(); const value = token; setToken(''); void task(async () => {await call('connect_facebook', value);});}}>
          <label className="composer-field">{t('Page access token')}<input aria-label={t('Page access token')} type="password" autoComplete="off" spellCheck={false} maxLength={8192} value={token} disabled={busy} onChange={event => setToken(event.target.value)}/></label>
          <button className="button primary" type="submit" disabled={busy || !token.trim()}>{t('Connect Fanpage')}</button>
        </form>
      </section>
    </div>}
  </details>;
}
