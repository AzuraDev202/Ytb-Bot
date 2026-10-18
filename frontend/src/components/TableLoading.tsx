import { useI18n } from '../i18n';
export function TableLoading({label = 'Loading data…'}: {label?: string}) {
  const { t } = useI18n();
  return <div className="table-loading" role="status" aria-label={t(label)}>
    <div className="loading-label"><span className="loading-dot"/>{t(label)}</div>
    <div className="skeleton-table" aria-hidden="true">{Array.from({length: 4}, (_, row) => <div key={row}>{Array.from({length: 3}, (_, col) => <span key={col}/>)}</div>)}</div>
  </div>;
}
