"""Minimal Gmail OAuth adapter: identity, refresh and one explicit send request."""
import base64
from email.message import EmailMessage
from email.policy import SMTP
from functools import partial
import json
import logging
import re
from urllib.error import HTTPError
from urllib.request import Request, urlopen

SCOPES = ['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/gmail.send']
OAUTH_REQUEST_TIMEOUT = 30
IDENTITY_CLOCK_SKEW_SECONDS = 10


def register_scope_validation(session):
    """Validate required grants before OAuthLib compares the returned scope set.

    Google can return a superset of previously granted scopes or OIDC aliases.
    Keep the actual granted scopes without relaxing validation process-wide.
    """
    def validate(response):
        if response.status_code != 200:
            return response
        payload = response.json()
        if 'error' in payload or 'scope' not in payload:
            return response
        raw = payload['scope']
        granted = raw.split() if isinstance(raw, str) else raw
        if not isinstance(granted, list) or not all(isinstance(scope, str) for scope in granted):
            raise ValueError('Google did not grant the required Gmail and identity permissions. Reconnect and allow all requested permissions.')
        aliases = {'email': 'https://www.googleapis.com/auth/userinfo.email'}
        normalized = {aliases.get(scope, scope) for scope in granted}
        if not set(SCOPES).issubset(normalized):
            raise ValueError('Google did not grant the required Gmail and identity permissions. Reconnect and allow all requested permissions.')
        session.scope = granted
        return response
    session.register_compliance_hook('access_token_response', validate)


def client_configuration(path):
    from pathlib import Path
    source = Path(path)
    if source.stat().st_size > 128_000:
        raise ValueError('The configuration file is too large.')
    raw = json.loads(source.read_text(encoding='utf-8-sig')).get('installed', {})
    client_id, secret = raw.get('client_id', ''), raw.get('client_secret', '')
    if not isinstance(client_id, str) or not re.fullmatch(r'[a-zA-Z0-9._-]+\.apps\.googleusercontent\.com', client_id) or not isinstance(secret, str) or not 1 <= len(secret) <= 4096:
        raise ValueError('Select a Google OAuth Client JSON file for a Desktop app.')
    # Never trust endpoints supplied by a local configuration file.
    return {'installed': {'client_id': client_id, 'client_secret': secret,
            'auth_uri': 'https://accounts.google.com/o/oauth2/v2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token', 'redirect_uris': ['http://localhost']}}


class Gmail:
    def connect(self, client):
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request as GoogleRequest
        from google.oauth2 import id_token
        # The library's INFO request log contains the loopback authorization code.
        logging.getLogger('google_auth_oauthlib.flow').disabled = True
        flow = InstalledAppFlow.from_client_config(client, SCOPES, autogenerate_code_verifier=True)
        register_scope_validation(flow.oauth2session)
        # run_local_server's timeout only covers the callback, not token exchange.
        flow.fetch_token = partial(flow.fetch_token, timeout=OAUTH_REQUEST_TIMEOUT)
        # Desktop loopback flow: https://developers.google.com/identity/protocols/oauth2/native-app
        credentials = flow.run_local_server(host='127.0.0.1', port=0, timeout_seconds=180, open_browser=True,
            authorization_prompt_message='', success_message='YTB-BOT: Google response received. Return to the app to check whether account connection completed. You can close this tab.',
            access_type='offline', prompt='consent select_account')
        identity = id_token.verify_oauth2_token(credentials.id_token,
            partial(GoogleRequest(), timeout=OAUTH_REQUEST_TIMEOUT), client['installed']['client_id'],
            clock_skew_in_seconds=IDENTITY_CLOCK_SKEW_SECONDS)
        if not identity.get('email_verified') or not credentials.refresh_token:
            raise ValueError('The account could not be verified or offline access was not granted.')
        return {'email': identity['email'], 'credentials': json.loads(credentials.to_json())}

    def access(self, account):
        from google.auth.transport.requests import Request as GoogleRequest
        from google.oauth2.credentials import Credentials
        credentials = Credentials.from_authorized_user_info(account['credentials'], SCOPES)
        if not credentials.valid:
            credentials.refresh(GoogleRequest())
        account['credentials'] = json.loads(credentials.to_json())
        return credentials.token

    def send(self, token, sender, recipient, subject, body):
        message = EmailMessage(policy=SMTP)
        message['From'], message['To'], message['Subject'] = sender, recipient, subject
        message.set_content(body)
        request = Request('https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
            data=json.dumps({'raw': base64.urlsafe_b64encode(message.as_bytes()).decode('ascii')}).encode(),
            headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}, method='POST')
        # No automatic retries: a timeout can happen after Google accepted mail.
        try:
            with urlopen(request, timeout=30) as response:
                result = json.load(response)
        except HTTPError as error:
            if 400 <= error.code < 500 and error.code != 408:
                raise SendRejected(f'Gmail rejected the request (HTTP {error.code}). Check send permissions and the account.') from None
            raise
        if not result.get('id'):
            raise RuntimeError('Missing provider message ID')
        return result['id']


class SendRejected(Exception):
    pass
