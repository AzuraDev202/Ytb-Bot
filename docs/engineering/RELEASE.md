# Phát hành YTB-BOT

## Build tại máy phát triển

Cài môi trường theo [hướng dẫn phát triển](DEVELOPMENT.md), sau đó chạy từ thư mục gốc:

```powershell
python scripts/release/build_release.py
```

Script cài dependency frontend bằng `npm ci`, build React, ghi metadata commit/build, chạy PyInstaller với `packaging/desktop.spec` và tạo checksum. Build Windows EXE trên Windows x64. Dừng Vite và test frontend trước khi build để tránh khóa file dependency.

| Đầu ra | Mục đích |
| --- | --- |
| `dist/gui_app.exe` | Desktop kèm frontend đã build |
| `dist/gui_app.exe.sha256` | SHA-256 của EXE |
| `dist/build-info.json` | Version, commit, thời điểm build và SHA-256 |

Không đóng gói `.env`, OAuth JSON hoặc kho đăng nhập. Chạy các [kiểm tra trước phát hành](DEVELOPMENT.md#kiểm-tra-trước-phát-hành), gồm smoke của EXE đã build. Không phát hành artifact từ một lần build chưa qua kiểm tra.

## Phát hành tự động

[Workflow](../../.github/workflows/release.yml) chạy khi push lên `main`, push tag `v*` hoặc chạy thủ công. Repo/Releases cần công khai để app tải cập nhật mà không nhúng GitHub token vào EXE.

- Giữ version cho thay đổi nhỏ, sửa lỗi và sắp xếp file; push `main` sẽ thay asset của Release cùng version.
- Khi có thay đổi lớn cần version mới, sửa `ytb_bot/version.py` theo định dạng `X.Y.Z`. Nếu dùng tag, tag phải khớp `vX.Y.Z`.
- Version thấp hơn không được phát hành; push lại tag bằng version hiện tại không ghi đè build từ `main`.
- Workflow kiểm thử Python, build React/EXE, test UI, bridge và cửa sổ EXE trước khi publish.
- Asset gồm `gui_app.exe`, `gui_app.exe.sha256` và `build-info.json`.

Không commit file build hoặc khóa thật. Khi phát hành thủ công, giữ EXE, checksum và metadata từ cùng một lần build. Trước khi phân phối rộng, kiểm tra cập nhật giữa hai EXE trên Windows và xác nhận dữ liệu cục bộ vẫn còn.

