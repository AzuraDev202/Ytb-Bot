import multiprocessing
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from ytb_bot.desktop.credential_vault import CredentialVault


def hold_transaction(path, ready, release):
    vault = CredentialVault(path)
    def hold(value):
        ready.set()
        release.wait(10)
        value['accounts']['retained'] = {'email': 'retained@example.com'}
    with patch('ytb_bot.desktop.credential_vault._protect', side_effect=lambda data, **kwargs: data):
        vault.update(hold)


@unittest.skipUnless(os.name == 'nt', 'Windows DPAPI and interprocess locking')
class VaultLockingTests(unittest.TestCase):
    def setUp(self):
        # Exercise actual OS file locking without requiring DPAPI in the sandbox.
        protection = patch('ytb_bot.desktop.credential_vault._protect', side_effect=lambda data, **kwargs: data)
        protection.start()
        self.addCleanup(protection.stop)

    def test_failed_mutation_keeps_previous_vault_and_releases_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'credentials.bin'
            vault = CredentialVault(path)
            original = {'client': None, 'accounts': {'retained': {'email': 'saved@example.com'}}}
            vault.write(original)
            def fail(value):
                value['accounts'].clear()
                raise ValueError('Simulated refresh failure')
            with self.assertRaises(ValueError):
                vault.update(fail)
            self.assertEqual(vault.read(), original)
            CredentialVault(path, lock_timeout=0).update(lambda value: value['accounts'].clear())
            self.assertEqual(vault.read()['accounts'], {})

    def test_failed_replace_preserves_previous_vault_and_removes_temporary(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'credentials.bin'
            vault = CredentialVault(path)
            original = {'client': None, 'accounts': {}}
            vault.write(original)
            with patch.object(Path, 'replace', side_effect=OSError('Simulated disk failure')):
                with self.assertRaises(OSError):
                    vault.update(lambda value: value.update({'client': 'replacement'}))
            self.assertEqual(vault.read(), original)
            self.assertFalse(list(path.parent.glob('*.tmp')))

    def test_another_process_times_out_then_updates_latest_accounts(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'credentials.bin'
            vault = CredentialVault(path)
            vault.write({'client': None, 'accounts': {'removed': {'email': 'old@example.com'}}})
            context = multiprocessing.get_context('spawn')
            ready, release = context.Event(), context.Event()
            process = context.Process(target=hold_transaction, args=(str(path), ready, release))
            process.start()
            try:
                self.assertTrue(ready.wait(5), 'Child failed to acquire vault transaction')
                started = time.monotonic()
                with self.assertRaises(TimeoutError):
                    CredentialVault(path, lock_timeout=0.15).update(lambda value: value['accounts'].clear())
                self.assertLess(time.monotonic() - started, 2)
            finally:
                release.set()
                process.join(10)
                if process.is_alive():
                    process.terminate()
                    process.join()
            self.assertEqual(process.exitcode, 0)
            vault.update(lambda value: value['accounts'].pop('removed'))
            self.assertEqual(set(vault.read()['accounts']), {'retained'})
            self.assertFalse(list(path.parent.glob('*.tmp')))


if __name__ == '__main__':
    unittest.main()
