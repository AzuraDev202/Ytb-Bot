import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock
from ytb_bot.core.outreach_store import OutreachStore
from ytb_bot.desktop.bulk import BulkOutreach
from ytb_bot.core.bulk_store import BulkStore


class RemoveFailedContactsTests(unittest.TestCase):
    def test_only_failed_contacts_are_removed_persistently_with_history_kept(self):
        with tempfile.TemporaryDirectory() as directory:
            store = OutreachStore(Path(directory) / 'workspace.sqlite3')
            run = store.begin_run(['topic'])
            rows = [{'Channel ID': 'failed', 'Email': 'failed@example.com', 'Facebook': 'https://facebook.com/creator'},
                    {'Channel ID': 'unknown', 'Email': 'unknown@example.com'}]
            store.save_run(run, 'complete', rows)
            for channel, status in [('failed', 'failed'), ('unknown', 'unknown')]:
                store.save_draft(channel, {'recipient': channel + '@example.com'})
                attempt, _ = store.claim(channel, 1)
                store.finish(attempt, status)
            outreach = MagicMock()
            outreach.store = store
            bulk = BulkOutreach(outreach)
            groups = bulk.groups()
            ids = [group['id'] for group in groups if group['kind'] == 'email']
            self.assertEqual(bulk.remove_failed_contacts(ids), 1)
            self.assertEqual(len(store.history('failed')), 1)
            self.assertFalse(BulkStore(store.path).claim_contact('new-sender@example.com', 'failed@example.com', 'old-draft'))
            draft = store.save_draft('failed', {'recipient': 'failed@example.com', 'body': 'New draft'})
            with self.assertRaisesRegex(ValueError, 'removed'):
                store.claim('failed', draft['revision'])
            store.clear_history()
            run = store.begin_run(['topic'])
            store.save_run(run, 'complete', rows)
            reopened = BulkOutreach(outreach)
            values = {group['value'] for group in reopened.groups()}
            self.assertNotIn('failed@example.com', values)
            self.assertIn('unknown@example.com', values)
            self.assertIn('https://facebook.com/creator', values)
