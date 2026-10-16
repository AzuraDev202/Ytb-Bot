"""Keep runtime files beside the EXE or at the source repository root."""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else PROJECT_ROOT
ENV_FILE = str(APP_DIR / ".env")
