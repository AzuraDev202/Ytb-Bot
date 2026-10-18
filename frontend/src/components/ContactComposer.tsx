import { useEffect, useId, useRef, useState } from 'react';
import { ArrowLeft, Check, Copy, ExternalLink, Loader2, Mail, Save, Send, UserPlus, X } from 'lucide-react';
import { call } from '../api';
import type { Notice } from './ConfirmDialog';

type Draft = {recipient: string; account_id: string; subject: string; body: string; revision?: number};
type MailState = {configured: boolean; connecting: boolean; error: string; accounts: {id: string; email: string}[]};
type Attempt = {id: string; revision: number; created: string; status: string; payload: Draft; message_id: string};
type Context = {channel_id: string; name: string; contacts: {kind: 'email' | 'social'; label: string; value: string}[]; draft: Draft | null; history: Attempt[]};
const emptyMail: MailState = {configured: false, connecting: false, error: '', accounts: []};
const statusLabels: Record<string, string> = {sending: 'Đang gửi / chưa rõ kết quả', accepted: 'Gmail đã nhận yêu cầu', failed: 'Gmail từ chối', unknown: 'Chưa rõ kết quả · Kiểm tra Gmail'};

export function ContactComposer({channelId, onClose, notify}: {channelId: string | null; onClose: () => void; notify: (notice: Notice) => void}) {
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
    if (!account || !email || !form.subject.trim() || !form.body.trim()) {setError('Chọn tài khoản gửi, người nhận và nhập tiêu đề, nội dung.'); return;}
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
    <header><div><span className="eyebrow">KẾT NỐI VỚI NHÀ SÁNG TẠO</span><h2 id={id + '-title'}>Soạn liên hệ</h2><p>{context?.name || 'Đang mở thông tin kênh…'}</p></div><button className="icon-button" aria-label="Đóng hộp soạn" disabled={working} onClick={close}><X size={20}/></button></header>
    <div className="composer-content">
      {error && <div className="composer-message error" role="alert">{error}{!context && <button className="button secondary" onClick={() => setRetry(value => value + 1)}>Thử lại</button>}</div>}
      {!context && !error && <p role="status"><Loader2 size={18} className="spin"/> Đang đọc liên hệ và bản nháp…</p>}
      {context && !context.contacts.length && <div className="composer-message">Kênh chưa có email hoặc liên kết liên hệ được hỗ trợ trong dữ liệu đã lưu. Chọn kênh khác hoặc kiểm tra trang kênh để liên hệ thủ công.</div>}
      {context && !!context.contacts.length && <>
        {review ? <section className="mail-review" aria-label="Xem lại email"><div className="review-heading"><Check size={18}/><strong>Kiểm tra trước khi gửi</strong></div><dl><div><dt>Từ</dt><dd>{account?.email}</dd></div><div><dt>Đến</dt><dd>{form.recipient}</dd></div><div><dt>Tiêu đề</dt><dd>{form.subject}</dd></div></dl><div className="message-preview">{form.body}</div></section> : <>
          <label className="composer-field">Liên hệ nhận<select aria-label="Liên hệ nhận" value={form.recipient} disabled={working} onChange={event => change('recipient', event.target.value)}>{context.contacts.map(contact => <option key={contact.value} value={contact.value}>{contact.label} · {contact.value}</option>)}</select></label>
          {email && <section className="sender-section" aria-label="Tài khoản gửi"><div className="sender-heading"><Mail size={18}/><strong>Gmail / Google Workspace</strong><span className="pill neutral">OAUTH</span></div>
            <label className="composer-field">Tài khoản gửi<select aria-label="Tài khoản gửi" value={form.account_id} disabled={working} onChange={event => change('account_id', event.target.value)}><option value="">Chọn tài khoản đã kết nối</option>{mail.accounts.map(item => <option key={item.id} value={item.id}>{item.email}</option>)}</select></label>
            <div className="sender-actions"><button className="button secondary" disabled={working || mail.connecting || !mail.configured} onClick={() => void task(async () => {await call('connect_gmail'); setMail(await call<MailState>('get_mail_state'));})}>{mail.connecting ? <Loader2 size={15} className="spin"/> : <UserPlus size={15}/>} {mail.connecting ? 'Chờ đăng nhập Google…' : 'Kết nối Gmail'}</button>{account && <button className="button ghost" disabled={working || mail.connecting} onClick={() => void task(async () => {setMail(await call<MailState>('disconnect_gmail', account.id)); change('account_id', '');})}>Gỡ tài khoản khỏi Bot</button>}</div>
            {mail.connecting && <p role="status" className="composer-hint">Hoàn tất đăng nhập và cấp quyền trong trình duyệt. Phiên chờ tối đa 3 phút.</p>}{mail.error && <p className="field-error" role="alert">{mail.error}</p>}
            <details className="gmail-setup" open={!mail.configured}><summary>{mail.configured ? 'Cấu hình OAuth đã sẵn sàng' : 'Thiết lập kết nối lần đầu'}</summary><p>Trong Google Cloud: bật Gmail API → cấu hình Google Auth Platform → thêm quyền gmail.send và email → tạo OAuth Client loại Desktop app → tải file JSON. Nếu ứng dụng ở chế độ Testing, thêm email của bạn vào Test users.</p><div className="sender-actions"><button className="button secondary" disabled={working || mail.connecting} onClick={() => void task(async () => {const value = await call<MailState | null>('configure_gmail'); if (value) setMail(value);})}>{mail.configured ? 'Đổi file OAuth JSON' : 'Nhập file OAuth JSON'}</button><button className="button ghost" onClick={() => void task(async () => {await call('open_gmail_setup');})}><ExternalLink size={14}/> Mở hướng dẫn Google</button></div></details>
          </section>}
          {!email && <div className="composer-message"><ExternalLink size={17}/><span>Soạn nội dung rồi sao chép và mở hồ sơ để gửi trên nền tảng tương ứng. Bot không tự gửi tin mạng xã hội.</span></div>}
          {email && <label className="composer-field">Tiêu đề<input aria-label="Tiêu đề email" maxLength={200} value={form.subject} disabled={working} onChange={event => change('subject', event.target.value)} placeholder="Ví dụ: Đề xuất hợp tác nội dung"/></label>}
          <label className="composer-field">Nội dung<textarea aria-label="Nội dung liên hệ" maxLength={50000} rows={8} value={form.body} disabled={working} onChange={event => change('body', event.target.value)} placeholder="Giới thiệu bản thân và điều bạn muốn trao đổi với kênh…"/><span className="composer-hint">{form.body.length.toLocaleString('vi-VN')} / 50.000 ký tự · {dirty ? 'Có thay đổi chưa lưu' : 'Bản nháp đã đồng bộ với nội dung đang mở'}</span></label>
        </>}
        {result && <div className={`composer-message ${result.status === 'accepted' ? 'success' : 'error'}`} role="status">{result.message}</div>}
        {!!context.history.length && <details className="contact-history"><summary>Lịch sử gửi của kênh · {context.history.length} lần gần nhất</summary><ul>{context.history.map(item => <li key={item.id}><strong>{statusLabels[item.status] || item.status}</strong><span>{new Date(item.created).toLocaleString('vi-VN')} · {item.payload.recipient}</span><span>{item.payload.subject}</span></li>)}</ul><p>Trạng thái chưa rõ: kiểm tra thư Đã gửi trong Gmail trước khi gửi lại. Muốn tạo lần gửi mới, chỉnh sửa nội dung và lưu bản mới.</p></details>}
      </>}
    </div>
    {closing && <div className="composer-discard" role="alert"><p>Bản nháp có thay đổi chưa lưu.</p><div className="sender-actions"><button className="button primary" disabled={working} onClick={() => void task(async () => {await save(); finishClose();})}>Lưu và đóng</button><button className="button secondary" disabled={working} onClick={() => {void call('set_contact_dirty', false).catch(() => {}); finishClose();}}>Bỏ thay đổi</button><button className="button ghost" onClick={() => setClosing(false)}>Tiếp tục soạn</button></div></div>}
    <footer><span>{working ? 'Đang xử lý…' : 'Bản nháp lưu trong Bot'}</span><div className="composer-actions">{context && !!context.contacts.length && (review ? <><button className="button secondary" disabled={working} onClick={() => {setReview(false); setResult(null);}}><ArrowLeft size={15}/> Chỉnh sửa</button><button className="button primary" disabled={working || !!attempted || result?.status === 'accepted' || result?.status === 'unknown' || result?.status === 'failed'} onClick={() => void send()}>{working ? <Loader2 size={16} className="spin"/> : <Send size={16}/>} Gửi email</button></> : <><button className="button secondary" disabled={working} onClick={() => void task(async () => {await save(); notify({text: 'Đã lưu bản nháp liên hệ trong Bot.'});})}><Save size={15}/> Lưu bản nháp</button>{email ? <button className="button primary" disabled={working || mail.connecting || !account || !form.subject.trim() || !form.body.trim()} onClick={() => void preview()}><Send size={16}/> Xem lại email</button> : <><button className="button secondary" disabled={working || !form.body.trim()} onClick={() => void task(async () => {await navigator.clipboard.writeText(form.body); notify({text: 'Đã sao chép nội dung. Bạn có thể dán vào cuộc trò chuyện.'});})}><Copy size={15}/> Sao chép nội dung</button><button className="button primary" disabled={working} onClick={() => void task(async () => {await save(); await call('open_social_contact', channelId, form.recipient); notify({text: 'Đã mở liên hệ. Bạn gửi nội dung trên nền tảng đó.'});})}><ExternalLink size={15}/> Mở liên hệ</button></> }</> )}</div></footer>
  </dialog>;
}
