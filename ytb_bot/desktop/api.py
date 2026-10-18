"""Narrow JSON bridge exposed only to the bundled React desktop document."""
from functools import wraps
import json
import os
from pathlib import Path
import threading
import webbrowser
from urllib.parse import urlparse

from dotenv import dotenv_values, set_key

from ytb_bot.build_info import build_id
from ytb_bot.core.engine import ScanEngine
from ytb_bot.core.contacts import CONTACT_COLUMNS
from ytb_bot.paths import APP_DIR, ENV_FILE, DATA_DIR
from ytb_bot.version import APP_VERSION
from ytb_bot.core.workbook import Workbook
from ytb_bot.core.storage import WorkspaceStore
from ytb_bot.desktop.outreach import Outreach
from ytb_bot.updater import check_for_update, download_update, install_update


def reply(method):
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        try:
            return {"ok": True, "data": method(self, *args, **kwargs)}
        except Exception as error:
            text = str(error)
            if self._key:
                text = text.replace(self._key, "<API_KEY>")
            return {"ok": False, "error": text}
    return wrapped


class DesktopAPI:
    def __init__(self, data_dir=None):
        self._window = None
        self._keywords_dirty = False
        self._contact_dirty = False
        self._contact_sending = False
        self._key = os.getenv("YOUTUBE_API_KEY") or dotenv_values(ENV_FILE).get("YOUTUBE_API_KEY", "")
        self._store = WorkspaceStore(Path(data_dir or DATA_DIR) / "workspace.sqlite3")
        self._scan = ScanEngine(APP_DIR, store=self._store)
        self._book = Workbook()
        self._outreach = Outreach(self._store.path)
        self._lock = threading.RLock()
        self._release = None
        self._staged_update = None
        self._update_committing = False
        self._update = {"status": "idle", "message": "Kiểm tra bản cập nhật khi bạn cần.", "progress": 0}

    @reply
    def get_bootstrap(self):
        try:
            preferences = json.loads((APP_DIR / "studio-settings.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            preferences = {}
        return {"version": APP_VERSION, "build": build_id(), "has_api_key": bool(self._key),
                "preferences": preferences if isinstance(preferences, dict) else {}, "keywords": self._store.keywords()}

    @reply
    def save_keywords(self, text):
        return self._store.save_keywords(text)

    @reply
    def set_keywords_dirty(self, dirty):
        if not isinstance(dirty, bool):
            raise ValueError("Trạng thái chỉnh sửa không hợp lệ.")
        with self._lock:
            if self._update_committing:
                raise ValueError('Ứng dụng đang khởi động lại để cập nhật.')
            self._keywords_dirty = dirty
        return True

    @reply
    def list_results(self):
        return self._store.runs()

    @reply
    def get_mail_state(self):
        return self._outreach.state()

    @reply
    def configure_gmail(self):
        import webview
        paths = self._window.create_file_dialog(webview.FileDialog.OPEN, allow_multiple=False,
                                               file_types=('Google OAuth Desktop (*.json)',))
        return self._outreach.configure(paths[0]) if paths else None

    @reply
    def connect_gmail(self):
        return self._outreach.connect()

    @reply
    def disconnect_gmail(self, account_id):
        return self._outreach.disconnect(account_id)

    @reply
    def contact_context(self, channel_id):
        return self._outreach.context(channel_id)

    @reply
    def save_contact_draft(self, channel_id, payload):
        result = self._outreach.save(channel_id, payload)
        self._contact_dirty = False
        return result

    @reply
    def set_contact_dirty(self, dirty):
        if not isinstance(dirty, bool):
            raise ValueError('Trạng thái bản nháp không hợp lệ.')
        with self._lock:
            if self._update_committing:
                raise ValueError('Ứng dụng đang khởi động lại để cập nhật.')
            self._contact_dirty = dirty
        return True

    @reply
    def send_contact_mail(self, channel_id, revision):
        with self._lock:
            if self._update_committing:
                raise ValueError('Ứng dụng đang khởi động lại để cập nhật.')
            if self._contact_sending:
                raise ValueError('Một email đang được gửi. Hãy chờ kết quả.')
            self._contact_sending = True
        try:
            return self._outreach.send(channel_id, revision)
        finally:
            with self._lock:
                self._contact_sending = False

    @reply
    def open_gmail_setup(self):
        return webbrowser.open('https://developers.google.com/workspace/gmail/api/quickstart/python#configure_the_oauth_consent_screen')

    @reply
    def open_social_contact(self, channel_id, target):
        return self._outreach.open_social(channel_id, target)

    @reply
    def save_preferences(self, theme, motion):
        if theme not in ("dark", "light") or not isinstance(motion, bool):
            raise ValueError("Tùy chọn giao diện không hợp lệ.")
        with self._lock:
            path = APP_DIR / "studio-settings.json"
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps({"theme": theme, "motion": motion}), encoding="utf-8")
            temporary.replace(path)
        return True

    @reply
    def get_state(self):
        with self._lock:
            return {**self._scan.snapshot(), "update": dict(self._update)}

    @reply
    def start_scan(self, settings):
        with self._lock:
            if self._update["status"] == "downloading":
                raise ValueError("Hãy chờ cập nhật hoàn tất trước khi quét.")
            key = str(settings.get("api_key", "")).strip() or self._key
            words = settings.get("keywords", [])
            if not isinstance(words, list) or not all(isinstance(word, str) for word in words):
                raise ValueError("Danh sách từ khóa không hợp lệ.")
            # Validate before changing the saved secret or creating a worker.
            days, views, pages = (int(settings.get(name, default)) for name, default in
                                 [("max_days", 90), ("min_views", 500), ("max_pages", 2)])
            if not key or not any(word.strip() for word in words):
                raise ValueError("Nhập API Key và ít nhất một từ khóa.")
            if days < 1 or views < 0 or not 1 <= pages <= 5:
                raise ValueError("Tuổi kênh từ 1, lượt xem từ 0, độ sâu từ 1 đến 5 trang.")
            if self._scan.snapshot()["status"] in ("running", "stopping"):
                raise ValueError("Một lượt quét đang chạy.")
            if settings.get("api_key", "").strip():
                set_key(ENV_FILE, "YOUTUBE_API_KEY", key)
                self._key = key
            self._scan.start(key, words, days, views, pages)
            return True

    @reply
    def stop_scan(self):
        self._scan.stop()
        return True

    @reply
    def clear_logs(self):
        self._scan.clear_logs()
        return True

    @reply
    def open_workbook(self):
        import webview
        paths = self._window.create_file_dialog(webview.FileDialog.OPEN, allow_multiple=False,
                                               file_types=("Excel (*.xlsx;*.xls)",))
        return self._book.open(paths[0]) if paths else None

    @reply
    def open_results(self, run_id=None):
        run = self._store.result(run_id)
        meta = Workbook().from_rows(run["rows"], f"Lượt quét #{run['id']}", columns=[
            "Tên Kênh", "Channel ID", "URL Kênh", "Từ Khóa Quét", "Ngày Tạo", "Tuổi Kênh (Ngày)",
            "Subscribers", "Tổng Lượt Xem", "Tổng Video", "Video Gần Nhất", "Quốc Gia", *CONTACT_COLUMNS])
        return {**meta, "run_id": run["id"]}

    @reply
    def results_page(self, sheet, query="", page=0, sort=None, descending=False):
        run = self._store.result(int(sheet.rsplit("#", 1)[1]))
        book = Workbook()
        book.from_rows(run["rows"], sheet, columns=[
            "Tên Kênh", "Channel ID", "URL Kênh", "Từ Khóa Quét", "Ngày Tạo", "Tuổi Kênh (Ngày)",
            "Subscribers", "Tổng Lượt Xem", "Tổng Video", "Video Gần Nhất", "Quốc Gia", *CONTACT_COLUMNS])
        return book.page(sheet, query, page, sort, descending)

    @reply
    def workbook_page(self, sheet, query="", page=0, sort=None, descending=False):
        return self._book.page(sheet, query, page, sort, descending)

    @reply
    def import_keywords(self, sheet, column):
        return self._book.keywords(sheet, column)

    @reply
    def open_channel(self, url):
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in ("www.youtube.com", "youtube.com"):
            raise ValueError("Chỉ mở địa chỉ kênh YouTube HTTPS.")
        webbrowser.open(url)
        return True

    @reply
    def check_updates(self):
        with self._lock:
            if self._update["status"] in ("checking", "downloading"):
                return False
            self._update = {"status": "checking", "message": "Đang kiểm tra…", "progress": 0}

        def check():
            try:
                release = check_for_update()
                with self._lock:
                    self._release = release
                    self._update.update(status="available" if release else "current",
                                        message=f"Có bản cập nhật v{release.version}" if release else "Bạn đang dùng bản mới nhất.")
            except Exception as error:
                with self._lock:
                    self._update.update(status="error", message=str(error))
        threading.Thread(target=check, daemon=True).start()
        return True

    @reply
    def install_available_update(self):
        with self._lock:
            if self._keywords_dirty:
                raise ValueError("Lưu bảng từ khóa trước khi cập nhật và khởi động lại.")
            if self._contact_dirty:
                raise ValueError('Lưu bản nháp liên hệ trước khi cập nhật và khởi động lại.')
            if self._contact_sending:
                raise ValueError('Chờ Gmail trả kết quả gửi trước khi cập nhật.')
            if self._scan.snapshot()["status"] in ("running", "stopping"):
                raise ValueError("Chờ lượt quét hoàn tất trước khi cập nhật.")
            if not self._release or self._update["status"] == "downloading":
                raise ValueError("Hãy kiểm tra bản cập nhật trước.")
            release = self._release
            self._update.update(status="downloading", message="Đang tải bản cập nhật…", progress=0)

        def progress(value):
            with self._lock:
                self._update["progress"] = value

        def install():
            staged = None
            try:
                staged = download_update(release, progress)
                with self._lock:
                    self._staged_update = staged
                self._window.destroy()
            except Exception as error:
                if staged:
                    staged.unlink(missing_ok=True)
                with self._lock:
                    self._staged_update = None
                    self._update.update(status="error", message=str(error))
        threading.Thread(target=install, daemon=True).start()
        return True

    def _finish_update_close(self, allowed):
        """Called under the close handler's lock, after all confirmations."""
        with self._lock:
            staged = self._staged_update
            if staged is None:
                return allowed
            if not allowed:
                staged.unlink(missing_ok=True)
                self._staged_update = None
                self._update.update(status='available', progress=0,
                                    message='Đã hủy khởi động lại. Bạn có thể cập nhật lại khi sẵn sàng.')
                return False
            try:
                self._update_committing = True
                install_update(staged)
            except Exception as error:
                self._update_committing = False
                staged.unlink(missing_ok=True)
                self._update.update(status='error', message=str(error))
                return False
            finally:
                self._staged_update = None
            return True
