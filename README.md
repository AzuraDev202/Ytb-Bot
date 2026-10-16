# Ytb-Bot

Ứng dụng Windows tìm kênh YouTube mới theo từ khóa, tuổi kênh và lượt xem; xuất kết quả Excel.

## Tải app cho laptop Windows

**[Tải bản desktop mới nhất](https://github.com/AzuraDev202/Ytb-Bot/releases/latest/download/gui_app.exe)**

[Xem các phiên bản và ghi chú cập nhật](https://github.com/AzuraDev202/Ytb-Bot/releases/latest) · [Tải SHA-256](https://github.com/AzuraDev202/Ytb-Bot/releases/latest/download/gui_app.exe.sha256)

Link tải cố định luôn trỏ tới EXE trong Release mới nhất. Link chỉ hoạt động sau khi GitHub Actions phát hành thành công bản đầu tiên. Tải EXE vào thư mục riêng có quyền ghi rồi mở trực tiếp, không cần cài Python. Bản desktop/build cũ được bỏ khỏi cây mã nguồn; file tải được lưu ở GitHub Releases.

## Chạy và build

```powershell
python -m pip install -r requirements.txt pyinstaller
python gui_app.py
python scripts/build_release.py
```

Build tạo `dist/gui_app.exe`, `dist/gui_app.exe.sha256` và `dist/build-info.json`. Mã build (commit + thời gian build UTC) xuất hiện trên titlebar và cạnh thông tin phiên bản để phân biệt các file cùng version. Không đóng gói `.env` hay API Key vào EXE.

## Cấu trúc thư mục

```text
ytb_bot/                 Mã nguồn ứng dụng
  ui/                    Giao diện desktop, Excel và bố cục cửa sổ
  scanner.py             Bộ quét chạy từ dòng lệnh
  updater.py             Kiểm tra, tải và cài bản cập nhật
  paths.py               Đường dẫn .env và dữ liệu lúc chạy
  version.py             Phiên bản và nguồn cập nhật
  __main__.py            Điểm khởi chạy desktop
packaging/desktop.spec   Cấu hình PyInstaller
scripts/                 Các lệnh build và chuẩn bị Release
tests/                   Kiểm thử
.github/workflows/       Quy trình GitHub Actions
gui_app.py               Lệnh chạy desktop tương thích cách cũ
bot.py                   Lệnh chạy scanner tương thích cách cũ
dist/                    EXE/checksum sinh ra khi build, không commit
.release-build/          File build tạm, không commit
```

Có thể chạy desktop bằng `python -m ytb_bot` hoặc `python gui_app.py`. Giữ `.env` tại thư mục gốc khi chạy mã nguồn; bản desktop tiếp tục dùng `.env` và Excel cạnh EXE.

Chỉ tăng version khi có thay đổi lớn về cấu trúc chính. Các chỉnh sửa nhỏ về UI, sửa lỗi hoặc sắp xếp file giữ nguyên version trừ khi có yêu cầu phát hành phiên bản mới. Workflow vẫn build và thay file tải của Release cùng version khi push lên `main`, sau khi test và kiểm tra cửa sổ EXE đạt.

## Xem và nhập Excel trong app

Giao diện **Creator Studio** có bộ đếm từ khóa/kênh/tiến độ, preset thêm chủ đề, lỗi tại ô nhập, nút dừng có lưu kết quả một phần, theme tối/sáng và tùy chọn tắt chuyển động. Bộ lọc tự thu gọn khi cửa sổ hẹp và có nút hiện/ẩn ở đầu trang. `Ctrl+Enter` bắt đầu quét, `Ctrl+O` mở Excel, `Esc` yêu cầu dừng sau yêu cầu mạng hiện tại.

Trong tab Excel, dùng **Tìm trong bảng**, bấm tiêu đề cột để sắp xếp, chọn dòng rồi **Sao chép dòng** hoặc `Ctrl+C`. Các thao tác xem không thay đổi file gốc; nhập từ khóa vẫn lấy toàn bộ cột gốc. Hướng dẫn thiết kế và kiểm tra trực quan ở [docs/UI_DESIGN.md](docs/UI_DESIGN.md).

Từ phiên bản 1.0.2, cửa sổ tự căn giữa vùng làm việc của màn hình chính, tính cả Windows DPI scaling và chừa chỗ cho taskbar/viền cửa sổ. Trên màn hình nhỏ, nội dung chính và bộ lọc có thể cuộn để các nút không bị khuất. Bạn vẫn có thể kéo giãn hoặc phóng to cửa sổ.

- Nhấn **Nhập Excel** hoặc vào tab **Excel → Mở file Excel**, chọn `.xlsx` hoặc `.xls`.
- Chọn sheet để xem bảng; bảng có thanh cuộn ngang/dọc và phân trang 200 dòng. Dữ liệu được đọc ở nền để cửa sổ vẫn phản hồi.
- Chọn cột rồi nhấn **Dùng cột làm từ khóa**. App lấy toàn bộ cột, bỏ ô trống và từ khóa trùng, rồi hỏi trước khi thay danh sách hiện tại. Cột `Keyword` được chọn mặc định nếu có.
- Nhấn **Xem kết quả Excel** để xem file kết quả ngay trong app. Sau lượt quét có kết quả, tab Excel tự mở file vừa xuất.

Bảng dùng để xem và nhập dữ liệu, chưa hỗ trợ sửa ô hoặc lưu thay đổi vào workbook gốc. Không cần cài Microsoft Excel để dùng các tính năng này.

## Cập nhật desktop

App kiểm tra GitHub Releases của `AzuraDev202/Ytb-Bot` sau khi mở, sau mỗi 6 giờ và khi nhấn **Kiểm tra cập nhật**. Bản desktop cũng so sánh SHA-256 khi Release có cùng version: file khác nghĩa là có bản build khác; file giống thì không báo lại. Bản chạy mã nguồn không so hash của Python. Khi có bản mới, sidebar và nhật ký thông báo; nhấn **Cập nhật ngay** và xác nhận để tải, kiểm tra SHA-256, tự thay EXE và mở lại. App không cập nhật giữa một lượt quét. Không có mạng hoặc GitHub giới hạn truy cập thì app vẫn dùng được; kiểm tra lại sau.

**EXE cũ chưa có updater hoặc chưa so hash cùng version cần thay thủ công một lần bằng bản mới.** Nếu bản cũ đang chạy ngầm, End Task tiến trình cũ, đợi workflow phát hành hoàn tất rồi tải và chạy lại file mới. Chỉ sửa code mà không cập nhật asset trên Releases không thay đổi file người dùng tải.

EXE phải nằm trong thư mục người dùng có quyền ghi (ví dụ thư mục riêng trong Downloads), không nên đặt trong Program Files. `.env` và kết quả Excel được đọc/ghi cạnh EXE và không bị bước cập nhật thay thế. Nếu chưa có `.env` cạnh EXE, lần đầu app có thể đọc `.env` từ thư mục khởi chạy rồi lưu cạnh EXE khi quét. Chuyển file Excel cũ sang thư mục cạnh EXE nếu trước đây bạn chạy từ thư mục khác.

Updater giữ bản cũ thành `gui_app.exe.previous` (hoặc `<tên EXE hiện tại>.previous` nếu đã đổi tên). Nếu thay file hoặc khởi chạy thất bại, helper khôi phục file cũ; lỗi được ghi ở `%TEMP%/ytb-update-*/update-error.log`. Nếu bản mới khởi chạy được nhưng gặp lỗi sau đó, đóng app và tự khôi phục file `.previous`. SHA-256 kiểm tra tính toàn vẹn của file tải; đây không phải chữ ký số Windows.

## Phát hành phiên bản mới

Repo và Releases cần công khai để app tải được mà không lưu GitHub token trong EXE.

1. Khi cần phát hành phiên bản mới, sửa `APP_VERSION` trong `ytb_bot/version.py`, ví dụ `1.1.0`; chỉ dùng `X.Y.Z`.
2. Commit và push code lên `main`, gồm workflow `.github/workflows/release.yml`:

   ```powershell
   git add -A
   git commit -m "Release v1.1.0"
   git push origin main
   ```

GitHub Actions chạy test, build EXE và kiểm tra cửa sổ hiện thật trước khi cập nhật link tải. Khi version tăng, workflow tạo Release mới. Khi version bằng Release mới nhất và nguồn chạy là `main`, workflow thay EXE/checksum/build-info của Release hiện tại; không tạo version mới. Push lại tag bằng version hiện tại không ghi đè bản từ `main`; version thấp hơn không được phát hành. Có thể chạy workflow thủ công trên `main` ở tab Actions. Khi chưa có Release, workflow phát hành phiên bản đang đặt trong `ytb_bot/version.py`.

Chỉ phát hành stable; updater bỏ qua draft/prerelease và phiên bản cũ. Khi phát hành thủ công, upload cả EXE và checksum vào cùng Release có tag khớp `APP_VERSION`. Không commit `build/`, `dist/` hoặc `.release-build/`; chúng được tạo lại khi build. Việc xóa file build khỏi cây mã nguồn không xóa chúng khỏi lịch sử Git cũ.

## Kiểm thử

```powershell
python -m unittest discover -s tests -v
```

Sau khi build, kiểm tra trực tiếp cửa sổ EXE trên Windows bằng `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke_desktop.ps1`. Bài kiểm tra tự chạy EXE, yêu cầu cửa sổ chính hiện liên tục ít nhất 2 giây rồi đóng đúng tiến trình vừa tạo. Workflow cũng chạy bước này trước khi phát hành để tránh trường hợp EXE chỉ chạy ngầm.

Trước khi phân phối, kiểm tra trên máy Windows: mở bản cũ có updater, phát hành bản cao hơn, chọn cập nhật, xác nhận app mở lại đúng phiên bản và `.env`/Excel vẫn còn. Test tự động dùng dữ liệu giả và helper thay file thử nghiệm, không thay EXE đang sử dụng.
