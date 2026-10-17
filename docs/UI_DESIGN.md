# YTB-BOT Creator Studio: thiết kế UI

Giao diện mặc định là React + TypeScript trong cửa sổ pywebview / Edge WebView2. Python xử lý dữ liệu; giao diện CustomTkinter nằm riêng tại `ytb_bot/legacy_ui/` và được mở qua `--legacy`.

## Hướng thiết kế

- Bề mặt xanh đen/trắng, hành động chính đỏ san hô và trạng thái thành công xanh ngọc.
- Bốn thẻ hiển thị dữ liệu thật: từ khóa duy nhất, kênh phù hợp, số chủ đề đã xử lý và thời gian.
- Một hành động chính: **Bắt đầu khám phá**. Dừng và xem kết quả là các hành động phụ.
- Excel có khu vực riêng, tìm kiếm, sắp xếp, chọn dòng và phân trang.
- Font hệ thống, tài nguyên frontend đóng gói cục bộ; không cần tải font lúc chạy.

## Cấu trúc

| Đường dẫn | Trách nhiệm |
| --- | --- |
| `frontend/src/App.tsx` | Màn hình chính và trạng thái UI |
| `frontend/src/components/ConfirmDialog.tsx` | Hộp xác nhận thao tác |
| `frontend/src/components/WorkbookView.tsx` | Trình xem Excel |
| `frontend/src/api.ts` | Kiểu dữ liệu và hợp đồng bridge |
| `frontend/src/styles.css` | Token sáng/tối, responsive và hiệu ứng |
| `ytb_bot/desktop/app.py` | Cửa sổ native, vị trí và vòng đời |
| `ytb_bot/desktop/api.py` | Bridge, hộp chọn file và cập nhật |
| `ytb_bot/core/` | Quét nền và xử lý workbook |

## Trạng thái và tương tác

Lỗi nhập liệu hiển thị cạnh trường bị lỗi. API Key được che mặc định; khóa được dùng cho yêu cầu Google YouTube API và được che trong lỗi quét.

Bộ lọc chuyển thành menu khi cửa sổ hẹp hơn 840 CSS pixel; menu đóng không nhận focus. Các vùng nội dung cuộn được. Theme và tùy chọn chuyển động được lưu cục bộ; hiệu ứng tôn trọng reduced motion.

Nút **Dừng** chờ yêu cầu mạng hiện tại rồi lưu kết quả đã có. Timeout mạng là 20 giây mỗi yêu cầu, không phải giới hạn tổng lượt quét.

Phím tắt và thao tác Excel được ghi tại [hướng dẫn desktop](DESKTOP_GUIDE.md). Dùng nút **Sao chép** cho dòng được chọn bằng checkbox. Nhập từ khóa luôn lấy cột gốc, kể cả khi bảng đang lọc.

## Kiểm tra trực quan

```powershell
npm test --prefix frontend
python scripts/smoke_react.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke_desktop.ps1
```

Playwright tạo `artifacts/ui/react-dark.png`, `react-light.png` và `react-compact.png`. Fixture bridge chỉ nằm trong tests; không dùng dữ liệu giả trong sản phẩm. Smoke React kiểm tra WebView2 thật, trạng thái HWND hiển thị và bridge có tham số. Smoke EXE kiểm tra bản đóng gói khi launcher yêu cầu Hidden, tránh hồi quy chỉ chạy ngầm.

Để chụp giao diện dự phòng: `python scripts/preview_legacy_ui.py --output artifacts/ui/legacy.png`. Công cụ này dùng dữ liệu minh họa, không gọi YouTube. Các test legacy phải đi qua `CTk.mainloop()` thật vì chỉ dùng `update()` có thể che lỗi khởi tạo cửa sổ.
