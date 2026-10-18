"""Exercise the real native WebView2 window and React/Python bridge."""
from pathlib import Path
import sys
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
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
            if window.evaluate_js("document.querySelector('.connection-status.connected') !== null"):
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
        window.evaluate_js("void window.pywebview.api.get_mail_state().then(r => {document.body.dataset.mailReady = String(r.ok && Array.isArray(r.data.accounts) && !JSON.stringify(r).includes('refresh_token'));})")
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if window.evaluate_js("document.body.dataset.mailReady === 'true'"):
                break
            time.sleep(.1)
        else:
            raise AssertionError('Native Gmail state bridge did not return public account metadata')
        # Exercise closing on the actual GUI thread: it must not wait for JS.
        confirmation_seen = threading.Event()
        original_confirmation = window.create_confirmation_dialog
        original_language = window._js_api._language
        captured = []
        def refuse_close(*args):
            captured.append(args)
            confirmation_seen.set()
            return False
        window.create_confirmation_dialog = refuse_close
        try:
            for language, title in [('en', 'Unsaved keywords'), ('vi', 'Từ khóa chưa lưu'), ('zh-CN', '未保存的关键词')]:
                window._js_api._language = language
                confirmation_seen.clear()
                window._js_api.set_keywords_dirty(True)
                window.destroy()
                assert confirmation_seen.wait(3), "Unsaved keyword close guard was not invoked"
                assert captured[-1][0] == title, 'Native close confirmation used the wrong language'
            window._js_api._language = original_language
            if sys.platform == "win32":
                assert ctypes.windll.user32.IsWindowVisible(ctypes.c_void_p(window.native.Handle.ToInt64())), "Close guard did not preserve the window"
            window._js_api.set_keywords_dirty(False)
            confirmation_seen.clear()
            window._js_api.set_contact_dirty(True)
            window.destroy()
            assert confirmation_seen.wait(3), 'Unsaved contact draft close guard was not invoked'
            window._js_api.set_contact_dirty(False)
            confirmation_seen.clear()
            window._js_api._contact_sending = True
            window.destroy()
            assert confirmation_seen.wait(3), 'In-flight email close guard was not invoked'
        finally:
            window._js_api._language = original_language
            window._js_api.set_keywords_dirty(False)
            window._js_api.set_contact_dirty(False)
            window._js_api._contact_sending = False
            window.create_confirmation_dialog = original_confirmation
        print("PASS: native WebView2 loaded React, Gmail metadata bridge, three-language close prompts and unsaved/in-flight guards")
    except Exception as error:
        failures.append(str(error))
    finally:
        done.set()
        window.destroy()


main(verify)
if failures:
    raise SystemExit("; ".join(failures))
