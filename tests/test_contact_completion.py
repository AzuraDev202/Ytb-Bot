import json
from pathlib import Path
import tempfile
import unittest

from ytb_bot.core.storage import WorkspaceStore
from ytb_bot.core.outreach_store import OutreachStore
from ytb_bot.core.bulk_store import BulkStore
from ytb_bot.core.contact_groups import contact_groups


class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = OutreachStore(Path(self.temp.name) / 'test.db')
        self.run = self.store.begin_run([])
        self.store.save_run(self.run, 'complete', [
            {'Channel ID': 'a', 'Email': 'shared@example.com\nalternate@example.com', 'Facebook': 'https://facebook.com/a'},
            {'Channel ID': 'b', 'Email': 'shared@example.com'},
        ])

    def attempt(self, status):
        self.store.save_draft('a', {'recipient': 'shared@example.com', 'subject': 'Hi', 'body': 'Hello', 'account_id': 'me'})
        key, _ = self.store.claim('a', 1)
        self.store.finish(key, status)

    def test_accepted_individual_removes_all_contacts_only_for_its_channel(self):
        self.attempt('accepted')
        groups = contact_groups(self.store)
        self.assertEqual([g['value'] for g in groups], ['shared@example.com'])
        self.assertEqual(groups[0]['channels'][0]['id'], 'b')
        # Historical acceptance survives new scans and a fresh store instance.
        run = self.store.begin_run([])
        self.store.save_run(run, 'complete', [{'Channel ID': 'a', 'Email': 'new@example.com'}])
        self.assertEqual(len(contact_groups(WorkspaceStore(self.store.path))), 1)

    def test_unknown_and_failed_keep_contacts(self):
        for status in ('unknown', 'failed'):
            with self.subTest(status=status):
                with self.store._connection() as db:
                    db.execute('DELETE FROM mail_attempts')
                    db.execute('DELETE FROM email_channel_claims')
                self.attempt(status)
                self.assertEqual(len(contact_groups(self.store)), 3)

    def test_accepted_bulk_uses_snapshot_not_current_shared_address(self):
        bulk = BulkStore(self.store.path)
        bulk.create({'recipients': [{'status': 'accepted', 'email': 'shared@example.com', 'channels': [{'id': 'a'}]}]})
        self.assertEqual([c['id'] for g in contact_groups(self.store) for c in g['channels']], ['b'])

    def test_persistent_exclusion_is_idempotent(self):
        from ytb_bot.core.contact_completion import ContactCompletion
        complete = ContactCompletion(self.store)
        complete.complete(['a'], 'test')
        complete.complete(['a'], 'test')
        self.assertEqual(complete.completed_ids(), {'a'})

