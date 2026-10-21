import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from ytb_bot.core.outreach_store import OutreachStore
from ytb_bot.core.bulk_store import BulkStore
from ytb_bot.core.email_history import email_records


class EmailHistoryTests(unittest.TestCase):
    def test_single_and_bulk_race_claims_same_channel_once(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'workspace.sqlite3'
            store, bulk = OutreachStore(path), BulkStore(path)
            store.save_draft('channel', {'recipient': 'single@example.com'})
            def single():
                try:
                    store.claim('channel', 1)
                    return True
                except ValueError:
                    return False
            with ThreadPoolExecutor(max_workers=2) as pool:
                one = pool.submit(single)
                two = pool.submit(bulk.claim_contact, 'sender@example.com', 'bulk@example.com',
                                  'batch', '', ['channel'])
                self.assertEqual(sum([one.result(), two.result()]), 1)

    def test_sent_channel_survives_scan_clear_and_new_draft_sender_and_address(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'workspace.sqlite3'
            store = OutreachStore(path)
            draft = {'recipient': 'first@example.com', 'subject': 'Hello', 'body': 'Hello', 'account_id': 'one'}
            saved = store.save_draft('channel', draft)
            attempt, _ = store.claim('channel', saved['revision'], 'sender@example.com')
            store.finish(attempt, 'accepted', 'gmail-id')
            # Simulate upgrading a workspace whose sends predate channel claims.
            with store._connection() as db:
                db.execute('DELETE FROM email_channel_claims')
            store.clear_history()
            store = OutreachStore(path)
            saved = store.save_draft('channel', {**draft, 'recipient': 'second@example.com', 'body': 'New', 'account_id': 'two'})
            with self.assertRaises(ValueError):
                store.claim('channel', saved['revision'], 'other@example.com')
            with store._connection() as db:
                self.assertEqual(email_records(db)[0]['message_id'], 'gmail-id')
            bulk = BulkStore(path)
            self.assertFalse(bulk.claim_contact('other@example.com', 'third@example.com', 'batch', channel_ids=['channel']))

    def test_bulk_claim_blocks_single_even_before_gmail_submission(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'workspace.sqlite3'
            bulk = BulkStore(path)
            self.assertTrue(bulk.claim_contact('one@example.com', 'to@example.com', 'batch', channel_ids=['channel']))
            store = OutreachStore(path)
            saved = store.save_draft('channel', {'recipient': 'new@example.com'})
            with self.assertRaises(ValueError):
                store.claim('channel', saved['revision'])

    def test_old_bulk_acceptance_survives_clear_and_blocks_single(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'workspace.sqlite3'
            bulk = BulkStore(path)
            bulk.create({'recipients': [{'email': 'sent@example.com', 'status': 'accepted',
                'message_id': 'bulk-gmail-id', 'channels': [{'id': 'channel', 'name': 'Creator'}]}]})
            bulk.clear_history()
            store = OutreachStore(path)
            saved = store.save_draft('channel', {'recipient': 'new@example.com'})
            with self.assertRaises(ValueError):
                store.claim('channel', saved['revision'])
            with store._connection() as db:
                record = email_records(db)[0]
                self.assertEqual((record['name'], record['message_id']), ('Creator', 'bulk-gmail-id'))
