import { useEffect, useRef, useState } from 'react';
import { ArrowDownToLine, ArrowLeft, ArrowRight, ArrowUpDown, Copy, FileSpreadsheet, FolderOpen, Loader2, Plus, Search, ShieldCheck, X } from 'lucide-react';
import { call, type WorkbookMeta, type WorkbookPage } from '../api';
import { TableLoading } from './TableLoading';
import { ResultDetails } from './ResultDetails';
import { ContactComposer } from './ContactComposer';
import { ConfirmDialog, type Confirmation, type Notice } from './ConfirmDialog';
const format = (value: number) => new Intl.NumberFormat('vi-VN').format(value);

export function WorkbookView({meta, onOpen, onImport, notify, readOnly = false}: {meta: WorkbookMeta | null; onOpen: () => void; onImport: (words: string[]) => void; notify: (notice: Notice) => void; readOnly?: boolean}) {
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
      catch (error) {if (!cancelled) {setFailure('Chưa đọc được bảng dữ liệu. Bạn có thể thử lại.'); notify({text: String(error), error: true});}}
      finally {if (!cancelled) setLoading(false);}
    }, 180);
    return () => {cancelled = true; window.clearTimeout(timer);};
  }, [sheet, query, page, sort, descending, meta, notify, readOnly, retry]);
  useEffect(() => {const index = data?.columns.findIndex(name => name.trim().toLowerCase() === 'keyword') ?? -1; if (index >= 0) setColumn(index);}, [sheet, data?.columns.join('|')]);
  async function copy() {
    if (!selection.length || !data) return;
    const text = selection.map(index => data.rows[index].map(value => value ?? '').join('\t')).join('\n');
    try {await navigator.clipboard.writeText(text); notify({text: `Đã sao chép ${selection.length} dòng.`});}
    catch {notify({text: 'Không truy cập được clipboard. Hãy chọn văn bản trong bảng và dùng Ctrl+C.', error: true});}
  }
  async function importColumn() {
    try {const words = await call<string[]>('import_keywords', sheet, column); if (!words.length) {notify({text: 'Cột này chưa có từ khóa.'}); return;}
      setConfirmation({title: `Nhập ${words.length} từ khóa?`, text: 'Danh sách từ khóa hiện tại sẽ được thay bằng toàn bộ cột gốc, đã bỏ ô trống và từ trùng. Bộ lọc tìm kiếm không ảnh hưởng dữ liệu nhập.', action: () => onImport(words)});
    } catch (error) {notify({text: String(error), error: true});}
  }
  return <section className="panel workbook-panel" aria-label="Bảng Excel">
    <div className="section-heading"><div><span className="eyebrow">{readOnly ? "DỮ LIỆU LƯỢT QUÉT" : "NHẬP TỪ FILE CŨ"}</span><h2>{readOnly ? 'Bảng kết quả' : 'Nhập dữ liệu cũ'}</h2><p>{readOnly ? 'Tìm kiếm, sắp xếp và sao chép ngay trong Bot.' : 'Đọc file có sẵn để đưa từ khóa vào kho nội bộ.'}</p></div>{!readOnly && <button className="button primary" onClick={onOpen}><FolderOpen size={17}/> Mở Excel</button>}</div>
    {!meta ? <div className="empty-state workbook-empty"><div className="empty-illustration"><FileSpreadsheet size={38}/><span className="small-orbit"><Plus size={16}/></span></div><h3>Bắt đầu với một bảng dữ liệu</h3><p>Mở file .xlsx hoặc .xls, chọn sheet và cột từ khóa.<br/>Không cần cài Microsoft Excel.</p><button className="button secondary" onClick={onOpen}><FolderOpen size={16}/> Chọn file từ máy</button><span className="quiet-note"><ShieldCheck size={13}/> File được xử lý trên máy của bạn</span></div> : <>
      <div className="file-banner"><FileSpreadsheet size={20}/><div><strong>{meta.filename}</strong><small>{meta.sheets.length} sheet · {readOnly ? 'Lưu trong Bot' : 'File gốc chỉ được đọc'}</small></div><span className="pill neutral">{readOnly ? 'BOT DATA' : 'LOCAL FILE'}</span></div>
      {!readOnly && <div className="workbook-controls"><label>Sheet<select value={sheet} onChange={event => {setSheet(event.target.value); setPage(0); setSort(null);}}>{meta.sheets.map(value => <option key={value}>{value}</option>)}</select></label><label>Cột từ khóa<select value={column} onChange={event => setColumn(Number(event.target.value))}>{data?.columns.map((name, index) => <option key={index} value={index}>{name}</option>)}</select></label><button className="button secondary import-column" disabled={!data?.columns.length || loading} onClick={importColumn}><ArrowDownToLine size={16}/> Nhập cột từ khóa</button></div>}
      <div className="table-tools"><div className="search-field"><Search size={17}/><input aria-label="Tìm trong bảng" placeholder="Tìm tên kênh, từ khóa, lượt xem…" value={query} onChange={event => {setQuery(event.target.value); setPage(0);}}/>{query && <button className="icon-button" aria-label="Xóa tìm kiếm" onClick={() => setQuery('')}><X size={14}/></button>}</div><button className="button ghost" onClick={copy} disabled={!selection.length || loading || !!failure}><Copy size={15}/> Sao chép {selection.length || ''}</button></div>
      <div ref={scroll} tabIndex={0} role="region" aria-label="Bảng dữ liệu cuộn ngang" onScroll={measureScroll} className={`table-scroll ${loading ? 'loading-table' : ''}`} aria-busy={loading}><table hidden={loading || !!failure}><thead><tr><th className={readOnly ? "checkbox-cell row-tools" : "checkbox-cell"}><span className="sr-only">Chọn dòng và xem chi tiết</span></th>{data?.columns.map((name, index) => <th key={index} aria-sort={sort === index ? descending ? 'descending' : 'ascending' : 'none'}><button onClick={() => {setDescending(sort === index ? !descending : false); setSort(index); setPage(0);}}>{name}<ArrowUpDown size={13}/></button></th>)}</tr></thead><tbody>{data?.rows.map((row, index) => <tr key={index} className={selection.includes(index) ? 'selected-row' : ''}><td className={readOnly ? "row-tools" : undefined}><div className="row-actions"><input type="checkbox" aria-label={`Chọn dòng ${index + 1}`} checked={selection.includes(index)} onChange={event => setSelection(values => event.target.checked ? [...values, index] : values.filter(value => value !== index))}/>{readOnly && <button className="row-detail-button" aria-label={`Xem đầy đủ dòng ${index + 1}`} onClick={() => setDetails({columns: data!.columns, values: row})}>Xem đầy đủ</button>}</div></td>{row.map((value, cell) => <td key={cell}><span className="cell-value" title={String(value ?? '—')}>{value ?? '—'}</span></td>)}</tr>)}</tbody></table>{failure ? <div className="table-empty" role="alert"><span>{failure}</span><button className="button secondary" onClick={() => setRetry(value => value + 1)}>Tải lại bảng</button></div> : loading ? <TableLoading label={readOnly ? 'Đang mở kết quả…' : 'Đang đọc bảng…'}/> : !data?.rows.length ? <div className="table-empty">Không tìm thấy dòng phù hợp. Thử từ tìm kiếm khác.</div> : null}</div>
      {edges.overflow && !loading && !failure && <div className="horizontal-controls"><span>Cuộn ngang để xem các cột phía sau · Hoặc chọn Xem đầy đủ</span><div><button className="icon-button" aria-label="Cuộn sang trái" disabled={edges.start} onClick={() => pan(-1)}><ArrowLeft size={18}/></button><button className="icon-button" aria-label="Cuộn sang phải" disabled={edges.end} onClick={() => pan(1)}><ArrowRight size={18}/></button></div></div>}
      <div className="table-footer"><span>{format(data?.total ?? 0)} / {format(data?.original_total ?? 0)} dòng · 100 dòng / trang</span><div><button className="icon-button" aria-label="Trang trước" disabled={page === 0 || loading} onClick={() => setPage(value => value - 1)}><ArrowLeft size={16}/></button><span>{(data?.page ?? 0) + 1} / {data?.pages ?? 1}</span><button className="icon-button" aria-label="Trang sau" disabled={page + 1 >= (data?.pages ?? 1) || loading} onClick={() => setPage(value => value + 1)}><ArrowRight size={16}/></button></div></div>
    </>}
    <ResultDetails record={details} onClose={() => setDetails(null)} onContact={readOnly && detailChannelId ? () => {setDetails(null); setContactChannel(String(detailChannelId));} : undefined}/>
    <ContactComposer channelId={contactChannel} onClose={() => setContactChannel(null)} notify={notify}/>
    <ConfirmDialog request={confirmation} dismiss={() => setConfirmation(null)}/>
  </section>;
}

