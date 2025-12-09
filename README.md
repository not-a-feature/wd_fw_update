[![PyPI-Server](https://img.shields.io/pypi/v/wd_fw_update.svg)](https://pypi.org/project/wd_fw_update/)
[![Monthly Downloads](https://pepy.tech/badge/wd_fw_update/month)](https://pepy.tech/project/wd_fw_update)

# wd_fw_update
<img alt="Western Digital SSD Firmware Update Tool" src=https://github.com/not-a-feature/wd_fw_update/raw/main/logo.png height=90>

This is a firmware update tool for Western Digital SSDs on Ubuntu / Linux Mint.

It provides a user-friendly interface to select the firmware version for the update process.

It uses the Western Digital API and the NVME toolbox `nvme-cli` but is NOT associated in any case to them.

It was originally developed for Frame.Work laptops, but should work with any Ubuntu / Mint device with Western Digital NVME SSD.

See the discussion on: [community.frame.work](https://community.frame.work/t/western-digital-drive-update-guide-without-windows-wd-dashboard/20616) and [juleskreuer.eu](https://juleskreuer.eu/western-digital-firmware-update/)

<img alt="GIF" src=https://github.com/not-a-feature/wd_fw_update/raw/main/gif.gif height=250>

## Installation
### Prerequisites

Make sure the following dependencies are installed on your system:
- sudo
- nvme-cli

### Via source

Clone the repository:

```bash
git clone https://github.com/not-a-feature/wd_fw_update.git
cd wd_fw_update

pip install .
```

### Via pypi:
The newest release is published on pypi.

```bash
pip install wd-fw-update
```


## Usage

Run

```bash
wd_fw_update
```

Follow the on-screen prompts to select the appropriate options for your firmware update.
The script will guide you through the process, and once completed, it will provide a summary of the update.
Depending on the update mode, it may prompt you to reboot or switch to the new slot.


## Command-Line Options

    --version: Display the version of the firmware update tool.
    -i, --info: Display information about the available drives.
    -m, --manual: Disable version and dependency checks.
    --ignore_ssl_errors: Disable SSL check.
    -v, --verbose: Set the log level to INFO.
    -vv, --very-verbose: Set the log level to DEBUG.

### -i, --info
The `-i` flag will display about the available drives.

Example:

```
========== Device Info ==========
Device                   : /dev/nvme0n1
Model                    : WD_BLACK SN770 500GB
Current fw version       : 731120WD
Slot 1 readonly          : False
Slot count               : 2
Current slot             : 2
Slots with firmware      : {1: '731030WD', 2: '731120WD'}

```

### -m, --manual
The `-m` flag enables manual mode, bypassing several checks:
- Displays all available firmware versions for selection, not just newer ones.
- Allows selection of firmware versions that do not list the current version as a dependency.



## Note

This project has been set up using PyScaffold 4.5. For details and usage
information on PyScaffold see https://pyscaffold.org/.

## Dependencies
- [nvme cli](https://github.com/linux-nvme/nvme-cli)
- [inquirer](https://pypi.org/project/inquirer/)
- [requests](https://pypi.org/project/requests/)

## License
Copyright (C) 2026 by Jules Kreuer - @not_a_feature and contributers.
This piece of software is published unter the GNU General Public License v3.0
TLDR:

 | Permissions      | Conditions                   | Limitations |
 | ---------------- | ---------------------------- | ----------- |
 | ✓ Commercial use | Disclose source              | ✕ Liability |
 | ✓ Distribution   | License and copyright notice | ✕ Warranty  |
 | ✓ Modification   | Same license                 |             |
 | ✓ Patent use     | State changes                |             |
 | ✓ Private use    |                              |             |

Go to [LICENSE](https://github.com/not-a-feature/wd_fw_update/blob/main/LICENSE) to see the full version.
