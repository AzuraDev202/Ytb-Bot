import { useI18n } from '../i18n';
import { useEffect, useId, useRef } from 'react';
import { ShieldCheck } from 'lucide-react';

export type Notice = {text: string; params?: Record<string, string | number>; error?: boolean};
export type Confirmation = {title: string; text: string; params?: Record<string, string | number>; action: () => void};

export function ConfirmDialog({request, dismiss}: {request: Confirmation | null; dismiss: () => void}) {
  const { t } = useI18n();
  const id = useId();
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {if (request && !dialog.current?.open) dialog.current?.showModal(); else if (!request) dialog.current?.close();}, [request]);
  return <dialog ref={dialog} className="confirmation" aria-labelledby={id + "-title"} aria-describedby={id + "-description"} onCancel={event => {event.preventDefault(); dismiss();}}>
    <div className="dialog-icon"><ShieldCheck size={25}/></div><h2 id={id + "-title"}>{t(request?.title || '', request?.params)}</h2><p id={id + "-description"}>{t(request?.text || '', request?.params)}</p>
    <div className="dialog-actions"><button className="button secondary" onClick={dismiss}>{t("Cancel")}</button><button className="button primary" onClick={() => {const action = request?.action; dismiss(); action?.();}}>{t("Confirm")}</button></div>
  </dialog>;
}

