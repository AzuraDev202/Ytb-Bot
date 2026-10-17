"""Narrow JSON bridge exposed only to the bundled React desktop document."""
from functools import wraps
import json
import os
import threading
import webbrowser
from urllib.parse import urlparse

from dotenv import dotenv_values, set_key

from ytb_bot.build_info import build_id
from ytb_bot.core.engine import ScanEngine
from ytb_bot.paths import APP_DIR, ENV_FILE
from ytb_bot.version import APP_VERSION
from ytb_bot.core.workbook import Workbook
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
    def __init__(self):
        self._window = None
        self._key = os.getenv("YOUTUBE_API_KEY") or dotenv_values(ENV_FILE).get("YOUTUBE_API_KEY", "")
        self._scan = ScanEngine(APP_DIR)
        self._book = Workbook()
        self._lock = threading.RLock()
        self._release = None
        self._update = {"status": "idle", "message": "Kiểm tra bản cập nhật khi bạn cần.", "progress": 0}

    @reply
    def get_bootstrap(self):
        try:
            preferences = json.loads((APP_DIR / "studio-settings.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            preferences = {}
        return {"version": APP_VERSION, "build": build_id(), "has_api_key": bool(self._key),
                "preferences": preferences if isinstance(preferences, dict) else {}}

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
    def open_results(self):
        path = APP_DIR / "danh_sach_kenh_viral_moi.xlsx"
        if not path.exists():
            raise ValueError("Chưa có file kết quả. Hãy chạy quét trước.")
        return self._book.open(path)

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
                install_update(staged)
                self._window.destroy()
            except Exception as error:
                if staged:
                    staged.unlink(missing_ok=True)
                with self._lock:
                    self._update.update(status="error", message=str(error))
        threading.Thread(target=install, daemon=True).start()
        return True
