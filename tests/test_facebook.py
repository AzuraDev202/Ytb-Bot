import datetime as dt
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from ytb_bot.desktop.facebook import FacebookClient, FacebookRejected, graph_request
from ytb_bot.desktop.facebook_outreach import FacebookOutreach
from ytb_bot.core.outreach_store import OutreachStore
from ytb_bot.core.contact_groups import contact_groups


class Vault:
    def __init__(self):
        self.value = {'accounts': {}}
    def read(self):
        import copy
        return copy.deepcopy(self.value)
    def update(self, operation):
        return operation(self.value)


class ClientTests(unittest.TestCase):
    def test_transport_uses_authorization_header_not_query_and_sanitizes_failures(self):
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value = b'{"id":"p"}'
        with patch('ytb_bot.desktop.facebook.build_opener', return_value=opener):
            self.assertEqual(graph_request('GET', 'me', 'very-private-token', {'fields': 'id'}), {'id': 'p'})
            request = opener.open.call_args.args[0]
            self.assertEqual(request.get_header('Authorization'), 'Bearer very-private-token')
            self.assertNotIn('very-private-token', request.full_url)
            self.assertTrue(request.full_url.startswith('https://graph.facebook.com/v25.0/'))
            opener.open.side_effect = TimeoutError('very-private-token')
            with self.assertRaises(ValueError) as caught:
                graph_request('GET', 'me', 'very-private-token')
            self.assertNotIn('very-private-token', str(caught.exception))

    def test_transport_distinguishes_explicit_rejection_from_server_uncertainty(self):
        from urllib.error import HTTPError
        opener = MagicMock()
        with patch('ytb_bot.desktop.facebook.build_opener', return_value=opener):
            opener.open.side_effect = HTTPError('https://graph.facebook.com', 403, 'private-token', {}, None)
            with self.assertRaises(FacebookRejected):
                graph_request('POST', 'p/messages', 'private-token', payload={})
            opener.open.side_effect = HTTPError('https://graph.facebook.com', 500, 'private-token', {}, None)
            with self.assertRaises(ValueError) as caught:
                graph_request('POST', 'p/messages', 'private-token', payload={})
            self.assertNotIsInstance(caught.exception, FacebookRejected)
            self.assertNotIn('private-token', str(caught.exception))

    def test_page_rejects_user_tokens(self):
        api = MagicMock(return_value={'id': '1', 'name': 'Person'})
        with self.assertRaises(ValueError):
            FacebookClient(api).page('secret')

    def test_page_checks_messaging_access(self):
        api = MagicMock(side_effect=[{'id': '1', 'name': 'Page', 'category': 'Business'}, {'data': []}])
        self.assertEqual(FacebookClient(api).page('secret')['id'], '1')
        self.assertEqual(api.call_count, 2)

    def test_recent_inbound_pagination_and_two_party_identity(self):
        now = dt.datetime.now(dt.timezone.utc).isoformat()
        def api(method, path, token, params=None, payload=None):
            if path == 'p/conversations':
                return {'data': [{'id': 'c', 'participants': {'data': [{'id': 'p'}, {'id': 'r', 'name': 'Creator'}]}}]}
            if (params or {}).get('after') == 'cursor':
                return {'data': [{'from': {'id': 'r'}, 'created_time': now}]}
            return {'data': [{'from': {'id': 'p'}, 'created_time': now}], 'paging': {'next': 'https://evil.test/token', 'cursors': {'after': 'cursor'}}}
        client = FacebookClient(api)
        self.assertTrue(client.conversations('secret', 'p')[0]['eligible'])
        self.assertEqual(client.recipient('secret', 'p', 'r')['id'], 'c')

    def test_incomplete_expired_future_history_not_eligible(self):
        for time in ((dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=2)).isoformat(),
                     (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)).isoformat(), 'bad'):
            def api(method, path, token, params=None, payload=None):
                if path.endswith('/conversations'):
                    return {'data': [{'id': 'c', 'participants': {'data': [{'id': 'p'}, {'id': 'r'}]}}]}
                return {'data': [{'from': {'id': 'r'}, 'created_time': time}]}
            self.assertFalse(FacebookClient(api).conversations('secret', 'p')[0]['eligible'])

    def test_repeated_cursor_fails_closed(self):
        api = MagicMock(return_value={'data': [], 'paging': {'next': 'x', 'cursors': {'after': 'same'}}})
        with self.assertRaises(ValueError):
            FacebookClient(api).conversations('secret', 'p')

    def test_recipient_fetches_only_bound_conversation_and_rejects_other_participant(self):
        now = dt.datetime.now(dt.timezone.utc).isoformat()
        api = MagicMock(side_effect=[{'id': 'c', 'participants': {'data': [{'id': 'p'}, {'id': 'r'}]}},
                                    {'data': [{'from': {'id': 'r'}, 'created_time': now}]}])
        self.assertTrue(FacebookClient(api).recipient('secret', 'p', 'r', 'c')['eligible'])
        self.assertEqual(api.call_args_list[0].args[1], 'c')
        api.side_effect = [{'id': 'c', 'participants': {'data': [{'id': 'p'}, {'id': 'other'}]}}, {'data': []}]
        with self.assertRaises(ValueError):
            FacebookClient(api).recipient('secret', 'p', 'r', 'c')

    def test_send_validates_response(self):
        api = MagicMock(return_value={'recipient_id': 'other', 'message_id': 'm'})
        with self.assertRaises(ValueError):
            FacebookClient(api).send('secret', 'p', 'r', 'Hello')


class OutreachTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = OutreachStore(Path(self.temp.name) / 'test.db')
        run = self.store.begin_run([])
        self.store.save_run(run, 'complete', [{'Channel ID': 'a', 'Facebook': 'https://facebook.com/a', 'Email': 'a@example.com'}])
        self.client = MagicMock()
        self.client.page.return_value = {'id': 'p', 'name': 'My Page'}
        self.conversation = {'id': 'c', 'recipient_id': 'r', 'name': 'Creator', 'eligible': True,
                             'last_inbound': dt.datetime.now(dt.timezone.utc).isoformat()}
        self.client.conversations.return_value = [self.conversation]
        self.client.recipient.return_value = self.conversation
        self.client.send.return_value = 'message'
        self.vault = Vault()
        self.outreach = FacebookOutreach(self.store.path, self.vault, self.client)
        self.outreach.connect('secret')
        self.outreach.bind('a', 'p', 'c', 'r')

    def draft(self):
        return self.outreach.prepare('a', {'page_id': 'p', 'body': 'Hello'})

    def test_state_hides_token_and_accepted_send_cleans_all_contacts(self):
        self.assertNotIn('secret', str(self.outreach.state()))
        draft = self.draft()
        result = self.outreach.send(draft['id'])
        self.assertEqual(result['status'], 'accepted')
        self.assertEqual(contact_groups(self.store), [])
        self.assertEqual(self.outreach.history('a')[0]['status'], 'accepted')
        with self.assertRaises(ValueError):
            self.outreach.send(draft['id'])
        self.client.send.assert_called_once()

    def test_timeout_preserves_contacts_and_cannot_retry(self):
        self.client.send.side_effect = TimeoutError('secret')
        draft = self.draft()
        result = self.outreach.send(draft['id'])
        self.assertEqual(result['status'], 'unknown')
        self.assertNotIn('secret', str(result))
        self.assertEqual(len(contact_groups(self.store)), 2)
        with self.assertRaises(ValueError):
            self.outreach.send(draft['id'])
        with self.assertRaises(ValueError):
            self.outreach.prepare('a', {'page_id': 'p', 'body': 'Changed message'})

    def test_expired_disconnected_or_changed_binding_blocks_send(self):
        draft = self.draft()
        self.client.recipient.return_value = {**self.conversation, 'eligible': False}
        with self.assertRaises(ValueError):
            self.outreach.send(draft['id'])
        self.client.send.assert_not_called()

    def test_reject_does_not_clean_queue(self):
        self.client.send.side_effect = FacebookRejected('Rejected')
        self.assertEqual(self.outreach.send(self.draft()['id'])['status'], 'failed')
        self.assertEqual(len(contact_groups(self.store)), 2)

    def test_process_restart_keeps_inflight_claim_without_resubmitting(self):
        draft = self.draft()
        self.outreach.store.claim(draft)
        reopened = FacebookOutreach(self.store.path, self.vault, self.client)
        with self.assertRaises(ValueError):
            reopened.send(draft['id'])
        self.client.send.assert_not_called()
        self.assertEqual(reopened.history('a')[0]['status'], 'sending')
        self.assertEqual(len(contact_groups(self.store)), 2)

    def test_disconnecting_reviewed_page_prevents_submission(self):
        draft = self.draft()
        self.outreach.disconnect('p')
        with self.assertRaises(ValueError):
            self.outreach.send(draft['id'])
        self.client.send.assert_not_called()

    def test_reviewed_binding_cannot_be_replaced_before_submission(self):
        draft = self.draft()
        self.outreach.store.bind('a', 'p', {**self.conversation, 'recipient_id': 'other'})
        with self.assertRaises(ValueError):
            self.outreach.send(draft['id'])
        self.client.send.assert_not_called()

    def test_binding_must_be_saved_facebook_channel_and_real_conversation(self):
        with self.assertRaises(ValueError):
            self.outreach.bind('missing', 'p', 'c', 'r')
        with self.assertRaises(ValueError):
            self.outreach.bind('a', 'p', 'forged', 'r')
        with self.assertRaises(ValueError):
            self.outreach.prepare('a', {'page_id': 'p', 'body': 'x' * 2001})

    def test_concurrent_submission_claims_once(self):
        from concurrent.futures import ThreadPoolExecutor
        draft = self.draft()
        def send():
            try:
                return self.outreach.send(draft['id'])['status']
            except ValueError:
                return 'blocked'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: send(), range(2)))
        self.assertEqual(sorted(results), ['accepted', 'blocked'])
        self.client.send.assert_called_once()

    def test_window_is_rechecked_after_network_verification(self):
        draft = self.draft()
        self.client.recipient.return_value = {**self.conversation, 'eligible': True,
            'last_inbound': (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1, seconds=1)).isoformat()}
        with self.assertRaises(ValueError):
            self.outreach.send(draft['id'])
        self.client.send.assert_not_called()

    def test_binding_updates_wait_for_inflight_send(self):
        import threading
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
        entered, release, started = threading.Event(), threading.Event(), threading.Event()
        def verify(*args):
            entered.set()
            release.wait(3)
            return self.conversation
        self.client.recipient.side_effect = verify
        draft = self.draft()
        def rebind():
            started.set()
            return self.outreach.bind('a', 'p', 'c', 'r')
        with ThreadPoolExecutor(max_workers=2) as pool:
            sending = pool.submit(self.outreach.send, draft['id'])
            self.assertTrue(entered.wait(2))
            binding = pool.submit(rebind)
            self.assertTrue(started.wait(2))
            try:
                with self.assertRaises(FutureTimeout):
                    binding.result(timeout=0.05)
            finally:
                release.set()
            self.assertEqual(sending.result()['status'], 'accepted')
            self.assertTrue(binding.result())
