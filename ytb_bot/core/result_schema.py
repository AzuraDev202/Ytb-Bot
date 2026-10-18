"""Read historical result labels without modifying stored user data."""

_LEGACY_COLUMNS = {
    'T\xean K\xeanh': 'Channel Name',
    'URL K\xeanh': 'Channel URL',
    'T\u1eeb Kh\xf3a Qu\xe9t': 'Search Keyword',
    'Ng\xe0y T\u1ea1o': 'Created Date',
    'Tu\u1ed5i K\xeanh (Ng\xe0y)': 'Channel Age (Days)',
    'T\u1ed5ng L\u01b0\u1ee3t Xem': 'Total Views',
    'T\u1ed5ng Video': 'Total Videos',
    'Video G\u1ea7n Nh\u1ea5t': 'Latest Video',
    'Qu\u1ed1c Gia': 'Country',
    'Li\xean H\u1ec7 Kh\xe1c': 'Other Contacts',
}


def normalize_result_row(row):
    result = {key: value for key, value in row.items() if key not in _LEGACY_COLUMNS}
    for old, new in _LEGACY_COLUMNS.items():
        if old in row and new not in result:
            result[new] = row[old]
    if result.get('Subscribers') == '\u1ea8n':
        result['Subscribers'] = 'Hidden'
    if result.get('Country') == 'Kh\u00f4ng c\u00f4ng b\u1ed1':
        result['Country'] = 'Not disclosed'
    return result
