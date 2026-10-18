import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import json
import os
import subprocess

from ytb_bot import updater


class UpdaterTests(unittest.TestCase):
    def release_data(self, version="v1.1.0"):
        base = f"https://github.com/{updater.UPDATE_REPOSITORY}/releases/download/{version}/"
        return {"tag_name": version, "assets": [
            {"name": "gui_app.exe", "size": 10, "browser_download_url": base + "gui_app.exe"},
            {"name": "gui_app.exe.sha256", "browser_download_url": base + "gui_app.exe.sha256"}]}

    def check(self, data):
        with patch.object(updater, "urlopen", return_value=io.BytesIO(json.dumps(data).encode())):
            return updater.check_for_update("1.0.0")

    def test_newer_release_and_numeric_version_order(self):
        self.assertEqual(self.check(self.release_data()).version, "1.1.0")
        self.assertGreater(updater.version_tuple("1.10.0"), updater.version_tuple("1.9.0"))

    def test_old_and_prerelease_are_ignored(self):
        self.assertIsNone(self.check(self.release_data("v0.9.0")))
        data = self.release_data()
        data["prerelease"] = True
        self.assertIsNone(self.check(data))

    def test_same_version_packaged_build_detects_new_binary_by_digest(self):
        data = self.release_data("v1.0.0")
        with tempfile.TemporaryDirectory() as directory:
            installed = Path(directory) / "installed.exe"
            installed.write_bytes(b"MZ-installed-build")
            with patch.object(updater.sys, "frozen", True, create=True), \
                    patch.object(updater.sys, "executable", str(installed)):
                data["assets"][0]["digest"] = "sha256:" + hashlib.sha256(installed.read_bytes()).hexdigest()
                self.assertIsNone(self.check(data))
                data["assets"][0]["digest"] = "sha256:" + hashlib.sha256(b"MZ-new-build").hexdigest()
                self.assertEqual(self.check(data).version, "1.0.0")
                data["assets"][0]["digest"] = None
                with self.assertRaises(updater.UpdateError):
                    self.check(data)

    def test_same_version_source_run_does_not_replace_python(self):
        with patch.object(updater.sys, "frozen", False, create=True):
            self.assertIsNone(self.check(self.release_data("v1.0.0")))

    def test_missing_asset_and_untrusted_download_rejected(self):
        data = self.release_data()
        data["assets"].pop()
        with self.assertRaises(updater.UpdateError):
            self.check(data)
        data = self.release_data()
        data["assets"][0]["browser_download_url"] = "https://example.com/malware.exe"
        with self.assertRaises(updater.UpdateError):
            self.check(data)

    def download(self, content, expected, size=None):
        release = updater.Release("1.1.0", "https://github.com/a", "https://github.com/b",
                                  len(content) if size is None else size)
        responses = [io.BytesIO(expected.encode()), io.BytesIO(content)]
        with patch.object(updater, "urlopen", side_effect=responses):
            return updater.download_update(release)

    def test_verified_download(self):
        content = b"MZtest-executable"
        target = self.download(content, hashlib.sha256(content).hexdigest())
        try:
            self.assertEqual(target.read_bytes(), content)
        finally:
            target.unlink()
            target.parent.rmdir()

    def test_corrupt_truncated_and_non_executable_downloads_rejected(self):
        content = b"MZtest-executable"
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory) / "stage"
            for data, checksum, size in [
                (content, "0" * 64, len(content)),
                (content, hashlib.sha256(content).hexdigest(), len(content) + 1),
                (b"bad", hashlib.sha256(b"bad").hexdigest(), 3),
            ]:
                stage.mkdir()
                with patch.object(updater.tempfile, "mkdtemp", return_value=str(stage)):
                    with self.assertRaises(updater.UpdateError):
                        self.download(data, checksum, size)
                self.assertFalse(stage.exists())

    def test_source_mode_cannot_replace_running_python(self):
        with patch.object(updater.sys, "frozen", False, create=True):
            with self.assertRaises(updater.UpdateError):
                updater.install_update("unused.exe")

    @unittest.skipUnless(os.name == "nt", "Windows helper")
    def test_windows_helper_replaces_file_and_keeps_backup(self):
        self.run_windows_helper()

    @unittest.skipUnless(os.name == "nt", "Windows helper")
    def test_windows_helper_checksum_failure_exits_without_dialog(self):
        self.run_windows_helper(checksum="0" * 64, expected_error="Checksum mismatch")

    @unittest.skipUnless(os.name == "nt", "Windows helper")
    def test_windows_helper_uses_localized_checksum_message(self):
        self.run_windows_helper(checksum='0' * 64, expected_error='checksum',
                                checksum_message='校验和不匹配。', expected_log='校验和不匹配。')

    @unittest.skipUnless(os.name == "nt", "Windows helper")
    def test_windows_helper_localized_failure_is_independent_of_parent_encoding(self):
        # Reproduce the hosted Windows runner even when the developer uses UTF-8.
        with patch('subprocess._text_encoding', return_value='cp1252'):
            self.run_windows_helper(checksum='0' * 64, expected_error='checksum',
                                    checksum_message='校验和不匹配。', expected_log='校验和不匹配。')

    @unittest.skipUnless(os.name == "nt", "Windows helper")
    def test_windows_helper_missing_target_fails_without_long_retry(self):
        self.run_windows_helper(target_exists=False, expected_error="Replace", max_attempts=30)

    def run_windows_helper(self, checksum=None, expected_error=None, target_exists=True, max_attempts=1,
                           checksum_message=None, expected_log=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "installed.exe"
            staged = root / "gui_app.exe"
            if target_exists:
                target.write_bytes(b"MZold")
            staged.write_bytes(b"MZnew")
            config = root / "install.json"
            config.write_text(json.dumps({"target": str(target), "staged": str(staged),
                                          "pid": 2147483647,
                                          "sha256": checksum or hashlib.sha256(b"MZnew").hexdigest(),
                                          "interactive": False, "maxReplaceAttempts": max_attempts,
                                          "checksum_message": checksum_message}))
            # Exercise actual PowerShell file replacement without launching a fake EXE.
            script = root / "test.ps1"
            script.write_text("param([string]$ConfigPath)\nImport-Module Microsoft.PowerShell.Utility, Microsoft.PowerShell.Management\n"
                              # Match both pipe endpoints instead of inheriting a Windows code page.
                              + "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)\n"
                              + "function Start-Process { param($FilePath, $WorkingDirectory, $WindowStyle) }\n"
                              # Reproduce the GitHub runner where Get-FileHash is unavailable.
                              + "function Get-FileHash { throw 'Get-FileHash is unavailable in this environment' }\n"
                              + "$ErrorActionPreference" + updater._INSTALL_SCRIPT.split("$ErrorActionPreference", 1)[1],
                              encoding="utf-8-sig")
            result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                                     "-File", str(script), "-ConfigPath", str(config)], timeout=20,
                                    capture_output=True, text=True, encoding="utf-8")
            if expected_error:
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(expected_log or expected_error, result.stderr)
                if target_exists:
                    self.assertEqual(target.read_bytes(), b"MZold")
                else:
                    self.assertFalse(target.exists())
                self.assertIn(expected_log or expected_error, (root / "update-error.log").read_text(encoding="utf-8-sig"))
            else:
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(target.read_bytes(), b"MZnew")
                self.assertEqual(Path(str(target) + ".previous").read_bytes(), b"MZold")
            self.assertFalse(staged.exists())


if __name__ == "__main__":
    unittest.main()
