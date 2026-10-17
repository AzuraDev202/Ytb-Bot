import datetime as dt
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from ytb_bot.engine import ScanEngine
from ytb_bot.workbook import Workbook
from ytb_bot.react_api import DesktopAPI


class ReactBackendTests(unittest.TestCase):
    def test_workbook_pagination_search_sort_and_original_import(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.xlsx"
            pd.DataFrame({"Keyword": ["alpha", "beta", "alpha", None] + [f"topic {i}" for i in range(102)],
                          "Views": list(range(106))}).to_excel(path, index=False)
            book = Workbook()
            self.assertEqual(book.open(path)["sheets"], ["Sheet1"])
            self.assertEqual(len(book.page("Sheet1")["rows"]), 100)
            self.assertEqual(len(book.page("Sheet1", page=1)["rows"]), 6)
            filtered = book.page("Sheet1", query="ALPHA")
            self.assertEqual(filtered["total"], 2)
            self.assertEqual(book.page("Sheet1", sort=1, descending=True)["rows"][0][1], 105)
            words = book.keywords("Sheet1", 0)
            self.assertEqual(len(words), 104)
            self.assertIn("beta", words)
            with self.assertRaises(ValueError):
                book.page("missing")

    def test_scan_filters_deduplicates_and_exports(self):
        youtube = MagicMock()
        youtube.search.return_value.list.return_value.execute.return_value = {"items": [
            {"snippet": {"channelId": name, "title": "Video"}} for name in ("new", "old", "small")]}
        now = dt.datetime.now(dt.timezone.utc)
        youtube.channels.return_value.list.return_value.execute.return_value = {"items": [
            {"id": name, "snippet": {"title": name, "publishedAt": (now - dt.timedelta(days=age)).isoformat()},
             "statistics": {"viewCount": str(views)}}
            for name, age, views in [("new", 2, 1000), ("old", 300, 5000), ("small", 1, 10)]]}
        with tempfile.TemporaryDirectory() as directory:
            engine = ScanEngine(directory, lambda _: youtube)
            engine.start("test-key", ["one", "two", "one"])
            state = engine.wait()
            self.assertEqual((state["status"], state["matches"], state["completed"]), ("complete", 1, 2))
            self.assertEqual(state["rows"][0]["Channel ID"], "new")
            self.assertEqual(len(pd.read_excel(Path(directory) / "danh_sach_kenh_viral_moi.xlsx")), 1)

    def test_scan_redacts_secret_on_failure(self):
        def broken(key):
            raise RuntimeError(f"request failed: {key}")
        engine = ScanEngine(".", broken)
        engine.start("test-secret", ["topic"])
        state = engine.wait()
        self.assertEqual(state["status"], "error")
        self.assertNotIn("test-secret", str(state))

    def test_stop_saves_partial_results_before_next_keyword(self):
        youtube = MagicMock()
        youtube.search.return_value.list.return_value.execute.return_value = {
            "items": [{"snippet": {"channelId": "new", "title": "Video"}}]}
        with tempfile.TemporaryDirectory() as directory:
            engine = ScanEngine(directory, lambda _: youtube)
            def channel_response():
                engine.stop()
                return {"items": [{"id": "new", "snippet": {"title": "New", "publishedAt": dt.datetime.now(dt.timezone.utc).isoformat()},
                                   "statistics": {"viewCount": "1000"}}]}
            youtube.channels.return_value.list.return_value.execute.side_effect = channel_response
            engine.start("test-key", ["one", "two"])
            state = engine.wait()
            self.assertEqual(state["status"], "stopped")
            self.assertTrue(state["output"])
            self.assertEqual(state["matches"], 1)
            youtube.search.return_value.list.assert_called_once()

    def test_preferences_survive_bridge_recreation(self):
        with tempfile.TemporaryDirectory() as directory, patch("ytb_bot.react_api.APP_DIR", Path(directory)):
            api = DesktopAPI()
            self.assertTrue(api.save_preferences("light", False)["ok"])
            self.assertEqual(DesktopAPI().get_bootstrap()["data"]["preferences"], {"theme": "light", "motion": False})
            self.assertFalse(api.save_preferences("unknown", True)["ok"])

    def test_bridge_never_returns_saved_key_and_rejects_invalid_input(self):
        with patch("ytb_bot.react_api.dotenv_values", return_value={"YOUTUBE_API_KEY": "test-secret"}), \
                patch.dict("os.environ", {"YOUTUBE_API_KEY": "test-secret"}):
            api = DesktopAPI()
            self.assertNotIn("test-secret", str(api.get_bootstrap()))
            self.assertTrue(api.get_bootstrap()["data"]["has_api_key"])
            with patch("ytb_bot.react_api.set_key") as save:
                result = api.start_scan({"api_key": "new", "keywords": ["a"], "max_days": -1})
                self.assertFalse(result["ok"])
                save.assert_not_called()
            self.assertFalse(api.open_channel("https://example.com")["ok"])
