import datetime as dt
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock

from ytb_bot.core.engine import ScanEngine
from ytb_bot.core.storage import WorkspaceStore
from ytb_bot.desktop.api import DesktopAPI


def client_for(countries):
    youtube = MagicMock()
    youtube.search.return_value.list.return_value.execute.return_value = {'items': [
        {'snippet': {'channelId': channel_id, 'title': 'Video'}} for channel_id in countries]}
    youtube.channels.return_value.list.return_value.execute.return_value = {'items': [
        {'id': channel_id, 'snippet': {'title': 'Same display name', 'description': 'hello@example.com',
         'publishedAt': dt.datetime.now(dt.timezone.utc).isoformat(), **({'country': country} if country else {})},
         'statistics': {'viewCount': '1000'}} for channel_id, country in countries.items()]}
    return youtube


class ScanHistoryTests(unittest.TestCase):
    def test_history_reads_all_statuses_and_rows_after_reopening(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'workspace.sqlite3'
            store = WorkspaceStore(path)
            self.assertEqual(store.known_channel_ids(), set())
            expected = set()
            for status in ['complete', 'stopped', 'error', 'running']:
                run = store.begin_run(['topic'])
                rows = [{'Channel ID': f'{status}-{i}'} for i in range(251)]
                expected.update(row['Channel ID'] for row in rows)
                store.save_run(run, status, rows + [{'Channel ID': ''}, {'Channel ID': None}, {'Tên Kênh': 'Legacy'}])
            self.assertEqual(WorkspaceStore(path).known_channel_ids(), expected)

    def test_saved_channels_are_excluded_before_details_and_across_restarts(self):
        with tempfile.TemporaryDirectory() as directory:
            store = WorkspaceStore(Path(directory) / 'workspace.sqlite3')
            old = store.begin_run(['previous'])
            store.save_run(old, 'error', [{'Channel ID': 'old', 'Tên Kênh': 'Renamed channel'}])
            youtube = client_for({'old': 'VN', 'new': 'US'})
            # Details responses follow the requested IDs, like the real API.
            all_items = youtube.channels.return_value.list.return_value.execute.return_value['items']
            youtube.channels.return_value.list.return_value.execute.side_effect = lambda: {'items': [all_items[1]]}
            engine = ScanEngine(directory, lambda _: youtube)
            engine.start('fake-key', ['first', 'second'])
            state = engine.wait()
            self.assertEqual(state['status'], 'complete')
            self.assertEqual([row['Channel ID'] for row in state['rows']], ['new'])
            youtube.channels.return_value.list.assert_called_once_with(part='snippet,statistics', id='new')
            self.assertEqual(store.result(old)['rows'][0]['Channel ID'], 'old')
            youtube.channels.return_value.list.reset_mock()
            reopened = ScanEngine(directory, lambda _: youtube)
            reopened.start('fake-key', ['third'])
            state = reopened.wait()
            self.assertEqual((state['status'], state['matches']), ('complete', 0))
            youtube.channels.return_value.list.assert_not_called()
            self.assertEqual(store.result()['rows'], [])
            self.assertEqual(store.known_channel_ids(), {'old', 'new'})

    def test_accepts_multiple_countries_and_undisclosed_country_without_region_parameters(self):
        with tempfile.TemporaryDirectory() as directory:
            youtube = client_for({'vn': 'VN', 'us': 'US', 'jp': 'JP', 'unknown': None})
            engine = ScanEngine(directory, lambda _: youtube)
            engine.start('fake-key', ['AI', '人工知能'])
            state = engine.wait()
            self.assertEqual(state['status'], 'complete')
            self.assertEqual({row['Quốc Gia'] for row in state['rows']}, {'VN', 'US', 'JP', 'Không công bố'})
            self.assertEqual(state['matches'], 4)
            for request in youtube.search.return_value.list.call_args_list:
                for parameter in ['regionCode', 'relevanceLanguage', 'location', 'locationRadius']:
                    self.assertNotIn(parameter, request.kwargs)
            api = DesktopAPI(directory)
            sheet = api.open_results()['data']['sheets'][0]
            page = api.results_page(sheet, 'JP')['data']
            self.assertEqual(page['total'], 1)
            self.assertEqual(page['rows'][0][page['columns'].index('Quốc Gia')], 'JP')
