import json
import unittest
from unittest.mock import patch, MagicMock
import time
from requests import Response, Request
from requests_oauthlib import OAuth2Session
from ytb_bot.desktop.gmail import SCOPES


class GmailScopeTests(unittest.TestCase):
    def test_identity_accepts_small_clock_skew_but_rejects_large_skew_and_expiry(self):
        from google.auth import jwt, exceptions
        from ytb_bot.desktop.gmail import Gmail
        credentials = MagicMock(id_token='signed-token', refresh_token='refresh-token')
        credentials.to_json.return_value = '{}'
        issued = int(time.time()) + 2
        expiry = issued + 3600
        def verify(token, request, audience, clock_skew_in_seconds=0):
            jwt._verify_iat_and_exp({'iat': issued, 'exp': expiry}, clock_skew_in_seconds)
            return {'email': 'sender@example.com', 'email_verified': True}
        with patch('google_auth_oauthlib.flow.InstalledAppFlow.from_client_config') as factory, \
                patch('google.oauth2.id_token.verify_oauth2_token', side_effect=verify):
            factory.return_value.run_local_server.return_value = credentials
            self.assertEqual(Gmail().connect({'installed': {'client_id': 'client'}})['email'], 'sender@example.com')
            issued = int(time.time()) + 60
            with self.assertRaises(exceptions.InvalidValue):
                Gmail().connect({'installed': {'client_id': 'client'}})
            issued, expiry = int(time.time()) - 3600, int(time.time()) - 60
            with self.assertRaises(exceptions.InvalidValue):
                Gmail().connect({'installed': {'client_id': 'client'}})

    def exchange(self, scopes, validate=True):
        from ytb_bot.desktop.gmail import register_scope_validation
        session = OAuth2Session('desktop-client', scope=SCOPES)
        if validate:
            register_scope_validation(session)
        response = Response()
        response.status_code = 200
        response.request = Request('POST', 'https://oauth2.googleapis.com/token').prepare()
        response._content = json.dumps({'access_token': 'test-access', 'refresh_token': 'test-refresh',
            'token_type': 'Bearer', 'expires_in': 3600, 'scope': ' '.join(scopes)}).encode()
        with patch.object(session, 'request', return_value=response):
            return session.fetch_token('https://oauth2.googleapis.com/token', code='test-code')

    def test_extra_previously_granted_scopes_do_not_abort_token_exchange(self):
        with self.assertRaisesRegex(Warning, 'Scope has changed'):
            self.exchange([*SCOPES, 'https://www.googleapis.com/auth/userinfo.profile'], validate=False)
        token = self.exchange([*SCOPES, 'https://www.googleapis.com/auth/userinfo.profile'])
        self.assertEqual(token['access_token'], 'test-access')

    def test_google_email_scope_alias_is_accepted(self):
        self.assertEqual(self.exchange(['openid', 'email', SCOPES[-1]])['refresh_token'], 'test-refresh')

    def test_partial_grants_are_rejected(self):
        for scopes in [SCOPES[:-1], SCOPES[1:], ['openid', SCOPES[-1]]]:
            with self.subTest(scopes=scopes), self.assertRaisesRegex(ValueError, 'required Gmail'):
                self.exchange(scopes)
