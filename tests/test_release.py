"""Release selection must deliver fixes even when the product version is unchanged."""
import io
import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError


class ReleaseTests(unittest.TestCase):
    def prepare(self, latest="v1.0.2", tag=False, error=None):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            env = {"GITHUB_REPOSITORY": "AzuraDev202/Ytb-Bot", "GH_TOKEN": "test-placeholder",
                   "GITHUB_OUTPUT": str(output), "GITHUB_REF": "refs/tags/v1.0.2" if tag else "refs/heads/main",
                   "GITHUB_REF_TYPE": "tag" if tag else "branch", "GITHUB_REF_NAME": "v1.0.2" if tag else "main"}
            with patch.dict(os.environ, env), patch("urllib.request.urlopen",
                    side_effect=error, return_value=io.BytesIO(json.dumps({"tag_name": latest}).encode())):
                runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/prepare_release.py"))
            return dict(line.split("=", 1) for line in output.read_text().splitlines())

    def test_push_main_refreshes_existing_version(self):
        result = self.prepare()
        self.assertEqual(result["publish"], "true")
        self.assertEqual(result["refresh"], "true")

    def test_existing_tag_does_not_overwrite_main_build(self):
        self.assertEqual(self.prepare(tag=True)["publish"], "false")

    def test_newer_local_version_creates_release_and_older_never_downgrades(self):
        result = self.prepare("v1.0.1")
        self.assertEqual((result["publish"], result["refresh"]), ("true", "false"))
        self.assertEqual(self.prepare("v1.1.0")["publish"], "false")

    def test_first_release_is_created_but_auth_errors_fail(self):
        result = self.prepare(error=HTTPError("https://api.github.com", 404, "Not found", {}, None))
        self.assertEqual((result["publish"], result["refresh"]), ("true", "false"))
        with self.assertRaises(HTTPError):
            self.prepare(error=HTTPError("https://api.github.com", 403, "Forbidden", {}, None))
