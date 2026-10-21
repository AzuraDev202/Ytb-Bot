import tempfile
import unittest
from unittest.mock import MagicMock

from ytb_bot.core.engine import ScanEngine
from ytb_bot.core.storage import WorkspaceStore


class ClearHistoryTests(unittest.TestCase):
    def test_same_keywords_restart_at_first_page_after_clear(self):
        for reopen in (False, True):
            with self.subTest(reopen=reopen), tempfile.TemporaryDirectory() as directory:
                client = MagicMock()
                client.search.return_value.list.return_value.execute.side_effect = [
                    {'items': []},
                    {'items': [], 'nextPageToken': 'saved-page'},
                    {'items': []},
                    {'items': []},
                ]
                keywords = ['first', 'second']
                engine = ScanEngine(directory, lambda _: client)
                engine.start('test-key', keywords, search_budget=2)
                state = engine.wait()
                self.assertTrue(state['can_resume'])
                self.assertEqual(engine._store.scan_checkpoint()['index'], 1)
                self.assertEqual(engine._store.scan_checkpoint()['token'], 'saved-page')

                engine.clear_history()
                if reopen:
                    engine = ScanEngine(directory, lambda _: client)
                with self.assertRaisesRegex(ValueError, 'No saved scan'):
                    engine.resume('test-key')
                engine.start('test-key', keywords)
                self.assertEqual(engine.wait()['status'], 'complete')
                requests = client.search.return_value.list.call_args_list
                self.assertEqual(requests[2].kwargs['q'], 'first')
                self.assertIsNone(requests[2].kwargs['pageToken'])
                self.assertEqual(requests[3].kwargs['q'], 'second')
                self.assertIsNone(requests[3].kwargs['pageToken'])

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
