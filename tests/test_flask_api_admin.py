# -*- coding: utf-8 -*-
#
# Copyright © 2014  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions
# of the GNU General Public License v.2, or (at your option) any later
# version.  This program is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY expressed or implied, including the
# implied warranties of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.  You
# should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Any Red Hat trademarks that are incorporated in the source
# code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission
# of Red Hat, Inc.
#

'''
pkgdb tests for the admin section of the Flask API.
'''

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import json
import unittest
import sys
import os

from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pkgdb2
from pkgdb2 import APP
from pkgdb2.lib import model
from tests import (Modeltests, FakeFasUser, FakeFasUserAdmin,
                   create_package_acl, user_set)


class FlaskApiAdminTest(Modeltests):
    """ Flask API admin tests. """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(FlaskApiAdminTest, self).setUp()

        pkgdb2.APP.config['TESTING'] = True
        pkgdb2.SESSION = self.session
        pkgdb2.api.admin.SESSION = self.session
        self.app = pkgdb2.APP.test_client()

    def test_admin_actions(self):
        """ Test the api_admin_actions function.  """

        output = self.app.get('/api/admin/actions/')
        data = json.loads(output.data)
        self.assertEqual(data['actions'], [])
        self.assertEqual(data['page'], 1)
        self.assertEqual(data['page_total'], 1)
        self.assertEqual(data['output'], 'notok')
        self.assertEqual(
            data['error'], 'No actions found for these parameters')

        output = self.app.get('/api/admin/actions/?page=abc&limit=abcd')
        data = json.loads(output.data)
        self.assertEqual(data['actions'], [])
        self.assertEqual(data['page'], 1)
        self.assertEqual(data['page_total'], 1)
        self.assertEqual(data['output'], 'notok')
        self.assertEqual(
            data['error'], 'No actions found for these parameters')


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(FlaskApiAdminTest)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
