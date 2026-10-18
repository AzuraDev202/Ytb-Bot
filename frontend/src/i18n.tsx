import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import vi from './vi.json';
import { zhCN } from './zh-CN';

export type Language = 'en' | 'zh-CN' | 'vi';
export type Params = Record<string, string | number>;
export const isLanguage = (value: unknown): value is Language => value === 'en' || value === 'zh-CN' || value === 'vi';
const catalogs: Record<Language, Record<string, string>> = {en: {}, 'zh-CN': zhCN, vi};
let active: Language = isLanguage(localStorage.getItem('ytb-language')) ? localStorage.getItem('ytb-language') as Language : 'en';
export function translate(source: string, params: Params = {}, language: Language = active): string {
  return (catalogs[language][source] ?? source).replace(/\{(\w+)\}/g, (match, key) => params[key] === undefined ? match : String(params[key]));
}
type I18n = {language: Language; locale: string; pending: boolean; t: (source: string, params?: Params) => string; setLanguage: (language: Language, persist?: boolean) => Promise<void>};
const Context = createContext<I18n | null>(null);
export function I18nProvider({children}: {children: ReactNode}) {
  const [language, update] = useState<Language>(active);
  const [pending, setPending] = useState(false);
  const saving = useRef(false);
  const apply = useCallback((value: Language) => {active = value; localStorage.setItem('ytb-language', value); document.documentElement.lang = value; update(value);}, []);
  const setLanguage = useCallback(async (value: Language, persist = true) => {
    if (!isLanguage(value) || (persist && saving.current)) return;
    const previous = active;
    apply(value);
    if (persist && window.pywebview?.api.set_language) {
      saving.current = true; setPending(true);
      try {const reply = await window.pywebview.api.set_language(value); if (!reply.ok) throw new Error(reply.error || 'Could not save the language preference.');}
      catch (error) {apply(previous); throw error;}
      finally {saving.current = false; setPending(false);}
    }
  }, [apply]);
  useEffect(() => {document.documentElement.lang = language;}, [language]);
  return <Context.Provider value={{language, pending, locale: language === 'en' ? 'en-US' : language === 'vi' ? 'vi-VN' : 'zh-CN', t: (source, params) => translate(source, params, language), setLanguage}}>{children}</Context.Provider>;
}
export function LanguageSelect({disabled = false}: {disabled?: boolean}) {
  const {language, pending, t, setLanguage} = useI18n();
  const [error, setError] = useState('');
  return <div className="language-picker"><label><span className="sr-only">{t('Language')}</span><select aria-label={t('Language')} value={language} disabled={disabled || pending} onChange={event => {if (isLanguage(event.target.value)) {setError(''); void setLanguage(event.target.value).catch(reason => setError(reason instanceof Error ? reason.message : String(reason)));}}}><option value="en">English</option><option value="zh-CN">简体中文</option><option value="vi">Tiếng Việt</option></select></label>{error && <span role="alert">{t(error)}</span>}</div>;
}
export function useI18n() {const context = useContext(Context); if (!context) throw new Error('I18nProvider is required'); return context;}
export const resultColumns = new Set(['Channel Name', 'Channel ID', 'Channel URL', 'Search Keyword', 'Created Date', 'Channel Age (Days)', 'Subscribers', 'Total Views', 'Total Videos', 'Latest Video', 'Country', 'Email', 'Facebook', 'Other Contacts']);
export function resultValue(column: string, value: string | number | null, t: I18n['t']) {
  return ((column === 'Subscribers' && value === 'Hidden') || (column === 'Country' && value === 'Not disclosed')) ? t(String(value)) : value;
}
