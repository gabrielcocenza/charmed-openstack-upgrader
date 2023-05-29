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

import cou.utils.juju as jujuutils
import logging
import os

from cou.steps.backup import backup
from cou.utils.upgrade_utils import get_database_app, backup_mysql
import cou.utils.model as model

from cou.utils import clean_up_libjuju_thread


def parse_args() -> argparse.Namespace:
    """Parse cli arguments."""
    parser = argparse.ArgumentParser(
        description="description", formatter_class=argparse.RawDescriptionHelpFormatter
    )
    return parser.parse_args()


def setup_logging(log_level='INFO'):
    """Do setup for logging.

    :returns: Nothing: This function is executed for its sideffect
    :rtype: None
    """
    level = getattr(logging, log_level.upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid log level: "{}"'.format(log_level))
    logFormatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S")
    rootLogger = logging.getLogger()
    rootLogger.setLevel(level)
    if not rootLogger.hasHandlers():
        consoleHandler = logging.StreamHandler()
        consoleHandler.setFormatter(logFormatter)
        rootLogger.addHandler(consoleHandler)


def entrypoint() -> None:
    """Execute 'charmed-openstack-upgrade' command."""
    try:
        args = parse_args()
        setup_logging(log_level='DEBUG')

        backup()

        clean_up_libjuju_thread()
    except Exception as exc:
        logging.error(exc)
        sys.exit(1)


entrypoint()
