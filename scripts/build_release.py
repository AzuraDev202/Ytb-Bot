"""Build a release with the checksum required by desktop auto-update."""
import hashlib
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app_version import APP_VERSION
from updater import version_tuple

version_tuple(APP_VERSION)
if len(sys.argv) > 1 and sys.argv[1] != f"v{APP_VERSION}":
    raise SystemExit("Git tag must match APP_VERSION in app_version.py")
subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--workpath", ".release-build", "gui_app.spec"],
               cwd=ROOT, check=True)
exe = ROOT / "dist" / "gui_app.exe"
checksum = hashlib.sha256(exe.read_bytes()).hexdigest()
(exe.parent / "gui_app.exe.sha256").write_text(f"{checksum}  gui_app.exe\n", encoding="ascii")
print(f"Built Ytb-Bot {APP_VERSION}: {exe}")
