import { Check, FileSpreadsheet, FolderOpen, Target } from 'lucide-react';
import type { ScanStatus } from '../api';

export type StudioPage = 'scan' | 'keywords' | 'results' | 'excel';
const pages = {
  scan: {number: '01', label: 'Khám phá', title: 'Khám phá kênh mới.', description: 'Tìm kênh đa quốc gia có liên hệ công khai, tự bỏ kênh trùng lịch sử.', icon: Target},
  keywords: {number: '02', label: 'Thư viện', title: 'Mọi ý tưởng, một nơi lưu.', description: 'Chỉnh sửa từ khóa ngay trong bảng. Lưu lại và tiếp tục bất cứ lúc nào.', icon: FileSpreadsheet},
  results: {number: '03', label: 'Lịch sử', title: 'Nhìn lại từng lượt khám phá.', description: 'Tìm lại những kênh đã thu thập. Toàn bộ kết quả được giữ trong Bot.', icon: Target},
  excel: {number: '02', label: 'Nhập dữ liệu', title: 'Đưa danh sách cũ vào studio.', description: 'Chọn sheet và cột từ khóa để tiếp tục chỉnh sửa trong Bot.', icon: FolderOpen},
};
export const statuses: Record<ScanStatus, string> = {ready: 'Sẵn sàng khám phá', running: 'Đang khám phá', stopping: 'Đang dừng an toàn', complete: 'Đã hoàn tất', stopped: 'Đã dừng', error: 'Cần kiểm tra'};

export function WorkspaceHeading({page, status, dirty, motion, onBack}: {page: StudioPage; status: ScanStatus; dirty: boolean; motion: boolean; onBack: () => void}) {
  const content = pages[page];
  return <header className="page-intro">
    <div><div className="intro-kicker"><span>{content.number}</span>{content.label}<i/> YTB-BOT Studio</div><h1>{content.title}</h1><p>{content.description}</p></div>
    <div className="page-context">{page === 'scan' ? <div className={`status-pill ${status}`}><span className={motion && status === 'running' ? 'pulse-dot' : ''}/>{statuses[status]}</div> : page === 'keywords' ? <span className={`save-state ${dirty ? 'unsaved' : ''}`}>{dirty ? <i/> : <Check size={15}/>} {dirty ? 'Bản nháp đang chỉnh sửa' : 'Thư viện đã sẵn sàng'}</span> : page === 'excel' ? <button className="button secondary" onClick={onBack}>Về bảng từ khóa</button> : <span className="context-note">Lưu nội bộ · Không tạo Excel</span>}</div>
  </header>;
}
