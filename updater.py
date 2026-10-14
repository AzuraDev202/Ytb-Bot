"""GitHub release discovery, verified downloads, and Windows executable handoff."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app_version import APP_VERSION, UPDATE_REPOSITORY, UPDATE_ASSET


class UpdateError(Exception):
    pass


@dataclass(frozen=True)
class Release:
    version: str
    url: str
    checksum_url: str
    size: int


def version_tuple(value):
    if not re.fullmatch(r"v?\d+\.\d+\.\d+", value):
        raise UpdateError("Phiên bản phải có định dạng X.Y.Z.")
    return tuple(map(int, value.removeprefix("v").split(".")))


def _request(url, accept="application/octet-stream"):
    return Request(url, headers={"User-Agent": f"Ytb-Bot/{APP_VERSION}", "Accept": accept})


def _asset_url(url):
    parsed = urlparse(url)
    if (parsed.scheme != "https" or parsed.netloc != "github.com"
            or not parsed.path.startswith(f"/{UPDATE_REPOSITORY}/releases/download/")):
        raise UpdateError("Địa chỉ tải cập nhật không hợp lệ.")
    return url


def check_for_update(current=APP_VERSION):
    try:
        with urlopen(_request(f"https://api.github.com/repos/{UPDATE_REPOSITORY}/releases/latest",
                              "application/vnd.github+json"), timeout=15) as response:
            data = json.loads(response.read(1024 * 1024))
    except HTTPError as error:
        if error.code == 404:
            return None
        raise UpdateError(f"Không thể kiểm tra cập nhật (HTTP {error.code}).") from error
    if data.get("draft") or data.get("prerelease"):
        return None
    version = data.get("tag_name", "")
    if version_tuple(version) <= version_tuple(current):
        return None
    assets = {item["name"]: item for item in data.get("assets", [])}
    if UPDATE_ASSET not in assets or f"{UPDATE_ASSET}.sha256" not in assets:
        raise UpdateError("Bản phát hành thiếu file EXE hoặc SHA-256.")
    exe = assets[UPDATE_ASSET]
    size = exe.get("size", 0)
    if not isinstance(size, int) or not 0 < size <= 512 * 1024 * 1024:
        raise UpdateError("Kích thước bản cập nhật không hợp lệ.")
    return Release(version.removeprefix("v"), _asset_url(exe["browser_download_url"]),
                   _asset_url(assets[f"{UPDATE_ASSET}.sha256"]["browser_download_url"]), size)


def download_update(release, progress=lambda value: None):
    """Return a verified staged EXE; incomplete files are removed on failure."""
    with urlopen(_request(release.checksum_url), timeout=15) as response:
        checksum = response.read(4096).decode("ascii").split()[0].lower()
    if not re.fullmatch(r"[0-9a-f]{64}", checksum):
        raise UpdateError("SHA-256 của bản cập nhật không hợp lệ.")
    directory = Path(tempfile.mkdtemp(prefix="ytb-update-"))
    target = directory / UPDATE_ASSET
    digest = hashlib.sha256()
    received = 0
    try:
        with urlopen(_request(release.url), timeout=30) as response, target.open("wb") as output:
            while chunk := response.read(256 * 1024):
                received += len(chunk)
                if received > release.size:
                    raise UpdateError("Bản cập nhật vượt kích thước đã công bố.")
                output.write(chunk)
                digest.update(chunk)
                progress(received / release.size)
        if received != release.size or digest.hexdigest() != checksum:
            raise UpdateError("Bản cập nhật không khớp SHA-256 hoặc tải chưa đầy đủ.")
        with target.open("rb") as downloaded:
            if downloaded.read(2) != b"MZ":
                raise UpdateError("Bản cập nhật không phải file thực thi Windows.")
        return target
    except Exception:
        target.unlink(missing_ok=True)
        directory.rmdir()
        raise


def install_update(staged):
    """Start a hidden helper. Caller must close the app after this succeeds."""
    if os.name != "nt" or not getattr(sys, "frozen", False):
        raise UpdateError("Tự cập nhật chỉ hỗ trợ bản desktop EXE trên Windows.")
    target = Path(sys.executable).resolve()
    staged = Path(staged).resolve()
    if staged.name != UPDATE_ASSET or staged.parent == target.parent:
        raise UpdateError("File cập nhật tạm không hợp lệ.")
    # Fail before shutting down if the install folder is not writable.
    with tempfile.TemporaryFile(dir=target.parent):
        pass
    digest = hashlib.sha256(staged.read_bytes()).hexdigest()
    config = staged.parent / "install.json"
    config.write_text(json.dumps({"target": str(target), "staged": str(staged),
                                  "pid": os.getpid(), "sha256": digest,
                                  "interactive": True}), encoding="utf-8")
    helper = staged.parent / "install.ps1"
    helper.write_text(_INSTALL_SCRIPT, encoding="utf-8-sig")
    powershell = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    helper_env = os.environ.copy()
    helper_env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    subprocess.Popen([str(powershell), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                      "-File", str(helper), "-ConfigPath", str(config)],
                     cwd=str(target.parent), creationflags=subprocess.CREATE_NO_WINDOW,
                     close_fds=True, env=helper_env)


_INSTALL_SCRIPT = r'''
param([Parameter(Mandatory=$true)][string]$ConfigPath)
$ErrorActionPreference = 'Stop'
$updateConfig = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
$targetPath = [IO.Path]::GetFullPath($updateConfig.target)
$stagedPath = [IO.Path]::GetFullPath($updateConfig.staged)
$backupPath = $targetPath + '.previous'
$candidatePath = $targetPath + '.incoming'
$replaced = $false
$exitCode = 0
$maxReplaceAttempts = 30
if ($null -ne $updateConfig.maxReplaceAttempts) {
    $maxReplaceAttempts = [Math]::Max(1, [Math]::Min(30, [int]$updateConfig.maxReplaceAttempts))
}
try {
    $oldProcess = Get-Process -Id $updateConfig.pid -ErrorAction SilentlyContinue
    if ($oldProcess -and -not $oldProcess.WaitForExit(120000)) {
        throw 'App did not close within 120 seconds.'
    }
    # Use .NET directly: Get-FileHash may be unavailable when launched from pwsh/CI.
    $hashAlgorithm = [Security.Cryptography.SHA256]::Create()
    $hashStream = $null
    try {
        $hashStream = [IO.File]::OpenRead($stagedPath)
        $actualHash = [BitConverter]::ToString($hashAlgorithm.ComputeHash($hashStream)).Replace('-', '').ToLowerInvariant()
    } finally {
        if ($null -ne $hashStream) { $hashStream.Dispose() }
        $hashAlgorithm.Dispose()
    }
    if ($actualHash -ne $updateConfig.sha256) { throw 'Checksum mismatch.' }
    Copy-Item -LiteralPath $stagedPath -Destination $candidatePath -Force
    # PyInstaller's parent bootloader may briefly keep the EXE locked.
    for ($attempt = 0; $attempt -lt $maxReplaceAttempts; $attempt++) {
        try {
            if (Test-Path -LiteralPath $backupPath) { Remove-Item -LiteralPath $backupPath -Force }
            [IO.File]::Replace($candidatePath, $targetPath, $backupPath)
            $replaced = $true
            break
        } catch {
            # Only retry Windows sharing/lock violations, not permanent errors.
            $replaceError = $_.Exception
            while ($replaceError.InnerException) { $replaceError = $replaceError.InnerException }
            $win32Error = $replaceError.HResult -band 0xffff
            if (($win32Error -notin @(32, 33)) -or ($attempt -eq ($maxReplaceAttempts - 1))) { throw }
            Start-Sleep -Seconds 1
        }
    }
    Start-Process -FilePath $targetPath -WorkingDirectory ([IO.Path]::GetDirectoryName($targetPath)) -WindowStyle Hidden
} catch {
    $exitCode = 1
    $failure = $_.ToString()
    if ($replaced -and (Test-Path -LiteralPath $backupPath)) {
        Copy-Item -LiteralPath $backupPath -Destination $targetPath -Force
    }
    $failure | Set-Content -LiteralPath (Join-Path ([IO.Path]::GetDirectoryName($stagedPath)) 'update-error.log') -Encoding UTF8
    [Console]::Error.WriteLine($failure)
    if ($updateConfig.interactive -eq $true) {
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.MessageBox]::Show("Cap nhat that bai. Ban cu duoc giu lai.`n$failure", 'Ytb-Bot') | Out-Null
    }
} finally {
    if (Test-Path -LiteralPath $candidatePath) { Remove-Item -LiteralPath $candidatePath -Force }
    if (Test-Path -LiteralPath $stagedPath) { Remove-Item -LiteralPath $stagedPath -Force }
}
exit $exitCode
'''
