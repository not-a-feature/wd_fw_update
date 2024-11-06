import argparse
import json
import logging
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from shutil import which
from tempfile import NamedTemporaryFile
from typing import List

import inquirer
import requests

from wd_fw_update import __name__ as package_name
from wd_fw_update import __version__

__author__ = "Jules Kreuer"
__copyright__ = "Jules Kreuer"
__license__ = "GPL-3.0-or-later"

_logger = logging.getLogger(__name__)

BASE_WD_DOMAIN = "https://wddashboarddownloads.wdc.com/wdDashboard"
DEVICE_LIST_URL = f"{BASE_WD_DOMAIN}/config/devices/lista_devices.xml"


@dataclass
class Drive:
    """Class for keeping track of the NVME drive and firmware properties."""

    device: str = ""
    model: str = ""
    current_fw_version: str = ""
    slot_1_readonly: bool = None
    slot_count: int = -1
    current_slot: int = -1
    slots_with_firmware: dict = field(default_factory=dict)
    selected_slot: int = -1
    activation_without_reset: bool = None
    relative_fw_urls: List[str] = field(default_factory=list)
    selected_version: str = ""
    firmware_url: str = ""
    activation_mode: int = -1
    tmp_fw_file_name: str = ""


def parse_args(args):
    """Parse command line parameters

    Args:
        args (List[str]): command line parameters as list of strings
             (for example  ``["--help"]``).

    Returns:
        :obj:`argparse.Namespace`: command line parameters namespace
    """
    parser = argparse.ArgumentParser(description="Updates the firmware of Western Digital SSDs.")
    parser.add_argument(
        "--version",
        action="version",
        version=f"wd_fw_update {__version__}",
    )

    parser.add_argument(
        "-i",
        "--info",
        action="store_true",
        help="Print information about available drives.",
    )

    # parser.add_argument(
    #    "-f",
    #    "--force",
    #    action="store_true",
    #    help="Force the firmware update without additional confirmation.",
    # )

    parser.add_argument(
        "-v",
        "--verbose",
        dest="loglevel",
        help="set loglevel to INFO",
        action="store_const",
        const=logging.INFO,
    )

    parser.add_argument(
        "-vv",
        "--very-verbose",
        dest="loglevel",
        help="set loglevel to DEBUG",
        action="store_const",
        const=logging.DEBUG,
    )

    return parser.parse_args(args)


