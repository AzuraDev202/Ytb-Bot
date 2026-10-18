# Review toàn dự án — 2026-10-18

Phạm vi: checkout `7367eba`, Python core/desktop/CLI/legacy, React, SQLite, Gmail/OAuth, updater, packaging và CI. Kết hợp góc nhìn ECC production-audit, mattpocock code-review (hành vi so với tài liệu và cấu trúc mã), Superpowers requesting-code-review (review độc lập). Không sửa mã nguồn, không gửi email hoặc gọi YouTube thật.

## Phát hiện cần sửa

### 1. P2 — Mất bản nháp khi lượt quét đổi trạng thái
- Vị trí: `frontend/src/components/ResultsView.tsx:51-67,86`; `ContactComposer.tsx:19,50,71`.
- Trong khi một lượt quét chạy, mở liên hệ từ lịch sử và nhập nội dung chưa lưu. Khi quét hoàn tất/dừng/lỗi, dependency `status` chạy lại effect, `setMeta(null)` tháo WorkbookView và ContactComposer.
- Nội dung chỉ nằm trong state bị mất, không qua hộp xác nhận; cleanup còn xóa cờ dirty phía Python.
- Hướng sửa: giữ composer bên ngoài vòng đời tải bảng hoặc giữ bảng đang mở khi làm mới; bảo vệ bản nháp trước mọi unmount. Thêm regression cho thay đổi scan status khi đang soạn.
- Bằng chứng: xác nhận đường đi qua source; chưa chạy tái hiện UI riêng cho tình huống này.

### 2. P2 — Worker cũ ghi nhầm vào lượt quét mới
- Vị trí: `ytb_bot/core/engine.py:145-155`, `start` thay `_run_id` và `_state`.
- Status được công bố complete trước khi worker vào khối finally lưu cuối. Lượt mới có thể bắt đầu trong khoảng này; worker cũ dùng shared `_run_id` mới và state mới.
- Tái hiện xác định bằng trace tạm dừng worker trước dòng 152 và chặn factory của lượt hai: lượt một vĩnh viễn còn running trong SQLite; worker cũ cũng đặt output=True cho lượt hai.
- Hướng sửa: hoàn tất persistence trước khi công bố trạng thái kết thúc, hoặc gắn run_id/state cục bộ cho từng worker và không cho start khi worker trước còn sống.

### 3. P2 — Hủy đóng cửa sổ khiến updater mắc kẹt
- Vị trí: `ytb_bot/desktop/api.py:264-265`; `ytb_bot/desktop/app.py:41-49`; `ytb_bot/updater.py` helper WaitForExit.
- Kiểm tra dirty chỉ ở đầu tải. Người dùng vẫn sửa từ khóa/soạn thư trong lúc tải. Sau tải, helper được chạy trước window.destroy(); người dùng có thể hủy đóng tại xác nhận unsaved.
- destroy là thao tác có thể bị hủy trong pywebview đã cài. Helper chờ 120 giây rồi lỗi; bridge không nhận kết quả và vẫn giữ downloading, chặn quét/cập nhật đến khi khởi động lại.
- Hướng sửa: phối hợp xác nhận đóng và khởi chạy helper; khóa chỉnh sửa trong giai đoạn cài hoặc kiểm tra lại và trả trạng thái có thể phục hồi khi hủy.
- Bằng chứng: source ứng dụng và implementation pywebview; không chạy thay EXE thật.

### 4. P2 — Giao diện legacy mất kết quả một phần khi API lỗi
- Vị trí: `ytb_bot/legacy_ui/desktop.py:375-399`.
- Export nằm cuối try chứa toàn bộ vòng quét. API/network lỗi ở từ khóa sau sẽ nhảy qua export; finally chỉ cập nhật giao diện. Kênh đã tìm chỉ còn trong RAM và bị mất.
- Hướng sửa: lưu tăng dần hoặc lưu phần đã gom trong đường kết thúc/lỗi, đồng thời phân biệt lỗi quét với lỗi ghi file.
- Bằng chứng: phân tích đường điều khiển; chưa chạy GUI legacy thành công vì Tcl môi trường lỗi.

### 5. P2 — Tiêu đề công khai bị xuất thành công thức Excel
- Vị trí: `ytb_bot/cli/scanner.py:128-129`; `ytb_bot/legacy_ui/desktop.py:382-383`.
- Tên kênh/video từ bên ngoài được ghi thẳng bằng openpyxl. Giá trị bắt đầu `=` thành công thức thay vì văn bản.
- Tái hiện in-memory: `=HYPERLINK("https://example.invalid","Creator")` tạo ô có data_type `f`.
- Hướng sửa: ghi dữ liệu văn bản không tin cậy bằng kiểu string tường minh và kiểm tra lại workbook sau export. Không áp dụng phát hiện này cho bảng SQLite/React vốn không xuất Excel.

