import os
import subprocess
import unittest
from unittest.mock import Mock, patch

from wd_fw_update import main


class DependencyTests(unittest.TestCase):
    def test_nvme_on_path_takes_precedence(self):
        with patch.object(main, "which", return_value="/custom/bin/nvme") as which:
            self.assertEqual(main.get_nvme_path(), "/custom/bin/nvme")
        which.assert_called_once_with("nvme")

    def test_nvme_falls_back_to_administration_directories(self):
        with patch.object(main, "which", side_effect=[None, "/usr/sbin/nvme"]) as which:
            self.assertEqual(main.get_nvme_path(), "/usr/sbin/nvme")
        self.assertEqual(
            which.call_args_list[1].kwargs, {"path": os.pathsep.join(("/usr/sbin", "/sbin"))}
        )

    def test_missing_dependencies(self):
        for sudo, nvme, missing in [
            ("/usr/bin/sudo", "/usr/sbin/nvme", False),
            (None, "/usr/sbin/nvme", True),
            ("/usr/bin/sudo", None, True),
        ]:
            with self.subTest(sudo=sudo, nvme=nvme):
                with (
                    patch.object(main, "which", return_value=sudo),
                    patch.object(main, "get_nvme_path", return_value=nvme),
                ):
                    self.assertEqual(main.check_missing_dependencies(), missing)

    def test_uninstalled_nvme_is_not_found(self):
        with patch.object(main, "which", return_value=None):
            self.assertIsNone(main.get_nvme_path())

    @patch.object(main, "get_nvme_path", return_value="/usr/sbin/nvme")
    def test_device_listing_uses_resolved_path(self, _):
        result = subprocess.CompletedProcess(
            [], 0, stdout="header\nseparator\n/dev/nvme0n1 model\n"
        )
        with patch.object(main.subprocess, "run", return_value=result) as run:
            self.assertEqual(main.get_devices(), ["/dev/nvme0"])
        self.assertEqual(run.call_args.args[0], ["/usr/sbin/nvme", "list"])

    @patch.object(main, "get_nvme_path", return_value="/usr/sbin/nvme")
    def test_property_queries_use_resolved_path(self, _):
        results = [
            Mock(stdout='{"mn": "WD_BLACK SN7100 4TB", "fr": "7613H0WD", "frmw": 4}'),
            Mock(
                returncode=0,
                stdout='{"fw_log": {"Active Firmware Slot (afi)": 1, "Firmware Rev Slot 1": "7613H0WD"}}',
            ),
        ]
        drive = main.Drive(device="/dev/nvme0n1")
        with patch.object(main.subprocess, "run", side_effect=results) as run:
            main.get_model_properties(drive)
        self.assertEqual(run.call_count, 2)
        for call, command in zip(run.call_args_list, ["id-ctrl", "fw-log"]):
            self.assertEqual(call.args[0][:3], ["sudo", "/usr/sbin/nvme", command])
        self.assertEqual(drive.current_fw_version, "7613H0WD")

    @patch.object(main, "get_nvme_path", return_value="/usr/sbin/nvme")
    def test_firmware_commands_use_resolved_path(self, _):
        drive = main.Drive(device="/dev/nvme0n1", selected_slot=2)
        drive.mode = 0
        response = Mock(status_code=200, content=b"firmware")
        with (
            patch.object(main, "NamedTemporaryFile"),
            patch.object(main.requests, "get", return_value=response),
            patch.object(main.inquirer, "prompt", return_value={"continue": True}),
            patch.object(main.subprocess, "run", return_value=Mock(returncode=0)) as run,
        ):
            self.assertTrue(main.update_fw(drive))
        self.assertEqual(run.call_count, 2)
        for call, command in zip(run.call_args_list, ["fw-download", "fw-commit"]):
            self.assertEqual(call.args[0][:3], ["sudo", "/usr/sbin/nvme", command])


if __name__ == "__main__":
    unittest.main()
