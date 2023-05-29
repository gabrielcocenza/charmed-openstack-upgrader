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

"""Functions for backing up openstack database."""
import logging
import os

from cou.utils import model
from cou.utils.upgrade_utils import get_database_app


def backup():
    mysql_app = get_database_app()
    mysql_leader = model.get_unit_from_name(model.get_lead_unit_name(mysql_app))

    logging.info("mysqldump mysql-innodb-cluster DBs ...")
    action = model.run_action_on_leader(mysql_app, 'mysqldump')
    remote_file = action.data["results"]["mysqldump-file"]
    basedir = action.data["parameters"]["basedir"]

    logging.info("Set permissions to read mysql-innodb-cluster:{} ...".format(basedir))
    model.run_on_leader(mysql_app, "chmod o+rx {}".format(basedir))

    local_file = os.path.abspath(os.path.basename(remote_file))
    logging.info("SCP from  mysql-innodb-cluster:{} to {} ...".format(remote_file, local_file))
    model.scp_from_unit(mysql_leader.name, remote_file, local_file)

    logging.info("Remove permissions to read mysql-innodb-cluster:{} ...".format(basedir))
    model.run_on_leader(mysql_app, "chmod o-rx {}".format(basedir))
