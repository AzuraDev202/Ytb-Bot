import { CheckCircle2, Clock3, Hash, Target } from 'lucide-react';
import type { Snapshot } from '../api';

export function ScanSummary({state, keywords}: {state: Snapshot; keywords: number}) {
  const items = [
    {label: 'Unique keywords', value: keywords.toLocaleString('en-US'), icon: Hash},
    {label: 'Matching channels', value: state.matches.toLocaleString('en-US'), icon: Target},
    {label: 'Topics processed', value: `${state.completed} / ${state.total}`, icon: CheckCircle2},
    {label: 'Scan duration', value: `${Math.floor(state.elapsed / 60).toString().padStart(2, '0')}:${(state.elapsed % 60).toString().padStart(2, '0')}`, icon: Clock3},
  ];
  return <section className="stats-grid" aria-label="Scan statistics">{items.map(item => <div className="stat-card" key={item.label}><span className="stat-icon"><item.icon size={17}/></span><div><span className="stat-label">{item.label}</span><strong className="stat-value">{item.value}</strong></div></div>)}</section>;
}
