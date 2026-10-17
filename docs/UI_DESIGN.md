# YTB-BOT Creator Studio: thiết kế UI

Giao diện mặc định là React + TypeScript trong cửa sổ pywebview / Edge WebView2. Python xử lý dữ liệu; giao diện CustomTkinter nằm riêng tại `ytb_bot/legacy_ui/` và được mở qua `--legacy`.

## Hướng thiết kế

- Nền graphite ở theme tối, trắng ngà ở theme sáng; một màu nhấn san hô, xanh lá chỉ dùng cho trạng thái. Không dùng gradient trang trí hoặc số liệu minh họa trong app.
- Dải số liệu gọn chỉ xuất hiện ở màn hình quét: từ khóa duy nhất, kênh phù hợp, chủ đề đã xử lý và thời gian. Trang từ khóa/lịch sử ưu tiên diện tích bảng.
- Một hành động chính: **Bắt đầu khám phá**. Dừng và xem kết quả là các hành động phụ.
- Từ khóa có bảng chỉnh sửa trực tiếp, thêm/xóa/dán dòng và trạng thái chưa lưu.
- Kết quả có lịch sử theo lượt quét, tìm kiếm, sắp xếp, chọn dòng và phân trang; không tải Excel.
- Segoe UI Variable/Segoe UI cho nội dung, Bahnschrift cho tiêu đề và số liệu; dùng font hệ thống Windows, không tải font lúc chạy. Số liệu dùng tabular numerals.

## Cấu trúc

| Đường dẫn | Trách nhiệm |
| --- | --- |
| `frontend/src/App.tsx` | Màn hình chính và trạng thái UI |
| `frontend/src/components/ConfirmDialog.tsx` | Hộp xác nhận thao tác |
| `frontend/src/components/KeywordTable.tsx` | Bảng từ khóa có chỉnh sửa |
| `frontend/src/components/ResultsView.tsx` | Chọn lượt quét và xem lịch sử |
| `frontend/src/components/WorkbookView.tsx` | Bảng kết quả / đọc Excel cũ |
| `frontend/src/api.ts` | Kiểu dữ liệu và hợp đồng bridge |
| `frontend/src/styles.css` | Các control và bố cục dùng chung |
| `frontend/src/studio.css` | Token graphite/san hô, bố cục studio và điều chỉnh laptop |
| `frontend/src/components/WorkspaceHeading.tsx` | Tiêu đề và trạng thái riêng cho từng màn hình |
| `frontend/src/components/ScanSummary.tsx` | Dải số liệu thật của lượt quét |
| `frontend/src/components/TableLoading.tsx` | Skeleton khi đọc bảng, không giả dữ liệu |
| `ytb_bot/desktop/app.py` | Cửa sổ native, vị trí và vòng đời |
| `ytb_bot/desktop/api.py` | Bridge, hộp chọn file và cập nhật |
| `ytb_bot/core/` | Quét nền, xử lý bảng và lưu SQLite |

## Trạng thái và tương tác

Lỗi nhập liệu hiển thị cạnh trường bị lỗi. API Key được che mặc định; khóa được dùng cho yêu cầu Google YouTube API và được che trong lỗi quét.

Bộ lọc chuyển thành menu khi cửa sổ hẹp hơn 840 CSS pixel; menu đóng không nhận focus. Khi mở, focus được giữ trong menu; Esc đóng và trả focus về nút mở. Nội dung phía sau dùng inert. Có skip link tới nội dung chính. Các vùng nội dung cuộn được. Nút bắt đầu được kiểm tra nằm trong vùng nhìn thấy ở 1280×720 và 1024×768. Theme và tùy chọn chuyển động được lưu cục bộ; hiệu ứng tôn trọng reduced motion.

Bảng có skeleton trong lúc tải, thông báo lỗi nội dòng và nút thử lại. Thêm dòng đưa focus vào ô mới. Nhật ký chỉ tự cuộn bên trong vùng log, không kéo trang tới cuối. Hộp xác nhận có tên và mô tả truy cập riêng.

Nút **Dừng** chờ yêu cầu mạng hiện tại rồi lưu kết quả đã có. Timeout mạng là 20 giây mỗi yêu cầu, không phải giới hạn tổng lượt quét.

Phím tắt và thao tác Excel được ghi tại [hướng dẫn desktop](DESKTOP_GUIDE.md). Dùng nút **Sao chép** cho dòng được chọn bằng checkbox. Nhập từ khóa luôn lấy cột gốc, kể cả khi bảng đang lọc. Sửa bảng được giữ trong draft khi chuyển màn hình và chỉ lưu khi nhấn Lưu/Dùng để quét hoặc bắt đầu quét. Đóng cửa sổ với draft chưa lưu có xác nhận; handler native không chờ JavaScript trên GUI thread.

## Kiểm tra trực quan

```powershell
npm test --prefix frontend
python scripts/smoke_react.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke_desktop.ps1
```

Playwright tạo `artifacts/ui/react-dark.png`, `react-light.png`, `react-compact.png`, `studio-laptop.png`, `keyword-editor.png` và `result-history.png`. Kiểm tra gồm bàn phím, chuyển màn hình, các trạng thái lỗi/trống, retry và tương phản chữ của nút chính/menu/nhật ký ở cả hai theme (ít nhất 4.5:1). Đây không phải chứng nhận accessibility cho toàn bộ ứng dụng. Fixture bridge chỉ nằm trong tests; không dùng dữ liệu giả trong sản phẩm. Smoke React kiểm tra WebView2 thật, trạng thái HWND hiển thị, bridge có tham số và hủy đóng khi bảng chưa lưu. Smoke EXE kiểm tra bản đóng gói khi launcher yêu cầu Hidden, tránh hồi quy chỉ chạy ngầm.

Để chụp giao diện dự phòng: `python scripts/preview_legacy_ui.py --output artifacts/ui/legacy.png`. Công cụ này dùng dữ liệu minh họa, không gọi YouTube. Các test legacy phải đi qua `CTk.mainloop()` thật vì chỉ dùng `update()` có thể che lỗi khởi tạo cửa sổ.

## Nguồn định hướng

Taste Skill (redesign-existing-projects) dùng để rà typography, màu sắc và các chi tiết dư thừa. UI/UX Pro Max trả về hướng Data-Dense Dashboard và hướng dẫn focus bàn phím; mẫu Enterprise Gateway/landing và animation GSAP đi kèm không áp dụng cho ứng dụng desktop. mattpocock-skills:codebase-design dùng để tách tiêu đề, số liệu và trạng thái tải thành các phần có trách nhiệm rõ. Giữ React/CSS/Lucide hiện tại để không phát sinh thư viện mới hoặc tài nguyên mạng.
