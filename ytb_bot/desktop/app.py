"""Native Edge WebView2 window hosting the bundled React application."""
import ctypes
import logging
import os
from pathlib import Path
import sys

from ytb_bot.build_info import build_id
from ytb_bot.desktop.api import DesktopAPI
from ytb_bot.version import APP_VERSION
from ytb_bot.paths import PROJECT_ROOT


def main(on_started=None):
    log_dir = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "Ytb-Bot" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=log_dir / "desktop.log", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    try:
        import webview
        root = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT))
        document = root / "frontend" / "web-dist" / "index.html"
        if not document.exists():
            raise RuntimeError("React has not been built. Run npm ci --prefix frontend and npm run build --prefix frontend.")
        api = DesktopAPI()
        width, height = 1180, 800
        if os.name == "nt":
            from ctypes import wintypes
            area = wintypes.RECT()
            if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(area), 0):
                dpi = ctypes.windll.user32.GetDpiForSystem() / 96
                width = min(width, max(320, int((area.right - area.left) / dpi) - 48))
                height = min(height, max(320, int((area.bottom - area.top) / dpi) - 64))
        window = webview.create_window(f"Ytb-Bot · v{APP_VERSION} · React · {build_id()}", str(document),
            js_api=api, width=width, height=height, min_size=(min(760, width), min(560, height)), hidden=False,
            background_color="#0c1018", text_select=True)
        api._window = window

        def confirm_closing():
            # Closing runs on the WinForms thread: never wait for JavaScript here.
            if api._contact_sending and not window.create_confirmation_dialog('Sending email', 'Gmail is processing the request. Closing now may leave the result unknown. Close anyway?'):
                return False
            if api._contact_dirty and not window.create_confirmation_dialog('Unsaved contact', 'The contact draft has unsaved changes. Closing the app will discard them. Close anyway?'):
                return False
            if api._keywords_dirty and not window.create_confirmation_dialog("Unsaved keywords", "The keyword table has unsaved changes. Closing the app will discard them. Close anyway?"):
                return False
            if api._scan.snapshot()["status"] in ("running", "stopping"):
                if not window.create_confirmation_dialog("Close YTB-BOT", "The scan is still running. Closing now may lose unsaved results. Close anyway?"):
                    return False
                api._scan.stop()
            return True

        def closing():
            # Serialize confirmation and update handoff with new sends/edits.
            with api._lock:
                return api._finish_update_close(confirm_closing())

        window.events.closing += closing
        def reveal():
            # A windowed EXE can inherit SW_HIDE from its launcher. WinForms
            # raises Shown even then; explicitly show the already-created HWND.
            if os.name == "nt":
                handle = ctypes.c_void_p(window.native.Handle.ToInt64())
                ctypes.windll.user32.ShowWindow(handle, 5)
                ctypes.windll.user32.SetForegroundWindow(handle)
        window.events.shown += reveal
        logging.info("Starting React desktop build %s", build_id())
        webview.start(on_started, (window,) if on_started else None,
                      gui="edgechromium" if os.name == "nt" else None, http_server=True)
    except Exception:
        logging.exception("Desktop startup failed")
        if os.name == "nt":
            ctypes.windll.user32.MessageBoxW(None,
                f"Could not open YTB-BOT. Check the Microsoft Edge WebView2 Runtime.\nDetails: {log_dir / 'desktop.log'}", "YTB-BOT", 0x10)
        raise
