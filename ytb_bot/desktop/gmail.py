"""Minimal Gmail OAuth adapter: identity, refresh and one explicit send request."""
import base64
from email.message import EmailMessage
from email.policy import SMTP
import json
import logging
import re
from urllib.error import HTTPError
from urllib.request import Request, urlopen

SCOPES = ['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/gmail.send']


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
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token', 'redirect_uris': ['http://localhost']}}


class Gmail:
    def connect(self, client):
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request as GoogleRequest
        from google.oauth2 import id_token
        # The library's INFO request log contains the loopback authorization code.
        logging.getLogger('google_auth_oauthlib.flow').disabled = True
        flow = InstalledAppFlow.from_client_config(client, SCOPES, autogenerate_code_verifier=True)
        credentials = flow.run_local_server(port=0, timeout_seconds=180, open_browser=True,
            authorization_prompt_message='', success_message='YTB-BOT: Connected. You can close this tab.',
            access_type='offline', prompt='consent select_account')
        identity = id_token.verify_oauth2_token(credentials.id_token, GoogleRequest(), client['installed']['client_id'])
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
