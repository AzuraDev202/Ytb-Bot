from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock

from ytb_bot.core.engine import ScanEngine
from ytb_bot.core.storage import WorkspaceStore
from ytb_bot.desktop.api import DesktopAPI


class WorkspaceTests(unittest.TestCase):
    def test_keywords_preserve_edits_blank_library_and_unicode_after_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            first = DesktopAPI(directory)
            self.assertTrue(first.save_keywords('AI \u2603\nsecond\nsecond\n')['ok'])
            second = DesktopAPI(directory)
            self.assertEqual(second.get_bootstrap()['data']['keywords'], 'AI \u2603\nsecond\nsecond\n')
            self.assertTrue(second.save_keywords('')['ok'])
            self.assertEqual(DesktopAPI(directory).get_bootstrap()['data']['keywords'], '')
            self.assertFalse(second.save_keywords(['invalid'])['ok'])
            self.assertFalse(list(Path(directory).glob('*.xlsx')))

    def test_history_contains_all_rows_and_independent_result_sessions(self):
        with tempfile.TemporaryDirectory() as directory:
            store = WorkspaceStore(Path(directory) / 'workspace.sqlite3')
            first = store.begin_run(['alpha'])
            rows = [{'Channel Name': f'Channel {i}', 'Total Views': i} for i in range(251)]
            store.save_run(first, 'complete', rows)
            second = store.begin_run(['beta'])
            store.save_run(second, 'stopped', [{'Channel Name': 'Partial'}])
            api = DesktopAPI(directory)
            self.assertEqual([run['id'] for run in api.list_results()['data']], [second, first])
            sheet = api.open_results(first)['data']['sheets'][0]
            api.open_results(second)
            page = api.results_page(sheet, '', 2)['data']
            self.assertEqual((page['total'], len(page['rows'])), (251, 51))
            self.assertEqual(api.results_page(sheet, 'Channel 250')['data']['total'], 1)
            sorted_page = api.results_page(sheet, '', 0, 7, True)['data']
            self.assertEqual(sorted_page['rows'][0][7], 250)
            self.assertEqual(DesktopAPI(directory).open_results()['data']['run_id'], second)

    def test_empty_success_is_a_saved_run_without_excel(self):
        with tempfile.TemporaryDirectory() as directory:
            youtube = MagicMock()
            youtube.search.return_value.list.return_value.execute.return_value = {'items': []}
            engine = ScanEngine(directory, lambda _: youtube)
            engine.start('test-key', ['topic'])
            self.assertEqual(engine.wait()['status'], 'complete')
            store = WorkspaceStore(Path(directory) / 'workspace.sqlite3')
            self.assertEqual(store.result()['rows'], [])
            self.assertEqual(store.runs()[0]['status'], 'complete')
            self.assertFalse(list(Path(directory).glob('*.xlsx')))

    def test_partial_results_survive_api_failure_and_reopen(self):
        import datetime as dt
        with tempfile.TemporaryDirectory() as directory:
            youtube = MagicMock()
            youtube.search.return_value.list.return_value.execute.side_effect = [
                {'items': [{'snippet': {'channelId': 'kept', 'title': 'Video'}}]}, RuntimeError('quota failed: secret-key')]
            youtube.channels.return_value.list.return_value.execute.return_value = {'items': [
                {'id': 'kept', 'snippet': {'title': 'Saved channel', 'description': 'test@example.com', 'publishedAt': dt.datetime.now(dt.timezone.utc).isoformat()},
                 'statistics': {'viewCount': '2000'}}]}
            engine = ScanEngine(directory, lambda _: youtube)
            engine.start('secret-key', ['first', 'second'])
            self.assertEqual(engine.wait()['status'], 'error')
            result = WorkspaceStore(Path(directory) / 'workspace.sqlite3').result()
            self.assertEqual(result['rows'][0]['Channel ID'], 'kept')
            self.assertEqual(result['status'], 'error')
            self.assertNotIn('secret-key', str(result))
            self.assertFalse(list(Path(directory).glob('*.xlsx')))

    def test_unsaved_keyword_state_blocks_restart_update(self):
        with tempfile.TemporaryDirectory() as directory:
            api = DesktopAPI(directory)
            self.assertTrue(api.set_keywords_dirty(True)['ok'])
            self.assertIn('keyword', api.install_available_update()['error'])
            self.assertFalse(api.set_keywords_dirty('invalid')['ok'])
            self.assertTrue(api.set_keywords_dirty(False)['ok'])
