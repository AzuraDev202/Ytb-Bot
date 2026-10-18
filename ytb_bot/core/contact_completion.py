"""Persistent queue exclusions, reconciled from immutable accepted sends."""
import json


class ContactCompletion:
    def __init__(self, store):
        self.store = store
        with store._connection() as db:
            db.execute('CREATE TABLE IF NOT EXISTS completed_contacts(channel_id TEXT PRIMARY KEY, source TEXT NOT NULL)')

    def complete(self, channel_ids, source):
        with self.store._connection() as db:
            db.executemany('INSERT OR IGNORE INTO completed_contacts VALUES (?,?)',
                           [(key, source) for key in set(channel_ids) if isinstance(key, str) and key])

    def completed_ids(self):
        # Reconciliation makes a crash after persisting acceptance harmless.
        with self.store._connection() as db:
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            accepted = []
            if 'mail_attempts' in tables:
                accepted.extend((row[0], 'gmail') for row in db.execute("SELECT channel_id FROM mail_attempts WHERE status='accepted'"))
            if 'bulk_batches' in tables:
                for row in db.execute('SELECT payload FROM bulk_batches'):
                    for recipient in json.loads(row[0]).get('recipients', []):
                        if recipient.get('status') == 'accepted':
                            accepted.extend((channel['id'], 'bulk') for channel in recipient.get('channels', []))
            if 'facebook_attempts' in tables:
                accepted.extend((row[0], 'facebook') for row in db.execute("SELECT channel_id FROM facebook_attempts WHERE status='accepted'"))
            db.executemany('INSERT OR IGNORE INTO completed_contacts VALUES (?,?)', accepted)
            return {row[0] for row in db.execute('SELECT channel_id FROM completed_contacts')}
