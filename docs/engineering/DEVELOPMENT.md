# Phát triển và kiểm thử

Chạy các lệnh tại thư mục gốc dự án bằng PowerShell, trừ khi có ghi chú khác.

## Môi trường

| Thành phần | Yêu cầu |
| --- | --- |
| Hệ điều hành | Windows x64 để chạy và đóng gói desktop Windows |
| Python | 3.12, cùng phiên bản CI đang dùng |
| Node.js | 22.12+ và npm; CI dùng Node.js 22 |
| Web engine | Microsoft Edge WebView2 Runtime |
| Kiểm thử trình duyệt | Microsoft Edge, theo cấu hình Playwright |
| Build | Git và PyInstaller từ dependency phát triển |

## Cài đặt

```powershell
git clone https://github.com/AzuraDev202/Ytb-Bot.git
cd Ytb-Bot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
npm ci --prefix frontend
npm run build --prefix frontend
python gui_app.py
```

Nhập YouTube API Key trong ứng dụng hoặc tạo `.env` dựa trên [mẫu](../../.env.example), đặt `YOUTUBE_API_KEY`. Giữ file chứa khóa thật ở máy phát triển. Gmail có [hướng dẫn OAuth riêng](../user/CONTACT_COMPOSER.md).

## Các chế độ chạy

| Lệnh | Mục đích |
| --- | --- |
| `python gui_app.py` | Desktop React mặc định |
| `python -m ytb_bot` | Cùng desktop qua package entrypoint |
| `npm run dev --prefix frontend` | Xem frontend trong trình duyệt; không có bridge Python |
| `python gui_app.py --legacy` | Giao diện CustomTkinter tương thích |
| `python bot.py` | CLI tương thích; dùng file từ khóa và xuất Excel riêng |

Build lại frontend trước khi chạy desktop sau khi sửa React. `npm run dev` không tự cung cấp hộp chọn file native, SQLite hoặc Gmail của Python.

## Kiểm tra trước phát hành

```powershell
python -m unittest discover -s tests -v
npm run build --prefix frontend
npm test --prefix frontend
python scripts/checks/smoke_react.py
```

Sau khi build EXE, chạy thêm:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/checks/smoke_desktop.ps1
```

- Python tests kiểm tra dữ liệu, scanner, bridge, outreach, updater và giao diện cũ. Một số bài cần Tk/Tcl, desktop Windows hoặc DPAPI hoạt động.
- Playwright dùng bridge giả lập; không xác nhận YouTube quota, OAuth thật hoặc khả năng gửi thư thật.
- `smoke_react.py` cần frontend đã build và phiên desktop tương tác để kiểm tra WebView2 cùng bridge thật.
- `smoke_desktop.ps1` cần `dist/gui_app.exe`; kiểm tra cửa sổ của chính process được khởi chạy.
- Chỉ công bố kết quả khi tiến trình kết thúc và trả mã thoát; các dòng test báo thành công chưa đủ nếu runner còn treo.

Kiểm tra Google/OAuth thật cần môi trường và hộp thư thử nghiệm do đội phát triển kiểm soát. Không dùng email lấy từ kênh làm địa chỉ thử nghiệm.

## Công cụ phát triển

```powershell
python scripts/dev/preview_legacy_ui.py --output artifacts/ui/legacy.png
```

Công cụ này chụp giao diện cũ với dữ liệu minh họa, không quét YouTube. Ảnh và log kiểm tra nằm trong thư mục sinh tự động.

## Chẩn đoán

- Không mở được React: kiểm tra `frontend/web-dist/index.html` và WebView2 Runtime.
- Lỗi `init.tcl`: kiểm tra cài đặt Tcl/Tk của Python đang dùng; không kết luận là lỗi logic từ lỗi môi trường này.
- Lỗi kho Gmail: kiểm tra ngữ cảnh tài khoản Windows và lỗi DPAPI; không ghi token vào log hoặc chuyển sang lưu plaintext.
- Log khởi động tại `%LOCALAPPDATA%/Ytb-Bot/logs/desktop.log`.
- Dừng Vite hoặc test đang giữ file dependency trước khi chạy build phát hành.

Xem [kiến trúc](ARCHITECTURE.md), [thiết kế giao diện](UI_DESIGN.md) và [phát hành](RELEASE.md).
