"""Identify packaged builds independently of the application version."""
import json
from pathlib import Path


def build_id():
    metadata = Path(__file__).with_name("build-info.json")
    if not metadata.exists():
        return "source"
    return json.loads(metadata.read_text(encoding="utf-8"))["build_id"]
