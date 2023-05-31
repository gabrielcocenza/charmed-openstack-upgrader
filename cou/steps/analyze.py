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

"""Functions for analyze openstack cloud before upgrade."""

import logging

from collections import defaultdict
from typing import Dict, DefaultDict

from cou.zaza_utils import model
from cou.zaza_utils.os_versions import SERVICE_GROUPS, CompareOpenStack, determine_next_openstack_release
from cou.zaza_utils.juju import get_full_juju_status, get_application_status
from cou.zaza_utils.upgrade_utils import extract_charm_name
from cou.zaza_utils.openstack import get_current_os_versions

def analyze() -> None:
    """Analyze the deployment before planning."""
    logging.info("Analyzing the Openstack release in the deployment...")
    os_versions = extract_os_versions()
    return check_os_versions(os_versions)

def extract_os_versions() -> Dict:
    """Extract OpenStack version on the deployment."""
    os_versions = {}
    status = get_full_juju_status().applications
    openstack_charms = set()
    for _, charms in SERVICE_GROUPS[2:]:
        for charm in charms:
            openstack_charms.add(charm)

    for app, app_status in status.items():
        charm = extract_charm_name(app_status.charm)
        if charm in openstack_charms:
            os_versions[app] = get_current_os_versions((app, charm))

    logging.debug(os_versions)
    return os_versions

def extract_app_channel(app:str) -> str:
    """Extract application channel by the juju status"""
    app_status = get_application_status(app)
    return app_status.get("charm-channel")

def extract_os_charm_config(app: str) -> str:
    app_config = model.get_application_config(app)
    for origin in ("openstack-origin", "source"):
        if app_config.get(origin):
            return app_config.get(origin).get("value")
    else:
        logging.warn("Failed to get origin for {}, no origin config found".format(app))
        return ""

def check_os_versions(os_versions:DefaultDict) -> None:
    """Check the consistency of OpenStack version on the deployment."""
    versions = defaultdict(set)
    os_app_channel = defaultdict(str)
    os_charm_config = defaultdict(str)
    upgrade_units = defaultdict(set)
    upgrade_charms = defaultdict(set)
    change_channel = defaultdict(set)
    change_openstack_release = defaultdict(set)
    for app, os_release_units in os_versions.items():
        os_app_channel[app] = extract_app_channel(app)
        os_charm_config[app] = extract_os_charm_config(app)
        os_version_units = set(os_release_units.keys())
        for os_version_unit in os_version_units:
            versions[os_version_unit].add(app)
        if len(os_version_units) > 1:
            logging.warning("Units are not in the same openstack version")
            os_sequence = sorted(list(os_version_units), key=lambda release: CompareOpenStack(release))
            for os_release in os_sequence[:-1]:
                next_release = determine_next_openstack_release(os_release)[1]
                upgrade_units[next_release].update(os_release_units[os_release])
                logging.warning(f"upgrade units: {os_release_units[os_release]} from: {os_release} to {next_release}")

    if len(versions) > 1:
        logging.warning("Charms are not in the same openstack version")
        os_sequence = sorted(versions.keys(), key=lambda release: CompareOpenStack(release))
        for os_release in os_sequence[:-1]:
            next_release = determine_next_openstack_release(os_release)[1]
            upgrade_charms[next_release].update(versions[os_release])
            logging.warning(f"upgrade charms: {versions[os_release]} from: {os_release} to {next_release}")

    else:
        actual_release = list(versions)[0]
        next_release = determine_next_openstack_release(actual_release)[1]
        logging.info(f"Charms are in the same openstack version and can be upgrade from: {actual_release} to: {next_release}")
        upgrade_charms[next_release].update(os_versions.keys())

        for app in os_app_channel:
            if actual_release not in os_app_channel[app]:
                change_channel[f"{actual_release}/stable"].add(app)
                logging.warning(f"App:{app} need to track the channel: {actual_release}/stable")

        for app in os_charm_config:
            expected_os_origin = f"cloud:focal-{actual_release}"
            # Exceptionally, if upgrading from Ussuri to Victoria
            if actual_release == "ussuri":
                if os_charm_config[app] != "distro":
                    logging.warning(f"App:{app} need to set openstack-origin or source to 'distro'")
                    change_openstack_release["distro"].add(app)

            else:
                if expected_os_origin not in os_charm_config:
                    change_openstack_release[expected_os_origin].add(app)
                    logging.warning(f"App:{app} need to set openstack-origin or source to {expected_os_origin}")

    return [upgrade_units, upgrade_charms, change_channel, change_openstack_release]

