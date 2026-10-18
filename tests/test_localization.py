"""Only application-owned messages are localized; inserted content stays intact."""
import ast
from pathlib import Path
import unittest

from ytb_bot.desktop.localization import translate_message


class LocalizationTests(unittest.TestCase):
    def test_default_and_unsupported_locales_keep_english(self):
        message = 'A scan is already running.'
        for language in ('en', 'fr', '', None, 'zh', 'VI', [], {}):
            with self.subTest(language=language):
                self.assertEqual(translate_message(message, language), message)
        self.assertEqual(translate_message(message), message)

    def test_static_messages_have_both_translations(self):
        self.assertEqual(translate_message('A scan is already running.', 'vi'), 'Một lượt quét đang chạy.')
        self.assertEqual(translate_message('A scan is already running.', 'zh-CN'), '已有扫描正在运行。')

    def test_provider_errors_and_partial_matches_remain_unchanged(self):
        for message in ('Provider says: A scan is already running.', 'HTTP 503: upstream lỗi',
                        'A scan is already running. More detail', 'Scanning: topic (a/b)', ''):
            for language in ('vi', 'zh-CN'):
                self.assertEqual(translate_message(message, language), message)

    def test_keyword_template_preserves_arbitrary_user_content(self):
        keyword = 'Kênh 中文 {title} "quoted" (7/8)\nline two'
        message = f'Scanning: {keyword} (2/9)'
        self.assertEqual(translate_message(message, 'vi'), f'Đang quét: {keyword} (2/9)')
        self.assertEqual(translate_message(message, 'zh-CN'), f'正在扫描：{keyword}（2/9）')

    def test_match_template_preserves_channel_name_and_view_format(self):
        name = 'Công nghệ 中文 {views} · 3 views'
        message = f'Match: {name} · 1,234 views'
        self.assertEqual(translate_message(message, 'vi'), f'Phù hợp: {name} · 1,234 lượt xem')
        self.assertEqual(translate_message(message, 'zh-CN'), f'匹配：{name} · 1,234 次观看')

    def test_external_detail_is_preserved_inside_known_error_wrapper(self):
        detail = 'provider {error}: 不可用\nretry "later"'
        self.assertEqual(translate_message(f'Could not save results: {detail}', 'vi'),
                         f'Không lưu được kết quả: {detail}')
        self.assertEqual(translate_message('Unable to check for updates (HTTP 503).', 'zh-CN'),
                         '无法检查更新（HTTP 503）。')

    def test_native_dialogs_and_delivery_caveats_are_localized(self):
        for message in ('Unsaved keywords', 'Close YTB-BOT',
                        'The keyword table has unsaved changes. Closing the app will discard them. Close anyway?',
                        'Gmail accepted the send request. This status does not confirm delivery to the recipient.'):
            for language in ('vi', 'zh-CN'):
                self.assertNotEqual(translate_message(message, language), message)

    def test_all_app_owned_constant_exceptions_have_translations(self):
        root = Path(__file__).resolve().parents[1]
        paths = ['core/engine.py', 'core/workbook.py', 'core/storage.py', 'core/outreach_store.py',
                 'desktop/api.py', 'desktop/outreach.py', 'desktop/gmail.py',
                 'desktop/credential_vault.py', 'desktop/app.py', 'updater.py']
        for relative in paths:
            tree = ast.parse((root / 'ytb_bot' / relative).read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call) or not node.exc.args:
                    continue
                value = node.exc.args[0]
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    for language in ('vi', 'zh-CN'):
                        with self.subTest(path=relative, message=value.value, language=language):
                            self.assertNotEqual(translate_message(value.value, language), value.value)

    def test_dynamic_scan_counts_versions_and_native_error_path(self):
        messages = ['Checked 10 channels in history. Only new channel IDs will be included.',
                    'Found 12 channels with recent videos. Checking filters...',
                    'Skipped 9 channels already in history.',
                    'Saved 3 channels. Open Results to review them.',
                    'Update available: v2.13.4',
                    'Gmail rejected the request (HTTP 403). Check send permissions and the account.']
        for message in messages:
            for language in ('vi', 'zh-CN'):
                with self.subTest(message=message, language=language):
                    self.assertNotEqual(translate_message(message, language), message)
        path = 'C:/Người dùng/中文 {file}/desktop.log'
        startup = f'Could not open YTB-BOT. Check the Microsoft Edge WebView2 Runtime.\nDetails: {path}'
        for language in ('vi', 'zh-CN'):
            self.assertTrue(translate_message(startup, language).endswith(path))

    def test_non_text_values_pass_through(self):
        for value in (None, 1, {'message': 'A scan is already running.'}):
            self.assertIs(translate_message(value, 'vi'), value)


if __name__ == '__main__':
    unittest.main()
