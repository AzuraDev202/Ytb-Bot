import { useEffect, useState } from 'react';
import { ArrowDownToLine, ArrowLeft, ArrowRight, ArrowUpDown, Copy, FileSpreadsheet, FolderOpen, Loader2, Plus, Search, ShieldCheck, X } from 'lucide-react';
import { call, type WorkbookMeta, type WorkbookPage } from '../api';
import { ConfirmDialog, type Confirmation, type Notice } from './ConfirmDialog';
const format = (value: number) => new Intl.NumberFormat('vi-VN').format(value);

export function WorkbookView({meta, onOpen, onImport, notify}: {meta: WorkbookMeta | null; onOpen: () => void; onImport: (words: string[]) => void; notify: (notice: Notice) => void}) {
  const [sheet, setSheet] = useState('');
  const [column, setColumn] = useState(0);
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(0);
  const [sort, setSort] = useState<number | null>(null);
  const [descending, setDescending] = useState(false);
  const [data, setData] = useState<WorkbookPage | null>(null);
  const [loading, setLoading] = useState(false);
  const [selection, setSelection] = useState<number[]>([]);
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null);
  useEffect(() => {setSheet(meta?.sheets[0] || ''); setColumn(0); setQuery(''); setPage(0); setSort(null); setData(null);}, [meta]);
  useEffect(() => {
    if (!sheet || !meta) return;
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      setLoading(true);
      try {const result = await call<WorkbookPage>('workbook_page', sheet, query, page, sort, descending); if (!cancelled) {setData(result); setSelection([]);}}
      catch (error) {if (!cancelled) notify({text: String(error), error: true});}
      finally {if (!cancelled) setLoading(false);}
    }, 180);
    return () => {cancelled = true; window.clearTimeout(timer);};
  }, [sheet, query, page, sort, descending, meta, notify]);
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
    <div className="section-heading"><div><span className="eyebrow">WORKSPACE / EXCEL</span><h2>Dữ liệu trong tầm tay.</h2><p>Xem, tìm và nhập từ khóa ngay trong studio.</p></div><button className="button primary" onClick={onOpen}><FolderOpen size={17}/> Mở Excel</button></div>
    {!meta ? <div className="empty-state workbook-empty"><div className="empty-illustration"><FileSpreadsheet size={38}/><span className="small-orbit"><Plus size={16}/></span></div><h3>Bắt đầu với một bảng dữ liệu</h3><p>Mở file .xlsx hoặc .xls, chọn sheet và cột từ khóa.<br/>Không cần cài Microsoft Excel.</p><button className="button secondary" onClick={onOpen}><FolderOpen size={16}/> Chọn file từ máy</button><span className="quiet-note"><ShieldCheck size={13}/> File được xử lý trên máy của bạn</span></div> : <>
      <div className="file-banner"><FileSpreadsheet size={20}/><div><strong>{meta.filename}</strong><small>{meta.sheets.length} sheet · Xem dữ liệu gốc, không chỉnh sửa file</small></div><span className="pill neutral">LOCAL FILE</span></div>
      <div className="workbook-controls"><label>Sheet<select value={sheet} onChange={event => {setSheet(event.target.value); setPage(0); setSort(null);}}>{meta.sheets.map(value => <option key={value}>{value}</option>)}</select></label><label>Cột từ khóa<select value={column} onChange={event => setColumn(Number(event.target.value))}>{data?.columns.map((name, index) => <option key={index} value={index}>{name}</option>)}</select></label><button className="button secondary import-column" disabled={!data?.columns.length || loading} onClick={importColumn}><ArrowDownToLine size={16}/> Nhập cột từ khóa</button></div>
      <div className="table-tools"><div className="search-field"><Search size={17}/><input aria-label="Tìm trong bảng" placeholder="Tìm tên kênh, từ khóa, lượt xem…" value={query} onChange={event => {setQuery(event.target.value); setPage(0);}}/>{query && <button className="icon-button" aria-label="Xóa tìm kiếm" onClick={() => setQuery('')}><X size={14}/></button>}</div><button className="button ghost" onClick={copy} disabled={!selection.length}><Copy size={15}/> Sao chép {selection.length || ''}</button></div>
      <div className={`table-scroll ${loading ? 'loading-table' : ''}`} aria-busy={loading}><table><thead><tr><th className="checkbox-cell"><span className="sr-only">Chọn dòng</span></th>{data?.columns.map((name, index) => <th key={index} aria-sort={sort === index ? descending ? 'descending' : 'ascending' : 'none'}><button onClick={() => {setDescending(sort === index ? !descending : false); setSort(index); setPage(0);}}>{name}<ArrowUpDown size={13}/></button></th>)}</tr></thead><tbody>{data?.rows.map((row, index) => <tr key={index} className={selection.includes(index) ? 'selected-row' : ''}><td><input type="checkbox" aria-label={`Chọn dòng ${index + 1}`} checked={selection.includes(index)} onChange={event => setSelection(values => event.target.checked ? [...values, index] : values.filter(value => value !== index))}/></td>{row.map((value, cell) => <td key={cell}>{value ?? '—'}</td>)}</tr>)}</tbody></table>{!data?.rows.length && <div className="table-empty">{loading ? <><Loader2 size={20} className="spin"/> Đang đọc workbook…</> : <>Không có dòng phù hợp. Thử sheet hoặc từ tìm kiếm khác.</>}</div>}</div>
      <div className="table-footer"><span>{format(data?.total ?? 0)} / {format(data?.original_total ?? 0)} dòng · 100 dòng / trang</span><div><button className="icon-button" aria-label="Trang trước" disabled={page === 0 || loading} onClick={() => setPage(value => value - 1)}><ArrowLeft size={16}/></button><span>{(data?.page ?? 0) + 1} / {data?.pages ?? 1}</span><button className="icon-button" aria-label="Trang sau" disabled={page + 1 >= (data?.pages ?? 1) || loading} onClick={() => setPage(value => value + 1)}><ArrowRight size={16}/></button></div></div>
    </>}
    <ConfirmDialog request={confirmation} dismiss={() => setConfirmation(null)}/>
  </section>;
}

