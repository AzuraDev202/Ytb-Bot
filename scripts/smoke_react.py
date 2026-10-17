"""Exercise the real native WebView2 window and React/Python bridge."""
from pathlib import Path
import sys
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ytb_bot.desktop.app import main

failures = []


def verify(window):
    done = threading.Event()
    def watchdog():
        if not done.wait(30):
            failures.append("React desktop did not become ready within 30 seconds")
            window.destroy()
    threading.Thread(target=watchdog, daemon=True).start()
    try:
        if not window.events.loaded.wait(20):
            raise AssertionError("WebView document did not load")
        import time
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if window.evaluate_js("document.querySelector('.connection-status')?.textContent === 'Xử lý trên máy'"):
                break
            time.sleep(.2)
        else:
            raise AssertionError("React/Python bridge did not connect")
        assert window.evaluate_js("document.querySelector('textarea') !== null"), "React composer missing"
        if sys.platform == "win32":
            import ctypes
            assert ctypes.windll.user32.IsWindowVisible(ctypes.c_void_p(window.native.Handle.ToInt64())), "Native React window is hidden"
        window.evaluate_js("void window.pywebview.api.start_scan({keywords: []}).then(r => {document.body.dataset.bridgeValidation = String(!r.ok);})")
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if window.evaluate_js("document.body.dataset.bridgeValidation === 'true'"):
                break
            time.sleep(.1)
        else:
            raise AssertionError("Bridge did not validate a request with arguments")
        # Exercise closing on the actual GUI thread: it must not wait for JS.
        confirmation_seen = threading.Event()
        original_confirmation = window.create_confirmation_dialog
        def refuse_close(*args):
            confirmation_seen.set()
            return False
        window.create_confirmation_dialog = refuse_close
        try:
            window._js_api.set_keywords_dirty(True)
            window.destroy()
            assert confirmation_seen.wait(3), "Unsaved keyword close guard was not invoked"
            if sys.platform == "win32":
                assert ctypes.windll.user32.IsWindowVisible(ctypes.c_void_p(window.native.Handle.ToInt64())), "Close guard did not preserve the window"
        finally:
            window._js_api.set_keywords_dirty(False)
            window.create_confirmation_dialog = original_confirmation
        print("PASS: native WebView2 loaded React and connected to Python")
    except Exception as error:
        failures.append(str(error))
    finally:
        done.set()
        window.destroy()


main(verify)
if failures:
    raise SystemExit("; ".join(failures))
