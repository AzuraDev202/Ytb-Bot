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
                raise ValueError('Chờ kết nối tài khoản hiện tại hoàn tất.')
            value = self.vault.read()
            # Existing accounts retain their own OAuth client in credentials.
            value['client'] = client
            self.vault.write(value)
        return self.state()

    def connect(self):
        with self._lock:
            if self._connecting:
                return False
            client = self.vault.read()['client']
            if not client:
                raise ValueError('Nhập file OAuth Client Desktop của Google trước khi kết nối.')
            self._connecting, self._error = True, ''
        def worker():
            try:
                account = self.gmail.connect(client)
                if not is_email(account['email']):
                    raise ValueError('Invalid account identity')
                key = hashlib.sha256(account['email'].casefold().encode()).hexdigest()
                with self._lock:
                    value = self.vault.read()
                    value['accounts'][key] = account
                    self.vault.write(value)
            except Exception:
                with self._lock:
                    self._error = 'Chưa kết nối được Gmail. Kiểm tra cấu hình, quyền gửi và tài khoản thử nghiệm rồi thử lại. Phiên đăng nhập hết hạn sau 3 phút.'
            finally:
                with self._lock:
                    self._connecting = False
        threading.Thread(target=worker, daemon=True).start()
        return True

    def disconnect(self, account_id):
        with self._lock:
            value = self.vault.read()
            value['accounts'].pop(account_id, None)
            self.vault.write(value)
        return self.state()

    def context(self, channel_id):
        channel = self.store.channel(channel_id)
        contacts = extract_contacts('\n'.join(str(channel.get(key) or '') for key in ['Email', 'Facebook', 'Liên Hệ Khác']))
        options = [{'kind': 'email' if kind == 'Email' else 'social', 'label': kind, 'value': value}
                   for kind, text in contacts.items() for value in text.splitlines() if value]
        return {'channel_id': channel_id, 'name': channel.get('Tên Kênh', channel_id), 'contacts': options,
                'draft': self.store.draft(channel_id), 'history': self.store.history(channel_id)}

    def save(self, channel_id, payload):
        context = self.context(channel_id)
        if not isinstance(payload, dict):
            raise ValueError('Bản nháp không hợp lệ.')
        clean = {key: payload.get(key, '') for key in ['recipient', 'account_id', 'subject', 'body']}
        if any(not isinstance(value, str) for value in clean.values()) or len(clean['subject']) > 200 or len(clean['body']) > 50_000:
            raise ValueError('Tiêu đề tối đa 200 ký tự, nội dung tối đa 50.000 ký tự.')
        if any(character in clean['subject'] for character in '\r\n'):
            raise ValueError('Tiêu đề không được chứa xuống dòng.')
        if clean['recipient'] and clean['recipient'] not in [item['value'] for item in context['contacts']]:
            raise ValueError('Chọn liên hệ trong dữ liệu đã lưu của kênh.')
        return self.store.save_draft(channel_id, clean)

    def send(self, channel_id, revision):
        # Read and validate first; claim the exact immutable revision before I/O.
        draft = self.store.draft(channel_id)
        if not draft or draft['revision'] != revision:
            raise ValueError('Lưu và xem lại bản nháp trước khi gửi.')
        if not draft['subject'].strip() or not draft['body'].strip():
            raise ValueError('Nhập tiêu đề và nội dung email.')
        recipients = [contact['value'] for contact in self.context(channel_id)['contacts'] if contact['kind'] == 'email']
        if draft['recipient'] not in recipients:
            raise ValueError('Người nhận phải là email đã lưu của kênh.')
        with self._lock:
            value = self.vault.read()
            account = value['accounts'].get(draft['account_id'])
            if not account:
                raise ValueError('Chọn tài khoản Gmail đã kết nối.')
            try:
                token = self.gmail.access(account)
            except Exception:
                raise ValueError('Không làm mới được đăng nhập. Kết nối lại tài khoản Gmail.') from None
            self.vault.write(value)
        attempt, snapshot = self.store.claim(channel_id, revision)
        try:
            message_id = self.gmail.send(token, account['email'], snapshot['recipient'], snapshot['subject'], snapshot['body'])
        except SendRejected as error:
            self.store.finish(attempt, 'failed')
            return {'status': 'failed', 'message': str(error)}
        except Exception:
            self.store.finish(attempt, 'unknown')
            return {'status': 'unknown', 'message': 'Chưa rõ Gmail đã nhận thư hay chưa. Kiểm tra thư Đã gửi trong Gmail trước khi gửi lại.'}
        self.store.finish(attempt, 'accepted', message_id)
        return {'status': 'accepted', 'message': 'Gmail đã nhận yêu cầu gửi. Trạng thái này không xác nhận thư đã đến người nhận.'}

    def open_social(self, channel_id, target):
        if target not in [contact['value'] for contact in self.context(channel_id)['contacts'] if contact['kind'] == 'social']:
            raise ValueError('Chỉ mở liên kết liên hệ đã lưu của kênh.')
        if not webbrowser.open(target):
            raise ValueError('Không mở được trình duyệt. Sao chép liên kết và mở thủ công.')
        return True