def setup_logging(loglevel: int) -> None:
    """Setup basic logging

    Args:
         loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(
        level=loglevel,
        stream=sys.stdout,
        format=logformat,
        datefmt="[%Y-%m-%d %H:%M:%S]",
    )


def check_missing_dependencies() -> bool:
    """Check for missing dependencies

    Returns:
        is_missing (bool): True if any dependency is missing, False otherwise.
    """
    dependencies = ["sudo", "nvme"]  # List of commands to check
    is_missing = any(which(cmd) is None for cmd in dependencies)
    return is_missing


def print_info(drive=None) -> None:
    """Print an overview of the NVME drive."""

    get_model_properties(drive=drive)
    print("========== Device Info ==========")
    for k, v in asdict(drive).items():
        k = k.replace("_", " ").ljust(25)
        k = k[0].upper() + k[1:]
        print(f"{k}: {v}")
    print()


def get_devices() -> List[str]:
    """Returns a list of all NVME drives.

    Returns:
        devices (List[str]): List of NVME drives
    """
    _logger.debug("Getting device list.")

    result = subprocess.run(
        ["nvme", "list"],
        shell=False,
        capture_output=True,
        text=True,
    )
    devices = [d.split(" ", 1)[0] for d in result.stdout.split("\n")[2:] if d]
    _logger.debug(f"Device list: {devices}\n")
    return devices


def ask_device(drive) -> None:
    """Prompt the user to select an NVME drive for the update.

    Args:
        drive (Drive): The Drive object.

    Returns:
        None

    Updates:
        drive.device (str): The selected device path.
    """

    devices = get_devices()

    if len(devices) == 1:
        _logger.debug(f"Only one device found: {devices}\n")
        drive.device = devices[0]
        return

    _logger.debug(f"Asking for device: {devices}\n")
    questions = [
        inquirer.List(
            "device",
            message="Select the NVME drive you want to update",
            choices=devices,
            carousel=True,
        ),
    ]
    device = inquirer.prompt(questions)["device"]
    drive.device = device


def get_model_properties(drive) -> None:
    """Retrieve model properties for the specified NVME device.

    Args:
        drive (Drive): The Drive object.

    Returns:
        None

    Updates:
        drive.model (str): The selected device path.
        drive.current_fw_version (str): The current firmware version.
        drive.slot_1_readonly (bool): Is slot 1 readonly?
        drive.slot_count (int): How many slots are available.
        drive.activation_without_reset (bool): Does the drive support fw activation without reset?
        drive.current_slot (int): The currently active slot.
        drive.slots_with_firmware (dict): Dictionaly of slots that have a fw installed with its respective version.
    """
    _logger.info(f"Getting device properties of {drive.device}")

    result = subprocess.run(
        ["sudo", "nvme", "id-ctrl", drive.device, "--output-format=json"],
        shell=False,
        capture_output=True,
        text=True,
    )
    # _logger.debug(result.stdout)
    raw_properties = json.loads(result.stdout)

    drive.model = raw_properties["mn"].strip()
    drive.current_fw_version = raw_properties["fr"].strip()

    # Get slot information
    frmw = bin(int(raw_properties["frmw"]))
    frmw = frmw.lstrip("0b").rjust(8, "0")

    drive.slot_1_readonly = bool(int(frmw[-1]))
    drive.slot_count = int(frmw[-4:-1], 2)
    drive.activation_without_reset = bool(int(frmw[-5]))

    # Get current active slot
    result = subprocess.run(
        ["sudo", "nvme", "fw-log", drive.device, "--output-format=json"],
        shell=False,
        capture_output=True,
        text=True,
    )
    # _logger.debug(result.stdout)

    result = json.loads(result.stdout)
    result = list(result.values())[0]

    """
    From: https://nvmexpress.org/wp-content/uploads/NVM-Express-1_4b-2020.09.21-Ratified.pdf

    Active Firmware Info (AFI): Specifies information about the active firmware revision.
    [...]

    - Bits 2:0  The firmware slot from which the actively running firmware revision was loaded.
    """
    active_firmware_slot = int(result["Active Firmware Slot (afi)"])
    active_firmware_slot = bin(active_firmware_slot).lstrip("0b").rjust(8, "0")
    current_slot = int(active_firmware_slot[-2:], 2)
    _logger.info(f"Current Active Firmware Slot: {current_slot}")

    slots_with_firmware = {}
    for k, v in result.items():
        if k.startswith("Firmware Rev Slot"):
            k = int(k.lstrip("Firmware Rev Slot "))
            slots_with_firmware[k] = v

    _logger.debug(f"Slots with Firmware: {slots_with_firmware}")

    drive.current_slot = current_slot
    drive.slots_with_firmware = slots_with_firmware


def get_fw_url(drive: Drive) -> None:
    """Fetch firmware URL for the specified model from the device list.

    Args:
        drive (Drive): The Drive object.

    Returns:
        None

    Updates:
        drive.relative_fw_urls (list): List of all fw properties urls.
    """
    _logger.debug("Getting firmware url.")

    response = requests.get(DEVICE_LIST_URL)
    response.raise_for_status()

    root = ET.fromstring(response.content)

    for device in root.findall("lista_device"):
        if device.get("model") == drive.model:
            drive.relative_fw_urls = [u.text for u in device.findall("url")]
            return

    raise RuntimeError("No Firmware found for this model. Please check your selection / model.")


def ask_fw_version(drive) -> None:
    """Prompt the user to select a firmware version.

    Args:
        drive (Drive): The Drive object.

    Returns:
        None

    Updates:
        drive.selected_version (str): Selected firmware version.
    """
    if not drive.relative_fw_urls:
        raise RuntimeError("No Firmware Version to select.")

    fw_versions = [
        v
        for url in drive.relative_fw_urls
        if not (v := url.split("/")[3]) == drive.current_fw_version
    ]
    _logger.debug(f"Firmware versions: {fw_versions}")

    if not fw_versions:
        print_info(drive=drive)
        print("No different / newer firmware version found.")
        print("You are probably already on the latest version.")
        exit(0)

    if len(fw_versions) == 1:
        _logger.debug("Only one firmware to select, skipping user-promt.")
        drive.selected_version = fw_versions[0]
        return

    questions = [
        inquirer.List(
            "version",
            message=f"Select the Firmware Version for {drive.model}",
            choices=fw_versions,
            carousel=True,
        ),
    ]
    selected_version = inquirer.prompt(questions)["version"]
    drive.selected_version = selected_version


def ask_slot(drive) -> None:
    """Prompt the user to select a firmware slot

    Args:
        drive (Drive): The Drive object.

    Returns:
        None

    Updates:
        drive.selected_slot (int): Selected slot number.
    """

    slots = list(range(1, drive.slot_count + 1))

    # If the first slot is read only
    if drive.slot_1_readonly:
        slots = slots[1:]

    _logger.debug(f"Firmware slots: {slots}")

    if len(slots) == 1:
        _logger.info("Only one slot to select, skipping user-promt.")
        drive.selected_slot = slots[0]
        return

    print("Select the slot to which the firmware should be installed.")

    slot_questions = []
    for s in slots:
        if s in drive.slots_with_firmware:
            fw_label = drive.slots_with_firmware[s]
        else:
            fw_label = "No firmware."
        slot_questions.append(f"{s}: {fw_label}")

    questions = [
        inquirer.List(
            "slot",
            message="Slot ID: Current Firmware Version",
            choices=slot_questions,
            carousel=True,
        ),
    ]
    slot = inquirer.prompt(questions)["slot"]
    slot = int(slot[0])
    drive.selected_slot = slot


def ask_mode(drive) -> None:
    """Prompt the user to select the firmware update mode

    Args:
        drive (Drive): The Drive object.

    Returns:
        None

    Updates:
        drive.mode (int): Selected update mode.
    """

    o0 = "0: Downloaded image replaces the image indicated by the Firmware Slot field. This image is not activated."
    o1 = "1: Downloaded image replaces the image indicated by the Firmware Slot field. This image is activated at the next reset."
    o2 = "2: The image indicated by the Firmware Slot field is activated at the next reset."
    o3 = "3: The image specified by the Firmware Slot field is requested to be activated immediately without reset."

    modes = [o0, o1, o2]
    if drive.activation_without_reset:
        modes.append(o3)

    questions = [
        inquirer.List(
            "mode",
            message="Select update action, Mode 2 is recommended",
            choices=modes,
            default=o2,
            carousel=True,
        ),
    ]
    mode = inquirer.prompt(questions)["mode"]
    mode = int(mode[0])
    drive.mode = mode


def get_upgrade_url(drive) -> None:
    """Check if an upgrade from the current firmware to the new one is supported and returns the firmware url.

    Args:
        drive (Drive): The Drive object.

    Returns:
        None

    Updates:
        drive.firmware_url (str): URL to the firmware file.
    """

    model = drive.model.replace(" ", "_")
    base_url = f"{BASE_WD_DOMAIN}/firmware/{model}/{drive.selected_version}"
    prop_url = f"{base_url}/device_properties.xml"

    _logger.debug(f"Firmware properties url: {prop_url}")

    response = requests.get(prop_url)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    dependencies_list = [dep.text for dep in root.findall("dependency")]

    _logger.debug(f"Firmware dependencies: {dependencies_list}")

    # Check if current firmware is in dependencies
    if drive.current_fw_version not in dependencies_list:
        print(f"The current firmware version {drive.current_fw_version} is not in the dependency")
        print(f"list of the new firmware. In order to upgrade to {drive.selected_version}, please")
        print(f"upgrade to one of these versions first: {dependencies_list}")
        exit(1)

    firmware_url = f"{base_url}/{root.findtext('fwfile')}"

    _logger.debug(f"Firmware file url: {firmware_url}\n")
    drive.firmware_url = firmware_url


def update_fw(drive) -> bool:
    """Update firmware for the specified NVME device

    Args:
        current_fw_version (str): Current firmware version.
        version (str): Firmware version to be installed.
        firmware_url (str): URL to new firmware file.
        model (str): Model name.
        device (str): NVME device identifier.
        current_slot (int): Current active firmware slot.
        slot (int): Selected firmware slot.
        mode (int): Selected update mode.

    Returns:
        success (bool): Success status.
    """
    _logger.info("Downloading firmware.")

    with NamedTemporaryFile(
        prefix=package_name,
        suffix=".fluf",
        mode="wb",
        delete=False,  # Important: Don't delete immediately
    ) as fw_file:
        drive.tmp_fw_file_name = fw_file.name

        try:
            r = requests.get(drive.firmware_url)
            r.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            fw_file.write(r.content)

        except requests.exceptions.RequestException as e:
            _logger.error(f"Error downloading firmware: {e}")
            print(f"Error downloading firmware: {e}")
            exit(1)

        _logger.info(f"HTTP Status Code: {r.status_code}")
        if not r.status_code == 200:
            print("Error downloading the firmware file.")
            exit(1)

        print()
        print("========== Summary ==========")
        print(f"NVME location:     {drive.device}")
        print(f"Model:             {drive.model}")
        print(f"Firmware Version:  {drive.current_fw_version} --> {drive.selected_version}")
        print(f"Installation Slot: {drive.selected_slot}")
        print(f"Active Slot:       {drive.current_slot} --> {drive.selected_slot}")
        print(f"Activation Mode:   {drive.mode}")
        print(f"Temporary File:    {drive.tmp_fw_file_name}\n\n")

        questions = [
            inquirer.Confirm("continue", message="The summary is correct. Continue", default=False)
        ]

        answer = inquirer.prompt(questions)["continue"]

        if not answer:
            print("Aborted.")
            exit(0)

        _logger.info("Loading the firmware file.")

        result = subprocess.run(
            [
                "sudo",
                "nvme",
                "fw-download",
                drive.device,
                f"--fw={drive.tmp_fw_file_name}",
            ],
            shell=False,
            capture_output=True,
            text=True,
        )
        _logger.debug(result)
        _logger.info(f"NVME Download returncode: {result.returncode}")

        if not result.returncode == 0:
            return False

        _logger.info("Commiting / Switching to the firmware file.")
        result = subprocess.run(
            [
                "sudo",
                "nvme",
                "fw-commit",
                drive.device,
                f"-s {drive.selected_slot}",
                f"-a {drive.mode}",
            ],
            shell=False,
            capture_output=True,
            text=True,
        )
        _logger.debug(result)
        _logger.info(f"NVME Commit returncode: {result.returncode}")

    if result.returncode == 0:
        return True
    else:
        print(result)
        return False


def wd_fw_update():
    """Updates the firmware of Western Digital SSDs on Ubuntu / Linux Mint.
    The user will be prompted for version / model / slot selection.
    """
    _logger.info("Starting firmware update process.")
    print("Western Digital SSD Firmware Update Tool\n")

    # Step 0: Check dependencies
    if check_missing_dependencies():
        print("Missing dependencies!")
        print("Please install: ")
        print("   sudo")
        print("   nvme-cli")
        exit(1)

    drive = Drive()

    # Step 1: Get model number and firmware version
    ask_device(drive=drive)

    # Step 2: Fetch the device list and find the firmware URL
    get_model_properties(drive=drive)

    get_fw_url(drive=drive)

    # Step 3: Check firmware version and dependencies
    ask_fw_version(drive=drive)

    # Step 4: Check if an upgrade from the current firmware to the new one is supported.
    get_upgrade_url(drive=drive)

    # Step 5: Ask for the slot to install the firmware
    ask_slot(drive=drive)

    # Step 6: Ask for installation mode
    ask_mode(drive=drive)

    # Step 7: Download and install the firmware file
    result = update_fw(drive)

    if result:
        if drive.mode == 0:
            print("Update complete. Don't forget to switch to the new slot.")
        elif drive.mode == 1 or drive.mode == 2:
            print("Update complete. Please reboot.")
        elif drive.mode == 3:
            print("Update complete. Switched to the new version.")
    else:
        print("An error happened during the update process.")
        raise RuntimeError("Please try again with caution.")

    _logger.info("Firmware update process completed.")


def main(args):
    """Wrapper allowing :func:`wd_fw_update` to be called with string arguments in a CLI fashion

    Instead of returning the value from :func:`wd_fw_update`, it prints the result to the
    ``stdout`` in a nicely formatted message.

    Args:
      args (List[str]): command line parameters as list of strings
          (for example  ``["--verbose", "--help"]``).
    """
    args = parse_args(args)
    setup_logging(args.loglevel)
    _logger.debug(args)

    if args.info:
        devices = get_devices()
        for d in devices:
            drive = Drive()
            drive.device = d
            print_info(drive=drive)

        exit()

    wd_fw_update()

    _logger.info("[END of script]")


def run():
    """Calls :func:`main` passing the CLI arguments extracted from :obj:`sys.argv`

    This function is used as entry point to create console scripts with setuptools.
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    # ^  This is a guard statement that will prevent the following code from
    #    being executed in the case someone imports this file instead of
    #    executing it as a script.
    #    https://docs.python.org/3/library/__main__.html
    run()
