"""Existing workspaces remain readable after switching column labels to English."""
import json
from pathlib import Path
import tempfile
import unittest

from ytb_bot.core.storage import WorkspaceStore
from ytb_bot.core.outreach_store import OutreachStore


class ResultSchemaTests(unittest.TestCase):
    def test_legacy_rows_are_read_in_english_without_rewriting_user_content(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'workspace.sqlite3'
            store = WorkspaceStore(path)
            run = store.begin_run(['original keyword'])
            legacy = {'Channel ID': 'old', 'T\u00ean K\u00eanh': 'Creator \u2603',
                      'T\u1ed5ng L\u01b0\u1ee3t Xem': 1200,
                      'Li\u00ean H\u1ec7 Kh\u00e1c': 'https://t.me/creator',
                      'Subscribers': '\u1ea8n', 'Qu\u1ed1c Gia': 'Kh\u00f4ng c\u00f4ng b\u1ed1'}
            store.save_run(run, 'complete', [legacy])
            expected = {'Channel ID': 'old', 'Channel Name': 'Creator \u2603',
                        'Total Views': 1200, 'Other Contacts': 'https://t.me/creator',
                        'Subscribers': 'Hidden', 'Country': 'Not disclosed'}
            self.assertEqual(WorkspaceStore(path).result(run)['rows'], [expected])
            self.assertEqual(OutreachStore(path).channel('old'), expected)
            self.assertEqual(store.known_channel_ids(), {'old'})
            with store._connection() as db:
                original = json.loads(db.execute('SELECT rows FROM runs WHERE id=?', (run,)).fetchone()[0])
            self.assertEqual(original, [legacy], 'Reading must not modify persisted user data')

    def test_english_fields_take_precedence_when_a_row_contains_both_formats(self):
        with tempfile.TemporaryDirectory() as directory:
            store = WorkspaceStore(Path(directory) / 'workspace.sqlite3')
            run = store.begin_run(['topic'])
            store.save_run(run, 'complete', [{'Channel Name': 'Current', 'T\u00ean K\u00eanh': 'Old', 'extra': 7}])
            self.assertEqual(store.result(run)['rows'], [{'Channel Name': 'Current', 'extra': 7}])
