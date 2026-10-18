# Liên hệ kênh từ YTB-BOT

Tính năng nằm trong desktop React: **Kết quả → Xem đầy đủ → Soạn liên hệ**. Bot dùng thông tin liên hệ trong lịch sử đã lưu của đúng Channel ID. Không cần tải Excel.

## Gmail / Google Workspace

### Cấu hình Google lần đầu

1. Mở [Google Cloud Console](https://console.cloud.google.com/), tạo/chọn project và bật **Gmail API**. YouTube API Key không thay thế cấu hình Gmail OAuth.
2. Vào **Google Auth Platform**: cấu hình Branding, Audience và Data Access. Cho phép quyền `openid`, `https://www.googleapis.com/auth/userinfo.email` và `https://www.googleapis.com/auth/gmail.send`. Bot không yêu cầu quyền đọc hộp thư.
3. Nếu Audience ở chế độ **Testing**, thêm các địa chỉ sẽ dùng để gửi vào **Test users**. Google có thể yêu cầu xác minh ứng dụng khi phát hành cho nhiều người; Google Workspace có thể cần quản trị viên chấp thuận.
4. Tạo **OAuth Client ID → Desktop app**, tải file JSON. Không chọn loại Web application.
5. Trong hộp soạn, mở **Thiết lập kết nối lần đầu → Nhập file OAuth JSON**, chọn file vừa tải. Không đưa file này lên GitHub.
6. Nhấn **Kết nối Gmail**. Bot mở trình duyệt mặc định để chọn tài khoản Google và cấp quyền. Phiên chờ tối đa 3 phút. Có thể kết nối nhiều tài khoản, sau đó chọn địa chỉ gửi trong danh sách.

Không đăng nhập Google trong WebView của Bot. Luồng OAuth dùng thư viện Google, callback localhost với cổng động, PKCE, kiểm tra state và xác minh danh tính email. Callback không được ghi vào log ứng dụng.

### Soạn và gửi

1. Chọn **Liên hệ nhận** là email đã lưu của kênh.
2. Chọn **Tài khoản gửi** đã kết nối. Địa chỉ From lấy từ tài khoản Google xác minh, không nhập tùy ý.
3. Nhập tiêu đề (tối đa 200 ký tự) và nội dung văn bản (tối đa 50.000 ký tự). Không hỗ trợ tệp đính kèm ở phiên bản này.
4. **Lưu bản nháp** để tiếp tục sau; hoặc **Xem lại email** để lưu và kiểm tra tên kênh, From, To, tiêu đề, nội dung.
5. Nhấn **Gửi email** để gửi trực tiếp qua Gmail API. Mỗi lần chỉ gửi tới một địa chỉ.

Đóng hộp soạn khi có thay đổi sẽ cho chọn lưu, bỏ thay đổi hoặc tiếp tục. Đóng desktop với bản nháp chưa lưu có xác nhận. Cập nhật app bị chặn nếu còn bản nháp chưa lưu hoặc email đang gửi.

### Lịch sử và chống gửi lặp

Lịch sử riêng cho từng Channel ID nằm dưới nội dung soạn, hiển thị tối đa 20 lần gần nhất. Các trạng thái:

- **Gmail đã nhận yêu cầu**: Gmail trả về message ID; không xác nhận thư đã đến người nhận.
- **Gmail từ chối**: API trả lỗi từ chối rõ ràng.
- **Chưa rõ kết quả**: timeout, lỗi mạng hoặc phản hồi không xác định. Kiểm tra thư **Đã gửi** trong Gmail trước khi thử lại.
- **Đang gửi / chưa rõ kết quả**: yêu cầu đang chạy hoặc ứng dụng đã đóng trước khi ghi được phản hồi.

Mỗi phiên bản bản nháp chỉ có một lần gửi, kể cả nhấn lặp hoặc mở lại app. Không tự retry yêu cầu gửi. Muốn gửi lần mới, chỉnh sửa nội dung và lưu thành phiên bản mới rồi xem lại. Lưu nguyên nội dung không tạo phiên bản mới.

## Facebook và liên hệ mạng xã hội

Chọn liên kết đã lưu → soạn văn bản → **Sao chép nội dung** → **Mở liên hệ**. Dán nội dung và gửi trên nền tảng đó bằng tài khoản của bạn. Bot không tự nhắn tin mạng xã hội và không ghi thao tác mở hồ sơ thành email đã gửi.

## Dữ liệu trên máy

- Bản nháp và lịch sử gửi lưu trong `%LOCALAPPDATA%/Ytb-Bot/data/workspace.sqlite3` cùng kho nội bộ. Mỗi kênh có một bản nháp hiện tại.
- Cấu hình OAuth và token lưu tại `%LOCALAPPDATA%/Ytb-Bot/data/mail/credentials.bin`, mã hóa bằng Windows DPAPI theo tài khoản Windows hiện tại; không nằm trong SQLite, `.env`, frontend hoặc EXE.
- Danh sách gửi tới React chỉ gồm mã tài khoản và email, không chứa token hay client secret.
- **Gỡ tài khoản khỏi Bot** xóa thông tin đăng nhập cục bộ. Để thu hồi quyền tại Google, dùng [quản lý kết nối tài khoản Google](https://myaccount.google.com/connections).
- Chức năng bảo vệ đăng nhập hiện hỗ trợ Windows. Khi chưa cấu hình OAuth, vẫn có thể soạn/lưu nháp và dùng thao tác mạng xã hội.

## Kiểm tra và giới hạn xác minh

Kiểm thử Python dùng Gmail giả lập: danh tính OAuth/PKCE, dữ liệu MIME tiếng Việt, mã hóa DPAPI thật, lưu nháp, chống gửi lặp, lỗi mạng và bảo vệ liên kết. Kiểm thử trình duyệt dùng bridge giả lập để kiểm tra soạn/lưu/xem lại/gửi và bố cục hẹp. Không gửi email thật trong tests.

Kiểm tra đăng nhập và gửi thật cần OAuth Client của bạn cùng một hộp thư thử nghiệm do bạn kiểm soát; không dùng địa chỉ kênh để thử nghiệm.

Tài liệu chính thức: [Gmail gửi thư](https://developers.google.com/workspace/gmail/api/guides/sending), [Gmail OAuth cho desktop Python](https://developers.google.com/workspace/gmail/api/quickstart/python), [OAuth cho desktop](https://developers.google.com/identity/protocols/oauth2/native-app).
