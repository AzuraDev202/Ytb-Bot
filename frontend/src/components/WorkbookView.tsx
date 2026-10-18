import { useI18n, resultColumns, resultValue } from '../i18n';
import { useEffect, useRef, useState } from 'react';
import { ArrowDownToLine, ArrowLeft, ArrowRight, ArrowUpDown, Copy, FileSpreadsheet, FolderOpen, Loader2, Plus, Search, X } from 'lucide-react';
import { call, type WorkbookMeta, type WorkbookPage } from '../api';
import { TableLoading } from './TableLoading';
import { ResultDetails } from './ResultDetails';
import { ContactComposer } from './ContactComposer';
import { ConfirmDialog, type Confirmation, type Notice } from './ConfirmDialog';

export function WorkbookView({meta, onOpen, onImport, notify, readOnly = false, onContact}: {meta: WorkbookMeta | null; onOpen: () => void; onImport: (words: string[]) => void; notify: (notice: Notice) => void; readOnly?: boolean; onContact?: (channelId: string) => void}) {
  const { t, locale } = useI18n();
  const format = (value: number) => new Intl.NumberFormat(locale).format(value);
  const [sheet, setSheet] = useState('');
  const [column, setColumn] = useState(0);
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(0);
  const [sort, setSort] = useState<number | null>(null);
  const [descending, setDescending] = useState(false);
  const [data, setData] = useState<WorkbookPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [failure, setFailure] = useState('');
  const [retry, setRetry] = useState(0);
  const [selection, setSelection] = useState<number[]>([]);
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null);
  const [details, setDetails] = useState<{columns: string[]; values: (string | number | null)[]} | null>(null);
  const [contactChannel, setContactChannel] = useState<string | null>(null);
  const detailChannelId = details?.values[details.columns.indexOf('Channel ID')];
  const scroll = useRef<HTMLDivElement>(null);
  const [edges, setEdges] = useState({overflow: false, start: true, end: true});
  function measureScroll() {
    const element = scroll.current;
    if (!element) return;
    setEdges({overflow: element.scrollWidth > element.clientWidth + 1, start: element.scrollLeft <= 1, end: element.scrollLeft + element.clientWidth >= element.scrollWidth - 2});
  }
  useEffect(() => {
    const element = scroll.current;
    if (!element) return;
    const observer = new ResizeObserver(measureScroll);
    observer.observe(element);
    if (element.querySelector('table')) observer.observe(element.querySelector('table')!);
    measureScroll();
    return () => observer.disconnect();
  }, [data, loading, failure, meta]);
  useEffect(() => {setDetails(null); if (scroll.current) scroll.current.scrollLeft = 0;}, [meta, page, query, sort, descending]);
  function pan(direction: number) {scroll.current?.scrollBy({left: direction * Math.max(240, scroll.current.clientWidth * .8), behavior: 'instant'});}
  useEffect(() => {setSheet(meta?.sheets[0] || ''); setColumn(0); setQuery(''); setPage(0); setSort(null); setData(null);}, [meta]);
  useEffect(() => {
    if (!sheet || !meta) return;
    setLoading(true);
    setFailure('');
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      setLoading(true);
      try {const result = await call<WorkbookPage>(readOnly ? 'results_page' : 'workbook_page', sheet, query, page, sort, descending); if (!cancelled) {setData(result); setSelection([]);}}
      catch (error) {if (!cancelled) {setFailure('Could not read the table. You can try again.'); notify({text: String(error), error: true});}}
      finally {if (!cancelled) setLoading(false);}
    }, 180);
    return () => {cancelled = true; window.clearTimeout(timer);};
  }, [sheet, query, page, sort, descending, meta, notify, readOnly, retry]);
  useEffect(() => {const index = data?.columns.findIndex(name => name.trim().toLowerCase() === 'keyword') ?? -1; if (index >= 0) setColumn(index);}, [sheet, data?.columns.join('|')]);
  async function copy() {
    if (!selection.length || !data) return;
    const text = selection.map(index => data.rows[index].map(value => value ?? '').join('\t')).join('\n');
    try {await navigator.clipboard.writeText(text); notify({text: 'Copied {count} rows.', params: {count: selection.length}});}
    catch {notify({text: 'Clipboard access failed. Select text in the table and press Ctrl+C.', error: true});}
  }
  async function importColumn() {
    try {const words = await call<string[]>('import_keywords', sheet, column); if (!words.length) {notify({text: 'This column has no keywords.'}); return;}
      setConfirmation({title: 'Import {count} keywords?', params: {count: words.length}, text: 'The current keyword list will be replaced with the entire original column, excluding blanks and duplicates. Search filters do not affect the import.', action: () => onImport(words)});
    } catch (error) {notify({text: String(error), error: true});}
  }
  return <section className="panel workbook-panel" aria-label={t("Excel table")}>
    <div className="section-heading"><div><h2>{readOnly ? t("Results table") : t("Import existing data")}</h2></div>{!readOnly && <button className="button primary" onClick={onOpen}><FolderOpen size={17}/> {t("Open Excel")}</button>}</div>
    {!meta ? <div className="empty-state workbook-empty"><div className="empty-illustration"><FileSpreadsheet size={38}/><span className="small-orbit"><Plus size={16}/></span></div><h3>{t("Start with a spreadsheet")}</h3><p>{t("Open an .xlsx or .xls file, then choose a sheet and keyword column.")}<br/>{t("Microsoft Excel is not required.")}</p><button className="button secondary" onClick={onOpen}><FolderOpen size={16}/> {t("Choose a local file")}</button></div> : <>
      <div className="file-banner"><FileSpreadsheet size={20}/><div><strong>{readOnly && meta.internal ? meta.filename.replace(/^Scan(?= #)/, t('Scan')) : meta.filename}</strong><small>{meta.sheets.length} {t('Sheet')} · {readOnly ? t("Save in the bot") : t("Original file is read-only")}</small></div><span className="pill neutral">{readOnly ? t('BOT DATA') : t('LOCAL FILE')}</span></div>
      {!readOnly && <div className="workbook-controls"><label>{t("Sheet")}<select value={sheet} onChange={event => {setSheet(event.target.value); setPage(0); setSort(null);}}>{meta.sheets.map(value => <option key={value}>{value}</option>)}</select></label><label>{t("Keyword column")}<select value={column} onChange={event => setColumn(Number(event.target.value))}>{data?.columns.map((name, index) => <option key={index} value={index}>{name}</option>)}</select></label><button className="button secondary import-column" disabled={!data?.columns.length || loading} onClick={importColumn}><ArrowDownToLine size={16}/> {t("Import keyword column")}</button></div>}
      <div className="table-tools"><div className="search-field"><Search size={17}/><input aria-label={t("Search table")} placeholder={t("Search channels, keywords, views…")} value={query} onChange={event => {setQuery(event.target.value); setPage(0);}}/>{query && <button className="icon-button" aria-label={t("Clear search")} onClick={() => setQuery('')}><X size={14}/></button>}</div><button className="button ghost" onClick={copy} disabled={!selection.length || loading || !!failure}><Copy size={15}/> {t("Copy")} {selection.length || ''}</button></div>
      <div ref={scroll} tabIndex={0} role="region" aria-label={t("Horizontally scrollable table")} onScroll={measureScroll} className={`table-scroll ${loading ? 'loading-table' : ''}`} aria-busy={loading}><table hidden={loading || !!failure}><thead><tr><th className={readOnly ? "checkbox-cell row-tools" : "checkbox-cell"}><span className="sr-only">{t("Select rows and view details")}</span></th>{data?.columns.map((name, index) => <th key={index} aria-sort={sort === index ? descending ? 'descending' : 'ascending' : 'none'}><button onClick={() => {setDescending(sort === index ? !descending : false); setSort(index); setPage(0);}}>{readOnly && resultColumns.has(name) ? t(name) : name}<ArrowUpDown size={13}/></button></th>)}</tr></thead><tbody>{data?.rows.map((row, index) => <tr key={index} className={selection.includes(index) ? 'selected-row' : ''}><td className={readOnly ? "row-tools" : undefined}><div className="row-actions"><input type="checkbox" aria-label={t("Select row {v0}", {v0: index + 1})} checked={selection.includes(index)} onChange={event => setSelection(values => event.target.checked ? [...values, index] : values.filter(value => value !== index))}/>{readOnly && <button className="row-detail-button" aria-label={t("View full row {v0}", {v0: index + 1})} onClick={() => setDetails({columns: data!.columns, values: row})}>{t("View full details")}</button>}</div></td>{row.map((value, cell) => <td key={cell}><span className="cell-value" title={String(value ?? '—')}>{readOnly ? resultValue(data!.columns[cell], value, t) ?? '—' : value ?? '—'}</span></td>)}</tr>)}</tbody></table>{failure ? <div className="table-empty" role="alert"><span>{t(failure)}</span><button className="button secondary" onClick={() => setRetry(value => value + 1)}>{t("Reload table")}</button></div> : loading ? <TableLoading label={readOnly ? t("Opening results…") : t("Reading table…")}/> : !data?.rows.length ? <div className="table-empty">{t("No matching rows found. Try another search.")}</div> : null}</div>
      {edges.overflow && !loading && !failure && <div className="horizontal-controls"><span>{t("Scroll horizontally to see more columns · Or select View full details")}</span><div><button className="icon-button" aria-label={t("Scroll left")} disabled={edges.start} onClick={() => pan(-1)}><ArrowLeft size={18}/></button><button className="icon-button" aria-label={t("Scroll right")} disabled={edges.end} onClick={() => pan(1)}><ArrowRight size={18}/></button></div></div>}
      <div className="table-footer"><span>{format(data?.total ?? 0)} / {format(data?.original_total ?? 0)} {t("rows · 100 rows / page")}</span><div><button className="icon-button" aria-label={t("Previous page")} disabled={page === 0 || loading} onClick={() => setPage(value => value - 1)}><ArrowLeft size={16}/></button><span>{(data?.page ?? 0) + 1} / {data?.pages ?? 1}</span><button className="icon-button" aria-label={t("Next page")} disabled={page + 1 >= (data?.pages ?? 1) || loading} onClick={() => setPage(value => value + 1)}><ArrowRight size={16}/></button></div></div>
    </>}
    <ResultDetails internal={readOnly} record={details} onClose={() => setDetails(null)} onContact={readOnly && detailChannelId ? () => {setDetails(null); (onContact || setContactChannel)(String(detailChannelId));} : undefined}/>
    {!onContact && <ContactComposer channelId={contactChannel} onClose={() => setContactChannel(null)} notify={notify}/>}
    <ConfirmDialog request={confirmation} dismiss={() => setConfirmation(null)}/>
  </section>;
}

