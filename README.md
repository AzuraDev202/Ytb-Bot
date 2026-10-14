# Ytb-Bot

Ứng dụng Windows tìm kênh YouTube mới theo từ khóa, tuổi kênh và lượt xem; xuất kết quả Excel.

## Chạy và build

```powershell
python -m pip install -r requirements.txt pyinstaller
python gui_app.py
python scripts/build_release.py
```

Build tạo `dist/gui_app.exe` và `dist/gui_app.exe.sha256`. Không đóng gói `.env` hay API Key vào EXE.

## Cập nhật desktop

App kiểm tra GitHub Releases của `AzuraDev202/Ytb-Bot` sau khi mở, sau mỗi 6 giờ và khi nhấn **Kiểm tra cập nhật**. Khi có bản mới, sidebar và nhật ký thông báo; nhấn **Cập nhật ngay** và xác nhận để tải, kiểm tra SHA-256, tự thay EXE và mở lại. App không cập nhật giữa một lượt quét. Không có mạng hoặc GitHub giới hạn truy cập thì app vẫn dùng được; kiểm tra lại sau.

**EXE cũ chưa có updater cần thay thủ công một lần bằng bản mới.** Không có cách thêm updater vào một EXE đang được người dùng giữ mà không thay bản đó trước.

EXE phải nằm trong thư mục người dùng có quyền ghi (ví dụ thư mục riêng trong Downloads), không nên đặt trong Program Files. `.env` và kết quả Excel được đọc/ghi cạnh EXE và không bị bước cập nhật thay thế. Nếu chưa có `.env` cạnh EXE, lần đầu app có thể đọc `.env` từ thư mục khởi chạy rồi lưu cạnh EXE khi quét. Chuyển file Excel cũ sang thư mục cạnh EXE nếu trước đây bạn chạy từ thư mục khác.

Updater giữ bản cũ thành `gui_app.exe.previous` (hoặc `<tên EXE hiện tại>.previous` nếu đã đổi tên). Nếu thay file hoặc khởi chạy thất bại, helper khôi phục file cũ; lỗi được ghi ở `%TEMP%/ytb-update-*/update-error.log`. Nếu bản mới khởi chạy được nhưng gặp lỗi sau đó, đóng app và tự khôi phục file `.previous`. SHA-256 kiểm tra tính toàn vẹn của file tải; đây không phải chữ ký số Windows.

## Phát hành phiên bản mới

Repo và Releases cần công khai để app tải được mà không lưu GitHub token trong EXE.

1. Sửa `APP_VERSION` trong `app_version.py`, ví dụ `1.0.1`; chỉ dùng `X.Y.Z`.
2. Commit và push code, gồm workflow `.github/workflows/release.yml`.
3. Tạo và push tag khớp phiên bản:

   ```powershell
   git tag v1.0.1
   git push origin v1.0.1
   ```

GitHub Actions chạy test, build Windows EXE và phát hành Release với cả EXE lẫn checksum. Chỉ phát hành stable; updater bỏ qua draft/prerelease và phiên bản cũ. Khi phát hành thủ công, upload cả hai file trên vào cùng Release có tag khớp `APP_VERSION`. Push code thông thường không tạo bản cập nhật desktop.

## Kiểm thử

```powershell
python -m unittest discover -s tests -v
```

Trước khi phân phối, kiểm tra trên máy Windows: mở bản cũ có updater, phát hành bản cao hơn, chọn cập nhật, xác nhận app mở lại đúng phiên bản và `.env`/Excel vẫn còn. Test tự động dùng dữ liệu giả và helper thay file thử nghiệm, không thay EXE đang sử dụng.
