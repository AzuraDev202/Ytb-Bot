"""Email records independent of discovery runs and sender accounts."""
import json


BLOCKED = {'accepted', 'sending', 'unknown'}


def email_records(db):
    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    records = []
    if 'mail_attempts' in tables:
        for row in db.execute('SELECT * FROM mail_attempts'):
            payload = json.loads(row['payload'])
            records.append({'id': row['id'], 'channel_id': row['channel_id'],
                'name': payload.get('channel_name') or row['channel_id'],
                'recipient': payload.get('recipient', ''), 'created': row['created'],
                'status': row['status'], 'message_id': row['message_id']})
    if 'bulk_batches' in tables:
        for row in db.execute('SELECT payload FROM bulk_batches'):
            batch = json.loads(row[0])
            for recipient in batch.get('recipients', []):
                if recipient.get('status') in {'pending', 'canceled', 'skipped'}:
                    continue
                for channel in recipient.get('channels', []):
                    records.append({'id': batch['id'], 'channel_id': channel['id'],
                        'name': channel.get('name') or channel['id'], 'recipient': recipient['email'],
                        'created': batch['created'], 'status': recipient['status'],
                        'message_id': recipient.get('message_id', '')})
    return sorted(records, key=lambda row: row['created'], reverse=True)


def reserve_channels(db, channel_ids, source):
    """Called within BEGIN IMMEDIATE to serialize single and bulk send claims."""
    for record in email_records(db):
        if record['status'] in BLOCKED:
            db.execute('INSERT OR IGNORE INTO email_channel_claims VALUES (?,?)',
                       (record['channel_id'], record['id']))
    ids = set(channel_ids)
    if any(db.execute('SELECT 1 FROM email_channel_claims WHERE channel_id=?', (key,)).fetchone() for key in ids):
        return False
    db.executemany('INSERT INTO email_channel_claims VALUES (?,?)', [(key, source) for key in ids])
    return True
