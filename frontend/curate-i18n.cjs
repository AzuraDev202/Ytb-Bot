const fs=require('fs');const vi=JSON.parse(fs.readFileSync('src/vi.generated.json','utf8'));
Object.assign(vi,{Language: 'Ngôn ngữ', Hidden: 'Ẩn', 'Created Date': 'Ngày tạo', 'Total Videos': 'Tổng video', 'Latest Video': 'Video gần nhất', 'Channel ID': 'ID kênh', Subscribers: 'Người đăng ký', Email: 'Email', 'Next page': 'Trang sau', 'YouTube API Key': 'Khóa API YouTube', views: 'lượt xem', Studio: 'Studio', Desktop: 'Máy tính', 'CREATOR WORKSPACE': 'KHÔNG GIAN NHÀ SÁNG TẠO', Sheet: 'Trang tính', 'BOT DATA': 'DỮ LIỆU BOT', 'LOCAL FILE': 'FILE CỤC BỘ', pages: 'trang'});
fs.writeFileSync('src/vi.json',JSON.stringify(vi,null,2)+'\n');
let p='src/i18n.tsx',s=fs.readFileSync(p,'utf8').replace("'./vi.generated.json'","'./vi.json'");s=s.replace(/vi: \{\.\.\.vi,[^\n]+\}\};/,'vi};');fs.writeFileSync(p,s);
p='src/components/WorkbookView.tsx';s=fs.readFileSync(p,'utf8').replace('aria-label="Next page"','aria-label={t("Next page")}');fs.writeFileSync(p,s);
