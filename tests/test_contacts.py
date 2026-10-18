import datetime as dt
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock

from ytb_bot.core.contacts import extract_contacts
from ytb_bot.core.engine import ScanEngine
from ytb_bot.core.storage import WorkspaceStore
from ytb_bot.desktop.api import DesktopAPI


class ContactTests(unittest.TestCase):
    def test_email_social_links_and_duplicates(self):
        contacts = extract_contacts('Email: hello+work@example.com; HELLO+WORK@example.com '
                                    'Facebook: (www.facebook.com/my.page). '
                                    'Instagram: https://instagram.com/creator '
                                    'Telegram t.me/myteam &amp; Zalo zalo.me/84912345678')
        self.assertEqual(contacts['Email'], 'hello+work@example.com')
        self.assertEqual(contacts['Facebook'], 'https://www.facebook.com/my.page')
        self.assertIn('https://instagram.com/creator', contacts['Liên Hệ Khác'])
        self.assertIn('https://t.me/myteam', contacts['Liên Hệ Khác'])
        self.assertIn('https://zalo.me/84912345678', contacts['Liên Hệ Khác'])

    def test_mentions_generic_links_and_lookalike_domains_do_not_qualify(self):
        for text in [None, '', 'Contact us via email or Facebook', '@creator', 'example.com',
                     'https://facebook.com/', 'https://facebook.com/sharer/sharer.php?u=example.com',
                     'https://evilfacebook.com/person', 'https://facebook.com.evil.test/person',
                     'https://evil.test/facebook.com/person', 'https://x.com/intent/tweet']:
            with self.subTest(text=text):
                self.assertEqual(extract_contacts(text), {})

    def test_contact_filter_persists_and_exposes_full_values_through_bridge(self):
        youtube = MagicMock()
        descriptions = {'email': 'contact: hello@example.com', 'facebook': 'facebook.com/creator',
                        'telegram': 't.me/creatorteam', 'none': 'Find us on Facebook',
                        'old': 'old@example.com', 'small': 'small@example.com'}
        youtube.search.return_value.list.return_value.execute.return_value = {'items': [
            {'snippet': {'channelId': name, 'title': 'Video'}} for name in descriptions]}
        now = dt.datetime.now(dt.timezone.utc)
        youtube.channels.return_value.list.return_value.execute.return_value = {'items': [
            {'id': name, 'snippet': {'title': name, 'description': description,
              'publishedAt': (now - dt.timedelta(days=300 if name == 'old' else 2)).isoformat()},
             'statistics': {'viewCount': '10' if name == 'small' else '1000'}}
            for name, description in descriptions.items()]}
        with tempfile.TemporaryDirectory() as directory:
            engine = ScanEngine(directory, lambda _: youtube)
            engine.start('fake-key', ['one', 'two'])
            state = engine.wait()
            self.assertEqual(state['status'], 'complete')
            self.assertEqual({row['Channel ID'] for row in state['rows']}, {'email', 'facebook', 'telegram'})
            stored = WorkspaceStore(Path(directory) / 'workspace.sqlite3').result()
            self.assertEqual(len(stored['rows']), 3)
            api = DesktopAPI(data_dir=directory)
            sheet = api.open_results(stored['id'])['data']['sheets'][0]
            page = api.results_page(sheet, 'hello@example.com')['data']
            self.assertEqual(page['total'], 1)
            self.assertEqual(page['rows'][0][page['columns'].index('Email')], 'hello@example.com')
            self.assertEqual(list(Path(directory).glob('*.xlsx')), [])
