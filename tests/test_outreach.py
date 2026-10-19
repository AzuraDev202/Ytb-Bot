import base64
import concurrent.futures
from datetime import datetime, timedelta, timezone
from email import policy
from email.parser import BytesParser
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from ytb_bot.core.storage import WorkspaceStore
from ytb_bot.desktop.credential_vault import CredentialVault
from ytb_bot.desktop.gmail import Gmail, SendRejected, client_configuration
from ytb_bot.desktop.outreach import Outreach
from ytb_bot.desktop.api import DesktopAPI


class MemoryVault:
    def __init__(self):
        self.value = {'client': {'installed': {'client_id': 'test-client'}}, 'accounts': {
            'account': {'email': 'sender@example.com', 'credentials': {'token': 'private-token'}}}}

    def read(self):
        return json.loads(json.dumps(self.value))

    def write(self, value):
        self.value = json.loads(json.dumps(value))

    def update(self, change):
        value = self.read()
        result = change(value)
        self.write(value)
        return result


class OutreachTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / 'workspace.sqlite3'
        store = WorkspaceStore(self.path)
        run = store.begin_run(['topic'])
        store.save_run(run, 'complete', [{'Channel ID': 'channel', 'Channel Name': 'Creator',
            'Email': 'creator@example.com', 'Facebook': 'https://facebook.com/creator'}])
        self.gmail = MagicMock()
        self.gmail.access.return_value = 'private-token'
        self.gmail.send.return_value = 'provider-id'
        self.outreach = Outreach(self.path, MemoryVault(), self.gmail)
        self.payload = {'account_id': 'account', 'recipient': 'creator@example.com', 'subject': 'Collaboration \u2603', 'body': 'Hello!\nDiscussion details.'}

    def test_draft_round_trip_and_single_submission_per_revision(self):
        saved = self.outreach.save('channel', self.payload)
        same = self.outreach.save('channel', self.payload)
        self.assertEqual(saved['revision'], same['revision'])
        reopened = Outreach(self.path, self.outreach.vault, self.gmail)
        self.assertEqual(reopened.context('channel')['draft']['body'], self.payload['body'])
        self.assertEqual(reopened.send('channel', saved['revision'])['status'], 'accepted')
        self.gmail.send.assert_called_once_with('private-token', 'sender@example.com', 'creator@example.com', 'Collaboration \u2603', self.payload['body'])
        with self.assertRaises(ValueError):
            reopened.send('channel', saved['revision'])
        self.assertEqual(self.gmail.send.call_count, 1)
        history = reopened.context('channel')['history']
        self.assertEqual((history[0]['status'], history[0]['message_id']), ('accepted', 'provider-id'))
        self.assertNotIn('private-token', str(history))

    def test_concurrent_clicks_claim_only_one_network_submission(self):
        saved = self.outreach.save('channel', self.payload)
        def send():
            try:
                return self.outreach.send('channel', saved['revision'])['status']
            except ValueError:
                return 'blocked'
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: send(), range(2)))
        self.assertCountEqual(results, ['accepted', 'blocked'])
        self.assertEqual(self.gmail.send.call_count, 1)

    def test_individual_send_cannot_duplicate_a_claimed_bulk_recipient(self):
        saved = self.outreach.save('channel', self.payload)
        with self.outreach.store._connection() as db:
            db.execute('INSERT INTO contact_claims VALUES (?,?,?,?)',
                       ('sender@example.com', 'creator@example.com', '2026-10-18', 'bulk:preview'))
        with self.assertRaises(ValueError):
            self.outreach.send('channel', saved['revision'])
        self.gmail.send.assert_not_called()

    def test_timeout_and_rejection_keep_history_and_never_auto_retry(self):
        for failure, expected in [(TimeoutError('private-token'), 'unknown'), (SendRejected('Gmail rejected request'), 'failed')]:
            self.payload['body'] += '\nNew version'
            saved = self.outreach.save('channel', self.payload)
            self.gmail.send.side_effect = failure
            result = self.outreach.send('channel', saved['revision'])
            self.assertEqual(result['status'], expected)
            self.assertNotIn('private-token', str(result))
            count = self.gmail.send.call_count
            with self.assertRaises(ValueError):
                self.outreach.send('channel', saved['revision'])
            self.assertEqual(self.gmail.send.call_count, count)
            self.assertEqual(self.outreach.context('channel')['history'][0]['status'], expected)

    def test_invalid_recipient_headers_accounts_and_stale_draft_are_rejected(self):
        for changes in [{'recipient': 'outsider@example.com'}, {'subject': 'Hello\r\nBcc: outsider@example.com'}, {'body': 'x' * 50001}]:
            with self.subTest(changes=list(changes)):
                with self.assertRaises(ValueError):
                    self.outreach.save('channel', {**self.payload, **changes})
        with self.assertRaises(ValueError):
            self.outreach.save('not-saved', self.payload)
        saved = self.outreach.save('channel', self.payload)
        self.outreach.save('channel', {**self.payload, 'subject': 'Changed'})
        with self.assertRaises(ValueError):
            self.outreach.send('channel', saved['revision'])
        changed = self.outreach.save('channel', {**self.payload, 'account_id': 'unknown'})
        with self.assertRaises(ValueError):
            self.outreach.send('channel', changed['revision'])
        self.gmail.send.assert_not_called()

    def test_only_saved_social_profiles_open_and_are_not_marked_sent(self):
        with patch('ytb_bot.desktop.outreach.webbrowser.open', return_value=True) as browser:
            self.outreach.open_social('channel', 'https://facebook.com/creator')
            browser.assert_called_once()
            with self.assertRaises(ValueError):
                self.outreach.open_social('channel', 'https://evil.test')
        self.assertEqual(self.outreach.context('channel')['history'], [])

    def test_public_account_state_disconnect_and_oauth_connection_do_not_expose_tokens(self):
        self.assertNotIn('private-token', str(self.outreach.state()))
        connected = threading.Event()
        self.gmail.connect.side_effect = lambda _: {'email': 'second@example.com', 'credentials': {'token': 'other-private'}}
        original_write = self.outreach.vault.write
        def write(value):
            original_write(value)
            connected.set()
        self.outreach.vault.write = write
        self.outreach.connect()
        self.assertTrue(connected.wait(3))
        state = self.outreach.state()
        self.assertEqual(len(state['accounts']), 2)
        self.assertNotIn('other-private', str(state))
        self.outreach.disconnect('account')
        self.assertNotIn('account', [account['id'] for account in self.outreach.state()['accounts']])

    def test_gmail_mime_preserves_unicode_and_uses_only_send_endpoint(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"id":"message-123"}'
        with patch('ytb_bot.desktop.gmail.urlopen', return_value=response) as request:
            result = Gmail().send('secret', 'sender@example.com', 'creator@example.com', 'Collaboration \u2603', 'Hello!')
        self.assertEqual(result, 'message-123')
        sent = request.call_args.args[0]
        self.assertEqual(sent.full_url, 'https://gmail.googleapis.com/gmail/v1/users/me/messages/send')
        raw = base64.urlsafe_b64decode(json.loads(sent.data)['raw'])
        message = BytesParser(policy=policy.default).parsebytes(raw)
        self.assertEqual(str(message['Subject']), 'Collaboration \u2603')
        self.assertEqual(message.get_content().strip(), 'Hello!')
        self.assertEqual(message['From'], 'sender@example.com')
        self.assertIsNone(message['Bcc'])

    def test_oauth_import_ignores_untrusted_endpoints_and_requires_desktop_client(self):
        path = Path(self.temporary.name) / 'client.json'
        path.write_text(json.dumps({'installed': {'client_id': '123.apps.googleusercontent.com', 'client_secret': 'secret', 'token_uri': 'https://evil.test'}}))
        result = client_configuration(path)
        self.assertEqual(result['installed']['token_uri'], 'https://oauth2.googleapis.com/token')
        path.write_text(json.dumps({'web': {'client_id': '123.apps.googleusercontent.com', 'client_secret': 'secret'}}))
        with self.assertRaises(ValueError):
            client_configuration(path)

    def test_google_oauth_uses_external_browser_pkce_and_verified_identity(self):
        credentials = MagicMock(id_token='signed-id-token', refresh_token='refresh-token')
        credentials.to_json.return_value = '{"token":"private-token"}'
        with patch('google_auth_oauthlib.flow.InstalledAppFlow.from_client_config') as factory, \
                patch('google.oauth2.id_token.verify_oauth2_token', return_value={'email': 'sender@example.com', 'email_verified': True}) as verify:
            factory.return_value.run_local_server.return_value = credentials
            account = Gmail().connect({'installed': {'client_id': 'client-id'}})
            self.assertEqual(account['email'], 'sender@example.com')
            self.assertTrue(factory.call_args.kwargs['autogenerate_code_verifier'])
            self.assertIn('https://www.googleapis.com/auth/gmail.send', factory.call_args.args[1])
            self.assertNotIn('https://mail.google.com/', factory.call_args.args[1])
            self.assertTrue(factory.return_value.run_local_server.call_args.kwargs['open_browser'])
            self.assertEqual(factory.return_value.run_local_server.call_args.kwargs['port'], 0)
            self.assertEqual(factory.return_value.run_local_server.call_args.kwargs['host'], '127.0.0.1')
            self.assertEqual(factory.return_value.run_local_server.call_args.kwargs['access_type'], 'offline')
            self.assertEqual(verify.call_args.args[2], 'client-id')
            verify.return_value = {'email': 'sender@example.com', 'email_verified': False}
            with self.assertRaises(ValueError):
                Gmail().connect({'installed': {'client_id': 'client-id'}})

    def oauth_account(self, expired=False):
        expiry = datetime.now(timezone.utc) + timedelta(hours=-1 if expired else 1)
        return {'email': 'sender@example.com', 'credentials': {
            'token': 'old-access', 'refresh_token': 'saved-refresh',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': 'desktop-client', 'client_secret': 'desktop-secret',
            'expiry': expiry.strftime('%Y-%m-%dT%H:%M:%SZ')}}

    def test_post_callback_token_timeout_clears_connecting_and_does_not_save_account(self):
        from requests.exceptions import Timeout
        completed = threading.Event()
        self.outreach.gmail = Gmail()
        with patch('google_auth_oauthlib.flow.InstalledAppFlow.from_client_config') as factory:
            flow = factory.return_value
            fetch = flow.fetch_token
            def exchange(**kwargs):
                try:
                    self.assertEqual(kwargs['timeout'], 30)
                finally:
                    completed.set()
                raise Timeout('sensitive-provider-details')
            fetch.side_effect = exchange
            flow.run_local_server.side_effect = lambda **_: flow.fetch_token(code='private-code')
            self.outreach.connect()
            self.assertTrue(completed.wait(3))
            # Synchronize on the worker's final state, not the simulated HTTP response.
            import time
            deadline = time.monotonic() + 3
            while self.outreach.state()['connecting'] and time.monotonic() < deadline:
                time.sleep(0.01)
            state = self.outreach.state()
            self.assertEqual(fetch.call_args.kwargs['timeout'], 30)
        self.assertFalse(state['connecting'])
        self.assertTrue(state['error'])
        self.assertNotIn('sensitive-provider-details', str(state))
        self.assertEqual(len(state['accounts']), 1)

    def test_identity_verification_transport_has_bounded_timeout(self):
        credentials = MagicMock(id_token='signed-id-token', refresh_token='refresh-token')
        credentials.to_json.return_value = '{}'
        with patch('google_auth_oauthlib.flow.InstalledAppFlow.from_client_config') as factory, \
                patch('google.auth.transport.requests.Request') as request, \
                patch('google.oauth2.id_token.verify_oauth2_token') as verify:
            factory.return_value.run_local_server.return_value = credentials
            def identity(token, transport, audience):
                transport('https://www.googleapis.com/oauth2/v1/certs')
                return {'email': 'sender@example.com', 'email_verified': True}
            verify.side_effect = identity
            Gmail().connect({'installed': {'client_id': 'test-client'}})
            self.assertEqual(request.return_value.call_args.kwargs['timeout'], 30)
            message = factory.return_value.run_local_server.call_args.kwargs['success_message']
            self.assertNotIn('Connected.', message)

    def test_valid_access_token_is_reused_without_refresh(self):
        account = self.oauth_account()
        with patch('google.auth.transport.requests.Request') as transport:
            self.assertEqual(Gmail().access(account), 'old-access')
        transport.assert_not_called()

    def test_expired_token_refresh_is_persisted_before_send_and_survives_reopen(self):
        account = self.oauth_account(expired=True)
        self.outreach.vault.value['accounts']['account'] = account
        self.outreach.gmail = Gmail()
        transport = MagicMock()
        transport.return_value.status = 200
        # Google need not return a new refresh token on refresh.
        transport.return_value.data = json.dumps({'access_token': 'new-access',
            'expires_in': 3600, 'token_type': 'Bearer'}).encode()
        def send(token, *args):
            reopened = Outreach(self.path, self.outreach.vault, Gmail())
            saved = reopened.vault.read()['accounts']['account']['credentials']
            self.assertEqual(saved['token'], 'new-access')
            self.assertEqual(saved['refresh_token'], 'saved-refresh')
            self.assertEqual(token, 'new-access')
            return 'provider-id'
        saved = self.outreach.save('channel', self.payload)
        with patch('google.auth.transport.requests.Request', return_value=transport), \
                patch.object(self.outreach.gmail, 'send', side_effect=send):
            self.assertEqual(self.outreach.send('channel', saved['revision'])['status'], 'accepted')
        self.assertEqual(transport.call_count, 1)
        self.assertEqual(transport.call_args.kwargs['url'], 'https://oauth2.googleapis.com/token')
        self.assertIn(b'grant_type=refresh_token', transport.call_args.kwargs['body'])

    def test_revoked_refresh_token_blocks_send_without_exposing_provider_details(self):
        self.outreach.vault.value['accounts']['account'] = self.oauth_account(expired=True)
        self.outreach.gmail = Gmail()
        transport = MagicMock()
        transport.return_value.status = 400
        transport.return_value.data = b'{"error":"invalid_grant","error_description":"saved-refresh revoked"}'
        saved = self.outreach.save('channel', self.payload)
        with patch('google.auth.transport.requests.Request', return_value=transport), \
                patch.object(self.outreach.gmail, 'send') as send:
            with self.assertRaisesRegex(ValueError, '^Unable to refresh sign-in. Reconnect the Gmail account.$'):
                self.outreach.send('channel', saved['revision'])
        send.assert_not_called()
        self.assertEqual(self.outreach.context('channel')['history'], [])

    def test_connection_requires_refresh_token_for_offline_access(self):
        credentials = MagicMock(id_token='signed-id-token', refresh_token=None)
        with patch('google_auth_oauthlib.flow.InstalledAppFlow.from_client_config') as factory, \
                patch('google.oauth2.id_token.verify_oauth2_token', return_value={'email': 'sender@example.com', 'email_verified': True}):
            factory.return_value.run_local_server.return_value = credentials
            with self.assertRaises(ValueError):
                Gmail().connect({'installed': {'client_id': 'client-id'}})

    @unittest.skipUnless(os.name == 'nt', 'Windows DPAPI')
    def test_windows_vault_encrypts_and_reopens_credentials(self):
        path = Path(self.temporary.name) / 'credentials.bin'
        vault = CredentialVault(path)
        vault.write({'client': None, 'accounts': {'token': 'very-private-refresh-token'}})
        self.assertNotIn(b'very-private-refresh-token', path.read_bytes())
        self.assertEqual(CredentialVault(path).read()['accounts']['token'], 'very-private-refresh-token')

    def test_unsaved_draft_and_active_send_block_update(self):
        api = DesktopAPI(self.temporary.name)
        self.assertTrue(api.set_contact_dirty(True)['ok'])
        self.assertFalse(api.install_available_update()['ok'])
        self.assertFalse(api.set_contact_dirty('invalid')['ok'])
        api.set_contact_dirty(False)
        api._contact_sending = True
        self.assertIn('Gmail', api.install_available_update()['error'])
