"""Page accounts, explicit recipient association and reviewed Messenger sends."""
import threading

from ytb_bot.core.contact_completion import ContactCompletion
from ytb_bot.core.contacts import extract_contacts
from ytb_bot.core.facebook_store import FacebookStore
from ytb_bot.desktop.credential_vault import CredentialVault
from ytb_bot.desktop.facebook import FacebookClient, FacebookRejected, TEXT_LIMIT, within_window


class FacebookOutreach:
    def __init__(self, path, vault=None, client=None):
        self.store = FacebookStore(path)
        self.vault = vault or CredentialVault(self.store.path.parent / 'facebook' / 'credentials.bin')
        self.client = client or FacebookClient()
        self._lock = threading.RLock()

    def state(self):
        return {'accounts': [{'id': key, 'name': value['name']} for key, value in self.vault.read()['accounts'].items()]}

    def connect(self, token):
        if not isinstance(token, str) or not token.strip() or len(token) > 8192 or any(c.isspace() for c in token):
            raise ValueError('Enter a valid Page access token.')
        try:
            page = self.client.page(token)
        except Exception:
            raise ValueError('Unable to connect the Page. Check the Page token and messaging permissions.') from None
        with self._lock:
            self.vault.update(lambda value: value['accounts'].update({page['id']: {'name': page['name'], 'token': token}}))
        return self.state()

    def disconnect(self, page_id):
        with self._lock:
            self.vault.update(lambda value: value['accounts'].pop(page_id, None))
        return self.state()

    def _account(self, page_id):
        account = self.vault.read()['accounts'].get(page_id)
        if not account:
            raise ValueError('Connect the selected Fanpage first.')
        return account

    def conversations(self, page_id):
        account = self._account(page_id)
        try:
            return self.client.conversations(account['token'], page_id)
        except Exception:
            raise ValueError('Unable to load Page conversations. Check permissions and reconnect the Page.') from None

    def bind(self, channel_id, page_id, conversation_id, recipient_id):
        with self._lock:
            return self._bind(channel_id, page_id, conversation_id, recipient_id)

    def _bind(self, channel_id, page_id, conversation_id, recipient_id):
        row = self.store.channel(channel_id)
        if not extract_contacts(str(row.get('Facebook') or '')).get('Facebook'):
            raise ValueError('The saved channel has no Facebook contact.')
        conversation = next((item for item in self.conversations(page_id)
                             if item['id'] == conversation_id and item['recipient_id'] == recipient_id), None)
        if not conversation:
            raise ValueError('Choose a verified Page conversation for this channel.')
        self.store.bind(channel_id, page_id, conversation)
        return True

    def prepare(self, channel_id, payload):
        if not isinstance(payload, dict):
            raise ValueError('Invalid Messenger draft.')
        body, page_id = payload.get('body'), payload.get('page_id')
        if not isinstance(body, str) or not body.strip() or len(body) > TEXT_LIMIT or not isinstance(page_id, str):
            raise ValueError('Enter a Messenger message between 1 and 2,000 characters.')
        if channel_id in ContactCompletion(self.store).completed_ids():
            raise ValueError('This channel has already been contacted.')
        self.store.channel(channel_id)
        account = self._account(page_id)
        binding = self.store.binding(channel_id, page_id)
        if not binding or not binding['eligible']:
            raise ValueError('Link an eligible Page conversation before reviewing.')
        if self.store.attempted(page_id, binding['recipient_id']):
            raise ValueError('This Page recipient already has a send attempt. Check the Page inbox before further contact.')
        return self.store.prepare({'channel_id': channel_id, 'page_id': page_id, 'page_name': account['name'],
            'conversation_id': binding['id'], 'recipient_id': binding['recipient_id'], 'recipient_name': binding['name'], 'body': body})

    def send(self, draft_id):
        # Serialize disconnect/rebinding and sends in this process; the SQL unique
        # recipient constraint also prevents duplicate sends from other processes.
        with self._lock:
            draft = self.store.draft(draft_id)
            account = self._account(draft['page_id'])
            binding = self.store.binding(draft['channel_id'], draft['page_id'])
            if not binding or binding['id'] != draft['conversation_id'] or binding['recipient_id'] != draft['recipient_id']:
                raise ValueError('The recipient changed. Review a new message.')
            try:
                current = self.client.recipient(account['token'], draft['page_id'], draft['recipient_id'], draft['conversation_id'])
            except Exception:
                raise ValueError('Unable to verify recipient eligibility. Refresh Page conversations.') from None
            if not current['eligible'] or not within_window(current.get('last_inbound')) or current['id'] != draft['conversation_id']:
                raise ValueError('The standard 24-hour messaging window is closed or cannot be verified.')
            if draft['channel_id'] in ContactCompletion(self.store).completed_ids():
                raise ValueError('This channel has already been contacted.')
            self.store.claim(draft)
            try:
                message = self.client.send(account['token'], draft['page_id'], draft['recipient_id'], draft['body'])
            except FacebookRejected:
                self.store.finish(draft_id, 'failed')
                return {'status': 'failed', 'message': 'Meta rejected the request. Check Page permissions and messaging eligibility.'}
            except Exception:
                self.store.finish(draft_id, 'unknown')
                return {'status': 'unknown', 'message': 'Messenger outcome is uncertain. Check the Page inbox before further contact.'}
            self.store.finish(draft_id, 'accepted', message)
            return {'status': 'accepted', 'message': 'Messenger accepted the request. Delivery is not confirmed.'}

    def history(self, channel_id):
        return self.store.history(channel_id)
