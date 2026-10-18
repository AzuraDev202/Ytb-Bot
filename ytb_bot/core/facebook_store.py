"""Bindings and immutable reviews; one durable attempt per Page recipient."""
import datetime as dt
import json
import sqlite3
import uuid
from ytb_bot.core.outreach_store import OutreachStore


class FacebookStore(OutreachStore):
    def __init__(self, path):
        super().__init__(path)
        with self._connection() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS facebook_bindings(
                    channel_id TEXT NOT NULL, page_id TEXT NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY(channel_id,page_id));
                CREATE TABLE IF NOT EXISTS facebook_drafts(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS facebook_attempts(
                    id TEXT PRIMARY KEY, channel_id TEXT NOT NULL, page_id TEXT NOT NULL,
                    recipient_id TEXT NOT NULL, created TEXT NOT NULL, status TEXT NOT NULL,
                    payload TEXT NOT NULL, message_id TEXT NOT NULL DEFAULT '',
                    UNIQUE(page_id,recipient_id));
            ''')

    def bind(self, channel_id, page_id, conversation):
        with self._connection() as db:
            db.execute('INSERT INTO facebook_bindings VALUES (?,?,?) ON CONFLICT(channel_id,page_id) DO UPDATE SET payload=excluded.payload',
                       (channel_id, page_id, json.dumps(conversation)))

    def binding(self, channel_id, page_id):
        with self._connection() as db:
            row = db.execute('SELECT payload FROM facebook_bindings WHERE channel_id=? AND page_id=?', (channel_id, page_id)).fetchone()
        return json.loads(row[0]) if row else None

    def attempted(self, page_id, recipient_id):
        with self._connection() as db:
            return bool(db.execute('SELECT 1 FROM facebook_attempts WHERE page_id=? AND recipient_id=?', (page_id, recipient_id)).fetchone())

    def prepare(self, payload):
        key = uuid.uuid4().hex
        with self._connection() as db:
            db.execute('INSERT INTO facebook_drafts VALUES (?,?)', (key, json.dumps(payload)))
        return dict(payload, id=key)

    def draft(self, key):
        with self._connection() as db:
            row = db.execute('SELECT payload FROM facebook_drafts WHERE id=?', (key,)).fetchone()
        if not row:
            raise ValueError('Review a Messenger message before sending.')
        return dict(json.loads(row[0]), id=key)

    def claim(self, draft):
        with self._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            binding = db.execute('SELECT payload FROM facebook_bindings WHERE channel_id=? AND page_id=?',
                                 (draft['channel_id'], draft['page_id'])).fetchone()
            value = json.loads(binding[0]) if binding else {}
            if value.get('id') != draft['conversation_id'] or value.get('recipient_id') != draft['recipient_id']:
                raise ValueError('The recipient changed. Review a new message.')
            try:
                db.execute('INSERT INTO facebook_attempts(id,channel_id,page_id,recipient_id,created,status,payload) VALUES (?,?,?,?,?,?,?)',
                           (draft['id'], draft['channel_id'], draft['page_id'], draft['recipient_id'],
                            dt.datetime.now(dt.timezone.utc).isoformat(), 'sending', json.dumps(draft)))
            except sqlite3.IntegrityError:
                raise ValueError('This Page recipient already has a send attempt. Check the Page inbox before further contact.') from None

    def finish(self, key, status, message_id=''):
        with self._connection() as db:
            db.execute('UPDATE facebook_attempts SET status=?,message_id=? WHERE id=?', (status, message_id, key))

    def history(self, channel_id):
        with self._connection() as db:
            return [dict(row, payload=json.loads(row['payload'])) for row in db.execute(
                'SELECT * FROM facebook_attempts WHERE channel_id=? ORDER BY created DESC LIMIT 20', (channel_id,))]
