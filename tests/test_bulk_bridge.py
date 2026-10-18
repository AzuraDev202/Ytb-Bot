"""Bulk review and send operations share desktop shutdown/update safeguards."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from ytb_bot.desktop.api import DesktopAPI


class BulkBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.patch = patch('ytb_bot.desktop.api.APP_DIR', Path(self.temp.name))
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.api = DesktopAPI(self.temp.name)
        self.bulk = MagicMock()
        self.bulk.is_running = False
        self.api._bulk = self.bulk

    def test_preparing_review_does_not_start_a_batch(self):
        self.bulk.prepare.return_value = {'id': 'preview', 'status': 'draft'}
        self.assertTrue(self.api.set_bulk_dirty(True)['ok'])
        result = self.api.prepare_bulk_mail({'group_ids': ['group'], 'subject': 'Hello'})
        self.assertEqual(result['data']['status'], 'draft')
        self.bulk.start.assert_not_called()
        self.assertFalse(self.api._bulk_dirty)

    def test_running_batch_blocks_individual_send_and_update(self):
        self.bulk.is_running = True
        self.assertFalse(self.api.send_contact_mail('channel', 1)['ok'])
        self.assertFalse(self.api.install_available_update()['ok'])
        self.assertFalse(self.api.prepare_bulk_mail({})['ok'])

    def test_individual_send_or_update_blocks_bulk_start(self):
        self.api._contact_sending = True
        self.assertFalse(self.api.start_bulk_mail('preview')['ok'])
        self.api._contact_sending = False
        self.api._update['status'] = 'downloading'
        self.assertFalse(self.api.start_bulk_mail('preview')['ok'])
        self.bulk.start.assert_not_called()

    def test_unsaved_bulk_draft_blocks_update_and_stale_preview_start(self):
        self.assertTrue(self.api.set_bulk_dirty(True)['ok'])
        self.assertFalse(self.api.install_available_update()['ok'])
        self.assertFalse(self.api.start_bulk_mail('preview')['ok'])
        self.assertFalse(self.api.set_bulk_dirty('invalid')['ok'])

    def test_shutdown_handoff_blocks_new_bulk_edits(self):
        self.api._update_committing = True
        self.assertFalse(self.api.set_bulk_dirty(True)['ok'])
        self.assertFalse(self.api.prepare_bulk_mail({})['ok'])
        self.assertFalse(self.api.start_bulk_mail('preview')['ok'])
