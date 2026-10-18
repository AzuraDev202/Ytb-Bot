import tempfile
import unittest
from unittest.mock import patch, MagicMock

from ytb_bot.desktop.api import DesktopAPI


class FacebookBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.api = DesktopAPI(self.temp.name)
        self.api._facebook = MagicMock()

    def test_public_bridge_and_send_guard(self):
        self.api._facebook.state.return_value = {'accounts': []}
        self.assertEqual(self.api.facebook_state(), {'ok': True, 'data': {'accounts': []}})
        self.api._facebook.send.return_value = {'status': 'accepted', 'message': 'ok'}
        self.assertTrue(self.api.send_facebook_message('draft')['ok'])
        self.assertFalse(self.api._contact_sending)
        self.api._contact_sending = True
        self.assertFalse(self.api.send_facebook_message('draft')['ok'])
        self.assertEqual(self.api._facebook.send.call_count, 1)

    def test_failure_resets_sending_and_dirty_blocks_update(self):
        self.api._facebook.send.side_effect = ValueError('not eligible')
        self.assertFalse(self.api.send_facebook_message('draft')['ok'])
        self.assertFalse(self.api._contact_sending)
        self.api.set_facebook_dirty(True)
        self.assertFalse(self.api.install_available_update()['ok'])

    def test_bridge_passes_only_server_owned_review_id_for_send(self):
        self.api._facebook.prepare.return_value = {'id': 'draft'}
        self.assertTrue(self.api.prepare_facebook_message('a', {'body': 'hello', 'page_id': 'p'})['ok'])
        self.api._facebook.prepare.assert_called_once_with('a', {'body': 'hello', 'page_id': 'p'})
