import { useI18n } from '../i18n';
import { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, ArrowRight, Check, FolderOpen, Plus, Save, Search, Trash2 } from 'lucide-react';
import { ConfirmDialog, type Confirmation } from './ConfirmDialog';

export function KeywordTable({text, onChange, dirty, saving, onSave, onUse, onImport}: {
  text: string; onChange: (value: string) => void; dirty: boolean; saving: boolean;
  onSave: () => Promise<boolean>; onUse: () => void; onImport: () => void;
}) {
  const { t } = useI18n();
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
    requestAnimationFrame(() => document.querySelector<HTMLInputElement>(`input[data-keyword-row="${index}"]`)?.focus());
  }
  function remove() {setConfirmation({title: 'Delete {count} rows?', params: {count: selected.length}, text: 'Selected rows will be removed from the table. Click Save keywords to save your changes.', action: () => {onChange(rows.filter((_, index) => !selected.includes(index)).join('\n')); setSelected([]);}});}
  return <section className="panel keyword-table" aria-label={t("Keyword table")}>
    <div className="section-heading"><div><h2>{t("Keywords in the bot")}</h2><p>{t("Edit cells directly. Paste multiple rows from Excel into one cell to quickly import the first column.")}</p></div><button className="button secondary" onClick={onImport}><FolderOpen size={16}/> {t("Import existing file")}</button></div>
    <div className="table-tools"><div className="search-field"><Search size={16}/><input aria-label={t("Search keywords")} value={query} placeholder={t("Search the keyword table…")} onChange={e => {setQuery(e.target.value); setPage(0);}}/></div><div className="table-actions"><button className="button secondary" onClick={addRow}><Plus size={15}/> {t("Add row")}</button><button className="button ghost" onClick={remove} disabled={!selected.length}><Trash2 size={15}/> {t("Delete")} {selected.length || ''}</button></div></div>
    <div className="table-scroll"><table><thead><tr><th>{t("Select")}</th><th>#</th><th>{t("Keywords")}</th></tr></thead><tbody>{visible.map(({value, index}) => <tr key={index}><td><input type="checkbox" aria-label={t("Select keyword {v0}", {v0: index + 1})} checked={selected.includes(index)} onChange={e => setSelected(values => e.target.checked ? [...values, index] : values.filter(item => item !== index))}/></td><td>{index + 1}</td><td><input className="keyword-cell" data-keyword-row={index} aria-label={t("Keyword row {v0}", {v0: index + 1})} value={value} placeholder={t("Enter a keyword…")} onChange={e => edit(index, e.target.value)} onPaste={e => {const pasted = e.clipboardData.getData('text'); if (/[\n\t]/.test(pasted)) {e.preventDefault(); paste(index, pasted);}}}/></td></tr>)}</tbody></table>{!visible.length && <div className="table-empty">{t("No keywords found.")}</div>}</div>
    <div className="table-footer"><span>{dirty ? t("Unsaved changes") : t("Saved in the bot")} · {rows.filter(row => row.trim()).length} {t("rows with keywords")}</span><div><button className="icon-button" aria-label={t("Previous keyword page")} disabled={!current} onClick={() => setPage(current - 1)}><ArrowLeft size={16}/></button><span>{current + 1} / {pages}</span><button className="icon-button" aria-label={t("Next keyword page")} disabled={current + 1 >= pages} onClick={() => setPage(current + 1)}><ArrowRight size={16}/></button></div></div>
    <div className="library-footer"><div><button className="button secondary" disabled={saving || !dirty} onClick={() => void onSave()}><Save size={16}/>{saving ? t("Saving…") : t("Save keywords")}</button><button className="button primary" disabled={saving} onClick={async () => {if (await onSave()) onUse();}}><Check size={16}/> {t("Use for scanning")}</button></div></div>
    <ConfirmDialog request={confirmation} dismiss={() => setConfirmation(null)}/>
  </section>;
}
