import concurrent.futures
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import MagicMock
from ytb_bot.core.storage import WorkspaceStore
from ytb_bot.desktop.outreach import Outreach
from ytb_bot.desktop.bulk import BulkOutreach


class Vault:
    def __init__(self):
        self.value = {'accounts': {'account': {'email': 'sender@example.com'}}, 'client': {}}
    def read(self):
        return json.loads(json.dumps(self.value))
    def update(self, operation):
        value = self.read()
        result = operation(value)
        self.value = value
        return result


class BulkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'test.db'
        store = WorkspaceStore(self.path)
        run = store.begin_run(['topic'])
        store.save_run(run, 'complete', [
            {'Channel ID': 'a', 'Channel Name': 'A', 'Email': 'CREATOR@example.com'},
            {'Channel ID': 'b', 'Channel Name': 'B', 'Email': 'creator@example.com'},
            {'Channel ID': 'c', 'Channel Name': 'C', 'Email': 'other@example.com', 'Facebook': 'https://facebook.com/Creator'}])
        self.gmail = MagicMock()
        self.gmail.access.return_value = 'secret'
        self.gmail.send.return_value = 'provider-id'
        self.outreach = Outreach(self.path, Vault(), self.gmail)
        self.bulk = BulkOutreach(self.outreach, interval=0)
        self.payload = {'group_ids': [group['id'] for group in self.bulk.groups() if group['kind'] == 'email'],
            'account_id': 'account', 'subject': 'Hello', 'body': 'Collaboration'}

    def finish(self):
        self.bulk._thread.join(5)
        self.assertFalse(self.bulk._thread.is_alive())

    def test_groups_dedup_and_latest_channel_data(self):
        groups = self.bulk.groups()
        self.assertEqual(len(groups), 3)
        group = next(group for group in groups if group['value'] == 'creator@example.com')
        self.assertEqual(len(group['channels']), 2)
        store = self.outreach.store
        run = store.begin_run([])
        store.save_run(run, 'complete', [{'Channel ID': 'a', 'Email': 'new@example.com'}])
        groups = self.bulk.groups()
        self.assertEqual(len(next(g for g in groups if g['value'] == 'creator@example.com')['channels']), 1)

    def test_preview_is_immutable_and_does_not_send(self):
        batch = self.bulk.prepare(self.payload)
        self.gmail.send.assert_not_called()
        batch['subject'] = 'tampered'
        self.assertEqual(self.bulk.get(batch['id'])['subject'], 'Hello')
        reopened = BulkOutreach(self.outreach, 0)
        self.assertEqual(reopened.get(batch['id'])['status'], 'draft')
        for ids in [['forged'], self.payload['group_ids'] * 2, [next(g['id'] for g in self.bulk.groups() if g['kind'] == 'social')]]:
            with self.assertRaises(ValueError):
                self.bulk.prepare(dict(self.payload, group_ids=ids))
        with self.assertRaises(ValueError):
            self.bulk.prepare(dict(self.payload, subject='Header\r\nBcc: x@example.com'))

    def test_double_start_single_delivery_and_skip_previous(self):
        batch = self.bulk.prepare(self.payload)
        def start():
            try:
                self.bulk.start(batch['id'])
                return True
            except ValueError:
                return False
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            self.assertEqual(sum(pool.map(lambda _: start(), range(2))), 1)
        self.finish()
        self.assertEqual(self.gmail.send.call_count, 2)
        self.assertTrue(all(row['status'] == 'skipped' for row in self.bulk.prepare(self.payload)['recipients']))

    def test_unknown_cancels_rest_and_never_retries(self):
        self.gmail.send.side_effect = TimeoutError('secret')
        batch = self.bulk.prepare(self.payload)
        self.bulk.start(batch['id'])
        self.finish()
        result = self.bulk.get(batch['id'])
        self.assertEqual([row['status'] for row in result['recipients']], ['unknown', 'canceled'])
        self.assertNotIn('secret', str(result))
        with self.assertRaises(ValueError):
            self.bulk.start(batch['id'])
        self.assertEqual(self.gmail.send.call_count, 1)

    def test_stop_during_send_and_live_second_instance(self):
        entered, release = threading.Event(), threading.Event()
        def send(*args):
            entered.set()
            release.wait(5)
            return 'provider-id'
        self.gmail.send.side_effect = send
        batch = self.bulk.prepare(self.payload)
        self.bulk.start(batch['id'])
        self.assertTrue(entered.wait(5))
        other = BulkOutreach(self.outreach, 0)
        self.assertEqual(other.get(batch['id'])['status'], 'running')
        self.bulk.stop(batch['id'])
        release.set()
        self.finish()
        self.assertEqual([row['status'] for row in self.bulk.get(batch['id'])['recipients']], ['accepted', 'canceled'])

    def test_recover_orphan_and_individual_history(self):
        draft = self.outreach.save('a', dict(self.payload, recipient='CREATOR@example.com'))
        self.outreach.store.claim('a', draft['revision'])
        result = self.bulk.prepare(self.payload)
        self.assertEqual(result['recipients'][0]['status'], 'skipped')
        self.bulk.store.change(result['id'], lambda value: value.update(status='running'))
        self.bulk.store.change(result['id'], lambda value: value['recipients'][1].update(status='sending'))
        reopened = BulkOutreach(self.outreach, 0)
        self.assertEqual(reopened.get(result['id'])['status'], 'interrupted')
        self.assertEqual(reopened.get(result['id'])['recipients'][1]['status'], 'unknown')

    def test_atomic_global_claim_checks_manual_history_and_other_bulk_claims(self):
        draft = self.outreach.save('a', dict(self.payload, recipient='CREATOR@example.com'))
        self.outreach.store.claim('a', draft['revision'])
        self.assertFalse(self.bulk.store.claim_contact('sender@example.com', 'creator@example.com', 'bulk', 'account'))
        def claim():
            return self.bulk.store.claim_contact('sender@example.com', 'other@example.com', 'bulk', 'account')
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            self.assertEqual(sum(pool.map(lambda _: claim(), range(2))), 1)

    def test_recover_stopped_batch_with_orphaned_request(self):
        batch = self.bulk.prepare(self.payload)
        def orphan(value):
            value['status'] = 'stopped'
            value['recipients'][0]['status'] = 'sending'
            value['recipients'][1]['status'] = 'canceled'
        self.bulk.store.change(batch['id'], orphan)
        reopened = BulkOutreach(self.outreach, 0)
        result = reopened.get(batch['id'])
        self.assertEqual(result['status'], 'stopped')
        self.assertEqual([row['status'] for row in result['recipients']], ['unknown', 'canceled'])
        self.gmail.send.assert_not_called()

    def test_rejected_send_cancels_queue(self):
        from ytb_bot.desktop.gmail import SendRejected
        self.gmail.send.side_effect = SendRejected('provider rejection')
        batch = self.bulk.prepare(self.payload)
        self.bulk.start(batch['id'])
        self.finish()
        self.assertEqual([row['status'] for row in self.bulk.get(batch['id'])['recipients']], ['failed', 'canceled'])
