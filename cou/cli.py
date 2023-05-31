# Copyright 2023 Canonical Limited.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Entrypoint to the 'canonical-openstack-upgrader'"""
import argparse
import logging
import sys

from cou.steps import UpgradeStep
from cou.steps.backup import backup
from cou.steps.plan import plan
from cou.utils import clean_up_libjuju_thread


def parse_args() -> argparse.Namespace:
    """Parse cli arguments."""
    parser = argparse.ArgumentParser(
        description="description", formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--dry-run",
                        default=False,
                        help="Do not run the upgrade just print out the steps.",
                        action="store_true")
    parser.add_argument("--log-level",
                        default="INFO",
                        dest="loglevel",
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help="Set the logging level")
    parser.add_argument("--interactive",
                        default=True,
                        help="Sets the interactive prompts",
                        action="store_true")

    return parser.parse_args()


def setup_logging(log_level='INFO'):
    """Do setup for logging.

    :returns: Nothing: This function is executed for its side effect
    :rtype: None
    """
    level = getattr(logging, log_level.upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid log level: "{}"'.format(log_level))
    log_formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S")
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    if not root_logger.hasHandlers():
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        root_logger.addHandler(console_handler)


def apply_plan(upgrade_plan):
    result = input(upgrade_plan.description + "[Continue/abort/skip]")
    match result:
        case "C" | "c":
            if upgrade_plan.function is not None:
                upgrade_plan.function(upgrade_plan.params) if upgrade_plan.params \
                    else upgrade_plan.function()
        case "A" | "a":
            sys.exit(1)
        case "S" | "s":
            pass
    for sub_step in upgrade_plan.sub_steps:
        apply_plan(sub_step)

def dump_plan(upgrade_plan: UpgradeStep, ident:int=0):
    tab = '\t'
    print(f"{tab*ident}{upgrade_plan.description}")
    for sub_step in upgrade_plan.sub_steps:
        dump_plan(sub_step, ident+1)


def entrypoint() -> None:
    """Execute 'charmed-openstack-upgrade' command."""
    try:
        args = parse_args()
        setup_logging(log_level=args.loglevel)

        upgrade_plan = plan(args)
        if args.dry_run:
            dump_plan(upgrade_plan)
        else:
            apply_plan(upgrade_plan)


        clean_up_libjuju_thread()
    except Exception as exc:
        logging.error(exc)
        sys.exit(1)
