export type ScanStatus = 'ready' | 'running' | 'stopping' | 'complete' | 'stopped' | 'error';
export interface Snapshot { status: ScanStatus; completed: number; total: number; matches: number; elapsed: number; rows: Record<string, string | number>[]; logs: {text: string; kind: string; time: string}[]; error: string; output: boolean; update: {status: string; message: string; progress: number} }
export interface Bootstrap {version: string; build: string; has_api_key: boolean; keywords: string; preferences?: {theme?: string; motion?: boolean; language?: string}}
export interface WorkbookMeta {filename: string; sheets: string[]; internal?: boolean; run_id?: number}
export interface WorkbookPage {columns: string[]; rows: (string | number | null)[][]; page: number; pages: number; total: number; original_total: number}
type Reply = {ok: boolean; data?: unknown; error?: string};
declare global {interface Window {pywebview?: {api: Record<string, (...args: unknown[]) => Promise<Reply>>}}}
export async function call<T>(method: string, ...args: unknown[]): Promise<T> {
  if (!window.pywebview?.api) throw new Error(translate('Python is not connected. Launch the app with python gui_app.py or the EXE.'));
  const reply = await window.pywebview.api[method](...args);
  if (!reply.ok) throw new Error(reply.error || translate('The operation could not be completed.'));
  return reply.data as T;
}
export const initialState: Snapshot = {status: 'ready', completed: 0, total: 0, matches: 0, elapsed: 0, rows: [], logs: [], error: '', output: false, update: {status: 'idle', message: 'Check for updates', progress: 0}};
import { translate } from './i18n';
