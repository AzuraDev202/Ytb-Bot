import type { ScanStatus } from '../api';

export type StudioPage = 'scan' | 'keywords' | 'results' | 'excel';
const pages = {
  scan: {number: '01', label: 'Khám phá', title: 'Khám phá kênh mới'},
  keywords: {number: '02', label: 'Thư viện', title: 'Danh sách từ khóa'},
  results: {number: '03', label: 'Lịch sử', title: 'Kết quả khám phá'},
  excel: {number: '02', label: 'Nhập dữ liệu', title: 'Nhập từ khóa từ Excel'},
};
export const statuses: Record<ScanStatus, string> = {ready: 'Sẵn sàng khám phá', running: 'Đang khám phá', stopping: 'Đang dừng an toàn', complete: 'Đã hoàn tất', stopped: 'Đã dừng', error: 'Cần kiểm tra'};

export function WorkspaceHeading({page, status, motion, onBack}: {page: StudioPage; status: ScanStatus; motion: boolean; onBack: () => void}) {
  const content = pages[page];
  return <header className="page-intro">
    <div><div className="intro-kicker"><span>{content.number}</span>{content.label}</div><h1>{content.title}</h1></div>
    <div className="page-context">{page === 'scan' ? <div className={`status-pill ${status}`}><span className={motion && status === 'running' ? 'pulse-dot' : ''}/>{statuses[status]}</div> : page === 'excel' ? <button className="button secondary" onClick={onBack}>Về bảng từ khóa</button> : null}</div>
  </header>;
}
