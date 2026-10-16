"""Publish new versions or refresh the same version from main."""
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ytb_bot.version import APP_VERSION
from ytb_bot.updater import version_tuple

version_tuple(APP_VERSION)
tag = f"v{APP_VERSION}"
if os.environ.get("GITHUB_REF_TYPE") == "tag" and os.environ.get("GITHUB_REF_NAME") != tag:
    raise SystemExit("Git tag must match APP_VERSION.")

repository = os.environ["GITHUB_REPOSITORY"]
request = Request(f"https://api.github.com/repos/{repository}/releases/latest", headers={
    "User-Agent": "Ytb-Bot-release", "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
})
try:
    with urlopen(request, timeout=30) as response:
        latest = json.load(response)["tag_name"]
except HTTPError as error:
    if error.code != 404:
        raise
    latest = None

same_version = latest is not None and version_tuple(APP_VERSION) == version_tuple(latest)
refresh = same_version and os.environ.get("GITHUB_REF") == "refs/heads/main"
publish = latest is None or version_tuple(APP_VERSION) > version_tuple(latest) or refresh
with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
    output.write(f"tag={tag}\npublish={str(publish).lower()}\nrefresh={str(refresh).lower()}\n")
print(f"Version {tag}: {'refresh existing release assets' if refresh else 'ready to publish' if publish else 'older or unchanged tag; skipped'}")
