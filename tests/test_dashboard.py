"""Desktop interactions and cancellation with deterministic YouTube responses."""
import datetime
import gc
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from ytb_bot.legacy_ui.desktop import YtbBotApp


@unittest.skipUnless(os.name == "nt", "Windows desktop GUI")
class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.check_patch = patch.object(YtbBotApp, "check_updates")
        self.check_patch.start()
        self.app = YtbBotApp()
        self.app.view.motion.set(False)

    def tearDown(self):
        for timer in self.app.tk.splitlist(self.app.tk.call("after", "info")):
            self.app.tk.call("after", "cancel", timer)
        self.app.destroy()
        self.app = None
        self.check_patch.stop()
        gc.collect()  # Finalize Tcl variables on the GUI thread, not a later Excel worker.

    def test_first_mainloop_shows_window_and_theme_change_keeps_it_visible(self):
        observations = []

        def change_theme():
            observations.append((self.app.state(), self.app.winfo_viewable()))
            self.app.view.change_theme("Sáng")
            self.app.after(250, finish)

        def finish():
            observations.append((self.app.state(), self.app.winfo_viewable()))
            self.app.quit()

        self.app.after(300, change_theme)
        self.app.after(3000, self.app.quit)
        # Do not call update() or deiconify(): those mask CTk's first-mainloop path.
        self.app.mainloop()
        self.assertEqual(observations, [("normal", 1), ("normal", 1)])

    def test_presets_counter_theme_and_inline_validation(self):
        view = self.app.view
        view.kw_textbox.delete("1.0", "end")
        view.add_keywords(["AI", "AI", "video"])
        self.assertEqual(view.keywords(), ["AI", "video"])
        self.assertEqual(view.stat_values["keywords"].cget("text"), "2")
        view.api_entry.delete(0, "end")
        with patch("ytb_bot.legacy_ui.desktop.set_key") as save:
            self.app.start_scan_thread()
            self.assertIn("API Key", view.form_error.cget("text"))
            save.assert_not_called()
        view.api_entry.insert(0, "test-api-key")
        view.max_age_entry.delete(0, "end")
        view.max_age_entry.insert(0, "-3")
        with patch("ytb_bot.legacy_ui.desktop.set_key") as save:
            self.app.start_scan_thread()
            self.assertIn("Tuổi kênh", view.form_error.cget("text"))
            save.assert_not_called()
        view.set_progress(0.5)
        self.assertEqual(view.progress_label.cget("text"), "50%")
        view.change_theme("Sáng")
        self.app.update()
        self.assertEqual(view.keywords(), ["AI", "video"])
        view.change_theme("Tối")

    def test_resize_hides_filters_and_keeps_them_accessible(self):
        self.app.geometry("920x640")
        view = self.app.view
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            self.app.update()
            if view._narrow and not view.grid_slaves(row=0, column=0):
                break
            time.sleep(0.01)
        self.assertFalse(view.grid_slaves(row=0, column=0))
        self.assertTrue(view.sidebar_toggle.winfo_manager())
        view.toggle_sidebar()
        self.app.update()
        self.assertTrue(view.grid_slaves(row=0, column=0))
        self.assertEqual(view.sidebar_toggle.cget("text"), "Ẩn bộ lọc")

    def test_stop_scan_saves_partial_results_and_updates_real_metrics(self):
        view = self.app.view
        view.api_entry.delete(0, "end")
        view.api_entry.insert(0, "test-api-key")
        view.kw_textbox.delete("1.0", "end")
        view.kw_textbox.insert("1.0", "first topic\nsecond topic")
        youtube = MagicMock()
        first = {"items": [{"snippet": {"channelId": "channel-1", "title": "New video"}}]}

        def stop_on_second_search():
            self.app.stop_scan()
            return {"items": []}

        searches = iter([first, None])

        def search():
            response = next(searches)
            return response if response is not None else stop_on_second_search()

        youtube.search.return_value.list.return_value.execute.side_effect = search
        youtube.channels.return_value.list.return_value.execute.return_value = {"items": [{
            "id": "channel-1", "snippet": {"title": "A real fixture channel", "description": "test@example.com",
                "publishedAt": datetime.datetime.now(datetime.timezone.utc).isoformat()},
            "statistics": {"viewCount": "2000", "subscriberCount": "100", "videoCount": "2"}}]}
        with tempfile.TemporaryDirectory() as directory, \
                patch("ytb_bot.legacy_ui.desktop.APP_DIR", Path(directory)), \
                patch("ytb_bot.legacy_ui.desktop.ENV_FILE", str(Path(directory) / ".env")), \
                patch("ytb_bot.legacy_ui.desktop.threading.Thread"), \
                patch("ytb_bot.legacy_ui.desktop.build", return_value=youtube):
            self.app.start_scan_thread()
            self.app.run_scanner("test-api-key", ["first topic", "second topic"], 90, 500, 1)
            self.app._process_ui_events()
            workbook = Path(directory) / "danh_sach_kenh_viral_moi.xlsx"
            self.assertEqual(len(pd.read_excel(workbook)), 1)
            self.assertEqual(view.stat_values["matches"].cget("text"), "1")
            self.assertEqual(view.stat_values["completed"].cget("text"), "1 / 2")
            self.assertEqual(view.state_badge.cget("text"), "ĐÃ DỪNG")
            self.assertFalse(self.app.is_scanning)
            self.assertEqual(view.stop_btn.cget("state"), "disabled")
