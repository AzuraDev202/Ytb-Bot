"""Transactional immutable bulk drafts and global recipient claims."""
import datetime as dt
import json
import sqlite3
import uuid
from ytb_bot.core.storage import WorkspaceStore


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


class BulkStore(WorkspaceStore):
    def __init__(self, path):
        super().__init__(path)
        with self._connection() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS bulk_batches(id TEXT PRIMARY KEY, created TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS contact_claims(sender TEXT NOT NULL, recipient TEXT NOT NULL, created TEXT NOT NULL, source TEXT NOT NULL, PRIMARY KEY(sender,recipient));''')

    def attempted(self, sender, account_id):
        with self._connection() as db:
            emails = {row[0] for row in db.execute('SELECT recipient FROM contact_claims WHERE sender=?', (sender.casefold(),))}
            exists = db.execute("SELECT 1 FROM sqlite_master WHERE name='mail_attempts'").fetchone()
            if exists:
                for row in db.execute('SELECT payload FROM mail_attempts'):
                    payload = json.loads(row[0])
                    if payload.get('sender_email', payload.get('sender', '')).casefold() == sender.casefold() or payload.get('account_id') == account_id:
                        emails.add(payload.get('recipient', '').casefold())
        return emails

    def claim_contact(self, sender, recipient, source, account_id=''):
        with self._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='mail_attempts'").fetchone():
                for row in db.execute('SELECT payload FROM mail_attempts'):
                    value = json.loads(row[0])
                    same_sender = value.get('sender_email', value.get('sender', '')).casefold() == sender.casefold() or (account_id and value.get('account_id') == account_id)
                    if same_sender and value.get('recipient', '').casefold() == recipient.casefold():
                        return False
            try:
                db.execute('INSERT INTO contact_claims VALUES (?,?,?,?)', (sender.casefold(), recipient.casefold(), now(), source))
            except sqlite3.IntegrityError:
                return False
        return True

    def create(self, payload):
        payload = dict(payload, id=uuid.uuid4().hex, created=now(), status='draft', error='')
        with self._connection() as db:
            db.execute('INSERT INTO bulk_batches VALUES (?,?,?)', (payload['id'], payload['created'], json.dumps(payload)))
        return payload

    def get(self, batch_id=None):
        with self._connection() as db:
            row = db.execute('SELECT payload FROM bulk_batches WHERE id=?', (batch_id,)).fetchone() if batch_id else db.execute('SELECT payload FROM bulk_batches ORDER BY created DESC LIMIT 1').fetchone()
        return json.loads(row[0]) if row else None

    def list(self):
        with self._connection() as db:
            return [json.loads(row[0]) for row in db.execute('SELECT payload FROM bulk_batches ORDER BY created DESC')]

    def change(self, batch_id, change):
        with self._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT payload FROM bulk_batches WHERE id=?', (batch_id,)).fetchone()
            if not row:
                raise ValueError('Batch not found.')
            payload = json.loads(row[0])
            change(payload)
            db.execute('UPDATE bulk_batches SET payload=? WHERE id=?', (json.dumps(payload), batch_id))
        return payload
