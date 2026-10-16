"""Exercise actual workbook reading and desktop import without YouTube calls."""
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import pandas as pd
import customtkinter as ctk

from gui_app import YtbBotApp


@unittest.skipUnless(os.name == "nt", "Windows desktop GUI")
class ExcelViewerTests(unittest.TestCase):
    @staticmethod
    def close_app(app):
        # Tests create several Tcl interpreters; cancel pending widget timers
        # before destroying each root so they cannot fire during the next test.
        for timer in app.tk.splitlist(app.tk.call("after", "info")):
            app.tk.call("after", "cancel", timer)
        app.destroy()

    def test_startup_centers_and_uses_scrolling_on_small_screens(self):
        for area in [(0, 0, 1366, 728), (0, 48, 1920, 1080)]:
            with self.subTest(area=area), patch("gui_app.screen_work_area", return_value=area), \
                    patch.object(YtbBotApp, "check_updates"):
                app = YtbBotApp()
                try:
                    app.update()
                    self.assertGreaterEqual(app.winfo_rootx(), area[0])
                    self.assertGreaterEqual(app.winfo_rooty(), area[1])
                    self.assertLessEqual(app.winfo_rootx() + app.winfo_width(), area[2])
                    self.assertLessEqual(app.winfo_rooty() + app.winfo_height(), area[3])
                    if app._compact:
                        self.assertIsInstance(app.main_frame, ctk.CTkScrollableFrame)
                finally:
                    self.close_app(app)

    def test_preview_sheet_selection_paging_and_full_column_import(self):
        with tempfile.TemporaryDirectory() as directory:
            workbook = Path(directory) / "keywords.xlsx"
            words = [" AI Agent ", None, "AI Agent", "tạo video"] + [f"keyword {i}" for i in range(401)]
            with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
                pd.DataFrame({"Notes": ["Chọn sheet Keywords"]}).to_excel(writer, sheet_name="Overview", index=False)
                pd.DataFrame({"Keyword": words, "Other": range(len(words))}).to_excel(writer, sheet_name="Keywords", index=False)
                pd.DataFrame().to_excel(writer, sheet_name="Empty", index=False)
            with patch.object(YtbBotApp, "check_updates"):
                app = YtbBotApp()
                app.withdraw()
                try:
                    viewer = app.excel_viewer

                    def ready():
                        deadline = time.monotonic() + 10
                        while time.monotonic() < deadline:
                            app.update()
                            if viewer.sheet_menu.cget("state") == "normal":
                                return
                            time.sleep(0.01)
                        self.fail("Workbook did not load within 10 seconds")

                    app._show_excel(str(workbook))
                    ready()
                    self.assertEqual(app.content_tabs.get(), "Excel")
                    self.assertEqual(viewer.sheet_menu.get(), "Overview")
                    viewer._select_sheet("Keywords")
                    ready()
                    self.assertEqual(len(viewer.data), 405)
                    self.assertEqual(len(viewer.table.get_children()), 200)
                    viewer._move_page(1)
                    viewer._move_page(1)
                    self.assertEqual(len(viewer.table.get_children()), 5)
                    self.assertEqual(viewer.next.cget("state"), "disabled")
                    with patch("excel_viewer.messagebox.askyesno", return_value=False):
                        before = app.kw_textbox.get("1.0", "end")
                        viewer.import_keywords()
                        self.assertEqual(app.kw_textbox.get("1.0", "end"), before)
                    with patch("excel_viewer.messagebox.askyesno", return_value=True):
                        viewer.import_keywords()
                    imported = app.kw_textbox.get("1.0", "end").strip().splitlines()
                    self.assertEqual(len(imported), 403)
                    self.assertEqual(imported[:2], ["AI Agent", "tạo video"])
                    self.assertEqual(imported[-1], "keyword 400")
                    viewer._select_sheet("Empty")
                    ready()
                    self.assertEqual(viewer.import_button.cget("state"), "disabled")
                    self.assertEqual(len(viewer.table.get_children()), 0)
                    broken = Path(directory) / "broken.xlsx"
                    broken.write_text("not an Excel file")
                    with patch("excel_viewer.messagebox.showerror") as error:
                        viewer.open_file(broken)
                        deadline = time.monotonic() + 10
                        while not error.called and time.monotonic() < deadline:
                            app.update()
                            time.sleep(0.01)
                        error.assert_called_once()
                    self.assertEqual(viewer.import_button.cget("state"), "disabled")
                finally:
                    self.close_app(app)
