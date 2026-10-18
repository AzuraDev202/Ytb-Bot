"""Windows user-bound encryption for OAuth configuration and refresh tokens."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
from contextlib import contextmanager
import tempfile
import time


class _Blob(ctypes.Structure):
    _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]


def _protect(data, decrypt=False):
    if os.name != 'nt':
        raise RuntimeError('Gmail account protection is currently supported on Windows.')
    buffer = ctypes.create_string_buffer(data)
    source = _Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output = _Blob()
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes = [ctypes.POINTER(_Blob), ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_Blob)]
    function.restype = wintypes.BOOL
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise RuntimeError('Unable to open the credential vault for this Windows account.')
    try:
        return ctypes.string_at(output.data, output.size)
    finally:
        kernel.LocalFree(output.data)


class CredentialVault:
    def __init__(self, path, lock_timeout=10):
        self.path = Path(path)
        self.lock_timeout = lock_timeout

    @contextmanager
    def _transaction_lock(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Keep this file in place: unlinking it can split concurrent locks.
        with self.path.with_suffix('.lock').open('a+b') as handle:
            handle.seek(0, os.SEEK_END)
            if not handle.tell():
                handle.write(b'\0')
                handle.flush()
            deadline = time.monotonic() + self.lock_timeout
            while True:
                try:
                    handle.seek(0)
                    if os.name == 'nt':
                        import msvcrt
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError('The credential vault is in use by another window. Try again later.') from None
                    time.sleep(0.025)
            try:
                yield
            finally:
                handle.seek(0)
                if os.name == 'nt':
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def read(self):
        if not self.path.exists():
            return {'client': None, 'accounts': {}}
        return json.loads(_protect(self.path.read_bytes(), decrypt=True))

    def write(self, value):
        with self._transaction_lock():
            self._write(value)

    def update(self, change):
        """Read, mutate and commit under one process-wide file transaction."""
        with self._transaction_lock():
            value = self.read()
            result = change(value)
            self._write(value)
            return result

    def _write(self, value):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        encrypted = _protect(json.dumps(value).encode('utf-8'))
        descriptor, name = tempfile.mkstemp(prefix=self.path.stem + '-', suffix='.tmp', dir=self.path.parent)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, 'wb') as output:
                output.write(encrypted)
                output.flush()
                os.fsync(output.fileno())
            temporary.replace(self.path)
        finally:
            temporary.unlink(missing_ok=True)
