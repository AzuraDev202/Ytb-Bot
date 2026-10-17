import { CheckCircle2, Clock3, Hash, Target } from 'lucide-react';
import type { Snapshot } from '../api';

export function ScanSummary({state, keywords}: {state: Snapshot; keywords: number}) {
  const items = [
    {label: 'Từ khóa duy nhất', value: keywords.toLocaleString('vi-VN'), icon: Hash},
    {label: 'Kênh phù hợp', value: state.matches.toLocaleString('vi-VN'), icon: Target},
    {label: 'Chủ đề đã xử lý', value: `${state.completed} / ${state.total}`, icon: CheckCircle2},
    {label: 'Thời gian lượt quét', value: `${Math.floor(state.elapsed / 60).toString().padStart(2, '0')}:${(state.elapsed % 60).toString().padStart(2, '0')}`, icon: Clock3},
  ];
  return <section className="stats-grid" aria-label="Số liệu lượt quét">{items.map(item => <div className="stat-card" key={item.label}><span className="stat-icon"><item.icon size={17}/></span><div><span className="stat-label">{item.label}</span><strong className="stat-value">{item.value}</strong></div></div>)}</section>;
}
