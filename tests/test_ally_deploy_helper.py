"""Static and extraction-contract tests for the root-side developer helper."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ally_hdm_deploy_helper", ROOT / "scripts" / "ally_hdm_deploy_helper.py")
assert SPEC and SPEC.loader
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)


REVISION = "a" * 40


def write_package(path: Path, *, revision: str = REVISION, extra: str | None = None) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("HandheldDockMode/plugin.json", "{}")
        archive.writestr("HandheldDockMode/main.py", "# test\n")
        archive.writestr("HandheldDockMode/package.json", json.dumps({"version": "0.2.0"}))
        archive.writestr("HandheldDockMode/build_info.json", json.dumps({"schema_version": 1, "version": "0.2.0", "revision": revision}))
        if extra is not None:
            archive.writestr(extra, "x")


class AllyDeployHelperTests(unittest.TestCase):
    def test_rejects_path_arguments_before_touching_downloads(self):
        with self.assertRaises(helper.DeploymentError):
            helper.fixed_download("../HDM-update-0.2.0-aaaaaaaaaaaa.zip", ".zip")

    def test_extracts_only_complete_prefix_matched_package(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "HDM-update-0.2.0-aaaaaaaaaaaa.zip"
            write_package(package)
            staged = helper.validate_and_extract(package, root / "unpacked", "0.2.0", "a" * 12)
            self.assertTrue((staged / "main.py").is_file())

    def test_rejects_revision_that_does_not_match_filename_prefix(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "HDM-update-0.2.0-aaaaaaaaaaaa.zip"
            write_package(package, revision="b" * 40)
            with self.assertRaisesRegex(helper.DeploymentError, "provenance"):
                helper.validate_and_extract(package, root / "unpacked", "0.2.0", "a" * 12)

    def test_rejects_archive_escape_member(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "HDM-update-0.2.0-aaaaaaaaaaaa.zip"
            write_package(package, extra="HandheldDockMode/../../outside")
            with self.assertRaisesRegex(helper.DeploymentError, "layout"):
                helper.validate_and_extract(package, root / "unpacked", "0.2.0", "a" * 12)

    def test_installer_has_constrained_sudo_command_and_no_session_actions(self):
        installer = (ROOT / "scripts" / "install_ally_deploy_helper.sh").read_text(encoding="utf-8")
        self.assertIn("mkdir -p /usr/local/libexec /etc/handheld-dock-mode", installer)
        self.assertIn("/usr/local/libexec/hdm-deploy-plugin HDM-update-*.zip HDM-update-*.zip.sig", installer)
        self.assertNotIn("systemctl", installer)
        self.assertNotIn("gamescope", installer.casefold())
        self.assertNotIn("decky", installer.casefold())
