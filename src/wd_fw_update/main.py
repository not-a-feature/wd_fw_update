import argparse
import logging
import subprocess
import sys
import xml.etree.ElementTree as ET
from shutil import which
from tempfile import NamedTemporaryFile
from typing import Dict, List, Tuple

import inquirer
import requests
from tqdm.auto import tqdm

from wd_fw_update import __name__ as package_name
from wd_fw_update import __version__

__author__ = "Jules Kreuer"
__copyright__ = "Jules Kreuer"
__license__ = "GPL-3.0-or-later"

_logger = logging.getLogger(__name__)

BASE_WD_DOMAIN = "https://wddashboarddownloads.wdc.com/wdDashboard"
DEVICE_LIST_URL = f"{BASE_WD_DOMAIN}/config/devices/lista_devices.xml"


def parse_args(args):
    """Parse command line parameters

    Args:
      args (List[str]): command line parameters as list of strings
          (for example  ``["--help"]``).

    Returns:
      :obj:`argparse.Namespace`: command line parameters namespace
    """
    parser = argparse.ArgumentParser(description="Just a Fibonacci demonstration")
    parser.add_argument(
        "--version",
        action="version",
        version=f"wd_fw_update {__version__}",
    )

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


def setup_logging(loglevel) -> None:
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
      bool: True if any dependency is missing, False otherwise
    """
    dependencies = ["sudo", "nvme"]  # List of commands to check

    return any(which(cmd) is None for cmd in dependencies)


def ask_device() -> str:
    """Prompt the user to select an NVME drive for the update

    Returns:
      str: Selected NVME drive
    """
    _logger.debug("Getting device list.")

    result = subprocess.run(
        ["nvme", "list"],
        shell=False,
        capture_output=True,
        text=True,
    )
    devices = [d.split(" ", 1)[0] for d in result.stdout.split("\n")[2:] if d]

    if len(devices) == 1:
        _logger.debug(f"Only one device found: {devices}\n")
        return devices[0]

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
    return device


def get_model_properties(device) -> Dict:
    """Retrieve model properties for the specified NVME device

    Args:
      device (str): NVME device identifier

    Returns:
      dict: Model properties
    """
    _logger.debug("Getting device properties.")

    result = subprocess.run(
        ["sudo", "nvme", "id-ctrl", device],
        shell=False,
        capture_output=True,
        text=True,
    )

    model_properties = {}
    for line in result.stdout.split("\n")[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            model_properties[k.strip()] = v.strip()
    return model_properties


def get_fw_url(model) -> List[str]:
    """Fetch firmware URL for the specified model from the device list

    Args:
      model (str): Model name

    Returns:
      list: List of firmware URLs
    """
    _logger.debug("Getting firmware url.")

    response = requests.get(DEVICE_LIST_URL)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    for device in root.findall("lista_device"):
        if device.get("model") == model:
            return [u.text for u in device.findall("url")]

    raise RuntimeError("No Firmware found for this model. Please check your selection / model.")


def ask_fw_version(device, relative_urls, model, current_fw_version) -> str:
    """Prompt the user to select a firmware version

    Args:
      relative_urls (list): List of firmware URLs
      model (str): Model name
      current_fw_version (str): Current firmware version

    Returns:
      str: Selected firmware version
    """
    if not relative_urls:
        raise RuntimeWarning("No Firmware Version to select.")

    fw_versions = [v for url in relative_urls if not (v := url.split("/")[3]) == current_fw_version]
    _logger.debug(f"Firmware versions: f{fw_versions}")

    if not fw_versions:
        print("========== Summary ==========")
        print(f"NVME location:     {device}")
        print(f"Model:             {model}")
        print(f"Firmware Version:  {current_fw_version}")
        print("No different / newer firmware version found.")
        print("You are probably already on the latest version.")
        exit(0)

    if len(fw_versions) == 1:
        _logger.debug("Only one firmware to select, skipping user-promt.")

        version = fw_versions[0]

    else:
        questions = [
            inquirer.List(
                "version",
                message=f"Select the Firmware Version for {model}",
                choices=fw_versions,
                carousel=True,
            ),
        ]
        version = inquirer.prompt(questions)["version"]

    return version


def ask_slot(device) -> Tuple[int, int]:
    """Prompt the user to select a firmware slot

    Args:
      device (str): NVME device identifier

    Returns:
      int, int: Current active firmware slot, Selected firmware slot
    """
    result = subprocess.run(
        ["sudo", "nvme", "fw-log", device, "--output-format=normal"],
        shell=False,
        capture_output=True,
        text=True,
    )
    _logger.debug(result.stdout)

    result = result.stdout.split("\n")

    """
    From: https://nvmexpress.org/wp-content/uploads/NVM-Express-1_4b-2020.09.21-Ratified.pdf

    Active Firmware Info (AFI): Specifies information about the active firmware revision.

    - Bit 7     Reserved.
    - Bits 6:4  The firmware slot that is going to be activated at the
                next Controller Level Reset. If this field is 0h, then the
                controller does not indicate the firmware slot that is
                going to be activated at the next Controller Level Reset.

    - Bit 3     Reserved.
    - Bits 2:0  The firmware slot from which the actively running firmware revision was loaded.
    """
    current_slot = result[1].split(":")[1].strip()
    current_slot = int(current_slot, 0)  # From Hex to Base 10
    if not current_slot == 1:
        current_slot = int("0b" + bin(current_slot)[-2:], base=0)  # Take last two bits

    print(f"Current Active Firmware Slot (afi): {current_slot}")

    slots = [s[3:] for s in sorted(result[2:10]) if s]
    _logger.debug(f"Firmware slots: {slots}")

    if len(slots) == 1:
        _logger.info("Only one slot to select, skipping user-promt.")

        return int(slots[0].split(":")[0])  # Should always be 1

    print("Select the slot to which the firmware should be installed.")
    questions = [
        inquirer.List(
            "slot",
            message="Slot ID: Current Firmware Version",
            choices=slots,
            carousel=True,
        ),
    ]
    slot = inquirer.prompt(questions)["slot"]
    slot = int(slot.split(":", 1)[0])
    return current_slot, slot


def ask_mode() -> int:
    """Prompt the user to select the firmware update mode

    Returns:
      int: Selected update mode
    """
    o0 = "0 Downloaded image replaces the image indicated by the Firmware Slot field. This image is not activated."
    o1 = "1 Downloaded image replaces the image indicated by the Firmware Slot field. This image is activated at the next reset."
    o2 = "2 The image indicated by the Firmware Slot field is activated at the next reset."
    o3 = "3 The image specified by the Firmware Slot field is requested to be activated immediately without reset."

    modes = [o0, o1, o2, o3]
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
    mode = int(mode.split(" ", 1)[0])
    return mode


def update_fw(version, current_fw_version, model, device, current_slot, slot, mode) -> bool:
    """Update firmware for the specified NVME device

    Args:
      version (str): Firmware version to be installed
      current_fw_version (str): Current firmware version
      model (str): Model name
      device (str): NVME device identifier
      current_slot (int): Current active firmware slot
      slot (int): Selected firmware slot
      mode (int): Selected update mode

    Returns:
      tuple: Success status (bool), Updated firmware slot (int)
    """
    # Get FW properties
    model = model.replace(" ", "_")
    prop_url = f"{BASE_WD_DOMAIN}/firmware/{model}/{version}/device_properties.xml"

    _logger.debug(f"Firmware properties url: {prop_url}")

    response = requests.get(prop_url)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    dependencies_list = [dep.text for dep in root.findall("dependency")]

    _logger.debug(f"Firmware dependencies: {dependencies_list}")

    # Check if current firmware is in dependencies
    if current_fw_version not in dependencies_list:
        print("Current firmware version is not in the dependencies.")
        raise RuntimeError(f"Please upgrade to one of these versions first: {dependencies_list}")

    firmware_url = f"{prop_url}{root.findtext('fwfile')}"

    _logger.debug(f"Firmware file url: {firmware_url}\n")
    _logger.info("Downloading firmware.")

    r = requests.get(firmware_url, stream=True)
    total_size = int(r.headers.get("content-length", 0))

    with NamedTemporaryFile(
        prefix=package_name,
        suffix=".fluf",
        mode="wb",
    ) as fw_file, tqdm(
        total=total_size,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
    ) as pbar:
        for data in r.iter_content(1024):
            pbar.update(len(data))
            fw_file.write(data)

        print()
        print("========== Summary ==========")
        print(f"NVME location:     {device}")
        print(f"Model:             {model}")
        print(f"Firmware Version:  {current_fw_version} --> {version}")
        print(f"Installation Slot: {slot}")
        print(f"Active Slot:       {current_slot} --> {slot}")
        print(f"Activation Mode:   {mode}")
        print(f"Temporary File:    {fw_file.name}\n\n")

        questions = [
            inquirer.Confirm("continue", message="The summary is correct. Continue", default=False),
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
                "download",
                fw_file.name,
                device,
            ],
            shell=False,
            capture_output=True,
            text=True,
        )
        _logger.debug(f"NVME Download returncode: {result.returncode}")

        _logger.info("Commiting / Switching to the firmware file.")
        result = subprocess.run(
            [
                "sudo",
                "nvme",
                "fw-commit",
                f"-s {slot}",
                f"-a {mode}",
                device,
            ],
            shell=False,
            capture_output=True,
            text=True,
        )
        _logger.debug(f"NVME Commit returncode: {result.returncode}")

    if result.returncode == 0:
        success = True
    else:
        success = False

    return success


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

    # Step 1: Get model number and firmware version
    device = ask_device()

    model_properties = get_model_properties(device)

    # Step 2: Fetch the device list and find the firmware URL
    model = model_properties["mn"]
    relative_urls = get_fw_url(model=model)

    # Step 3: Check firmware version and dependencies
    current_fw_version = model_properties["fr"]

    selected_version = ask_fw_version(
        device=device,
        relative_urls=relative_urls,
        model=model,
        current_fw_version=current_fw_version,
    )

    # Step 4: Ask for the slot to install the firmware
    current_slot, slot = ask_slot(device)

    # Step 5: Ask for installation mode
    mode = ask_mode()

    # Step 6: Download and install the firmware file
    result = update_fw(
        version=selected_version,
        current_fw_version=current_fw_version,
        model=model,
        device=device,
        current_slot=current_slot,
        slot=slot,
        mode=mode,
    )

    if result:
        if mode == 0:
            print("Update complete. Don't forget to switch to the new slot.")
        elif mode == 1 or mode == 2:
            print("Update complete. Please reboot.")
        elif mode == 3:
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
