"""Narrow JSON bridge exposed only to the bundled React desktop document."""
from functools import wraps
import json
import os
from pathlib import Path
import threading
import tempfile
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
from ytb_bot.desktop.bulk import BulkOutreach
from ytb_bot.desktop.facebook_outreach import FacebookOutreach
from ytb_bot.desktop.localization import SUPPORTED_LANGUAGES, translate_message
from ytb_bot.updater import check_for_update, download_update, install_update

def read_preferences():
    try:
        value = json.loads((APP_DIR / 'studio-settings.json').read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        value = {}
    preferences = value if isinstance(value, dict) else {}
    if preferences.get('language') not in SUPPORTED_LANGUAGES:
        preferences['language'] = 'en'
    return preferences


def reply(method):
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        try:
            return {"ok": True, "data": method(self, *args, **kwargs)}
        except Exception as error:
            text = str(error)
            if self._key:
                text = text.replace(self._key, "<API_KEY>")
            return {"ok": False, "error": self._translate(text)}
    return wrapped


class DesktopAPI:
    def __init__(self, data_dir=None):
        self._window = None
        self._keywords_dirty = False
        self._contact_dirty = False
        self._contact_sending = False
        self._facebook_sending = False
        self._bulk_dirty = False
        self._key = os.getenv("YOUTUBE_API_KEY") or dotenv_values(ENV_FILE).get("YOUTUBE_API_KEY", "")
        self._store = WorkspaceStore(Path(data_dir or DATA_DIR) / "workspace.sqlite3")
        self._scan = ScanEngine(APP_DIR, store=self._store)
        self._book = Workbook()
        self._outreach = Outreach(self._store.path)
        self._bulk = BulkOutreach(self._outreach)
        self._facebook = FacebookOutreach(self._store.path)
        self._facebook_dirty = False
        self._lock = threading.RLock()
        self._language = read_preferences()['language']
        self._release = None
        self._staged_update = None
        self._update_committing = False
        self._update = {"status": "idle", "message": "Check for updates whenever you need.", "progress": 0}

    @reply
    def get_bootstrap(self):
        with self._lock:
            preferences = {**read_preferences(), 'language': self._language}
        return {"version": APP_VERSION, "build": build_id(), "has_api_key": bool(self._key),
                "preferences": preferences, "keywords": self._store.keywords()}

    def _translate(self, message):
        return translate_message(message, self._language)

    def _save_preferences(self, changes):
        preferences = {**read_preferences(), **changes}
        descriptor, name = tempfile.mkstemp(prefix='.studio-settings-', suffix='.tmp', dir=APP_DIR)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
                json.dump(preferences, output, ensure_ascii=False)
                output.flush()
                os.fsync(output.fileno())
            temporary.replace(APP_DIR / 'studio-settings.json')
        finally:
            temporary.unlink(missing_ok=True)

    @reply
    def set_language(self, language):
        if language not in SUPPORTED_LANGUAGES:
            raise ValueError('Unsupported language.')
        with self._lock:
            if self._update_committing:
                raise ValueError('The app is restarting to install an update.')
            self._save_preferences({'language': language})
            self._language = language
        return True

    def _localized_mail_state(self, state):
        return {**state, 'error': self._translate(state['error'])}

    @reply
    def save_keywords(self, text):
        return self._store.save_keywords(text)

    @reply
    def set_keywords_dirty(self, dirty):
        if not isinstance(dirty, bool):
            raise ValueError("Invalid editing state.")
        with self._lock:
            if self._update_committing:
                raise ValueError('The app is restarting to install an update.')
            self._keywords_dirty = dirty
        return True

    @reply
    def list_results(self):
        return [{**run, 'error': self._translate(run['error'])} for run in self._store.runs()]

    @reply
    def email_contact_history(self):
        from ytb_bot.core.email_history import email_records
        with self._store._connection() as db:
            return email_records(db)

    @reply
    def clear_scan_history(self):
        with self._lock:
            self._scan.clear_history()
        return True

    @reply
    def get_mail_state(self):
        return self._localized_mail_state(self._outreach.state())

    @reply
    def contact_groups(self):
        return self._bulk.groups()

    @reply
    def facebook_state(self):
        return self._facebook.state()

    @reply
    def connect_facebook(self, token):
        return self._facebook.connect(token)

    @reply
    def disconnect_facebook(self, page_id):
        return self._facebook.disconnect(page_id)

    @reply
    def facebook_conversations(self, page_id):
        return self._facebook.conversations(page_id)

    @reply
    def bind_facebook_contact(self, channel_id, page_id, conversation_id, recipient_id):
        return self._facebook.bind(channel_id, page_id, conversation_id, recipient_id)

    @reply
    def prepare_facebook_message(self, channel_id, payload):
        return self._facebook.prepare(channel_id, payload)

    @reply
    def facebook_history(self, channel_id):
        return self._facebook.history(channel_id)

    @reply
    def set_facebook_dirty(self, dirty):
        if not isinstance(dirty, bool):
            raise ValueError('Invalid draft state.')
        with self._lock:
            if self._update_committing:
                raise ValueError('The app is restarting to install an update.')
            self._facebook_dirty = dirty
        return True

    @reply
    def send_facebook_message(self, draft_id):
        with self._lock:
            self._check_bulk_start()
            self._contact_sending = True
            self._facebook_sending = True
        try:
            return self._facebook.send(draft_id)
        finally:
            with self._lock:
                self._contact_sending = False
                self._facebook_sending = False

    @reply
    def prepare_bulk_mail(self, payload):
        with self._lock:
            self._check_bulk_start()
            result = self._bulk.prepare(payload)
            self._bulk_dirty = False
            return result

    def _check_bulk_start(self):
        if self._update_committing or self._update['status'] == 'downloading':
            raise ValueError('Wait for the update to finish before sending mail.')
        if self._contact_sending or self._bulk.is_running:
            raise ValueError('A mail send is already running. Wait for its result.')

    @reply
    def start_bulk_mail(self, batch_id):
        with self._lock:
            self._check_bulk_start()
            if self._bulk_dirty:
                raise ValueError('Review the bulk email draft before sending.')
            return self._bulk.start(batch_id)

    @reply
    def stop_bulk_mail(self, batch_id):
        return self._bulk.stop(batch_id)

    @reply
    def get_bulk_mail(self, batch_id=None):
        return self._bulk.get(batch_id)

    @reply
    def list_bulk_mail(self):
        return self._bulk.list()

    @reply
    def set_bulk_dirty(self, dirty):
        if not isinstance(dirty, bool):
            raise ValueError('Invalid draft state.')
        with self._lock:
            if self._update_committing:
                raise ValueError('The app is restarting to install an update.')
            self._bulk_dirty = dirty
        return True

    @reply
    def configure_gmail(self):
        import webview
        paths = self._window.create_file_dialog(webview.FileDialog.OPEN, allow_multiple=False,
                                               file_types=('Google OAuth Desktop (*.json)',))
        return self._localized_mail_state(self._outreach.configure(paths[0])) if paths else None

    @reply
    def connect_gmail(self):
        return self._outreach.connect()

    @reply
    def disconnect_gmail(self, account_id):
        return self._localized_mail_state(self._outreach.disconnect(account_id))

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
            raise ValueError('Invalid draft state.')
        with self._lock:
            if self._update_committing:
                raise ValueError('The app is restarting to install an update.')
            self._contact_dirty = dirty
        return True

    @reply
    def send_contact_mail(self, channel_id, revision):
        with self._lock:
            if self._bulk.is_running:
                raise ValueError('A mail send is already running. Wait for its result.')
            if self._update_committing:
                raise ValueError('The app is restarting to install an update.')
            if self._contact_sending:
                raise ValueError('An email is being sent. Please wait for the result.')
            self._contact_sending = True
        try:
            result = self._outreach.send(channel_id, revision)
            return {**result, 'message': self._translate(result['message'])}
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
            raise ValueError("Invalid display preferences.")
        with self._lock:
            self._save_preferences({'theme': theme, 'motion': motion})
        return True

    @reply
    def get_state(self):
        with self._lock:
            state = self._scan.snapshot()
            return {**state, 'error': self._translate(state['error']),
                    'logs': [{**log, 'text': self._translate(log['text'])} for log in state['logs']],
                    'update': {**self._update, 'message': self._translate(self._update['message'])}}

    @reply
    def start_scan(self, settings):
        with self._lock:
            if self._update["status"] == "downloading":
                raise ValueError("Wait for the update to finish before scanning.")
            key = str(settings.get("api_key", "")).strip() or self._key
            words = settings.get("keywords", [])
            if not isinstance(words, list) or not all(isinstance(word, str) for word in words):
                raise ValueError("Invalid keyword list.")
            # Validate before changing the saved secret or creating a worker.
            days, views, pages = (int(settings.get(name, default)) for name, default in
                                 [("max_days", 90), ("min_views", 500), ("max_pages", 2)])
            if not key or not any(word.strip() for word in words):
                raise ValueError("Enter an API key and at least one keyword.")
            if days < 1 or views < 0 or not 1 <= pages <= 5:
                raise ValueError("Channel age must be at least 1 day, views at least 0, and depth between 1 and 5 pages.")
            if self._scan.snapshot()["status"] in ("running", "stopping"):
                raise ValueError("A scan is already running.")
            budget = int(settings.get("search_budget", 50))
            if not 1 <= budget <= 10000:
                raise ValueError("Search budget must be between 1 and 10000 calls.")
            if settings.get("api_key", "").strip():
                set_key(ENV_FILE, "YOUTUBE_API_KEY", key)
                self._key = key
            self._scan.start(key, words, days, views, pages, budget)
            return True

    @reply
    def resume_scan(self, settings):
        with self._lock:
            if self._update["status"] == "downloading":
                raise ValueError("Wait for the update to finish before scanning.")
            self._scan.resume(str(settings.get("api_key", "")).strip() or self._key,
                              int(settings.get("search_budget", 50)))
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
        meta = Workbook().from_rows(run["rows"], f"Scan #{run['id']}", columns=[
            "Channel Name", "Channel ID", "Channel URL", "Search Keyword", "Created Date", "Channel Age (Days)",
            "Subscribers", "Total Views", "Total Videos", "Latest Video", "Country", *CONTACT_COLUMNS])
        return {**meta, "run_id": run["id"]}

    @reply
    def results_page(self, sheet, query="", page=0, sort=None, descending=False):
        run = self._store.result(int(sheet.rsplit("#", 1)[1]))
        book = Workbook()
        book.from_rows(run["rows"], sheet, columns=[
            "Channel Name", "Channel ID", "Channel URL", "Search Keyword", "Created Date", "Channel Age (Days)",
            "Subscribers", "Total Views", "Total Videos", "Latest Video", "Country", *CONTACT_COLUMNS])
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
            raise ValueError("Only HTTPS YouTube channel URLs can be opened.")
        webbrowser.open(url)
        return True

    @reply
    def check_updates(self):
        with self._lock:
            if self._update["status"] in ("checking", "downloading"):
                return False
            self._update = {"status": "checking", "message": "Checking…", "progress": 0}

        def check():
            try:
                release = check_for_update()
                with self._lock:
                    self._release = release
                    self._update.update(status="available" if release else "current",
                                        message=f"Update available: v{release.version}" if release else "You are using the latest version.")
            except Exception as error:
                with self._lock:
                    self._update.update(status="error", message=str(error))
        threading.Thread(target=check, daemon=True).start()
        return True

    @reply
    def install_available_update(self):
        with self._lock:
            if self._facebook_dirty:
                raise ValueError('Finish the Messenger draft before updating.')
            if self._bulk.is_running or self._bulk_dirty:
                raise ValueError('Finish the bulk send and save its draft before updating.')
            if self._keywords_dirty:
                raise ValueError("Save the keyword table before updating and restarting.")
            if self._contact_dirty:
                raise ValueError('Save the contact draft before updating and restarting.')
            if self._contact_sending:
                raise ValueError('Wait for Gmail to return the send result before updating.')
            if self._scan.snapshot()["status"] in ("running", "stopping"):
                raise ValueError("Wait for the scan to finish before updating.")
            if not self._release or self._update["status"] == "downloading":
                raise ValueError("Check for updates first.")
            release = self._release
            self._update.update(status="downloading", message="Downloading update…", progress=0)

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
                                    message='Restart canceled. You can update again when ready.')
                return False
            try:
                self._update_committing = True
                install_update(staged, language=self._language)
            except Exception as error:
                self._update_committing = False
                staged.unlink(missing_ok=True)
                self._update.update(status='error', message=str(error))
                return False
            finally:
                self._staged_update = None
            return True
