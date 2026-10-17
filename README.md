# YTB-BOT · Creator Studio

YTB-BOT là ứng dụng desktop Windows giúp khám phá kênh YouTube mới theo từ khóa, tuổi kênh và tổng lượt xem. Giao diện **React + TypeScript** chạy trong cửa sổ **pywebview / Microsoft Edge WebView2**; Python xử lý YouTube Data API và dữ liệu Excel.

**[Tải YTB-BOT cho Windows](https://github.com/AzuraDev202/Ytb-Bot/releases/latest/download/gui_app.exe)**

[Mã nguồn](https://github.com/AzuraDev202/Ytb-Bot) · [GitHub Releases](https://github.com/AzuraDev202/Ytb-Bot/releases/latest) · [SHA-256](https://github.com/AzuraDev202/Ytb-Bot/releases/latest/download/gui_app.exe.sha256)

Link tải trỏ tới asset trong Release mới nhất sau khi workflow phát hành thành công. Tải EXE vào thư mục riêng có quyền ghi rồi mở trực tiếp; không cần cài Python, Node.js hoặc Microsoft Excel.

## Mục tiêu dự án

- Tìm kênh YouTube mới có tiềm năng bằng các bộ lọc có thể điều chỉnh.
- Tập trung quét kênh, theo dõi tiến trình và quản lý danh sách từ khóa trong một ứng dụng.
- Xem, tìm kiếm, sắp xếp và nhập từ khóa từ Excel; tự xuất danh sách kênh phù hợp.
- Cung cấp giao diện sáng/tối, bố cục co giãn và cập nhật từ GitHub Releases.

Kết quả phục vụ nghiên cứu kênh, không cam kết kênh sẽ viral. Trình xem Excel hiện chưa hỗ trợ sửa ô và lưu thay đổi vào workbook gốc.

## Yêu cầu cấu hình dự án

| Thành phần | Chạy bản desktop | Phát triển / build |
| --- | --- | --- |
| Hệ điều hành | Windows 10/11 x64 | Windows x64 để tạo EXE Windows |
| Web engine | Microsoft Edge WebView2 Runtime | WebView2 Runtime; Microsoft Edge để chạy test UI |
| Python | Không cần | Python 3.12, phiên bản dùng trong CI |
| Node.js / npm | Không cần | Node.js 22.12+ và npm; CI dùng Node.js 22 |
| Git | Không cần | Clone mã nguồn và tạo mã nhận diện build |
| Kết nối mạng | Quét YouTube và tải cập nhật | Cài dependency, quét API và cập nhật |
| API | YouTube Data API v3 key hợp lệ, còn quota | Tương tự khi quét dữ liệu thật |
| Quyền ghi | Thư mục chứa EXE | Thư mục dự án và build |

Nhập API Key trong app hoặc cấu hình `YOUTUBE_API_KEY` trong `.env`. Khóa được lưu cục bộ và sử dụng khi gửi yêu cầu tới Google YouTube Data API. `.env`, Excel và tùy chọn giao diện nằm cạnh EXE khi chạy bản đóng gói; khi chạy mã nguồn, chúng nằm ở thư mục gốc dự án. Không commit API Key.

## Chạy từ mã nguồn

Mở PowerShell tại thư mục muốn lưu dự án:

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

`python -m ytb_bot` mở cùng ứng dụng. `python gui_app.py --legacy` mở giao diện CustomTkinter dự phòng; `python bot.py` chạy scanner dòng lệnh. Xem mẫu cấu hình tại [.env.example](.env.example); không ghi đè `.env` đang chứa khóa của bạn.

`npm run dev --prefix frontend` xem trước React trên trình duyệt. Chức năng Python, hộp chọn file và Excel cần chạy trong cửa sổ desktop.

## Cách build dự án

Sau khi cài dependency ở trên, chạy tại thư mục gốc:

```powershell
python scripts/build_release.py
```

Script tự chạy `npm ci`, build React, đóng gói bằng PyInstaller và tạo checksum/metadata. Dừng Vite hoặc test frontend trước khi build để tránh khóa file dependency trên Windows.

| File đầu ra | Mục đích |
| --- | --- |
| `dist/gui_app.exe` | App desktop, gồm frontend đã build |
| `dist/gui_app.exe.sha256` | Kiểm tra tính toàn vẹn của EXE |
| `dist/build-info.json` | Version, commit, thời điểm build và SHA-256 |

Không đóng gói `.env` hoặc API Key vào EXE. Mã build trên titlebar giúp phân biệt các bản cùng version. Log khởi động nằm tại `%LOCALAPPDATA%/Ytb-Bot/logs/desktop.log`.

Khi push lên `main`, [workflow phát hành](.github/workflows/release.yml) chạy test, build và kiểm tra cửa sổ trước khi đăng asset. Thay đổi nhỏ hoặc sắp xếp file giữ version hiện tại; workflow có thể thay asset của Release cùng version. Xem [hướng dẫn phát hành](docs/DESKTOP_GUIDE.md).

## Cấu trúc thư mục

```text
frontend/
  src/
    components/          Hộp xác nhận và trình xem Excel
    App.tsx              Màn hình React và trạng thái UI
    api.ts               Kiểu dữ liệu và cầu nối Python
    styles.css           Theme và bố cục responsive
  tests/                 Kiểm thử thao tác bằng Playwright
ytb_bot/
  core/                  Bộ quét nền và xử lý workbook
  desktop/               Cửa sổ WebView2 và API cho React
  cli/                   Scanner dòng lệnh
  legacy_ui/             CustomTkinter dự phòng (--legacy)
  paths.py               Đường dẫn dữ liệu lúc chạy
  updater.py             Kiểm tra, tải và cài cập nhật
  build_info.py          Đọc mã nhận diện build
  version.py             Version và nguồn cập nhật
scripts/                 Build, phát hành và kiểm tra desktop
packaging/               Cấu hình PyInstaller
tests/                   Kiểm thử Python
docs/                    Hướng dẫn sử dụng và thiết kế
.github/workflows/       CI và GitHub Releases
gui_app.py               Launcher desktop
bot.py                   Launcher CLI
```

`dist/`, `.release-build/`, `frontend/web-dist/`, `frontend/node_modules/` và `artifacts/` được sinh tự động, không commit. Giữ `frontend/package-lock.json` để CI cài đúng dependency.

## Kiểm thử

```powershell
python -m unittest discover -s tests -v
npm test --prefix frontend
python scripts/smoke_react.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke_desktop.ps1
```

Hai lệnh smoke cần Windows có phiên desktop tương tác. Build frontend trước `smoke_react.py` và build EXE trước `smoke_desktop.ps1`. Test UI và scanner dùng fixture/mock, không xác nhận quota hoặc dữ liệu YouTube thật.

## Tài liệu

- [Thao tác Excel, cập nhật và phát hành](docs/DESKTOP_GUIDE.md)
- [Thiết kế UI và kiểm tra trực quan](docs/UI_DESIGN.md)
- [Giấy phép](LICENSE)
