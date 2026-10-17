# YTB-BOT Creator Studio

Giao diện mặc định dùng React + TypeScript trong cửa sổ pywebview / Edge WebView2, giữ version `1.0.2`. Giao diện CustomTkinter cũ có thể mở bằng `--legacy`.

## Hướng thiết kế

Tham khảo dữ liệu local của skill UI/UX Pro Max: phong cách Data-Dense Dashboard và hướng dẫn Progress Indicators. Mẫu landing page Enterprise Gateway trả về cùng kết quả tìm kiếm không áp dụng cho desktop. Chuyển typography sang Segoe UI/Consolas có sẵn trên Windows; không tải font hay tài nguyên web lúc chạy.

- Bề mặt xanh đen/trắng, nút hành động đỏ san hô, trạng thái thành công xanh ngọc.
- Bốn thẻ số liệu lấy từ dữ liệu thực: từ khóa duy nhất, kênh phù hợp, số chủ đề đã xử lý và thời gian.
- Một hành động chính: Bắt đầu khám phá. Dừng và xem kết quả là hành động phụ.
- Excel có khu vực làm việc riêng, bảng xen kẽ màu dòng, tiêu đề sắp xếp và ô tìm kiếm.

## Cấu trúc

- `frontend/src/styles.css`: token màu sáng/tối, bố cục responsive và hiệu ứng tôn trọng reduced motion.
- `frontend/src/App.tsx`: điều phối trạng thái giao diện, bộ lọc, nhật ký và kết quả.
- `frontend/src/WorkbookView.tsx`: trình xem Excel và nhập cột từ khóa.
- `frontend/src/api.ts`: kiểu dữ liệu và hợp đồng cầu nối JSON với Python.
- `ytb_bot/react_desktop.py`, `react_api.py`: cửa sổ desktop, hộp chọn file và cầu nối có kiểm tra lỗi.
- `ytb_bot/engine.py`, `workbook.py`: xử lý nền, dữ liệu thật và các phiên Excel, độc lập với React.

## Kiểm tra React

`npm test --prefix frontend` kiểm tra sáng/tối, bắt đầu/dừng, cửa sổ hẹp và nhập Excel có xác nhận. Fixture bridge chỉ nằm trong thư mục tests. Ảnh được tạo tại `artifacts/ui/react-dark.png`, `react-light.png`, `react-compact.png`. `python scripts/smoke_react.py` kiểm tra WebView2 thật tải React và kết nối với Python; `scripts/smoke_desktop.ps1` kiểm tra cửa sổ EXE sau khi đóng gói.

## Trạng thái và tương tác

- Lỗi nhập liệu nằm cạnh trường bị lỗi và tại form; không ghi API Key trước khi các giá trị hợp lệ.
- Nút Dừng chờ yêu cầu mạng hiện tại hoàn tất, sau đó lưu kết quả đã thu thập. HTTP timeout là 20 giây mỗi yêu cầu, không phải giới hạn tổng lượt quét.
- Tiến trình dùng chuyển động ngắn, không có hiệu ứng trang trí chạy liên tục. Người dùng tắt được chuyển động; mặc định tham khảo cài đặt animation của Windows.
- API Key được che mặc định và chỉ hiện khi người dùng chủ động chọn. Lỗi API được che khóa trước khi ghi nhật ký.
- Khi cửa sổ hẹp hơn 1030 logical pixel, bộ lọc thu gọn với nút hiện/ẩn ở đầu trang. Nội dung vẫn cuộn được sau khi resize.
- `Ctrl+Enter`: bắt đầu; `Ctrl+O`: mở Excel; `Esc`: yêu cầu dừng. Trong bảng, `Ctrl+C` sao chép dòng đã chọn. Các thao tác quan trọng có nút văn bản tương ứng.
- Tìm kiếm Excel có debounce. Sắp xếp tác động đến bảng xem; nhập từ khóa vẫn lấy toàn bộ cột gốc, không chỉ các dòng đang lọc.

## Kiểm tra trực quan

```powershell
python scripts/preview_ui.py --output artifacts/ui/dashboard-dark.png
python scripts/preview_ui.py --theme light --output artifacts/ui/dashboard-light.png
python scripts/preview_ui.py --compact --output artifacts/ui/dashboard-compact.png
python scripts/preview_ui.py --excel --output artifacts/ui/excel-dark.png
```

Ảnh được chụp từ cửa sổ thật; file Excel trong preview là dữ liệu minh họa có tên rõ ràng. `artifacts/` không được commit. Script này không gọi YouTube API.

Kiểm tra trên Windows với cửa sổ thường/nhỏ, cả hai theme, chế độ giảm chuyển động, preset, lỗi nhập liệu, clipboard, Excel nhiều sheet và dừng có kết quả một phần. CustomTkinter không cung cấp đầy đủ ngữ nghĩa Windows UI Automation như các framework native chuyên dụng; không coi kiểm thử bàn phím là chứng nhận hỗ trợ screen reader.

Kiểm tra khởi động phải đi qua `CTk.mainloop()` thật. Windows titlebar initialization có thể bơm sự kiện rồi khôi phục trạng thái `withdrawn`; cửa sổ chỉ được hiện khi CustomTkinter hoàn tất khởi tạo. Không thay test startup bằng `update()` hoặc tự gọi `deiconify()` trong script chụp ảnh, vì chúng có thể che lỗi chạy ngầm. Regression test kiểm tra cả lần vào mainloop đầu tiên và đổi theme; `scripts/smoke_desktop.ps1` kiểm tra chính EXE sau build.
