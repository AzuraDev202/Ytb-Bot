"""Persistent drafts and immutable, single-attempt email submissions."""
import datetime as dt
import json
import sqlite3
import uuid

from ytb_bot.core.storage import WorkspaceStore
from ytb_bot.core.result_schema import normalize_result_row
from ytb_bot.core.email_history import reserve_channels


class OutreachStore(WorkspaceStore):
    def __init__(self, path):
        super().__init__(path)
        with self._connection() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS contact_drafts (
                    channel_id TEXT PRIMARY KEY, payload TEXT NOT NULL, revision INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS mail_attempts (
                    id TEXT PRIMARY KEY, channel_id TEXT NOT NULL, revision INTEGER NOT NULL,
                    created TEXT NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL,
                    message_id TEXT NOT NULL DEFAULT '', UNIQUE(channel_id, revision)
                );
                CREATE TABLE IF NOT EXISTS contact_claims (
                    sender TEXT NOT NULL, recipient TEXT NOT NULL, created TEXT NOT NULL,
                    source TEXT NOT NULL, PRIMARY KEY(sender,recipient)
                );
            ''')

    def channel(self, channel_id):
        with self._connection() as db:
            row = db.execute('''SELECT item.value FROM runs, json_each(runs.rows) AS item
                WHERE json_extract(item.value, '$."Channel ID"') = ? ORDER BY runs.id DESC LIMIT 1''', (channel_id,)).fetchone()
        if not row:
            raise ValueError('Channel not found in saved history.')
        return normalize_result_row(json.loads(row[0]))

    def draft(self, channel_id):
        with self._connection() as db:
            row = db.execute('SELECT payload,revision FROM contact_drafts WHERE channel_id=?', (channel_id,)).fetchone()
        return {**json.loads(row[0]), 'revision': row[1]} if row else None

    def save_draft(self, channel_id, payload):
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        with self._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT payload,revision FROM contact_drafts WHERE channel_id=?', (channel_id,)).fetchone()
            revision = previous[1] + (previous[0] != encoded) if previous else 1
            db.execute('INSERT INTO contact_drafts VALUES (?,?,?) ON CONFLICT(channel_id) DO UPDATE SET payload=excluded.payload,revision=excluded.revision', (channel_id, encoded, revision))
        return {**payload, 'revision': revision}

    def claim(self, channel_id, revision, sender=None):
        with self._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT payload,revision FROM contact_drafts WHERE channel_id=?', (channel_id,)).fetchone()
            if not row or row[1] != revision:
                raise ValueError('The draft has changed. Save and review it before sending.')
            payload = json.loads(row[0])
            if db.execute('SELECT 1 FROM removed_email_contacts WHERE email=?', (payload['recipient'].strip().casefold(),)).fetchone():
                raise ValueError('This email was removed from the contact queue.')
            if sender:
                claimed = db.execute('SELECT 1 FROM contact_claims WHERE sender=? AND recipient=?',
                                     (sender.strip().casefold(), payload['recipient'].strip().casefold())).fetchone()
                if claimed:
                    raise ValueError('This recipient already belongs to a bulk send attempt. Check the contact history.')
                payload['sender_email'] = sender
            encoded = json.dumps(payload, ensure_ascii=False)
            attempt = uuid.uuid4().hex
            if not reserve_channels(db, [channel_id], attempt):
                raise ValueError('This channel already has an accepted or uncertain email attempt. Check email history before further contact.')
            channel = db.execute('''SELECT json_extract(item.value, '$."Channel Name"')
                FROM runs, json_each(runs.rows) AS item
                WHERE json_extract(item.value, '$."Channel ID"')=? ORDER BY runs.id DESC LIMIT 1''', (channel_id,)).fetchone()
            payload['channel_name'] = channel[0] if channel else channel_id
            encoded = json.dumps(payload, ensure_ascii=False)
            try:
                db.execute('INSERT INTO mail_attempts(id,channel_id,revision,created,status,payload) VALUES (?,?,?,?,?,?)',
                    (attempt, channel_id, revision, dt.datetime.now(dt.timezone.utc).isoformat(), 'sending', encoded))
            except sqlite3.IntegrityError:
                raise ValueError('This draft already has a send attempt. Check its history; edit and save a new revision to send again.') from None
        return attempt, payload

    def finish(self, attempt, status, message_id=''):
        with self._connection() as db:
            db.execute('UPDATE mail_attempts SET status=?,message_id=? WHERE id=?', (status, message_id, attempt))
            if status == 'failed':
                db.execute('DELETE FROM email_channel_claims WHERE source=?', (attempt,))

    def history(self, channel_id):
        with self._connection() as db:
            rows = db.execute('SELECT id,revision,created,status,payload,message_id FROM mail_attempts WHERE channel_id=? ORDER BY created DESC LIMIT 20', (channel_id,)).fetchall()
        return [{**dict(row), 'payload': json.loads(row['payload'])} for row in rows]
