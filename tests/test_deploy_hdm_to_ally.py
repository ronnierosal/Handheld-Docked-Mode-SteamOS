from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DirectDeployScriptTests(unittest.TestCase):
    def source(self) -> str:
        return (ROOT / "scripts" / "deploy_hdm_to_ally.ps1").read_text(encoding="utf-8")

    def test_requires_explicit_confirmation_and_interactive_sudo_option(self):
        source = self.source()
        self.assertIn("[switch]$ConfirmDeploy", source)
        self.assertIn("[switch]$InteractiveSudo", source)
        self.assertIn("if (-not $ConfirmDeploy)", source)

    def test_backups_replacement_exec_bit_restart_and_provenance_are_ordered(self):
        source = self.source()
        self.assertIn("HandheldDockMode.backup-", source)
        self.assertIn('mv "`$PLUGIN_DIR" "`$BACKUP"', source)
        self.assertIn('chmod 0755 "`$PLUGIN_DIR/bin/gamescope"', source)
        self.assertIn("systemctl restart plugin_loader.service", source)
        self.assertLess(source.index('mv "`$STAGING/HandheldDockMode" "`$PLUGIN_DIR"'), source.index("systemctl restart plugin_loader.service"))
        self.assertIn("build_info.json", source)

    def test_never_targets_session_or_hardware_actions(self):
        source = self.source().casefold()
        self.assertNotIn("systemctl restart gamescope", source)
        self.assertNotIn("systemctl suspend", source)
        self.assertNotIn("reboot", source)
        self.assertNotIn("usb4", source)
        self.assertNotIn("amdgpu", source)


if __name__ == "__main__":
    unittest.main()
