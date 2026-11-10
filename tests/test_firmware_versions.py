import unittest
from unittest.mock import Mock, patch

from wd_fw_update import main


class FirmwareVersionTests(unittest.TestCase):
    def test_automatic_mode_only_offers_newer_versions(self):
        cases = [
            ("7613H0WD", ["7612H0WD", "7613H0WD", "7616H0WD"], ["7616H0WD"]),
            ("7615M0WD", ["7615M0WD", "7619M0WD"], ["7619M0WD"]),
            ("731120WD", ["731030WD", "731120WD", "731150WD"], ["731150WD"]),
            ("9WD", ["8WD", "9WD", "10WD"], ["10WD"]),
            ("7613H9WD", ["7613H8WD", "7613H9WD", "7613H10WD"], ["7613H10WD"]),
        ]
        for current, available, expected in cases:
            with self.subTest(current=current):
                drive = self.make_drive(current, available)
                with patch.object(
                    main.inquirer, "prompt", return_value={"version": expected[0]}
                ) as prompt:
                    main.ask_fw_version(drive, manual_mode=False)
                self.assertEqual(prompt.call_args.args[0][0].choices, expected)
                self.assertEqual(drive.selected_version, expected[0])

    def test_no_newer_version_exits_without_prompting(self):
        drive = self.make_drive("7616H0WD", ["7613H0WD", "7616H0WD"])
        with patch.object(main, "print_info"), patch.object(main.inquirer, "prompt") as prompt:
            with self.assertRaises(SystemExit) as result:
                main.ask_fw_version(drive, manual_mode=False)
        self.assertEqual(result.exception.code, 0)
        prompt.assert_not_called()

    def test_manual_mode_includes_all_versions(self):
        versions = ["7613H0WD", "7616H0WD", "7619M0WD"]
        drive = self.make_drive("7616H0WD", versions)
        with patch.object(main.inquirer, "prompt", return_value={"version": versions[0]}) as prompt:
            main.ask_fw_version(drive, manual_mode=True)
        self.assertEqual(prompt.call_args.args[0][0].choices, versions)

    def test_numeric_versions_with_optional_wd_suffix_compare_equally(self):
        self.assertEqual(main.firmware_version_key("0010WD"), main.firmware_version_key("10"))

    def test_dependency_check_still_rejects_incompatible_firmware(self):
        drive = self.make_drive("7613H0WD", ["7619M0WD"])
        drive.selected_version = "7619M0WD"
        response = Mock(content=b"<device><dependency>7615M0WD</dependency></device>")
        with patch.object(main.requests, "get", return_value=response):
            with self.assertRaises(SystemExit) as result:
                main.get_upgrade_url(drive, manual_mode=False)
        self.assertEqual(result.exception.code, 1)
        self.assertEqual(drive.firmware_url, "")

    @staticmethod
    def make_drive(current, versions):
        return main.Drive(
            model="WD_BLACK SN7100 4TB",
            current_fw_version=current,
            relative_fw_urls=[
                f"wdDashboard/firmware/WD_BLACK_SN7100_4TB/{v}/device_properties.xml"
                for v in versions
            ],
        )


if __name__ == "__main__":
    unittest.main()
