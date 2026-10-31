"""Reviewed bulk mail with durable claims and one sequential worker."""
import os
import threading
from ytb_bot.core.bulk_store import BulkStore
from ytb_bot.core.contact_groups import contact_groups
from ytb_bot.core.contacts import is_email
from ytb_bot.desktop.gmail import SendRejected


class WorkerLock:
    """An OS-owned lock: process death releases it without PID probing."""
    def __init__(self, path):
        self.path, self.file = str(path) + '.bulk.lock', None

    def acquire(self):
        handle = open(self.path, 'a+b')
        try:
            handle.seek(0)
            if os.name == 'nt':
                import msvcrt
                if not os.path.getsize(self.path):
                    handle.write(b'0')
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError):
            handle.close()
            return False
        self.file = handle
        return True

    def release(self):
        if self.file:
            if os.name == 'nt':
                import msvcrt
                self.file.seek(0)
                msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file, fcntl.LOCK_UN)
            self.file.close()
            self.file = None


class BulkOutreach:
    def __init__(self, outreach, interval=2):
        self.outreach = outreach
        self.store = BulkStore(outreach.store.path)
        self.interval = interval
        self._mutex = threading.RLock()
        self._stop = threading.Event()
        self._thread = None
        self._active_id = None
        self._recover()

    def _recover(self):
        lock = WorkerLock(self.store.path)
        if lock.acquire():
            try:
                for batch in self.store.list():
                    if batch['status'] == 'running' or any(row['status'] == 'sending' for row in batch['recipients']):
                        def interrupt(value):
                            if value['status'] == 'running':
                                value['status'] = 'interrupted'
                            for row in value['recipients']:
                                if row['status'] == 'sending':
                                    row['status'] = 'unknown'
                                elif row['status'] == 'pending':
                                    row['status'] = 'canceled'
                        self.store.change(batch['id'], interrupt)
            finally:
                lock.release()

    @property
    def is_running(self):
        return bool(self._thread and self._thread.is_alive())

    def active(self):
        lock = WorkerLock(self.store.path)
        if not lock.acquire():
            return True
        lock.release()
        return False

    def groups(self):
        groups = contact_groups(self.outreach.store)
        history = self.store.list()
        with self.outreach.store._connection() as db:
            attempts = db.execute('SELECT created,status,payload FROM mail_attempts ORDER BY created DESC').fetchall()
        for group in groups:
            events = []
            for batch in history:
                for row in batch['recipients']:
                    if group['kind'] == 'email' and row['email'] == group['value'] and row['status'] not in ('pending', 'skipped', 'canceled'):
                        events.append((batch['created'], row['status']))
            import json
            for attempt in attempts:
                if json.loads(attempt['payload']).get('recipient', '').casefold() == group['value']:
                    events.append((attempt['created'], attempt['status']))
            if events:
                group['last_created'], group['last_status'] = max(events)
        return groups

    def remove_failed_contacts(self, group_ids):
        if not isinstance(group_ids, list) or not 1 <= len(group_ids) <= 100 or not all(isinstance(key, str) for key in group_ids):
            raise ValueError('Select between 1 and 100 unique email groups.')
        with self._mutex:
            if self.is_running:
                raise ValueError('Stop the bulk send before removing failed contacts.')
            selected = set(group_ids)
            emails = {group['value'] for group in self.groups() if group['id'] in selected
                      and group['kind'] == 'email' and group['last_status'] == 'failed'}
            with self.store._connection() as db:
                db.executemany('INSERT OR IGNORE INTO removed_email_contacts VALUES (?)', [(email,) for email in emails])
            return len(emails)

    def prepare(self, payload):
        if not isinstance(payload, dict):
            raise ValueError('Invalid batch draft.')
        ids = payload.get('group_ids')
        if not isinstance(ids, list) or not 1 <= len(ids) <= 100 or any(not isinstance(key, str) for key in ids) or len(set(ids)) != len(ids):
            raise ValueError('Select between 1 and 100 unique email groups.')
        for field, limit in (('subject', 200), ('body', 50000), ('account_id', 256)):
            value = payload.get(field)
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise ValueError('Enter a valid account, subject (200 characters) and body (50,000 characters).')
        if '\r' in payload['subject'] or '\n' in payload['subject']:
            raise ValueError('The subject must not contain line breaks.')
        account = self.outreach.vault.read()['accounts'].get(payload['account_id'])
        if not account or not is_email(account.get('email')):
            raise ValueError('Select a connected Gmail account.')
        groups = {group['id']: group for group in self.groups()}
        if any(key not in groups or groups[key]['kind'] != 'email' for key in ids):
            raise ValueError('Only saved email groups can be selected.')
        attempted = self.store.attempted(account['email'], payload['account_id'])
        recipients = [{'email': groups[key]['value'], 'channels': groups[key]['channels'],
            'status': 'skipped' if groups[key]['value'] in attempted else 'pending', 'message_id': '',
            'error': 'Previously attempted for this sender.' if groups[key]['value'] in attempted else ''} for key in ids]
        return self.store.create({'account_id': payload['account_id'], 'sender': account['email'],
            'subject': payload['subject'], 'body': payload['body'], 'recipients': recipients})

    def get(self, batch_id=None):
        return self.store.get(batch_id)

    def list(self):
        return self.store.list()

    def start(self, batch_id):
        with self._mutex:
            lock = WorkerLock(self.store.path)
            if not lock.acquire():
                raise ValueError('A mail batch is already running.')
            try:
                def claim(value):
                    if value['status'] != 'draft':
                        raise ValueError('This batch already started. Prepare and review a new draft.')
                    account = self.outreach.vault.read()['accounts'].get(value['account_id'])
                    if not account or account['email'] != value['sender']:
                        raise ValueError('The reviewed sender is no longer connected.')
                    value['status'] = 'running'
                batch = self.store.change(batch_id, claim)
                self._active_id = batch_id
                self._stop.clear()
                self._thread = threading.Thread(target=self._worker, args=(batch_id, lock), daemon=True)
                self._thread.start()
                return batch
            except Exception:
                lock.release()
                raise

    def stop(self, batch_id=None):
        if batch_id is None:
            batch_id = self._active_id
            if batch_id is None:
                return None
        def stop(value):
            if value['status'] in ('draft', 'running'):
                value['status'] = 'stopped'
                for row in value['recipients']:
                    if row['status'] == 'pending':
                        row['status'] = 'canceled'
        result = self.store.change(batch_id, stop)
        if batch_id == self._active_id:
            self._stop.set()
        return result

    def _worker(self, batch_id, lock):
        try:
            batch = self.store.get(batch_id)
            sent = False
            for index, recipient in enumerate(batch['recipients']):
                if recipient['status'] != 'pending':
                    continue
                if sent:
                    self._stop.wait(self.interval)
                current = self.store.get(batch_id)
                if current['status'] != 'running':
                    break
                attempted = self.store.attempted(batch['sender'], batch['account_id'])
                if recipient['email'] in attempted or not self.store.claim_contact(batch['sender'], recipient['email'], batch_id, batch['account_id'], [channel['id'] for channel in recipient['channels']]):
                    self.store.change(batch_id, lambda value: value['recipients'][index].update(status='skipped', error='Previously attempted for this sender.'))
                    continue
                def sending(value):
                    if value['status'] != 'running':
                        raise ValueError('Batch stopped.')
                    value['recipients'][index]['status'] = 'sending'
                self.store.change(batch_id, sending)
                try:
                    def refresh(value):
                        account = value['accounts'].get(batch['account_id'])
                        if not account or account['email'] != batch['sender']:
                            raise ValueError('Sender account disconnected.')
                        return self.outreach.gmail.access(account)
                    token = self.outreach.vault.update(refresh)
                except Exception:
                    self._failed(batch_id, index, 'failed', 'Unable to refresh Gmail sign-in.')
                    break
                try:
                    message = self.outreach.gmail.send(token, batch['sender'], recipient['email'], batch['subject'], batch['body'])
                except SendRejected:
                    self._failed(batch_id, index, 'failed', 'Gmail rejected the request. Check the account and permissions.')
                    break
                except Exception:
                    self._failed(batch_id, index, 'unknown', 'Acceptance is unknown. Check Gmail Sent before any further contact.')
                    break
                self.store.change(batch_id, lambda value: value['recipients'][index].update(status='accepted', message_id=message))
                sent = True
            self.store.change(batch_id, lambda value: value.update(status='completed') if value['status'] == 'running' else None)
        except Exception:
            def error(value):
                value['status'], value['error'] = 'error', 'Batch stopped safely. Review recipient statuses before further contact.'
                for row in value['recipients']:
                    if row['status'] == 'sending':
                        row['status'] = 'unknown'
                    elif row['status'] == 'pending':
                        row['status'] = 'canceled'
            self.store.change(batch_id, error)
        finally:
            lock.release()

    def _failed(self, batch_id, index, status, error):
        def failed(value):
            value['status'], value['error'] = 'error', error
            value['recipients'][index].update(status=status, error=error)
            for row in value['recipients']:
                if row['status'] == 'pending':
                    row['status'] = 'canceled'
        self.store.change(batch_id, failed)
