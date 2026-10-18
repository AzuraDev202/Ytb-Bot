"""Canonical contact groups derived from the latest saved row for each channel."""
import hashlib
import json
from urllib.parse import urlsplit, urlunsplit
from ytb_bot.core.contacts import extract_contacts
from ytb_bot.core.result_schema import normalize_result_row


def contact_groups(store):
    with store._connection() as db:
        rows = db.execute('SELECT rows FROM runs ORDER BY id DESC').fetchall()
    channels, groups = set(), {}
    for record in rows:
        for raw in json.loads(record[0]):
            row = normalize_result_row(raw)
            channel_id = row.get('Channel ID')
            if not channel_id or channel_id in channels:
                continue
            channels.add(channel_id)
            contacts = extract_contacts('\n'.join(str(row.get(key) or '') for key in ('Email', 'Facebook', 'Other Contacts')))
            for label, values in contacts.items():
                for value in values.splitlines():
                    kind = 'email' if label == 'Email' else 'social'
                    if kind == 'email':
                        value = value.casefold()
                    else:
                        parsed = urlsplit(value)
                        host = parsed.hostname.casefold().removeprefix('www.').removeprefix('m.')
                        value = urlunsplit(('https', host, parsed.path, parsed.query, ''))
                    key = kind + ':' + value
                    group = groups.setdefault(key, {'id': hashlib.sha256(key.encode()).hexdigest(), 'kind': kind,
                        'value': value, 'channels': [], 'last_status': '', 'last_created': ''})
                    group['channels'].append({'id': channel_id, 'name': row.get('Channel Name') or channel_id})
    return sorted(groups.values(), key=lambda group: (group['kind'], group['value']))
