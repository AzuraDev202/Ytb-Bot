import { useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { call, type WorkbookMeta, type ScanStatus } from '../api';
import { WorkbookView } from './WorkbookView';
import type { Notice } from './ConfirmDialog';

type Run = {id: number; created: string; status: string; count: number; error: string};
const labels: Record<string, string> = {running: 'Đang quét / chưa kết thúc', complete: 'Hoàn tất', stopped: 'Đã dừng', error: 'Có lỗi'};
export function ResultsView({status, notify}: {status: ScanStatus; notify: (notice: Notice) => void}) {
  const [runs, setRuns] = useState<Run[]>([]);
  const [selected, setSelected] = useState('');
  const [meta, setMeta] = useState<WorkbookMeta | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(true);
  useEffect(() => {let cancelled = false; setLoading(true); void call<Run[]>('list_results').then(rows => {if (!cancelled) {setRuns(rows); setSelected(value => value || String(rows[0]?.id || ''));}}).catch(error => {if (!cancelled) notify({text: String(error), error: true});}).finally(() => {if (!cancelled) setLoading(false);}); return () => {cancelled = true;};}, [status, refresh, notify]);
  useEffect(() => {let cancelled = false; setMeta(null); if (selected) void call<WorkbookMeta>('open_results', Number(selected)).then(value => {if (!cancelled) setMeta(value);}).catch(error => {if (!cancelled) notify({text: String(error), error: true});}); return () => {cancelled = true;};}, [selected, status, refresh, notify]);
  const run = runs.find(item => String(item.id) === selected);
  return <div className="results-workspace"><section className="panel history-toolbar"><div><span className="eyebrow">LỊCH SỬ KHÁM PHÁ</span><h2>Kết quả được giữ trong Bot</h2><p>Mở lại từng lượt quét, kể cả kết quả một phần. Không cần tìm file Excel trên máy.</p></div><div className="history-select"><label>Lượt quét<select aria-label="Lượt quét" value={selected} onChange={e => setSelected(e.target.value)}><option value="" disabled>Chọn lượt quét</option>{runs.map(item => <option key={item.id} value={item.id}>#{item.id} · {new Date(item.created).toLocaleString('vi-VN')} · {item.count} kênh · {labels[item.status] || item.status}</option>)}</select></label><button className="button secondary" disabled={loading} onClick={() => setRefresh(value => value + 1)}><RefreshCw size={15}/> Làm mới</button></div>{run?.error && <p role="alert" className="field-error">Lượt quét gặp lỗi: {run.error}. Các kênh đã thu thập vẫn được giữ.</p>}</section>{meta ? <WorkbookView meta={meta} onOpen={() => {}} onImport={() => {}} notify={notify} readOnly/> : <section className="panel table-empty">{loading || selected ? 'Đang đọc kết quả…' : 'Chưa có lượt quét. Kết quả sẽ xuất hiện tại đây sau khi bắt đầu khám phá.'}</section>}</div>;
}
