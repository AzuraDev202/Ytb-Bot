# Sử dụng và phát hành YTB-BOT Desktop

## Quét và xem Excel

1. Nhập YouTube API Key, tuổi kênh tối đa, lượt xem tối thiểu và độ sâu quét.
2. Nhập mỗi từ khóa trên một dòng hoặc chọn **Nhập Excel**. Từ khóa trùng được gộp.
3. Nhấn **Bắt đầu khám phá**. Nhật ký và số liệu phản ánh lượt quét thật.
4. **Dừng** chờ yêu cầu mạng hiện tại hoàn tất rồi lưu kết quả đã tìm được.
5. Nhấn **Xem kết quả Excel** để mở file xuất trong app.

Trong **Bảng dữ liệu**, nhấn **Mở Excel**, chọn file `.xlsx` hoặc `.xls`, sheet và cột từ khóa. Bảng phân trang 100 dòng; tìm kiếm và sắp xếp chỉ thay đổi phần xem. Chọn dòng rồi nhấn **Sao chép** để lấy nội dung các dòng đó.

**Nhập cột từ khóa** lấy toàn bộ cột gốc, loại ô trống và từ trùng, rồi hỏi xác nhận trước khi thay danh sách hiện tại. Trình xem không sửa file gốc.

Phím tắt: `Ctrl+Enter` bắt đầu, `Ctrl+O` chọn Excel, `Esc` đóng bộ lọc hoặc yêu cầu dừng. `Ctrl+C` thông thường chỉ sao chép văn bản được bôi chọn; dùng nút **Sao chép** cho các dòng có checkbox.

## Dữ liệu và chẩn đoán

- Bản EXE đọc/ghi `.env`, `studio-settings.json` và Excel cạnh EXE. Đặt EXE trong thư mục có quyền ghi.
- Chạy mã nguồn lưu các file đó tại thư mục gốc dự án.
- Kết quả được lưu thành `danh_sach_kenh_viral_moi.xlsx` khi có kênh phù hợp.
- API Key được lưu cục bộ và gửi tới Google để gọi YouTube Data API; không đóng gói vào EXE.
- Log khởi động: `%LOCALAPPDATA%/Ytb-Bot/logs/desktop.log`.
- Nếu không mở được app, kiểm tra WebView2 Runtime và log. `python gui_app.py --legacy` mở giao diện dự phòng.

## Cập nhật desktop

App kiểm tra GitHub Releases sau khi mở, mỗi 6 giờ và khi nhấn **Kiểm tra cập nhật**. Khi có bản cập nhật, chọn **Cập nhật ngay** và xác nhận; app tải, kiểm tra SHA-256, thay EXE rồi mở lại. Không cài cập nhật giữa một lượt quét.

Bản EXE so sánh SHA-256 cả khi Release có cùng version, nên có thể nhận một build khác mà không tăng version. Bản chạy mã nguồn không tự thay Python. Bản EXE cũ chưa hỗ trợ cơ chế này cần tải lại thủ công một lần.

Updater giữ bản trước thành `<tên EXE>.previous`. Helper khôi phục file cũ nếu thay thế hoặc khởi chạy thất bại. Nếu app mới mở được nhưng lỗi sau đó, đóng app rồi khôi phục file `.previous` thủ công. Log helper ở `%TEMP%/ytb-update-*/update-error.log`. SHA-256 kiểm tra toàn vẹn, không phải chữ ký số Windows.

## Phát hành GitHub Releases

[Workflow](../.github/workflows/release.yml) chạy khi push lên `main`, push tag `v*` hoặc chạy thủ công. Repo/Releases cần công khai để app tải cập nhật mà không nhúng GitHub token vào EXE.

- Giữ version cho thay đổi nhỏ, sửa lỗi và sắp xếp file; push `main` sẽ thay asset của Release cùng version.
- Khi có thay đổi lớn cần version mới, sửa `ytb_bot/version.py` theo định dạng `X.Y.Z`. Nếu dùng tag, tag phải khớp `vX.Y.Z`.
- Version thấp hơn không được phát hành; push lại tag bằng version hiện tại không ghi đè build từ `main`.
- Workflow kiểm thử Python, build React/EXE, test UI, bridge và cửa sổ EXE trước khi publish.
- Asset gồm `gui_app.exe`, `gui_app.exe.sha256` và `build-info.json`.

Không commit file build hoặc khóa thật. Khi phát hành thủ công, giữ EXE, checksum và metadata từ cùng một lần build. Trước khi phân phối rộng, kiểm tra cập nhật giữa hai EXE trên Windows và xác nhận dữ liệu cục bộ vẫn còn.
