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

"""Manage package and distribution."""
from setuptools import setup
import subprocess
from typing import List


def find_version() -> str:
    """Parse charmed-openstack-upgrader version based on the git tag."""
    try:
        cmd: List[str] = ["git", "describe", "--tags", "--always", "HEAD"]
        gitversion: str = subprocess.check_output(
            cmd, stderr=subprocess.DEVNULL
        ).decode().strip()
        if all(char.isdigit() or char == "." for char in gitversion):
            return gitversion
        else:
            build: List[str] = gitversion.split("-")
            return "{}.post{}".format(build[0], build[1])
    except IndexError:
        cmd: List[str] = ["git", "rev-list", "--count", "HEAD"]
        commits_count: str = subprocess.check_output(
            cmd, stderr=subprocess.DEVNULL
        ).decode().strip()
        return "0.0.dev{}".format(commits_count)
    except subprocess.CalledProcessError:
        return "0.0.dev0"


setup(version=find_version())