# Sử dụng và phát hành YTB-BOT Desktop

## Từ khóa trong Bot

1. Vào **Từ khóa** hoặc nhấn **Sửa bảng từ khóa** trên màn hình khám phá.
2. Sửa trực tiếp trong ô, nhấn **Thêm dòng**, hoặc dán nhiều dòng từ Excel vào một ô. Khi dán nhiều cột, chỉ cột đầu tiên được lấy.
3. Chọn checkbox rồi **Xóa** để bỏ dòng; thao tác xóa có xác nhận.
4. Nhấn **Lưu từ khóa** hoặc **Ctrl+S** trong bảng để lưu nội bộ. **Dùng để quét** vừa lưu vừa quay lại màn hình khám phá.
5. Dòng trống được bỏ qua và từ trùng được gộp khi quét. Bạn có thể lưu một bảng trống.
6. Nếu đóng app khi còn thay đổi chưa lưu, Bot hỏi xác nhận. Cần lưu trước khi cập nhật và khởi động lại.

Để lấy dữ liệu từ file cũ, chọn **Nhập từ file cũ**, mở `.xlsx` hoặc `.xls`, chọn sheet/cột rồi **Nhập cột từ khóa**. Bot hỏi trước khi thay danh sách, lấy toàn bộ cột gốc dù đang lọc, rồi đưa dữ liệu vào bảng chỉnh sửa. Nhấn **Lưu từ khóa** để giữ lại. File gốc không bị ghi đè.

## Quét và xem kết quả

Nhập API Key và bộ lọc rồi nhấn **Bắt đầu khám phá**. Danh sách từ khóa đang dùng được lưu trước khi quét. **Dừng** chờ yêu cầu mạng hiện tại hoàn tất rồi giữ kết quả đã có.

Vào **Kết quả** hoặc **Xem kết quả trong Bot** để xem từng lượt quét theo thời gian, trạng thái và số kênh. Bảng có tìm kiếm, sắp xếp, phân trang 100 dòng và sao chép các dòng có checkbox. Dữ liệu đầy đủ được giữ, kể cả lượt quét không có kênh hoặc gặp lỗi; màn hình khám phá chỉ hiển thị nhanh 200 kênh đầu tiên.

Kết quả được ghi vào kho nội bộ theo từng đợt xử lý và khi lượt quét kết thúc, không tạo file `.xlsx`. Nhấn **Làm mới** nếu đang xem một lượt còn quét. Nếu ứng dụng bị tắt đột ngột, các đợt đã lưu vẫn có thể xem lại; phần yêu cầu đang xử lý có thể chưa được ghi.

Phím tắt: `Ctrl+Enter` bắt đầu, `Ctrl+O` nhập file cũ, `Esc` đóng bộ lọc hoặc yêu cầu dừng. `Ctrl+C` thông thường sao chép văn bản bôi chọn; dùng nút **Sao chép** cho dòng có checkbox.

## Dữ liệu và chẩn đoán

- Bảng từ khóa và lịch sử: `%LOCALAPPDATA%/Ytb-Bot/data/workspace.sqlite3`. Đây là dữ liệu nội bộ của app, không phải file Excel để người dùng theo dõi thủ công.
- Đóng Bot trước khi sao lưu hoặc chuyển kho dữ liệu sang máy khác. Sao chép `workspace.sqlite3` tới cùng thư mục dữ liệu trên máy đích.
- `.env` và `studio-settings.json` ở cạnh EXE hoặc thư mục gốc khi chạy source.
- Các file Excel cũ không bị xóa hoặc sửa bởi tính năng mới.
- API Key được lưu cục bộ, dùng để gọi Google YouTube Data API và không được đóng gói vào EXE.
- Log khởi động: `%LOCALAPPDATA%/Ytb-Bot/logs/desktop.log`.
- Luồng quản lý dữ liệu trong Bot dùng giao diện React mặc định. CLI và `--legacy` là các công cụ cũ được giữ để tương thích.

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

## Lọc kênh có liên hệ công khai

Lượt quét mới chỉ nhận kênh đáp ứng tuổi kênh, lượt xem **và** có email hoặc đường dẫn liên hệ cụ thể trong mô tả kênh. Bot nhận diện email, Facebook, Instagram, LinkedIn, TikTok, X/Twitter, Telegram, Zalo và WhatsApp. Chỉ nhắc tên nền tảng, link trang chủ hoặc link chia sẻ không đủ điều kiện. Bot không kiểm chứng chủ sở hữu hay khả năng liên lạc của địa chỉ/link được ghi trong mô tả.

Trong **Kết quả**, các cột **Email**, **Facebook**, **Liên Hệ Khác** chứa thông tin tìm được; dùng **Xem đầy đủ** hoặc **Sao chép** để lấy nội dung nguyên vẹn. Lịch sử cũ vẫn giữ nguyên; cần quét lại để kiểm tra liên hệ theo logic mới. Quét mặc định tiếp tục lưu trong Bot, không tạo file Excel.

Nguồn kiểm tra là `snippet.description` của [YouTube Data API](https://developers.google.com/youtube/data/reference/rest/v3/channels#snippet.description). Liên hệ chỉ nằm trong video, banner, liên kết ngoài mô tả hoặc mục email cần đăng nhập không nằm trong phạm vi kiểm tra hiện tại.
