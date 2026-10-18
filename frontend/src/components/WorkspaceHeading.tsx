import { useI18n } from '../i18n';
import type { ScanStatus } from '../api';

export type StudioPage = 'scan' | 'keywords' | 'results' | 'excel';
const pages = {
  scan: {title: 'Discover new channels', description: 'Start with a topic. Find your next creator connection.'},
  keywords: {title: 'Keyword list', description: 'Keep your ideas together, ready for your next discovery.'},
  results: {title: 'Discovery results', description: 'From discovered channels to thoughtful conversations.'},
  excel: {title: 'Import keywords from Excel', description: 'Bring your existing ideas into your workspace.'},
};
export const statuses: Record<ScanStatus, string> = {ready: 'Ready to discover', running: 'Discovering', stopping: 'Stopping safely', complete: 'Completed', stopped: 'Stopped', error: 'Needs attention'};

export function WorkspaceHeading({page, status, motion, onBack}: {page: StudioPage; status: ScanStatus; motion: boolean; onBack: () => void}) {
  const { t } = useI18n();
  const content = pages[page];
  return <header className={`page-intro workspace-banner banner-${page}`}>
    <div className="banner-copy"><h1>{t(content.title)}</h1><p>{t(content.description)}</p></div>
    <svg key={page} className="banner-art" width="196" height="84" viewBox="0 0 196 84" fill="none" aria-hidden="true">
      <path className="banner-route" d="M42 22H83Q98 22 98 42T113 62H154"/>
      <rect x="8" y="6" width="44" height="32" rx="7"/>
      <path className="banner-play" d="M26 16L35 22L26 28Z"/>
      <rect x="8" y="46" width="44" height="32" rx="7"/>
      <path d="M19 57H41M19 65H33"/>
      <rect className="banner-envelope" x="144" y="43" width="44" height="35" rx="7"/>
      <path d="M149 50L166 62L183 50"/>
      <circle className="banner-node" cx="98" cy="42" r="7"/>
      <path d="M95 42L97 44L101 40"/>
    </svg>
    <div className="page-context">{page === 'scan' ? <div className={`status-pill ${status}`}><span className={motion && status === 'running' ? 'pulse-dot' : ''}/>{t(statuses[status])}</div> : page === 'excel' ? <button className="button secondary" onClick={onBack}>{t("Back to keyword table")}</button> : null}</div>
  </header>;
}
