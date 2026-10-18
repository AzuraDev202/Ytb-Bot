import { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, ArrowRight, Check, FolderOpen, Plus, Save, Search, Trash2 } from 'lucide-react';
import { ConfirmDialog, type Confirmation } from './ConfirmDialog';

export function KeywordTable({text, onChange, dirty, saving, onSave, onUse, onImport}: {
  text: string; onChange: (value: string) => void; dirty: boolean; saving: boolean;
  onSave: () => Promise<boolean>; onUse: () => void; onImport: () => void;
}) {
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<number[]>([]);
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null);
  const rows = text.split('\n');
  const filtered = useMemo(() => text.split('\n').map((value, index) => ({value, index})).filter(row => row.value.toLocaleLowerCase().includes(query.toLocaleLowerCase())), [text, query]);
  const pages = Math.max(1, Math.ceil(filtered.length / 100));
  const current = Math.min(page, pages - 1);
  const visible = filtered.slice(current * 100, (current + 1) * 100);
  useEffect(() => {function shortcut(event: KeyboardEvent) {if (document.querySelector('dialog[open]')) return; if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {event.preventDefault(); void onSave();}} window.addEventListener('keydown', shortcut); return () => window.removeEventListener('keydown', shortcut);}, [onSave]);
  function edit(index: number, value: string) {const next = [...rows]; next[index] = value; onChange(next.join('\n'));}
  function paste(index: number, value: string) {
    const values = value.replace(/\r/g, '').replace(/\n$/, '').split('\n').map(line => line.split('\t')[0]);
    const next = [...rows]; next.splice(index, 1, ...values); onChange(next.join('\n')); setSelected([]);
  }
  function addRow() {
    const index = rows.length;
    onChange(`${text}\n`); setQuery(''); setPage(Math.floor(index / 100));
    requestAnimationFrame(() => document.querySelector<HTMLInputElement>(`input[aria-label="Từ khóa dòng ${index + 1}"]`)?.focus());
  }
  function remove() {setConfirmation({title: `Xóa ${selected.length} dòng?`, text: 'Các dòng được chọn sẽ bị xóa khỏi bảng. Nhấn Lưu từ khóa để lưu thay đổi.', action: () => {onChange(rows.filter((_, index) => !selected.includes(index)).join('\n')); setSelected([]);}});}
  return <section className="panel keyword-table" aria-label="Bảng từ khóa">
    <div className="section-heading"><div><span className="eyebrow">THƯ VIỆN CỦA BẠN</span><h2>Từ khóa trong Bot</h2><p>Sửa trực tiếp trong ô. Dán nhiều dòng từ Excel vào một ô để nhập nhanh cột đầu tiên.</p></div><button className="button secondary" onClick={onImport}><FolderOpen size={16}/> Nhập từ file cũ</button></div>
    <div className="table-tools"><div className="search-field"><Search size={16}/><input aria-label="Tìm từ khóa" value={query} placeholder="Tìm trong bảng từ khóa…" onChange={e => {setQuery(e.target.value); setPage(0);}}/></div><div className="table-actions"><button className="button secondary" onClick={addRow}><Plus size={15}/> Thêm dòng</button><button className="button ghost" onClick={remove} disabled={!selected.length}><Trash2 size={15}/> Xóa {selected.length || ''}</button></div></div>
    <div className="table-scroll"><table><thead><tr><th>Chọn</th><th>#</th><th>Từ khóa</th></tr></thead><tbody>{visible.map(({value, index}) => <tr key={index}><td><input type="checkbox" aria-label={`Chọn từ khóa ${index + 1}`} checked={selected.includes(index)} onChange={e => setSelected(values => e.target.checked ? [...values, index] : values.filter(item => item !== index))}/></td><td>{index + 1}</td><td><input className="keyword-cell" aria-label={`Từ khóa dòng ${index + 1}`} value={value} placeholder="Nhập từ khóa…" onChange={e => edit(index, e.target.value)} onPaste={e => {const pasted = e.clipboardData.getData('text'); if (/[\n\t]/.test(pasted)) {e.preventDefault(); paste(index, pasted);}}}/></td></tr>)}</tbody></table>{!visible.length && <div className="table-empty">Không tìm thấy từ khóa.</div>}</div>
    <div className="table-footer"><span>{dirty ? 'Có thay đổi chưa lưu' : 'Đã lưu trong Bot'} · {rows.filter(row => row.trim()).length} dòng có từ khóa</span><div><button className="icon-button" aria-label="Trang từ khóa trước" disabled={!current} onClick={() => setPage(current - 1)}><ArrowLeft size={16}/></button><span>{current + 1} / {pages}</span><button className="icon-button" aria-label="Trang từ khóa sau" disabled={current + 1 >= pages} onClick={() => setPage(current + 1)}><ArrowRight size={16}/></button></div></div>
    <div className="library-footer"><div><button className="button secondary" disabled={saving || !dirty} onClick={() => void onSave()}><Save size={16}/>{saving ? 'Đang lưu…' : 'Lưu từ khóa'}</button><button className="button primary" disabled={saving} onClick={async () => {if (await onSave()) onUse();}}><Check size={16}/> Dùng để quét</button></div></div>
    <ConfirmDialog request={confirmation} dismiss={() => setConfirmation(null)}/>
  </section>;
}