### 6. P2 — Hai phiên ứng dụng có thể làm mất hoặc khôi phục tài khoản Gmail đã gỡ
- Vị trí: `ytb_bot/desktop/credential_vault.py:44-48`; `ytb_bot/desktop/outreach.py:64-68,102-111`.
- Lock chỉ có hiệu lực trong một instance. Phiên A đọc kho để refresh; phiên B gỡ tài khoản; A ghi snapshot cũ và khôi phục token đã gỡ. Hai bên còn dùng chung file .tmp nên có thể tranh chấp replace.
- Hướng sửa: interprocess lock bao toàn bộ read-modify-write, hoặc chỉ cho một instance dùng cùng kho.
- Bằng chứng: phân tích đường ghi giữa các process; chưa chạy hai phiên thật.

## Kiểm tra và giới hạn

- `npm run build --prefix frontend`: PASS, TypeScript và Vite build thành công.
- `npm test --prefix frontend`: cả 13 test đã in `ok`; runner bị treo sau các kết quả test và đã được dừng bằng Ctrl+C (exit 1), vì vậy chưa xác nhận toàn tiến trình kết thúc sạch.
- `python -m unittest discover -s tests`: 52 test, FAILED với 8 error. Lỗi khởi tạo Tk/Tcl và một bài Windows credential encryption; không mặc định quy các lỗi này thành bug sản phẩm. Một test có nhiều subtest lỗi nên không suy ra số test pass bằng 52-8.
- Review updater riêng: 11/11 pass; release riêng: 4/4 pass, sử dụng dummy file và mock khởi chạy.
- Chưa xác nhận YouTube quota/API thật, OAuth/Gmail thật hoặc cập nhật EXE thật. Không có tuyên bố chứng nhận an toàn/production-ready.
- Không phát hiện thêm lỗi chắc chắn trong phân trang/import workbook, nhận diện liên hệ và cơ chế claim một revision trước gửi; điều này không bảo đảm không còn lỗi.

Ưu tiên xử lý: mất bản nháp và race worker; tiếp theo updater và toàn vẹn dữ liệu legacy/Excel; sau đó đồng bộ kho tài khoản giữa các process.


## Cập nhật khắc phục — 2026-10-18

Đã sửa cả sáu phát hiện trong báo cáo:

- Composer của lịch sử được giữ bên ngoài vùng bảng bị thay thế khi tải lại; thay đổi trạng thái quét hoặc lỗi lịch sử không làm mất bản nháp và vẫn giữ xác nhận trước khi bỏ thay đổi.
- Scanner không cho lượt mới khởi chạy khi worker cũ chưa thoát, kể cả khi trạng thái đã chuyển hoàn tất.
- Updater chỉ chạy helper sau khi các xác nhận đóng được chấp nhận; hủy đóng trở lại trạng thái có thể thử lại, lỗi handoff giữ cửa sổ mở. Giai đoạn commit chặn gửi thư/chuyển cờ chỉnh sửa mới.
- Legacy lưu kết quả đã gom cả trên đường lỗi API; lỗi ghi file được báo riêng.
- CLI/legacy ghi công thức từ dữ liệu công khai thành chuỗi; xuất qua file tạm rồi thay thế nguyên tử để giữ file cũ khi ghi thất bại.
- Kho Gmail dùng khóa giữa các process cho toàn bộ read-modify-write; thời gian chờ có giới hạn, file tạm riêng, fsync và thay thế nguyên tử. Refresh không ghi đè snapshot cũ lên tài khoản đã gỡ.

Kiểm chứng bản sửa: 61/61 bài Python qua khi chạy ngoài sandbox (bao gồm Tk/Tcl và DPAPI Windows thật); 14/14 Playwright qua và runner thoát sạch; TypeScript/Vite build qua; smoke WebView2 thật qua (bridge Gmail metadata, unsaved/in-flight close guards). Đã thêm regression và quan sát lỗi trước bản sửa; review chéo cuối không tìm thấy lỗi chắc chắn mới. Không gửi email thật, không quét YouTube thật hoặc thay EXE thật. Bản EXE hiện có trong dist chưa được build lại từ thay đổi này.
