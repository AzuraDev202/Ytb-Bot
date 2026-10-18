# Chuẩn bị thương mại hóa YTB-BOT

Tài liệu này là định hướng chuẩn bị, không mô tả gói trả phí đã bán hoặc cam kết chất lượng đã đạt.

## Khách hàng và định vị

Khách hàng ưu tiên đã được chủ sản phẩm chọn: **người nghiên cứu thị trường YouTube**. Định vị là ứng dụng Windows hỗ trợ khám phá kênh theo chủ đề, sàng lọc dữ liệu công khai và tổ chức kết quả nghiên cứu. Mức giá và mô hình bán chưa được chốt.

Giá trị cốt lõi là luồng **chủ đề nghiên cứu → từ khóa → sàng lọc kênh → xem xét chỉ số → lưu và xem lại**, với dữ liệu làm việc lưu trên máy. Liên hệ là chức năng hỗ trợ sau nghiên cứu.

Giới hạn quan trọng của phiên bản hiện tại: scanner chỉ nhận kênh có liên hệ công khai, và bỏ qua kênh đã lưu trong các lượt sau. Điều này phù hợp với khám phá kênh mới nhưng chưa đáp ứng khảo sát thị trường đầy đủ hoặc đo tăng trưởng theo thời gian. Khi giới thiệu sản phẩm, phải nêu rõ giới hạn lấy mẫu này.

## Hiện trạng và kế hoạch

| Hiện có trong mã nguồn | Cần xác lập trước khi kinh doanh |
| --- | --- |
| Desktop Windows, quét và kho dữ liệu cục bộ | Bài toán nghiên cứu ưu tiên, gói giá và phạm vi hỗ trợ |
| API Key do người dùng cung cấp | Trải nghiệm cấu hình key, trách nhiệm quota và thông báo lỗi |
| Gmail OAuth qua JSON người dùng nhập | Onboarding Gmail cho khách hàng và kiểm thử tài khoản đại diện |
| Bản nháp và lịch sử gửi | Quy trình hỗ trợ trường hợp gửi chưa rõ kết quả |
| EXE, checksum và cập nhật GitHub | Phát hành thử, rollback và phân phối cho khách hàng |
| LICENSE hiện tại là Apache 2.0 | Quyết định mô hình phân phối và tài liệu thương mại phù hợp |

Hiện chưa có luồng mua hàng/kích hoạt bản quyền trong trải nghiệm được mô tả ở đây. Không quảng bá thanh toán, đồng bộ đám mây, cộng tác nhóm, thuê bao hoặc SLA như tính năng đã có.

## Các mốc chuẩn bị

### Ưu tiên sản phẩm cho người nghiên cứu

Các mục sau là đề xuất cần thiết kế và xác nhận trước khi triển khai, chưa phải tính năng hiện có:

- Cho phép khảo sát kênh không có liên hệ công khai, đồng thời giữ bộ lọc liên hệ như một tùy chọn.
- Tách khám phá kênh mới khỏi việc cập nhật chỉ số của kênh đã lưu; xác định cách lưu ảnh chụp chỉ số theo thời gian nếu cần đo tăng trưởng.
- Ghi rõ cấu hình và thời điểm khảo sát, phạm vi tìm kiếm và các giới hạn để người nghiên cứu diễn giải kết quả đúng.
- Xác nhận nhu cầu nhóm nghiên cứu theo chủ đề, ghi chú, so sánh và xuất báo cáo bằng phỏng vấn/thử nghiệm với khách hàng mục tiêu.

### 1. Ổn định sản phẩm

- Đối chiếu [báo cáo review ban đầu](../reviews/PROJECT_REVIEW_2026-10-18.md) với mã mới và kiểm thử hồi quy; không coi lỗi đã sửa chỉ vì có commit mới.
- Kiểm thử trên Windows sạch: mở EXE, quét, dừng, lưu/mở lại, soạn/gửi, cập nhật và phục hồi dữ liệu.
- Kiểm tra nhiều phiên ứng dụng, lỗi mạng, quota hết và gửi chưa rõ kết quả.
- Tách kết quả mock khỏi kết quả tích hợp thật trong ghi chú phát hành.

### 2. Giảm công sức thiết lập

- Chọn rõ khách hàng tự quản lý YouTube API Key và Gmail OAuth hay được đội sản phẩm hỗ trợ cấu hình.
- Viết hướng dẫn có ảnh cho lần chạy đầu, kết nối Gmail và xử lý lỗi thông dụng.
- Kiểm tra yêu cầu hiện hành của Google cho phương án OAuth/phân phối được chọn trước khi triển khai rộng; tài liệu này không thay thế việc xác minh đó.

### 3. Chuẩn hóa vận hành thương mại

- Xác lập giá, hình thức bán và cơ chế quyền sử dụng nếu cần; triển khai sau khi mô hình được chốt.
- Công bố phạm vi hỗ trợ, kênh tiếp nhận, xử lý sự cố và chính sách cập nhật.
- Chuẩn bị thông tin quyền riêng tư, điều khoản khách hàng và nội dung giấy phép cho bản phân phối đã chọn; rà soát riêng trước khi công bố.
- Đánh giá ký số Windows, quy trình phát hành và cách khách hàng xác minh nguồn tải.
- Giữ version/build có thể truy vết; EXE, checksum và metadata phải thuộc cùng một lần build.

### 4. Thử nghiệm với khách hàng nhỏ

Mời một nhóm người nghiên cứu thị trường YouTube khảo sát một chủ đề cụ thể: lập từ khóa, lọc kênh, xem xét chỉ số và mở lại kết quả. Đánh giá mức hữu ích của danh sách, khả năng hiểu giới hạn mẫu, thời gian đến kết quả đầu tiên, tỷ lệ hoàn thành thiết lập và nhu cầu hỗ trợ. Chỉ thu thập dữ liệu sử dụng sau khi đã quyết định cơ chế thông báo và quyền lựa chọn phù hợp; hiện không mặc định bổ sung telemetry.

Mở rộng phân phối sau khi xử lý vấn đề từ thử nghiệm và chốt trách nhiệm vận hành. README chuyên nghiệp hỗ trợ bán hàng, nhưng không thay thế kiểm thử và quy trình hỗ trợ.
