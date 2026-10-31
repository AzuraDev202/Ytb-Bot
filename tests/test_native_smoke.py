import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.checks import smoke_react
from ytb_bot.core.storage import WorkspaceStore


class NativeSmokeTests(unittest.TestCase):
    def tearDown(self):
        smoke_react.failures.clear()

    def test_smoke_workspace_is_empty_and_disposable(self):
        paths = []
        def launch(callback, *, data_dir, storage_path):
            paths.append(Path(data_dir))
            store = WorkspaceStore(Path(data_dir) / 'workspace.sqlite3')
            self.assertEqual(store.runs(), [])
            self.assertIsNone(store.scan_checkpoint())
            Path(storage_path).mkdir()
            store.begin_run(['smoke-only'])
        with patch.object(smoke_react, 'main', side_effect=launch):
            smoke_react.run()
        self.assertFalse(paths[0].exists())

    def test_document_timeout_fails_and_closes_window(self):
        window = MagicMock()
        window.events.loaded.wait.return_value = False
        with patch.object(smoke_react.threading, 'Thread'):
            smoke_react.verify(window)
        self.assertTrue(smoke_react.failures)
        self.assertIn('document did not load', smoke_react.failures[0])
        window.evaluate_js.assert_not_called()
        window.destroy.assert_called_once()

    def test_failed_verification_keeps_runner_failed(self):
        def launch(callback, **kwargs):
            smoke_react.failures.append('bridge failure')
        with patch.object(smoke_react, 'main', side_effect=launch), self.assertRaisesRegex(SystemExit, 'bridge failure'):
            smoke_react.run()
