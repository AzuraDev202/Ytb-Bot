export type ScanStatus = 'ready' | 'running' | 'stopping' | 'complete' | 'stopped' | 'error';
export interface Snapshot { status: ScanStatus; completed: number; total: number; matches: number; elapsed: number; rows: Record<string, string | number>[]; logs: {text: string; kind: string; time: string}[]; error: string; output: boolean; update: {status: string; message: string; progress: number} }
export interface Bootstrap {version: string; build: string; has_api_key: boolean; preferences?: {theme?: string; motion?: boolean}}
export interface WorkbookMeta {filename: string; sheets: string[]}
export interface WorkbookPage {columns: string[]; rows: (string | number | null)[][]; page: number; pages: number; total: number; original_total: number}
type Reply = {ok: boolean; data?: unknown; error?: string};
declare global {interface Window {pywebview?: {api: Record<string, (...args: unknown[]) => Promise<Reply>>}}}
export async function call<T>(method: string, ...args: unknown[]): Promise<T> {
  if (!window.pywebview?.api) throw new Error('Chưa kết nối Python. Mở app bằng python gui_app.py hoặc bản EXE.');
  const reply = await window.pywebview.api[method](...args);
  if (!reply.ok) throw new Error(reply.error || 'Thao tác chưa hoàn tất.');
  return reply.data as T;
}
export const initialState: Snapshot = {status: 'ready', completed: 0, total: 0, matches: 0, elapsed: 0, rows: [], logs: [], error: '', output: false, update: {status: 'idle', message: 'Kiểm tra bản cập nhật', progress: 0}};
