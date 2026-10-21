"""Contact composition and explicit Gmail submission, independent of the UI."""
import hashlib
import threading
import webbrowser

from ytb_bot.core.contacts import extract_contacts, is_email
from ytb_bot.core.outreach_store import OutreachStore
from ytb_bot.desktop.credential_vault import CredentialVault
from ytb_bot.desktop.gmail import Gmail, SendRejected, client_configuration


class Outreach:
    def __init__(self, path, vault=None, gmail=None):
        self.store = OutreachStore(path)
        self.vault = vault or CredentialVault(self.store.path.parent / 'mail' / 'credentials.bin')
        self.gmail = gmail or Gmail()
        self._lock = threading.RLock()
        self._connecting, self._error = False, ''

    def state(self):
        with self._lock:
            value = self.vault.read()
            return {'configured': bool(value['client']), 'connecting': self._connecting, 'error': self._error,
                    'accounts': [{'id': key, 'email': account['email']} for key, account in value['accounts'].items()]}

    def configure(self, path):
        client = client_configuration(path)
        with self._lock:
            if self._connecting:
                raise ValueError('Wait for the current account connection to finish.')
            # Existing accounts retain their own OAuth client in credentials.
            self.vault.update(lambda value: value.update({'client': client}))
        return self.state()

    def connect(self):
        with self._lock:
            if self._connecting:
                return False
            client = self.vault.read()['client']
            if not client:
                raise ValueError('Import a Google Desktop OAuth Client file before connecting.')
            self._connecting, self._error = True, ''
        def worker():
            try:
                account = self.gmail.connect(client)
                if not is_email(account['email']):
                    raise ValueError('Invalid account identity')
                key = hashlib.sha256(account['email'].casefold().encode()).hexdigest()
                with self._lock:
                    self.vault.update(lambda value: value['accounts'].update({key: account}))
            except Exception:
                with self._lock:
                    self._error = 'Unable to connect to Gmail. Check the configuration, send permissions, and test account, then try again. The sign-in session expires after 3 minutes.'
            finally:
                with self._lock:
                    self._connecting = False
        threading.Thread(target=worker, daemon=True).start()
        return True

    def disconnect(self, account_id):
        with self._lock:
            self.vault.update(lambda value: value['accounts'].pop(account_id, None))
        return self.state()

    def context(self, channel_id):
        from ytb_bot.core.email_history import email_records, BLOCKED
        channel = self.store.channel(channel_id)
        with self.store._connection() as db:
            blocked = bool(db.execute('SELECT 1 FROM email_channel_claims WHERE channel_id=?', (channel_id,)).fetchone()) or any(
                row['channel_id'] == channel_id and row['status'] in BLOCKED for row in email_records(db))
        contacts = extract_contacts('\n'.join(str(channel.get(key) or '') for key in ['Email', 'Facebook', 'Other Contacts']))
        options = [{'kind': 'email' if kind == 'Email' else 'social', 'label': kind, 'value': value}
                   for kind, text in contacts.items() for value in text.splitlines() if value]
        return {'channel_id': channel_id, 'name': channel.get('Channel Name', channel_id), 'contacts': options,
                'draft': self.store.draft(channel_id), 'history': self.store.history(channel_id), 'email_blocked': blocked}

    def save(self, channel_id, payload):
        context = self.context(channel_id)
        if not isinstance(payload, dict):
            raise ValueError('Invalid draft.')
        clean = {key: payload.get(key, '') for key in ['recipient', 'account_id', 'subject', 'body']}
        if any(not isinstance(value, str) for value in clean.values()) or len(clean['subject']) > 200 or len(clean['body']) > 50_000:
            raise ValueError('The subject can contain up to 200 characters and the body up to 50,000 characters.')
        if any(character in clean['subject'] for character in '\r\n'):
            raise ValueError('The subject must not contain line breaks.')
        if clean['recipient'] and clean['recipient'] not in [item['value'] for item in context['contacts']]:
            raise ValueError('Select a contact from the saved channel data.')
        return self.store.save_draft(channel_id, clean)

    def send(self, channel_id, revision):
        # Read and validate first; claim the exact immutable revision before I/O.
        draft = self.store.draft(channel_id)
        if not draft or draft['revision'] != revision:
            raise ValueError('Save and review the draft before sending.')
        if not draft['subject'].strip() or not draft['body'].strip():
            raise ValueError('Enter an email subject and body.')
        recipients = [contact['value'] for contact in self.context(channel_id)['contacts'] if contact['kind'] == 'email']
        if draft['recipient'] not in recipients:
            raise ValueError('The recipient must be a saved email address for this channel.')
        with self._lock:
            def refresh(value):
                account = value['accounts'].get(draft['account_id'])
                if not account:
                    raise ValueError('Select a connected Gmail account.')
                try:
                    token = self.gmail.access(account)
                except Exception:
                    raise ValueError('Unable to refresh sign-in. Reconnect the Gmail account.') from None
                return token, account
            # Refresh writes must not restore accounts removed in another app.
            token, account = self.vault.update(refresh)
        attempt, snapshot = self.store.claim(channel_id, revision, account['email'])
        try:
            message_id = self.gmail.send(token, account['email'], snapshot['recipient'], snapshot['subject'], snapshot['body'])
        except SendRejected as error:
            self.store.finish(attempt, 'failed')
            return {'status': 'failed', 'message': str(error)}
        except Exception:
            self.store.finish(attempt, 'unknown')
            return {'status': 'unknown', 'message': 'It is unknown whether Gmail accepted the email. Check Sent in Gmail before sending again.'}
        self.store.finish(attempt, 'accepted', message_id)
        return {'status': 'accepted', 'message': 'Gmail accepted the send request. This status does not confirm delivery to the recipient.'}

    def open_social(self, channel_id, target):
        if target not in [contact['value'] for contact in self.context(channel_id)['contacts'] if contact['kind'] == 'social']:
            raise ValueError('Only saved contact links for this channel can be opened.')
        if not webbrowser.open(target):
            raise ValueError('Unable to open the browser. Copy the link and open it manually.')
        return True
