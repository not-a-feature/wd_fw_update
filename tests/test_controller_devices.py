import io
import json
import subprocess
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from wd_fw_update import main

# Firmware-log responses supplied by the reporter in issue #16:
# https://github.com/not-a-feature/wd_fw_update/issues/16
FIRMWARE_LOG = {
    "nvme0": {
        "Active Firmware Slot (afi)": 2,
        "Firmware Rev Slot 1": "4924458804934881846 (620311WD)",
        "Firmware Rev Slot 2": "4924458826409718326 (620361WD)",
    }
}
FIRMWARE_ERROR = {"error": "fw log: No such device or address"}
CONTROLLER_INFO = {"mn": "WD_BLACK SN850X 2000GB", "fr": "620361WD", "frmw": 20}


def command_result(stdout, returncode=0, stderr=""):
    return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr=stderr)


class ControllerDeviceTests(unittest.TestCase):
    def test_discovery_deduplicates_namespaces_and_preserves_drive_order(self):
        output = (
            "Node Generic Model\n------------------\n"
            "/dev/nvme0n1 /dev/ng0n1 WD\n"
            "/dev/nvme12n3 /dev/ng12n3 WD\n"
            "\n"
            "/dev/nvme0n2 /dev/ng0n2 WD\n"
            "/dev/nvme12n1 /dev/ng12n1 WD\n"
        )
        with patch.object(main.subprocess, "run", return_value=command_result(output)):
            self.assertEqual(main.get_devices(), ["/dev/nvme0", "/dev/nvme12"])

    def test_empty_device_list(self):
        with patch.object(main.subprocess, "run", return_value=command_result("Header\n---\n")):
            self.assertEqual(main.get_devices(), [])

    def test_info_queries_controller_and_displays_reported_firmware_log(self):
        results = [
            command_result("Node Model\n----------\n/dev/nvme0n1 WD_BLACK SN850X 2000GB\n"),
            command_result(json.dumps(CONTROLLER_INFO)),
            command_result(json.dumps(FIRMWARE_LOG)),
        ]
        output = io.StringIO()
        with (
            patch.object(main, "get_nvme_path", return_value="/usr/sbin/nvme"),
            patch.object(main.subprocess, "run", side_effect=results) as run,
            redirect_stdout(output),
        ):
            with self.assertRaises(SystemExit) as result:
                main.main(["--info"])
        self.assertIsNone(result.exception.code)
        self.assertEqual(run.call_count, 3)
        for call, command in zip(run.call_args_list[1:], ["id-ctrl", "fw-log"]):
            self.assertEqual(call.args[0][2:4], [command, "/dev/nvme0"])
        self.assertIn("620361WD", output.getvalue())
        self.assertIn("4924458804934881846 (620311WD)", output.getvalue())

    def test_legacy_firmware_log_format_remains_supported(self):
        firmware_log = {
            "nvme0": {"Active Firmware Slot (afi)": 1, "Firmware Rev Slot 1": "620311WD"}
        }
        drive = main.Drive(device="/dev/nvme0")
        results = [
            command_result(json.dumps(CONTROLLER_INFO)),
            command_result(json.dumps(firmware_log)),
        ]
        with patch.object(main.subprocess, "run", side_effect=results):
            main.get_model_properties(drive)
        self.assertEqual(drive.current_slot, 1)
        self.assertEqual(drive.slots_with_firmware, {1: "620311WD"})

    def test_failed_or_unrecognized_logs_are_rejected_before_slot_selection(self):
        cases = [
            (command_result(json.dumps(FIRMWARE_ERROR), 1), "No such device or address"),
            (command_result(json.dumps(FIRMWARE_ERROR)), "No such device or address"),
            (command_result("", 1, "Permission denied"), "Permission denied"),
            (command_result("not JSON"), "Invalid firmware log JSON"),
            (command_result("{}"), "Unexpected firmware log format"),
            (command_result("[]"), "Unexpected firmware log format"),
            (command_result('{"nvme0": "invalid"}'), "Unexpected firmware log format"),
            (command_result('{"nvme0": {}}'), "Unexpected firmware log format"),
            (command_result('{"nvme0": {}, "nvme1": {}}'), "Unexpected firmware log format"),
        ]
        for log_result, message in cases:
            with self.subTest(stdout=log_result.stdout, returncode=log_result.returncode):
                drive = main.Drive(device="/dev/nvme0")
                results = [command_result(json.dumps(CONTROLLER_INFO)), log_result]
                with patch.object(main.subprocess, "run", side_effect=results):
                    with self.assertRaisesRegex(RuntimeError, message):
                        main.get_model_properties(drive)
                self.assertEqual(drive.current_slot, -1)
                self.assertEqual(drive.slots_with_firmware, {})


if __name__ == "__main__":
    unittest.main()
