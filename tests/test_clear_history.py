import tempfile
import unittest
from unittest.mock import MagicMock

from ytb_bot.core.engine import ScanEngine
from ytb_bot.core.storage import WorkspaceStore


class ClearHistoryTests(unittest.TestCase):
    def test_clear_removes_runs_and_resume_but_keeps_keywords(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = ScanEngine(directory)
            store = engine._store
            store.save_keywords('my keywords')
            run = store.begin_run(['topic'])
            store.save_run(run, 'complete', [{'Channel ID': 'saved'}])
            store.save_scan_checkpoint({'index': 0, 'keywords': ['topic']})
            engine.clear_history()
            reopened = WorkspaceStore(store.path)
            self.assertEqual(reopened.runs(), [])
            self.assertEqual(reopened.known_channel_ids(), set())
            self.assertIsNone(reopened.scan_checkpoint())
            self.assertEqual(reopened.keywords(), 'my keywords')
            self.assertFalse(engine.snapshot()['can_resume'])

    def test_clear_rejects_a_live_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = ScanEngine(directory)
            engine._thread = MagicMock()
            engine._thread.is_alive.return_value = True
            with self.assertRaises(ValueError):
                engine.clear_history()
