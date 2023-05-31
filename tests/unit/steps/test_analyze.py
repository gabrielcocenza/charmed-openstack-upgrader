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

import mock

from collections import defaultdict

from cou.steps import analyze
from cou.zaza_utils import clean_up_libjuju_thread
from cou.zaza_utils import generic as generic_utils
from cou.zaza_utils import juju as juju_utils

import tests.unit.utils as ut_utils

FAKE_STATUS = {
    "can-upgrade-to": "",
    "charm": "keystone",
    "subordinate-to": [],
    "charm-channel": "ussuri/stable",
    "units": {
        "keystone/0": {
            "leader": True,
            "machine": "0",
            "subordinates": {
                "app-hacluster/0": {"charm": "local:trusty/hacluster-0", "leader": True}
            },
        },
        "keystone/1": {
            "machine": "1",
            "subordinates": {"app-hacluster/1": {"charm": "local:trusty/hacluster-0"}},
        },
        "keystone/2": {
            "machine": "2",
            "subordinates": {"app-hacluster/2": {"charm": "local:trusty/hacluster-0"}},
        },
    },
}

FAKE_FULL_STATUS = {
    "keystone": {
        "charm": "keystone",
        "series": "focal",
        "os": "ubuntu",
        "charm-origin": "charmhub",
        "charm-name": "keystone",
        "charm-rev": 698,
        "charm-channel": "ussuri/stable",
        "units": FAKE_STATUS["units"],
    }
}

FAKE_CONFIG = {}


def tearDownModule():
    clean_up_libjuju_thread()


class TestAnalyze(ut_utils.BaseTestCase):
    def setUp(self):
        super(TestAnalyze, self).setUp()
        # Patch all subprocess calls
        self.patch(
            "cou.zaza_utils.generic.subprocess", new_callable=mock.MagicMock(), name="subprocess"
        )

        # Juju Status Object and data
        self.juju_status = mock.MagicMock()
        self.juju_status.applications.__getitem__.return_value = FAKE_STATUS
        self.patch_object(analyze, "model")
        self.model.get_status.return_value = self.juju_status

    def test_extract_app_channel(self):
        self.patch_object(analyze, "get_application_status", return_value=FAKE_STATUS)
        result = analyze.extract_app_channel("keystone")
        self.assertEqual(result, "ussuri/stable")

    def test_check_os_versions(self):
        # scenario where everything is ok
        os_release_units_keystone = defaultdict(set)
        os_release_units_cinder = defaultdict(set)
        os_release_units_keystone["ussuri"].update({"keystone/0", "keystone/1", "keystone/2"})
        os_release_units_cinder["ussuri"].update({"cinder/0"})
        os_versions = {"keystone": os_release_units_keystone, "cinder": os_release_units_cinder}
        self.patch_object(analyze, "extract_app_channel", return_value="ussuri/stable")
        self.patch_object(analyze, "extract_os_charm_config", return_value="distro")
        results = analyze.check_os_versions(os_versions)
        expected_result = defaultdict(set)
        expected_result["victoria"].update({"keystone", "cinder"})
        upgrade_charms = results[1]
        self.assertEqual(upgrade_charms, expected_result)

        # scenario where it needs to upgrade units
        os_release_units = defaultdict(set)
        os_release_units["ussuri"].update({"keystone/1", "keystone/2"})
        os_release_units["victoria"].update({"keystone/0"})
        os_versions = {"keystone": os_release_units}
        results = analyze.check_os_versions(os_versions)
        expected_result = defaultdict(set)
        expected_result["victoria"].update({"keystone/1", "keystone/2"})
        upgrade_units, *_ = results
        self.assertEqual(upgrade_units, expected_result)

        # scenario where it needs to upgrade charms
        os_release_units_keystone = defaultdict(set)
        os_release_units_keystone["victoria"].update({"keystone/0"})
        os_release_units_cinder = defaultdict(set)
        os_release_units_cinder["ussuri"].update({"cinder/0"})
        os_versions = {"keystone": os_release_units_keystone, "cinder": os_release_units_cinder}
        expected_result = defaultdict(set)
        expected_result["victoria"].update({"cinder"})
        results = analyze.check_os_versions(os_versions)
        _, upgrade_charms, *_ = results
        self.assertEqual(expected_result, upgrade_charms)

        # scenario where it needs to change charm channel
        os_release_units = defaultdict(set)
        os_release_units["victoria"].update({"keystone/0"})
        os_versions = {"keystone": os_release_units}
        self.patch_object(analyze, "extract_app_channel", return_value="ussuri/stable")
        results = analyze.check_os_versions(os_versions)
        expected_result = defaultdict(set)
        change_channel = results[2]
        expected_result = defaultdict(set)
        expected_result["victoria/stable"].update({"keystone"})
        self.assertEqual(change_channel, expected_result)

        # scenario where it needs to change openstack release config
        os_release_units = defaultdict(set)
        os_release_units["victoria"].update({"keystone/0"})
        os_versions = {"keystone": os_release_units}
        self.patch_object(analyze, "extract_app_channel", return_value="ussuri/stable")
        self.patch_object(analyze, "extract_os_charm_config", return_value="distro")
        results = analyze.check_os_versions(os_versions)
        expected_result = defaultdict(set)
        *_, change_openstack_release = results
        expected_result = defaultdict(set)
        expected_result["cloud:focal-victoria"].update({"keystone"})
        self.assertEqual(change_openstack_release, expected_result)

        # scenario where 'distro' is not set to ussuri
        os_release_units = defaultdict(set)
        os_release_units["ussuri"].update({"keystone/0"})
        os_versions = {"keystone": os_release_units}
        self.patch_object(analyze, "extract_app_channel", return_value="ussuri/stable")
        self.patch_object(analyze, "extract_os_charm_config", return_value="cloud:focal-ussuri")
        results = analyze.check_os_versions(os_versions)
        *_, change_openstack_release = results
        expected_result = defaultdict(set)
        expected_result["distro"].update({"keystone"})
        self.assertEqual(change_openstack_release, expected_result)
