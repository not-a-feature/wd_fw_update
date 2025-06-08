import json
import subprocess
import unittest
from unittest.mock import patch, MagicMock

# Adjust the import path based on how wd_fw_update modules are typically imported.
# This might need to be src.wd_fw_update.main or wd_fw_update.main depending on PYTHONPATH setup for tests.
from src.wd_fw_update.main import get_devices, _logger

class TestGetDevices(unittest.TestCase):

    @patch('subprocess.run')
    def test_get_devices_fedora_case(self, mock_subprocess_run):
        # Simulate output for Fedora: nvme list -o json results in /dev/nvme0n1
        mock_output = {
            "Devices": [
                {
                    "NameSpace": 1,
                    "DevicePath": "/dev/nvme0n1",
                    "Firmware": "620361WD",
                    "ModelNumber": "WD_BLACK SN850X 2000GB",
                    "SerialNumber": "231915800224"
                }
            ]
        }
        mock_subprocess_run.return_value = MagicMock(
            stdout=json.dumps(mock_output),
            stderr="",
            returncode=0
        )

        # Suppress logging output during the test
        _logger.disabled = True
        devices = get_devices()
        _logger.disabled = False # Re-enable logging

        self.assertEqual(devices, ["/dev/nvme0"])

    @patch('subprocess.run')
    def test_get_devices_multiple_devices(self, mock_subprocess_run):
        # Simulate output for multiple devices, some with namespaces, some without
        mock_output = {
            "Devices": [
                {
                    "NameSpace": 1,
                    "DevicePath": "/dev/nvme0n1",
                    "Firmware": "FW1",
                    "ModelNumber": "Model1",
                    "SerialNumber": "SN1"
                },
                {
                    "DevicePath": "/dev/nvme1", # No namespace
                    "Firmware": "FW2",
                    "ModelNumber": "Model2",
                    "SerialNumber": "SN2"
                },
                {
                    "NameSpace": 1,
                    "DevicePath": "/dev/nvme2n1",
                    "Firmware": "FW3",
                    "ModelNumber": "Model3",
                    "SerialNumber": "SN3"
                }
            ]
        }
        mock_subprocess_run.return_value = MagicMock(
            stdout=json.dumps(mock_output),
            stderr="",
            returncode=0
        )
        _logger.disabled = True
        devices = get_devices()
        _logger.disabled = False

        # Expected order might vary if set is used internally before list conversion,
        # but the content should be the same. Sorting for robust comparison.
        self.assertEqual(sorted(devices), sorted(["/dev/nvme0", "/dev/nvme1", "/dev/nvme2"]))

    @patch('subprocess.run')
    def test_get_devices_no_devices(self, mock_subprocess_run):
        # Simulate output for no devices found
        mock_output = {"Devices": []}
        mock_subprocess_run.return_value = MagicMock(
            stdout=json.dumps(mock_output),
            stderr="",
            returncode=0
        )
        _logger.disabled = True
        devices = get_devices()
        _logger.disabled = False
        self.assertEqual(devices, [])

    @patch('subprocess.run')
    def test_get_devices_json_decode_error(self, mock_subprocess_run):
        # Simulate invalid JSON output
        mock_subprocess_run.return_value = MagicMock(
            stdout="not a valid json",
            stderr="",
            returncode=0
        )
        _logger.disabled = True
        devices = get_devices()
        _logger.disabled = False
        self.assertEqual(devices, []) # Expect empty list on decode error

    @patch('subprocess.run')
    def test_get_devices_subprocess_error(self, mock_subprocess_run):
        # Simulate an error during subprocess execution
        mock_subprocess_run.return_value = MagicMock(
            stdout="",
            stderr="some error",
            returncode=1 # Non-zero return code
        )
        _logger.disabled = True
        # Depending on implementation, this might raise an exception or return an empty list.
        # The current get_devices() seems to not explicitly handle non-zero return codes
        # other than json parsing. If result.stdout is empty, it will return [].
        devices = get_devices()
        _logger.disabled = False
        self.assertEqual(devices, [])

if __name__ == '__main__':
    unittest.main()
