import datetime as dt
import tempfile
import unittest
from unittest.mock import MagicMock
import json
from googleapiclient.errors import HttpError
import httplib2

from ytb_bot.core.engine import ScanEngine


class ScanBudgetTests(unittest.TestCase):
    def test_budget_and_resume_after_reopening(self):
        with tempfile.TemporaryDirectory() as directory:
            client = MagicMock()
            client.search.return_value.list.return_value.execute.side_effect = [
                {'items': [], 'nextPageToken': 'page-two'}, {'items': []}, {'items': []}]
            engine = ScanEngine(directory, lambda _: client)
            engine.start('secret', ['first', 'second'], search_budget=1)
            state = engine.wait()
            self.assertEqual(state['status'], 'stopped')
            self.assertEqual(state['search_used'], 1)
            self.assertTrue(state['can_resume'])
            reopened = ScanEngine(directory, lambda _: client)
            self.assertTrue(reopened.snapshot()['can_resume'])
            reopened.resume('secret', search_budget=5)
            self.assertEqual(reopened.wait()['status'], 'complete')
            calls = client.search.return_value.list.call_args_list
            self.assertEqual(calls[1].kwargs['pageToken'], 'page-two')
            self.assertEqual(calls[2].kwargs['q'], 'second')
            self.assertFalse(reopened.snapshot()['can_resume'])

    def test_pacific_reset_tracks_daylight_saving(self):
        from ytb_bot.core.quota import next_reset
        for month, hour in [(7, 7), (12, 8)]:
            now = dt.datetime(2026, month, 10, 1, tzinfo=dt.timezone.utc)
            self.assertEqual(next_reset(now).hour, hour)

    def test_daily_quota_blocks_resume_but_minute_limit_does_not(self):
        for message, available in [('Search Queries per day quota exceeded', False),
                                   ('Too many requests per minute', True)]:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as directory:
                client = MagicMock()
                client.search.return_value.list.return_value.execute.side_effect = HttpError(
                    httplib2.Response({'status': '429'}), json.dumps({'error': {
                        'message': message, 'errors': [{'reason': 'rateLimitExceeded'}]
                    }}).encode())
                engine = ScanEngine(directory, lambda _: client)
                engine.start('secret', ['topic'])
                state = engine.wait()
                self.assertEqual(state['status'], 'error')
                self.assertTrue(state['can_resume'])
                self.assertEqual(state['resume_available'], available)
                if not available:
                    with self.assertRaisesRegex(ValueError, 'reset'):
                        engine.resume('secret')
                self.assertEqual(client.search.return_value.list.call_count, 1)

    def test_budget_preserves_candidates_before_channel_filtering(self):
        with tempfile.TemporaryDirectory() as directory:
            client = MagicMock()
            client.search.return_value.list.return_value.execute.side_effect = [
                {'items': [{'snippet': {'channelId': 'channel', 'title': 'video'}}],
                 'nextPageToken': 'next'}, {'items': []}]
            client.channels.return_value.list.return_value.execute.return_value = {'items': [
                {'id': 'channel', 'snippet': {'title': 'Creator', 'description': 'a@example.com',
                 'publishedAt': dt.datetime.now(dt.timezone.utc).isoformat()},
                 'statistics': {'viewCount': '1000'}}]}
            engine = ScanEngine(directory, lambda _: client)
            engine.start('secret', ['topic'], search_budget=1)
            engine.wait()
            engine = ScanEngine(directory, lambda _: client)
            engine.resume('secret')
            state = engine.wait()
            self.assertEqual(state['matches'], 1)
            self.assertEqual(state['rows'][0]['Channel ID'], 'channel')
