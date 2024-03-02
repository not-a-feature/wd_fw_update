import argparse
import logging
import sys

from wd_fw_update import __version__

__author__ = "Jules Kreuer"
__copyright__ = "Jules Kreuer"
__license__ = "GPL-3.0-or-later"

_logger = logging.getLogger(__name__)


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
    parser.add_argument(dest="n", help="n-th Fibonacci number", type=int, metavar="INT")
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


def setup_logging(loglevel):
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


def check_dependencies():
    return


def get_model():
    return


def get_fw_url():
    return


def download_fw():
    return


def update_fw():
    return


def wd_fw_update():
    """Updates the firmware of Western Digital SSDs on Ubuntu / Linux Mint."""

    # Step 0: Check dependencies

    # Step 1: Get model number and firmware version

    # Step 2: Fetch the device list and find the firmware URL

    # Step 3: Check firmware version dependencies

    # Step 4: Download firmware file

    # Step 5: Update the firmware


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
