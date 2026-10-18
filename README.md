# YTB-BOT Creator Studio

**Khám phá kênh YouTube mới. Sàng lọc cơ hội. Quản lý nghiên cứu trong một ứng dụng.**

YTB-BOT là ứng dụng Windows dành cho người nghiên cứu thị trường YouTube và tìm kiếm nhà sáng tạo phù hợp để hợp tác. Từ danh sách chủ đề, ứng dụng tìm kênh theo tuổi kênh và tổng lượt xem, lưu kết quả có liên hệ công khai để bạn xem xét và tiếp tục trao đổi.

[Tải cho Windows](https://github.com/AzuraDev202/Ytb-Bot/releases/latest/download/gui_app.exe) · [Hướng dẫn sử dụng](docs/user/DESKTOP_GUIDE.md) · [Tài liệu](docs/README.md) · [Báo lỗi](https://github.com/AzuraDev202/Ytb-Bot/issues)

## Từ chủ đề đến danh sách kênh

1. **Chuẩn bị từ khóa:** nhập chủ đề, dán danh sách hoặc nhập cột từ Excel.
2. **Chọn bộ lọc:** đặt tuổi kênh tối đa, lượt xem tối thiểu và độ sâu tìm kiếm.
3. **Đánh giá kết quả:** so sánh chỉ số, tìm kiếm, sắp xếp và xem thông tin liên hệ.
4. **Tiếp tục công việc:** xem lại lịch sử, sao chép dữ liệu hoặc soạn email từ kênh đã chọn.

## Tính năng

| Công việc | Khả năng |
| --- | --- |
| Khám phá | Tìm video theo từ khóa và kiểm tra kênh bằng YouTube Data API v3 |
| Sàng lọc | Lọc tuổi kênh, tổng lượt xem và liên hệ công khai; bỏ Channel ID đã lưu trong lịch sử |
| Quản lý từ khóa | Chỉnh sửa bảng, thêm/xóa dòng, dán nhiều dòng và nhập `.xlsx`/`.xls` |
| Lưu kết quả | Lịch sử từng lượt quét, bao gồm kết quả một phần khi dừng hoặc gặp lỗi API |
| Xem dữ liệu | Tìm kiếm, sắp xếp, phân trang, xem chi tiết và sao chép |
| Liên hệ | Gmail nhiều tài khoản qua OAuth, lưu nháp, xem lại trước khi gửi và lịch sử gửi |
| Desktop | Giao diện sáng/tối, bố cục co giãn và cập nhật từ GitHub Releases |

Các tính năng trên thuộc desktop React mặc định. CLI và giao diện `--legacy` có luồng xuất Excel riêng, được giữ để tương thích.

## Bắt đầu sử dụng

**Yêu cầu:** Windows 10/11 x64, Microsoft Edge WebView2 Runtime, kết nối Internet và YouTube Data API v3 key còn quota.

1. Tải `gui_app.exe` từ [bản phát hành mới nhất](https://github.com/AzuraDev202/Ytb-Bot/releases/latest).
2. Đặt file vào thư mục có quyền ghi và mở ứng dụng.
3. Nhập API Key, thêm từ khóa, chọn **Bắt đầu khám phá**.
4. Mở **Kết quả** để xem và quản lý các kênh đã lưu.

Bản EXE chạy độc lập, không cần cài Python, Node.js hoặc Microsoft Excel. [Checksum SHA-256](https://github.com/AzuraDev202/Ytb-Bot/releases/latest/download/gui_app.exe.sha256) được cung cấp cùng bản phát hành.

Gửi email cần [thiết lập Gmail OAuth](docs/user/CONTACT_COMPOSER.md) riêng. Với mạng xã hội, ứng dụng hỗ trợ sao chép nội dung và mở hồ sơ để bạn gửi thủ công.

## Dữ liệu và quyền truy cập

- **Từ khóa, kết quả, bản nháp và lịch sử gửi** lưu tại `%LOCALAPPDATA%/Ytb-Bot/data/workspace.sqlite3`.
- **API Key** lưu trong `.env` cạnh EXE hoặc ở gốc dự án khi chạy mã nguồn.
- **Thông tin đăng nhập Gmail** được mã hóa bằng Windows DPAPI theo tài khoản Windows; ứng dụng xin quyền gửi thư và xác định email, không đọc hộp thư.
- **File Excel nhập vào** chỉ được đọc. Desktop mặc định lưu kết quả trong SQLite.
- **Dịch vụ kết nối:** Google cho tìm kiếm, đăng nhập và gửi thư; GitHub cho cập nhật ứng dụng.

Xem [hướng dẫn sao lưu và chẩn đoán](docs/user/DESKTOP_GUIDE.md#dữ-liệu-và-chẩn-đoán). Loại bỏ khóa và thông tin đăng nhập trước khi chia sẻ log hoặc báo lỗi.

## Phạm vi kết quả

YTB-BOT tập trung vào kênh mới đáp ứng bộ lọc và có email hoặc liên kết liên hệ được hỗ trợ trong mô tả công khai. Kết quả phụ thuộc từ khóa, độ sâu tìm kiếm và quota API; không đại diện toàn bộ thị trường, không dự đoán doanh thu hay khả năng viral. Chỉ số đã lưu không tự cập nhật theo thời gian.

Thông tin liên hệ chưa được xác minh khả năng nhận thư. Trạng thái Gmail chấp nhận yêu cầu không bảo đảm email đã đến người nhận.

## Phát triển

Ứng dụng sử dụng React, TypeScript, Python, pywebview / Edge WebView2 và SQLite. Chuẩn bị Python 3.12, Node.js 22.12+ và npm, sau đó chạy tại thư mục dự án:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
npm ci --prefix frontend
npm run build --prefix frontend
python gui_app.py
```

Cấu hình API theo [`.env.example`](.env.example). Hướng dẫn kiểm thử, build và vận hành nằm trong các tài liệu dưới đây:

| Tài liệu | Nội dung |
| --- | --- |
| [Phát triển và kiểm thử](docs/engineering/DEVELOPMENT.md) | Môi trường, lệnh chạy và xác minh |
| [Kiến trúc](docs/engineering/ARCHITECTURE.md) | Cấu trúc và trách nhiệm các phần |
| [Build và phát hành](docs/engineering/RELEASE.md) | Đóng gói EXE, CI và cập nhật |
| [Định hướng sản phẩm](docs/product/COMMERCIALIZATION.md) | Phạm vi và chuẩn bị thương mại hóa |

## Giấy phép

Mã nguồn được phân phối theo [Apache License 2.0](LICENSE).
