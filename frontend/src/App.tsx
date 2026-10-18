import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Activity, ArrowDown, ArrowRight, Check, ChevronRight, CircleHelp, Eye, EyeOff, FileSpreadsheet, LayoutDashboard, Loader2, Menu, Moon, Play, Plus, Radio, RefreshCw, Settings2, ShieldCheck, Sparkles, Square, Sun, Target, Trash2, X } from 'lucide-react';
import { call, initialState, type Bootstrap, type Snapshot, type WorkbookMeta } from './api';
import { ConfirmDialog, type Confirmation, type Notice } from './components/ConfirmDialog';
import { WorkspaceHeading, statuses, type StudioPage } from './components/WorkspaceHeading';
import { ScanSummary } from './components/ScanSummary';
import { KeywordTable } from './components/KeywordTable';
import { ResultsView } from './components/ResultsView';
import { WorkbookView } from './components/WorkbookView';

const format = (value: number) => new Intl.NumberFormat('vi-VN').format(value);
export default function App() {
  const [bootstrap, setBootstrap] = useState<Bootstrap | null>(null);
  const [state, setState] = useState<Snapshot>(initialState);
  const [tab, setTab] = useState<StudioPage>('scan');
  const [menu, setMenu] = useState(false);
  const [compact, setCompact] = useState(() => matchMedia('(max-width: 840px)').matches);
  const [theme, setTheme] = useState(() => localStorage.getItem('ytb-theme') || 'dark');
  const [motion, setMotion] = useState(() => localStorage.getItem('ytb-motion') !== 'off' && !matchMedia('(prefers-reduced-motion: reduce)').matches);
  const [key, setKey] = useState(''); const [showKey, setShowKey] = useState(false);
  const [age, setAge] = useState('90'); const [views, setViews] = useState('500'); const [depth, setDepth] = useState('2');
  const [text, setText] = useState('AI Automation\nAI Agent\ntạo video bằng AI');
  const [savedText, setSavedText] = useState<string | null>(null);
  const [savingKeywords, setSavingKeywords] = useState(false);
  const savingRef = useRef(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [notice, setNotice] = useState<Notice | null>(null);
  const [meta, setMeta] = useState<WorkbookMeta | null>(null);
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null);
  const [pending, setPending] = useState(false);
  const keywords = useMemo(() => [...new Set(text.split('\n').map(value => value.trim()).filter(Boolean))], [text]);
  const running = state.status === 'running' || state.status === 'stopping';
  const notify = useCallback((value: Notice) => setNotice(value), []);
  const logEnd = useRef<HTMLDivElement>(null);
  useEffect(() => {document.documentElement.dataset.theme = theme; localStorage.setItem('ytb-theme', theme);}, [theme]);
  useEffect(() => {document.documentElement.dataset.motion = motion ? 'on' : 'off'; localStorage.setItem('ytb-motion', motion ? 'on' : 'off');}, [motion]);
  useEffect(() => {if (notice) {const timer = window.setTimeout(() => setNotice(null), 6000); return () => clearTimeout(timer);}}, [notice]);
  useEffect(() => {const log = logEnd.current?.parentElement; if (log) log.scrollTop = log.scrollHeight;}, [state.logs.length]);
  useEffect(() => {
    let cancelled = false; let timer = 0; let connected = false;
    async function poll() {try {const snapshot = await call<Snapshot>('get_state'); if (!cancelled) setState(snapshot);} catch (error) {if (!cancelled) notify({text: String(error), error: true});} if (!cancelled) timer = window.setTimeout(poll, 700);}
    async function connect() {if (connected || cancelled) return; connected = true; try {const value = await call<Bootstrap>('get_bootstrap'); if (!cancelled) {setBootstrap(value); setText(value.keywords); setSavedText(value.keywords); if (value.preferences?.theme === 'dark' || value.preferences?.theme === 'light') setTheme(value.preferences.theme); if (typeof value.preferences?.motion === 'boolean') setMotion(value.preferences.motion); void poll(); void call('check_updates').catch(() => {});}} catch (error) {connected = false; if (!cancelled) notify({text: String(error), error: true});}}
    if (window.pywebview?.api) void connect();
    window.addEventListener('pywebviewready', connect);
    const updates = window.setInterval(() => {if (connected) void call('check_updates').catch(() => {});}, 6 * 60 * 60 * 1000);
    return () => {cancelled = true; clearTimeout(timer); clearInterval(updates); window.removeEventListener('pywebviewready', connect);};
  }, [notify]);

  const saveKeywords = useCallback(async () => {
    if (!bootstrap || savingRef.current) return false;
    savingRef.current = true; setSavingKeywords(true);
    try {await call('save_keywords', text); setSavedText(text); notify({text: 'Đã lưu từ khóa trong Bot.'}); return true;}
    catch (error) {notify({text: String(error), error: true}); return false;}
    finally {savingRef.current = false; setSavingKeywords(false);}
  }, [bootstrap, text, notify]);
  const dirty = savedText !== null && text !== savedText;
  useEffect(() => {document.documentElement.dataset.keywordsDirty = String(dirty); if (bootstrap) void call('set_keywords_dirty', dirty).catch(error => notify({text: String(error), error: true}));}, [dirty, bootstrap, notify]);
  useEffect(() => {const beforeUnload = (event: BeforeUnloadEvent) => {if (dirty) {event.preventDefault(); event.returnValue = '';}}; window.addEventListener('beforeunload', beforeUnload); return () => window.removeEventListener('beforeunload', beforeUnload);}, [dirty]);

  const start = useCallback(async () => {
    if (running || pending || !bootstrap) return;
    const nextErrors: Record<string, string> = {};
    if (!key.trim() && !bootstrap.has_api_key) nextErrors.key = 'Nhập YouTube API Key để bắt đầu.';
    if (!keywords.length) nextErrors.keywords = 'Thêm ít nhất một từ khóa, mỗi dòng một chủ đề.';
    if (!age.trim() || !Number.isInteger(Number(age)) || Number(age) < 1) nextErrors.age = 'Tuổi kênh phải là số nguyên từ 1.';
    if (!views.trim() || !Number.isInteger(Number(views)) || Number(views) < 0) nextErrors.views = 'Lượt xem phải là số nguyên từ 0.';
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) {if (nextErrors.key || nextErrors.age || nextErrors.views) setMenu(true); return;}
    setPending(true);
    try {if (!await saveKeywords()) return; await call('start_scan', {api_key: key, keywords, max_days: age, min_views: views, max_pages: depth}); setKey(''); setBootstrap(value => value ? {...value, has_api_key: true} : value); notify({text: 'Đã bắt đầu khám phá. Bạn có thể dừng bất cứ lúc nào.'});}
    catch (error) {notify({text: String(error), error: true});} finally {setPending(false);}
  }, [running, pending, bootstrap, key, keywords, age, views, depth, notify, saveKeywords]);
  const stop = useCallback(async () => {if (running) {try {await call('stop_scan'); notify({text: 'Đang dừng sau yêu cầu hiện tại; kết quả đã tìm sẽ được lưu.'});} catch (error) {notify({text: String(error), error: true});}}}, [running, notify]);
  const openExcel = useCallback(async (results = false) => {if (results) {setTab('results'); setMenu(false); return;} setPending(true); try {const workbook = await call<WorkbookMeta | null>(results ? 'open_results' : 'open_workbook'); if (workbook) {setMeta(workbook); setTab('excel'); setMenu(false);}} catch (error) {notify({text: String(error), error: true});} finally {setPending(false);}}, [notify]);
  useEffect(() => {function handle(event: KeyboardEvent) {if (document.querySelector('dialog[open]')) return; if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {event.preventDefault(); void start();} if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'o') {event.preventDefault(); void openExcel();} if (event.key === 'Escape') {if (menu) setMenu(false); else void stop();}} window.addEventListener('keydown', handle); return () => window.removeEventListener('keydown', handle);}, [start, stop, openExcel, menu]);
  useEffect(() => {if (bootstrap) void call('save_preferences', theme, motion).catch(error => notify({text: String(error), error: true}));}, [bootstrap, theme, motion, notify]);
  const percentage = state.total ? Math.round(state.completed / state.total * 100) : 0;
  const addPreset = (values: string[]) => setText([...new Set([...keywords, ...values])].join('\n'));
  useEffect(() => {
    const media = matchMedia('(max-width: 840px)');
    const resize = () => {setCompact(media.matches); if (!media.matches) setMenu(false);};
    media.addEventListener('change', resize); return () => media.removeEventListener('change', resize);
  }, []);
  useEffect(() => {
    if (!menu || !compact) return;
    const previous = document.activeElement as HTMLElement | null;
    const sidebar = document.getElementById('studio-sidebar');
    const focusables = () => Array.from(sidebar?.querySelectorAll<HTMLElement>('button:not([disabled]),input:not([disabled]),select:not([disabled])') || []).filter(item => item.getClientRects().length);
    focusables()[0]?.focus();
    const trap = (event: KeyboardEvent) => {
      if (event.key !== 'Tab') return;
      const items = focusables(); const first = items[0]; const last = items.at(-1);
      if (event.shiftKey && document.activeElement === first) {event.preventDefault(); last?.focus();}
      else if (!event.shiftKey && document.activeElement === last) {event.preventDefault(); first?.focus();}
    };
    document.addEventListener('keydown', trap);
    return () => {document.removeEventListener('keydown', trap); previous?.focus();};
  }, [menu, compact]);
  return <div className="studio-shell">
    <a className="skip-link" href="#workspace-content" onClick={event => {event.preventDefault(); document.getElementById('workspace-content')?.focus();}}>Đến nội dung chính</a>
    {menu && <button className="sidebar-scrim" aria-label="Đóng bộ lọc" onClick={() => setMenu(false)}/>}
    <aside id="studio-sidebar" inert={compact && !menu} className={`sidebar ${menu ? 'is-open' : ''}`} aria-label="Điều hướng và bộ lọc">
      <div className="brand"><span className="brand-mark"><Play size={23} fill="currentColor"/></span><div><strong>YTB<span>BOT</span><i/></strong><small>CREATOR WORKSPACE</small></div><button className="icon-button mobile-close" aria-label="Đóng menu" onClick={() => setMenu(false)}><X size={18}/></button></div>
      <span className="sidebar-caption">KHÔNG GIAN LÀM VIỆC</span><nav aria-label="Màn hình"><button aria-current={tab === 'scan' ? 'page' : undefined} className={tab === 'scan' ? 'nav-item active' : 'nav-item'} onClick={() => {setTab('scan'); setMenu(false);}}><LayoutDashboard size={18}/> Khám phá kênh <ChevronRight size={15}/></button><button disabled={!bootstrap} aria-current={tab === 'keywords' ? 'page' : undefined} className={tab === 'keywords' ? 'nav-item active' : 'nav-item'} onClick={() => {setTab('keywords'); setMenu(false);}}><FileSpreadsheet size={18}/> Từ khóa <span className="nav-hint">Sửa bảng</span></button><button disabled={!bootstrap} aria-current={tab === 'results' ? 'page' : undefined} className={tab === 'results' ? 'nav-item active' : 'nav-item'} onClick={() => {setTab('results'); setMenu(false);}}><FileSpreadsheet size={18}/> Kết quả <span className="nav-hint">Lịch sử</span></button></nav>
      <div className="sidebar-divider"/><div className="filter-heading"><span className="sidebar-caption">BỘ LỌC KHÁM PHÁ</span><Settings2 size={14}/></div>
      <div className="filter-stack"><label htmlFor="api-key">YouTube API Key <ShieldCheck size={13}/></label><div className={`password-input ${errors.key ? 'invalid' : ''}`}><input id="api-key" type={showKey ? 'text' : 'password'} value={key} autoComplete="off" spellCheck={false} placeholder={bootstrap?.has_api_key ? 'Đã lưu trên máy của bạn' : 'Nhập API Key…'} onChange={event => setKey(event.target.value)} aria-invalid={!!errors.key} aria-describedby="api-help"/><button className="icon-button" aria-label={showKey ? 'Ẩn API Key' : 'Hiện API Key'} aria-pressed={showKey} onClick={() => setShowKey(value => !value)}>{showKey ? <EyeOff size={16}/> : <Eye size={16}/>}</button></div><small id="api-help" className={errors.key ? 'field-error' : 'field-help'}>{errors.key || 'Khóa được lưu và xử lý trên máy.'}</small>
        <label htmlFor="channel-age">Tuổi kênh tối đa</label><div className={`number-input ${errors.age ? 'invalid' : ''}`}><input id="channel-age" type="number" min="1" step="1" value={age} onChange={event => setAge(event.target.value)} aria-invalid={!!errors.age}/><span>ngày</span></div>{errors.age && <small className="field-error">{errors.age}</small>}
        <label htmlFor="min-views">Lượt xem tối thiểu</label><div className={`number-input ${errors.views ? 'invalid' : ''}`}><input id="min-views" type="number" min="0" step="1" value={views} onChange={event => setViews(event.target.value)} aria-invalid={!!errors.views}/><span>views</span></div>{errors.views && <small className="field-error">{errors.views}</small>}
        <label htmlFor="scan-depth" className="range-label">Độ sâu quét <strong>{depth} trang</strong></label><input id="scan-depth" type="range" min="1" max="5" step="1" value={depth} onChange={event => setDepth(event.target.value)}/><div className="range-ticks"><span>Nhanh hơn</span><span>Sâu hơn</span></div><div className="quota-note"><CircleHelp size={15}/><span>Chỉ nhận kênh có email hoặc link liên hệ trong mô tả công khai.<br/>Mỗi trang tối đa 50 video; vẫn áp dụng tuổi kênh và lượt xem.</span></div>
      </div><div className="sidebar-bottom"><div className="motion-setting"><span>Hiệu ứng chuyển động</span><button className={`switch ${motion ? 'on' : ''}`} role="switch" aria-checked={motion} aria-label="Hiệu ứng chuyển động" onClick={() => setMotion(value => !value)}><span/></button></div><button className="update-button" disabled={!bootstrap || ['checking', 'downloading'].includes(state.update.status)} onClick={() => {if (state.update.status === 'available') setConfirmation({title: 'Cập nhật và khởi động lại?', text: 'App sẽ tải bản mới, kiểm tra checksum và mở lại. API Key và dữ liệu đã lưu được giữ nguyên.', action: () => {void call('install_available_update').catch(error => notify({text: String(error), error: true}));}}); else void call('check_updates').catch(error => notify({text: String(error), error: true}));}}><RefreshCw size={14} className={state.update.status === 'checking' ? 'spin' : ''}/><span>{state.update.status === 'available' ? 'Cập nhật ngay' : state.update.status === 'downloading' ? `Đang tải ${Math.round(state.update.progress * 100)}%` : 'Kiểm tra cập nhật'}</span></button><p className="build-info">{bootstrap ? `v${bootstrap.version} · ${bootstrap.build}` : 'Đang kết nối Python…'}</p><p className="update-message">{state.update.message}</p></div>
    </aside>
    <main id="workspace-content" tabIndex={-1} inert={compact && menu} className="workspace"><header className="topbar"><div className="breadcrumbs"><button className="icon-button menu-toggle" aria-label="Mở menu và bộ lọc" aria-expanded={menu} aria-controls="studio-sidebar" onClick={() => setMenu(true)}><Menu size={19}/></button><span>Studio</span><ChevronRight size={13}/><strong>{tab === 'scan' ? 'Khám phá kênh' : tab === 'keywords' ? 'Từ khóa' : tab === 'results' ? 'Kết quả' : 'Nhập file cũ'}</strong></div><div className="topbar-actions"><span className={`connection-status ${bootstrap ? 'connected' : ''}`}><i/>{bootstrap ? 'Xử lý trên máy' : 'Đang kết nối'}</span><button className="icon-button theme-toggle" aria-label={theme === 'dark' ? 'Chuyển giao diện sáng' : 'Chuyển giao diện tối'} onClick={() => setTheme(value => value === 'dark' ? 'light' : 'dark')}>{theme === 'dark' ? <Sun size={18}/> : <Moon size={18}/>}</button><span className="desktop-label">Desktop</span></div></header>
      <div className="workspace-body"><WorkspaceHeading page={tab} status={state.status} dirty={dirty} motion={motion} onBack={() => setTab('keywords')}/>
      {!bootstrap && <div className="connection-banner"><Radio size={17}/><span>Đang chờ kết nối desktop. Nếu xem bằng trình duyệt, hãy mở app bằng <code>python gui_app.py</code> để dùng chức năng Python.</span></div>}
      {tab === 'scan' && <ScanSummary state={state} keywords={keywords.length}/>}
      {tab === 'scan' ? <><div className="scan-grid"><section className="panel composer"><div className="section-heading"><div><span className="eyebrow"><Sparkles size={12}/> BƯỚC TIẾP THEO</span><h2>Bắt đầu từ một chủ đề</h2></div><button className="button ghost" disabled={!bootstrap || pending} aria-label="Sửa bảng từ khóa" onClick={() => setTab('keywords')}><FileSpreadsheet size={16}/> Sửa bảng</button></div><label htmlFor="keywords" className="sr-only">Danh sách từ khóa</label><div className={`keyword-editor ${errors.keywords ? 'invalid' : ''}`}><textarea id="keywords" disabled={!bootstrap} value={text} onChange={event => setText(event.target.value)} placeholder="AI Automation&#10;AI Agent&#10;tạo video bằng AI" spellCheck={false} aria-invalid={!!errors.keywords} aria-describedby="keyword-help"/><div className="editor-footer"><span id="keyword-help">{errors.keywords || 'Mỗi dòng một từ khóa. Từ trùng sẽ được gộp.'}</span><span className="keyword-count">{keywords.length} từ khóa</span></div></div><div className="preset-row"><span>Gợi ý nhanh</span><button disabled={!bootstrap} onClick={() => addPreset(['AI Automation', 'AI Agent', 'Công nghệ AI'])}><Plus size={13}/> AI & Công nghệ</button><button disabled={!bootstrap} onClick={() => addPreset(['YouTube Shorts', 'Content creator', 'Video editing'])}><Plus size={13}/> Sáng tạo nội dung</button></div><div className="composer-actions"><button className="button primary start-button" onClick={() => void start()} disabled={!bootstrap || running || pending || state.update.status === 'downloading'}>{running ? <Loader2 size={17} className="spin"/> : <Play size={16} fill="currentColor"/>}{running ? 'Đang khám phá…' : 'Bắt đầu khám phá'}<kbd>Ctrl ↵</kbd></button><button className="button secondary stop-button" disabled={state.status !== 'running'} onClick={() => void stop()}><Square size={13} fill="currentColor"/> Dừng</button></div><div className="composer-footnote"><ShieldCheck size={13}/> API Key được lưu trên máy và dùng cho YouTube API.</div></section>
      <section className="panel activity-panel"><div className="section-heading"><div><span className="eyebrow">TIẾN TRÌNH</span><h2><Activity size={17}/> Nhật ký khám phá</h2></div><button className="icon-button" aria-label="Xóa nhật ký" disabled={!bootstrap || !state.logs.length} onClick={() => {void call('clear_logs').catch(error => notify({text: String(error), error: true}));}}><Trash2 size={15}/></button></div><div className="progress-summary"><span>{state.status === 'stopping' ? 'Đang chờ yêu cầu hiện tại…' : statuses[state.status]}</span><strong>{percentage}%</strong></div><div className="progress-track" role="progressbar" aria-label="Tiến trình lượt quét" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percentage}><span style={{width: `${percentage}%`}}/></div><div className="log-list" role="log" aria-label="Nhật ký quét">{state.logs.length ? state.logs.map((log,index) => <div className={`log-line ${log.kind}`} key={`${log.time}-${index}`}><span className="log-time">{new Date(log.time).toLocaleTimeString('vi-VN', {hour:'2-digit',minute:'2-digit',second:'2-digit'})}</span><span>{log.text}</span></div>) : <div className="log-placeholder"><span className="signal-bars"><i/><i/><i/><i/><i/></span><strong>Sẵn sàng khi bạn bắt đầu.</strong><p>Nhật ký và kết quả xuất hiện tại đây<br/>khi bạn bắt đầu lượt khám phá.</p></div>}<div ref={logEnd}/></div></section></div>
      <section className="panel results-panel"><div className="section-heading"><div><span className="eyebrow">KẾT QUẢ GẦN NHẤT</span><h2>Kênh trong tầm ngắm <span className="count-badge">{state.matches}</span></h2></div><button className="button ghost" disabled={!bootstrap || pending} onClick={() => void openExcel(true)}><FileSpreadsheet size={16}/> Xem kết quả trong Bot <ChevronRight size={15}/></button></div>{state.rows.length ? <div className="table-scroll"><table><thead><tr><th>Kênh YouTube</th><th>Chủ đề</th><th>Lượt xem</th><th>Subscribers</th><th>Tuổi kênh</th><th>Liên hệ công khai</th><th/></tr></thead><tbody>{state.rows.map(row => <tr key={row['Channel ID']}><td><div className="channel-name"><span>{String(row['Tên Kênh']).slice(0,1)}</span><strong>{row['Tên Kênh']}</strong></div></td><td><span className="topic-tag">{row['Từ Khóa Quét']}</span></td><td className="numeric">{format(Number(row['Tổng Lượt Xem']))}</td><td className="numeric">{typeof row.Subscribers === 'number' ? format(row.Subscribers) : row.Subscribers}</td><td>{row['Tuổi Kênh (Ngày)']} ngày</td><td><span className="contact-preview" title={[row.Email, row.Facebook, row['Liên Hệ Khác']].filter(Boolean).join(' · ')}>{row.Email || row.Facebook || row['Liên Hệ Khác'] || 'Chưa kiểm tra (lượt cũ)'}</span></td><td><button className="icon-button" aria-label={`Mở kênh ${row['Tên Kênh']}`} onClick={() => {void call('open_channel', row['URL Kênh']).catch(error => notify({text:String(error),error:true}));}}><ArrowRight size={16}/></button></td></tr>)}</tbody></table></div> : <div className="results-empty"><div className="radar-illustration"><span/><span/><Target size={24}/></div><div><h3>{state.status === 'complete' ? 'Chưa có kênh phù hợp với bộ lọc.' : 'Kênh phù hợp sẽ xuất hiện tại đây.'}</h3><p>{state.status === 'complete' ? 'Chưa tìm thấy liên hệ công khai phù hợp. Thử thêm từ khóa hoặc mở rộng bộ lọc.' : 'Tìm kênh có email hoặc đường dẫn liên hệ công khai trong mô tả.'}</p></div><span className="empty-shortcut"><ArrowDown size={15}/> Kết quả lưu trong Bot · Không tạo Excel</span></div>}</section></> : tab === 'keywords' ? <KeywordTable text={text} onChange={setText} dirty={dirty} saving={savingKeywords} onSave={saveKeywords} onUse={() => setTab('scan')} onImport={() => void openExcel()}/> : tab === 'results' ? <ResultsView status={state.status} notify={notify} onDiscover={() => setTab('scan')}/> : <WorkbookView meta={meta} onOpen={() => void openExcel()} notify={notify} onImport={words => {setText(words.join('\n')); setTab('keywords'); notify({text: `Đã nhập ${words.length} từ khóa. Nhấn Lưu từ khóa để giữ trong Bot.`});}}/>}
      <footer className="workspace-footer"><span><ShieldCheck size={13}/> Từ khóa và kết quả được lưu trong Bot</span><span>YTB-BOT Creator Studio <i/> Dữ liệu của bạn · Studio của bạn</span></footer></div>
    </main>
    {notice && <div className={`toast ${notice.error ? 'error' : ''}`} role={notice.error ? 'alert' : 'status'}>{notice.error ? <CircleHelp size={18}/> : <Check size={18}/>}<span>{notice.text}</span><button className="icon-button" aria-label="Đóng thông báo" onClick={() => setNotice(null)}><X size={15}/></button></div>}
    <ConfirmDialog request={confirmation} dismiss={() => setConfirmation(null)}/>
  </div>;
}
