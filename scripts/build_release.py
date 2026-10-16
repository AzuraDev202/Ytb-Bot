"""Build a release with the checksum required by desktop auto-update."""
import hashlib
import datetime
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ytb_bot.version import APP_VERSION
from ytb_bot.updater import version_tuple

version_tuple(APP_VERSION)
if len(sys.argv) > 1 and sys.argv[1] != f"v{APP_VERSION}":
    raise SystemExit("Git tag must match APP_VERSION in ytb_bot/version.py")
revision = subprocess.check_output(["git", "rev-parse", "--short=8", "HEAD"], cwd=ROOT, text=True).strip()
built_at = datetime.datetime.now(datetime.timezone.utc)
metadata = {"version": APP_VERSION, "commit": revision,
            "built_at": built_at.isoformat(), "build_id": f"{revision}-{built_at:%Y%m%d%H%M%S}"}
build_metadata = ROOT / ".release-build" / "build-info.json"
build_metadata.parent.mkdir(parents=True, exist_ok=True)
build_metadata.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--workpath", ".release-build", "packaging/desktop.spec"],
               cwd=ROOT, check=True)
exe = ROOT / "dist" / "gui_app.exe"
checksum = hashlib.sha256(exe.read_bytes()).hexdigest()
(exe.parent / "gui_app.exe.sha256").write_text(f"{checksum}  gui_app.exe\n", encoding="ascii")
metadata["sha256"] = checksum
(exe.parent / "build-info.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
print(f"Built Ytb-Bot {APP_VERSION}: {exe}")
