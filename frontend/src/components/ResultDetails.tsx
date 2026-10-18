import { useEffect, useId, useRef } from 'react';
import { X } from 'lucide-react';

export function ResultDetails({record, onClose}: {record: {columns: string[]; values: (string | number | null)[]} | null; onClose: () => void}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const title = useId();
  useEffect(() => {if (record && !dialog.current?.open) dialog.current?.showModal(); else if (!record) dialog.current?.close();}, [record]);
  return <dialog ref={dialog} className="result-details" aria-labelledby={title} onCancel={event => {event.preventDefault(); onClose();}}>
    <header><div><span className="eyebrow">TOÀN BỘ THÔNG TIN</span><h2 id={title}>Chi tiết kết quả</h2></div><button className="icon-button" aria-label="Đóng chi tiết" onClick={onClose}><X size={20}/></button></header>
    <dl>{record?.columns.map((column, index) => <div key={index}><dt>{column}</dt><dd>{record.values[index] ?? '—'}</dd></div>)}</dl>
    <footer><span>Có thể bôi chọn và sao chép nội dung.</span><button className="button secondary" onClick={onClose}>Đóng</button></footer>
  </dialog>;
}
