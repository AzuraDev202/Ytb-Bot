import { useI18n } from '../i18n';
import type { ScanStatus } from '../api';

export type StudioPage = 'scan' | 'keywords' | 'results' | 'excel';
const pages = {
  scan: {number: '01', label: 'Discovery', title: 'Discover new channels'},
  keywords: {number: '02', label: 'Library', title: 'Keyword list'},
  results: {number: '03', label: 'History', title: 'Discovery results'},
  excel: {number: '02', label: 'Import data', title: 'Import keywords from Excel'},
};
export const statuses: Record<ScanStatus, string> = {ready: 'Ready to discover', running: 'Discovering', stopping: 'Stopping safely', complete: 'Completed', stopped: 'Stopped', error: 'Needs attention'};

export function WorkspaceHeading({page, status, motion, onBack}: {page: StudioPage; status: ScanStatus; motion: boolean; onBack: () => void}) {
  const { t } = useI18n();
  const content = pages[page];
  return <header className="page-intro">
    <div><div className="intro-kicker"><span>{content.number}</span>{t(content.label)}</div><h1>{t(content.title)}</h1></div>
    <div className="page-context">{page === 'scan' ? <div className={`status-pill ${status}`}><span className={motion && status === 'running' ? 'pulse-dot' : ''}/>{t(statuses[status])}</div> : page === 'excel' ? <button className="button secondary" onClick={onBack}>{t("Back to keyword table")}</button> : null}</div>
  </header>;
}
