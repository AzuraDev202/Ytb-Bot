import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Activity, ArrowRight, Check, ChevronRight, CircleHelp, Eye, EyeOff, FileSpreadsheet, LayoutDashboard, Loader2, Menu, Moon, Play, Plus, Radio, RefreshCw, Settings2, ShieldCheck, Sparkles, Square, Sun, Target, Trash2, X } from 'lucide-react';
import { call, initialState, type Bootstrap, type Snapshot, type WorkbookMeta } from './api';
import { ConfirmDialog, type Confirmation, type Notice } from './components/ConfirmDialog';
import { WorkspaceHeading, statuses, type StudioPage } from './components/WorkspaceHeading';
import { ScanSummary } from './components/ScanSummary';
import { KeywordTable } from './components/KeywordTable';
import { ResultsView } from './components/ResultsView';
import { WorkbookView } from './components/WorkbookView';

const format = (value: number) => new Intl.NumberFormat('en-US').format(value);
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
  const [text, setText] = useState('AI Automation\nAI Agent\nAI video creation');
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
    try {await call('save_keywords', text); setSavedText(text); notify({text: 'Keywords saved in the bot.'}); return true;}
    catch (error) {notify({text: String(error), error: true}); return false;}
    finally {savingRef.current = false; setSavingKeywords(false);}
  }, [bootstrap, text, notify]);
  const dirty = savedText !== null && text !== savedText;
  useEffect(() => {document.documentElement.dataset.keywordsDirty = String(dirty); if (bootstrap) void call('set_keywords_dirty', dirty).catch(error => notify({text: String(error), error: true}));}, [dirty, bootstrap, notify]);
  useEffect(() => {const beforeUnload = (event: BeforeUnloadEvent) => {if (dirty) {event.preventDefault(); event.returnValue = '';}}; window.addEventListener('beforeunload', beforeUnload); return () => window.removeEventListener('beforeunload', beforeUnload);}, [dirty]);

  const start = useCallback(async () => {
    if (running || pending || !bootstrap) return;
    const nextErrors: Record<string, string> = {};
    if (!key.trim() && !bootstrap.has_api_key) nextErrors.key = 'Enter a YouTube API key to start.';
    if (!keywords.length) nextErrors.keywords = 'Add at least one keyword, one topic per line.';
    if (!age.trim() || !Number.isInteger(Number(age)) || Number(age) < 1) nextErrors.age = 'Channel age must be a whole number of at least 1.';
    if (!views.trim() || !Number.isInteger(Number(views)) || Number(views) < 0) nextErrors.views = 'Views must be a whole number of at least 0.';
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) {if (nextErrors.key || nextErrors.age || nextErrors.views) setMenu(true); return;}
    setPending(true);
    try {if (!await saveKeywords()) return; await call('start_scan', {api_key: key, keywords, max_days: age, min_views: views, max_pages: depth}); setKey(''); setBootstrap(value => value ? {...value, has_api_key: true} : value); notify({text: 'Discovery started. You can stop at any time.'});}
    catch (error) {notify({text: String(error), error: true});} finally {setPending(false);}
  }, [running, pending, bootstrap, key, keywords, age, views, depth, notify, saveKeywords]);
  const stop = useCallback(async () => {if (running) {try {await call('stop_scan'); notify({text: 'Stopping after the current request; discovered results will be saved.'});} catch (error) {notify({text: String(error), error: true});}}}, [running, notify]);
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
    <a className="skip-link" href="#workspace-content" onClick={event => {event.preventDefault(); document.getElementById('workspace-content')?.focus();}}>Skip to main content</a>
    {menu && <button className="sidebar-scrim" aria-label="Close filters" onClick={() => setMenu(false)}/>}
    <aside id="studio-sidebar" inert={compact && !menu} className={`sidebar ${menu ? 'is-open' : ''}`} aria-label="Navigation and filters">
      <div className="brand"><span className="brand-mark"><Play size={23} fill="currentColor"/></span><div><strong>YTB<span>BOT</span><i/></strong><small>CREATOR WORKSPACE</small></div><button className="icon-button mobile-close" aria-label="Close menu" onClick={() => setMenu(false)}><X size={18}/></button></div>
      <span className="sidebar-caption">WORKSPACE</span><nav aria-label="Pages"><button aria-current={tab === 'scan' ? 'page' : undefined} className={tab === 'scan' ? 'nav-item active' : 'nav-item'} onClick={() => {setTab('scan'); setMenu(false);}}><LayoutDashboard size={18}/> Discover channels <ChevronRight size={15}/></button><button disabled={!bootstrap} aria-current={tab === 'keywords' ? 'page' : undefined} className={tab === 'keywords' ? 'nav-item active' : 'nav-item'} onClick={() => {setTab('keywords'); setMenu(false);}}><FileSpreadsheet size={18}/> Keywords </button><button disabled={!bootstrap} aria-current={tab === 'results' ? 'page' : undefined} className={tab === 'results' ? 'nav-item active' : 'nav-item'} onClick={() => {setTab('results'); setMenu(false);}}><FileSpreadsheet size={18}/> Results </button></nav>
      <div className="sidebar-divider"/><div className="filter-heading"><span className="sidebar-caption">DISCOVERY FILTERS</span><Settings2 size={14}/></div>
      <div className="filter-stack"><label htmlFor="api-key">YouTube API Key <ShieldCheck size={13}/></label><div className={`password-input ${errors.key ? 'invalid' : ''}`}><input id="api-key" type={showKey ? 'text' : 'password'} value={key} autoComplete="off" spellCheck={false} placeholder={bootstrap?.has_api_key ? 'Saved on your device' : 'Enter API key…'} onChange={event => setKey(event.target.value)} aria-invalid={!!errors.key} aria-describedby={errors.key ? 'api-help' : undefined}/><button className="icon-button" aria-label={showKey ? 'Hide API key' : 'Show API key'} aria-pressed={showKey} onClick={() => setShowKey(value => !value)}>{showKey ? <EyeOff size={16}/> : <Eye size={16}/>}</button></div>{errors.key && <small id="api-help" className="field-error">{errors.key}</small>}
        <label htmlFor="channel-age">Maximum channel age</label><div className={`number-input ${errors.age ? 'invalid' : ''}`}><input id="channel-age" type="number" min="1" step="1" value={age} onChange={event => setAge(event.target.value)} aria-invalid={!!errors.age}/><span>days</span></div>{errors.age && <small className="field-error">{errors.age}</small>}
        <label htmlFor="min-views">Minimum views</label><div className={`number-input ${errors.views ? 'invalid' : ''}`}><input id="min-views" type="number" min="0" step="1" value={views} onChange={event => setViews(event.target.value)} aria-invalid={!!errors.views}/><span>views</span></div>{errors.views && <small className="field-error">{errors.views}</small>}
        <label htmlFor="scan-depth" className="range-label">Scan depth <strong>{depth} pages</strong></label><input id="scan-depth" type="range" min="1" max="5" step="1" value={depth} onChange={event => setDepth(event.target.value)}/><div className="range-ticks"><span>Faster</span><span>Deeper</span></div><div className="quota-note"><CircleHelp size={15}/><span>Only include channels with an email or contact link in their public description.</span></div>
      </div><div className="sidebar-bottom"><div className="motion-setting"><span>Motion effects</span><button className={`switch ${motion ? 'on' : ''}`} role="switch" aria-checked={motion} aria-label="Motion effects" onClick={() => setMotion(value => !value)}><span/></button></div><button className="update-button" disabled={!bootstrap || ['checking', 'downloading'].includes(state.update.status)} onClick={() => {if (state.update.status === 'available') setConfirmation({title: 'Update and restart?', text: 'The app will download the update, verify its checksum, and restart. Your API key and saved data will be preserved.', action: () => {void call('install_available_update').catch(error => notify({text: String(error), error: true}));}}); else void call('check_updates').catch(error => notify({text: String(error), error: true}));}}><RefreshCw size={14} className={state.update.status === 'checking' ? 'spin' : ''}/><span>{state.update.status === 'available' ? 'Update now' : state.update.status === 'downloading' ? `Downloading ${Math.round(state.update.progress * 100)}%` : 'Check for updates'}</span></button><p className="build-info">{bootstrap ? `v${bootstrap.version} · ${bootstrap.build}` : 'Connecting to Python…'}</p><p className="update-message">{state.update.message}</p></div>
    </aside>
    <main id="workspace-content" tabIndex={-1} inert={compact && menu} className="workspace"><header className="topbar"><div className="breadcrumbs"><button className="icon-button menu-toggle" aria-label="Open menu and filters" aria-expanded={menu} aria-controls="studio-sidebar" onClick={() => setMenu(true)}><Menu size={19}/></button><span>Studio</span><ChevronRight size={13}/><strong>{tab === 'scan' ? 'Discover channels' : tab === 'keywords' ? 'Keywords' : tab === 'results' ? 'Results' : 'Import existing file'}</strong></div><div className="topbar-actions"><span className={`connection-status ${bootstrap ? 'connected' : ''}`}><i/>{bootstrap ? 'Local processing' : 'Connecting'}</span><button className="icon-button theme-toggle" aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'} onClick={() => setTheme(value => value === 'dark' ? 'light' : 'dark')}>{theme === 'dark' ? <Sun size={18}/> : <Moon size={18}/>}</button><span className="desktop-label">Desktop</span></div></header>
      <div className="workspace-body"><WorkspaceHeading page={tab} status={state.status} motion={motion} onBack={() => setTab('keywords')}/>
      {!bootstrap && <div className="connection-banner"><Radio size={17}/><span>Waiting for the desktop connection. If viewing in a browser, launch the app with <code>python gui_app.py</code> to use Python features.</span></div>}
      {tab === 'scan' && <ScanSummary state={state} keywords={keywords.length}/>}
      {tab === 'scan' ? <><div className="scan-grid"><section className="panel composer"><div className="section-heading"><div><span className="eyebrow"><Sparkles size={12}/> NEXT STEP</span><h2>Start with a topic</h2></div><button className="button ghost" disabled={!bootstrap || pending} aria-label="Edit keyword table" onClick={() => setTab('keywords')}><FileSpreadsheet size={16}/> Edit table</button></div><label htmlFor="keywords" className="sr-only">Keyword list</label><div className={`keyword-editor ${errors.keywords ? 'invalid' : ''}`}><textarea id="keywords" disabled={!bootstrap} value={text} onChange={event => setText(event.target.value)} placeholder="AI Automation&#10;AI Agent&#10;AI video creation" spellCheck={false} aria-invalid={!!errors.keywords} aria-describedby="keyword-help"/><div className="editor-footer"><span id="keyword-help">{errors.keywords || 'One keyword per line. Duplicates will be merged.'}</span><span className="keyword-count">{keywords.length} keywords</span></div></div><div className="preset-row"><span>Quick suggestions</span><button disabled={!bootstrap} onClick={() => addPreset(['AI Automation', 'AI Agent', 'AI technology'])}><Plus size={13}/> AI & Technology</button><button disabled={!bootstrap} onClick={() => addPreset(['YouTube Shorts', 'Content creator', 'Video editing'])}><Plus size={13}/> Content creation</button></div><div className="composer-actions"><button className="button primary start-button" onClick={() => void start()} disabled={!bootstrap || running || pending || state.update.status === 'downloading'}>{running ? <Loader2 size={17} className="spin"/> : <Play size={16} fill="currentColor"/>}{running ? 'Discovering…' : 'Start discovery'}<kbd>Ctrl ↵</kbd></button><button className="button secondary stop-button" disabled={state.status !== 'running'} onClick={() => void stop()}><Square size={13} fill="currentColor"/> Stop</button></div></section>
      <section className="panel activity-panel"><div className="section-heading"><div><span className="eyebrow">PROGRESS</span><h2><Activity size={17}/> Discovery log</h2></div><button className="icon-button" aria-label="Clear logs" disabled={!bootstrap || !state.logs.length} onClick={() => {void call('clear_logs').catch(error => notify({text: String(error), error: true}));}}><Trash2 size={15}/></button></div><div className="progress-summary"><span>{state.status === 'stopping' ? 'Waiting for the current request…' : statuses[state.status]}</span><strong>{percentage}%</strong></div><div className="progress-track" role="progressbar" aria-label="Scan progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percentage}><span style={{width: `${percentage}%`}}/></div><div className="log-list" role="log" aria-label="Scan log">{state.logs.length ? state.logs.map((log,index) => <div className={`log-line ${log.kind}`} key={`${log.time}-${index}`}><span className="log-time">{new Date(log.time).toLocaleTimeString('en-US', {hour:'2-digit',minute:'2-digit',second:'2-digit'})}</span><span>{log.text}</span></div>) : <div className="log-placeholder"><span className="signal-bars"><i/><i/><i/><i/><i/></span><strong>Ready when you are.</strong><p>Logs and results appear here<br/>when you start a discovery scan.</p></div>}<div ref={logEnd}/></div></section></div>
      <section className="panel results-panel"><div className="section-heading"><div><span className="eyebrow">LATEST RESULTS</span><h2>Channels to explore <span className="count-badge">{state.matches}</span></h2></div><button className="button ghost" disabled={!bootstrap || pending} onClick={() => void openExcel(true)}><FileSpreadsheet size={16}/> View results in the bot <ChevronRight size={15}/></button></div>{state.rows.length ? <div className="table-scroll"><table><thead><tr><th>YouTube channel</th><th>Topic</th><th>Views</th><th>Subscribers</th><th>Channel age</th><th>Country</th><th>Public contacts</th><th/></tr></thead><tbody>{state.rows.map(row => <tr key={row['Channel ID']}><td><div className="channel-name"><span>{String(row['Channel Name']).slice(0,1)}</span><strong>{row['Channel Name']}</strong></div></td><td><span className="topic-tag">{row['Search Keyword']}</span></td><td className="numeric">{format(Number(row['Total Views']))}</td><td className="numeric">{typeof row.Subscribers === 'number' ? format(row.Subscribers) : row.Subscribers}</td><td>{row['Channel Age (Days)']} days</td><td>{row['Country'] || 'Not disclosed'}</td><td><span className="contact-preview" title={[row.Email, row.Facebook, row['Other Contacts']].filter(Boolean).join(' · ')}>{row.Email || row.Facebook || row['Other Contacts'] || 'Not checked (older scan)'}</span></td><td><button className="icon-button" aria-label={`Open channel ${row['Channel Name']}`} onClick={() => {void call('open_channel', row['Channel URL']).catch(error => notify({text:String(error),error:true}));}}><ArrowRight size={16}/></button></td></tr>)}</tbody></table></div> : <div className="results-empty"><div className="radar-illustration"><span/><span/><Target size={24}/></div><div><h3>{state.status === 'complete' ? 'No channels match your filters yet.' : 'Matching channels will appear here.'}</h3><p>{state.status === 'complete' ? 'Saved channels are skipped. Try keywords in other languages or increase scan depth.' : 'Find channels with an email or public contact link in their description.'}</p></div></div>}</section></> : tab === 'keywords' ? <KeywordTable text={text} onChange={setText} dirty={dirty} saving={savingKeywords} onSave={saveKeywords} onUse={() => setTab('scan')} onImport={() => void openExcel()}/> : tab === 'results' ? <ResultsView status={state.status} notify={notify} onDiscover={() => setTab('scan')}/> : <WorkbookView meta={meta} onOpen={() => void openExcel()} notify={notify} onImport={words => {setText(words.join('\n')); setTab('keywords'); notify({text: `Imported ${words.length} keywords. Click Save keywords to keep them in the bot.`});}}/>}
      </div>
    </main>
    {notice && <div className={`toast ${notice.error ? 'error' : ''}`} role={notice.error ? 'alert' : 'status'}>{notice.error ? <CircleHelp size={18}/> : <Check size={18}/>}<span>{notice.text}</span><button className="icon-button" aria-label="Dismiss notification" onClick={() => setNotice(null)}><X size={15}/></button></div>}
    <ConfirmDialog request={confirmation} dismiss={() => setConfirmation(null)}/>
  </div>;
}
