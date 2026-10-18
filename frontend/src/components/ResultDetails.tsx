import { useEffect, useId, useRef } from 'react';
import { Mail, X } from 'lucide-react';

export function ResultDetails({record, onClose, onContact}: {record: {columns: string[]; values: (string | number | null)[]} | null; onClose: () => void; onContact?: () => void}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const title = useId();
  useEffect(() => {if (record && !dialog.current?.open) dialog.current?.showModal(); else if (!record) dialog.current?.close();}, [record]);
  return <dialog ref={dialog} className="result-details" aria-labelledby={title} onCancel={event => {event.preventDefault(); onClose();}}>
    <header><div><span className="eyebrow">FULL DETAILS</span><h2 id={title}>Result details</h2></div><button className="icon-button" aria-label="Close details" onClick={onClose}><X size={20}/></button></header>
    <dl>{record?.columns.map((column, index) => <div key={index}><dt>{column}</dt><dd>{record.values[index] ?? '—'}</dd></div>)}</dl>
    <footer><span>You can select and copy the text.</span><div className="sender-actions">{onContact && <button className="button primary" onClick={onContact}><Mail size={16}/> Compose contact</button>}<button className="button secondary" onClick={onClose}>Close</button></div></footer>
  </dialog>;
}
