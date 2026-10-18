import { useI18n, resultColumns, resultValue } from '../i18n';
import { useEffect, useId, useRef } from 'react';
import { Mail, X } from 'lucide-react';

export function ResultDetails({record, onClose, onContact, internal = false}: {record: {columns: string[]; values: (string | number | null)[]} | null; onClose: () => void; internal?: boolean; onContact?: () => void}) {
  const { t } = useI18n();
  const dialog = useRef<HTMLDialogElement>(null);
  const title = useId();
  useEffect(() => {if (record && !dialog.current?.open) dialog.current?.showModal(); else if (!record) dialog.current?.close();}, [record]);
  return <dialog ref={dialog} className="result-details" aria-labelledby={title} onCancel={event => {event.preventDefault(); onClose();}}>
    <header><div><span className="eyebrow">{t("FULL DETAILS")}</span><h2 id={title}>{t("Result details")}</h2></div><button className="icon-button" aria-label={t("Close details")} onClick={onClose}><X size={20}/></button></header>
    <dl>{record?.columns.map((column, index) => <div key={index}><dt>{internal && resultColumns.has(column) ? t(column) : column}</dt><dd>{internal ? resultValue(column, record.values[index], t) ?? '—' : record.values[index] ?? '—'}</dd></div>)}</dl>
    <footer><span>{t("You can select and copy the text.")}</span><div className="sender-actions">{onContact && <button className="button primary" onClick={onContact}><Mail size={16}/> {t("Compose contact")}</button>}<button className="button secondary" onClick={onClose}>{t("Close")}</button></div></footer>
  </dialog>;
}
