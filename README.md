[![ReadTheDocs](https://readthedocs.org/projects/wd_fw_update/badge/?version=latest)](https://wd_fw_update.readthedocs.io/en/stable/)
[![PyPI-Server](https://img.shields.io/pypi/v/wd_fw_update.svg)](https://pypi.org/project/wd_fw_update/)
[![Conda-Forge](https://img.shields.io/conda/vn/conda-forge/wd_fw_update.svg)](https://anaconda.org/conda-forge/wd_fw_update)
[![Monthly Downloads](https://pepy.tech/badge/wd_fw_update/month)](https://pepy.tech/project/wd_fw_update)

# Western Digital SSD Firmware Update Tool

This is a firmware update tool for Western Digital SSDs on Ubuntu / Linux Mint.
It provides a user-friendly interface to select the firmware version for the update process.

It uses the Western Digital API and the NVME toolbox `nvme-cli`.

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

pip install -r requirements.txt
pip install .
```

### Via pypi:
The newest release is published on pypi.
```bash
pip install wd-fw-update
```


## Usage

Follow the on-screen prompts to select the appropriate options for your firmware update.
The script will guide you through the process, and once completed, it will provide a summary of the update.
Depending on the update mode, it may prompt you to reboot or switch to the new slot.

## Command-Line Options

    --version: Display the version of the firmware update tool.
    -v, --verbose: Set the log level to INFO.
    -vv, --very-verbose: Set the log level to DEBUG.

<!-- pyscaffold-notes -->

## Note

This project has been set up using PyScaffold 4.5. For details and usage
information on PyScaffold see https://pyscaffold.org/.

## License
Copyright (C) 2024 by Jules Kreuer - @not_a_feature
This piece of software is published unter the GNU General Public License v3.0
TLDR:

 | Permissions      | Conditions                   | Limitations |
 | ---------------- | ---------------------------- | ----------- |
 | ✓ Commercial use | Disclose source              | ✕ Liability |
 | ✓ Distribution   | License and copyright notice | ✕ Warranty  |
 | ✓ Modification   | Same license                 |             |
 | ✓ Patent use     | State changes                |             |
 | ✓ Private use    |                              |             |

Go to [LICENSE.md](https://github.com/not-a-feature/wd_fw_update/blob/main/LICENSE) to see the full version.
