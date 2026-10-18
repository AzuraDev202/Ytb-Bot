"""Language settings persist independently of display preferences and user data."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ytb_bot.desktop.api import DesktopAPI
from ytb_bot import updater
from ytb_bot.desktop.localization import translate_message


class LanguagePreferenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.patch = patch('ytb_bot.desktop.api.APP_DIR', self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_language_and_display_settings_survive_independent_saves_and_reopening(self):
        api = DesktopAPI(self.root)
        self.assertTrue(api.save_preferences('light', False)['ok'])
        self.assertTrue(api.set_language('vi')['ok'])
        self.assertTrue(api.save_preferences('dark', True)['ok'])
        reopened = DesktopAPI(self.root)
        self.assertEqual(reopened.get_bootstrap()['data']['preferences'],
                         {'theme': 'dark', 'motion': True, 'language': 'vi'})
        self.assertTrue(reopened.set_language('zh-CN')['ok'])
        self.assertEqual(DesktopAPI(self.root).get_bootstrap()['data']['preferences'],
                         {'theme': 'dark', 'motion': True, 'language': 'zh-CN'})

    def test_invalid_language_is_rejected_without_changing_saved_settings(self):
        api = DesktopAPI(self.root)
        self.assertTrue(api.set_language('vi')['ok'])
        before = (self.root / 'studio-settings.json').read_bytes()
        for language in ('fr', '', None, [], 'zh'):
            self.assertFalse(api.set_language(language)['ok'])
            self.assertEqual((self.root / 'studio-settings.json').read_bytes(), before)

    def test_corrupt_or_unsupported_saved_language_falls_back_to_english(self):
        path = self.root / 'studio-settings.json'
        for value in ('not json', '[]', json.dumps({'language': 'unsupported'})):
            path.write_text(value, encoding='utf-8')
            api = DesktopAPI(self.root)
            self.assertEqual(api.get_bootstrap()['data']['preferences']['language'], 'en')

    def test_switching_language_preserves_saved_user_text_and_canonical_scan_messages(self):
        api = DesktopAPI(self.root)
        original = 'User keyword \u2603\nsecond'
        api.save_keywords(original)
        api._scan._log('A scan is already running.')
        self.assertTrue(api.set_language('vi')['ok'])
        self.assertEqual(api.get_state()['data']['logs'][0]['text'], 'Một lượt quét đang chạy.')
        self.assertTrue(api.set_language('zh-CN')['ok'])
        self.assertEqual(api.get_state()['data']['logs'][0]['text'], '已有扫描正在运行。')
        self.assertEqual(api.get_bootstrap()['data']['keywords'], original)
        self.assertEqual(api._scan.snapshot()['logs'][0]['text'], 'A scan is already running.')

    def test_language_switch_rejected_during_update_handoff(self):
        api = DesktopAPI(self.root)
        api._update_committing = True
        self.assertFalse(api.set_language('vi')['ok'])
        self.assertFalse((self.root / 'studio-settings.json').exists())

    def test_failed_save_keeps_previous_language_and_cleans_up_temporary_file(self):
        api = DesktopAPI(self.root)
        self.assertTrue(api.set_language('en')['ok'])
        before = (self.root / 'studio-settings.json').read_bytes()
        with patch('ytb_bot.desktop.api.Path.replace', side_effect=PermissionError('Read-only folder')):
            self.assertFalse(api.set_language('vi')['ok'])
        self.assertEqual(api.get_bootstrap()['data']['preferences']['language'], 'en')
        self.assertEqual((self.root / 'studio-settings.json').read_bytes(), before)
        self.assertEqual(list(self.root.glob('.studio-settings-*.tmp')), [])

    def test_update_helper_receives_localized_failure_message_as_json_data(self):
        target = self.root / 'installed.exe'
        target.write_bytes(b'MZold')
        stage = self.root / 'staging' / updater.UPDATE_ASSET
        stage.parent.mkdir()
        stage.write_bytes(b'MZnew')
        with patch('ytb_bot.updater.sys.executable', str(target)), \
                patch('ytb_bot.updater.sys.frozen', True, create=True), \
                patch('ytb_bot.updater.subprocess.Popen'):
            updater.install_update(stage, language='zh-CN')
        config = json.loads((stage.parent / 'install.json').read_text(encoding='utf-8'))
        self.assertEqual(config['failure_message'], translate_message(
            'Update failed. The previous version has been preserved.', 'zh-CN'))
