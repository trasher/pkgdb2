# -*- coding: utf-8 -*-
#
# Copyright © 2013-2014  Red Hat, Inc.
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
pkgdb tests for the Flask API regarding collections.
'''

__requires__ = ['SQLAlchemy >= 0.7']
import pkg_resources

import json
import unittest
import sys
import os

from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pkgdb2
from pkgdb2 import lib as pkgdblib
from pkgdb2.lib import model
from tests import (Modeltests, FakeFasUser, FakeFasUserAdmin,
                   create_collection, create_package, create_package_acl,
                   create_package_critpath, user_set)


class FlaskApiPackagesTest(Modeltests):
    """ Flask API Packages tests. """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(FlaskApiPackagesTest, self).setUp()

        pkgdb2.APP.config['TESTING'] = True
        pkgdb2.SESSION = self.session
        pkgdb2.api.packages.SESSION = self.session
        self.app = pkgdb2.APP.test_client()

    @patch('pkgdb2.lib.utils')
    @patch('pkgdb2.is_admin')
    def test_api_package_new(self, login_func, mock_func):
        """ Test the api_package_new function.  """
        login_func.return_value = None

        # Redirect as you are not admin
        user = FakeFasUser()

        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/new/')
            self.assertEqual(output.status_code, 302)

        user = FakeFasUserAdmin()

        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/new/')
            self.assertEqual(output.status_code, 500)
            data = json.loads(output.data)
            self.assertEqual(
                sorted(data),
                ['error', 'error_detail', 'output']
            )
            self.assertEqual(
                data['error'], "Invalid input submitted")

            self.assertEqual(
                data['output'], "notok")

            self.assertEqual(
                sorted(data['error_detail']),
                [
                    "branches: This field is required.",
                    "pkgname: This field is required.",
                    "poc: This field is required.",
                    "review_url: This field is required.",
                    "status: Not a valid choice",
                    "summary: This field is required.",
                ]
            )

        data = {
            'pkgname': 'gnome-terminal',
            'summary': 'Terminal emulator for GNOME',
            'description': 'Terminal for GNOME...',
            'review_url': 'http://bugzilla.redhat.com/1234',
            'status': '',
            'critpath': '',
            'branches': '',
            'poc': '',
            'upstream_url': '',
        }
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/new/', data=data)
            self.assertEqual(output.status_code, 500)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "error": "Invalid input submitted",
                    "error_detail": [
                        "status: This field is required.",
                        "branches: '' is not a valid choice for this field",
                        "poc: This field is required.",
                    ],
                    "output": "notok"
                }
            )

        data = {
            'pkgname': 'gnome-terminal',
            'summary': 'Terminal emulator for GNOME',
            'description': 'Terminal for GNOME...',
            'review_url': 'http://bugzilla.redhat.com/1234',
            'status': 'Approved',
            'branches': 'master',
            'poc': 'mclasen',
            'upstream_url': 'http://www.gnome.org/',
            'critpath': False,
        }
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/new/', data=data)
            self.assertEqual(output.status_code, 500)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "error": "Invalid input submitted",
                    "error_detail": [
                        "branches: 'master' is not a valid choice for this "
                        "field"
                    ],
                    "output": "notok"
                }

            )

        create_collection(self.session)

        data = {
            'pkgname': 'gnome-terminal',
            'summary': 'Terminal emulator for GNOME',
            'description': 'Terminal for GNOME...',
            'review_url': 'http://bugzilla.redhat.com/1234',
            'status': 'Approved',
            'branches': 'master',
            'poc': 'mclasen',
            'upstream_url': 'http://www.gnome.org/',
            'critpath': False,
        }
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/new/', data=data)
            self.assertEqual(output.status_code, 500)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "error": "User \"mclasen\" is not in the packager group",
                    "output": "notok"
                }
            )

        mock_func.get_packagers.return_value = ['mclasen']
        mock_func.log.return_value = ''

        data = {
            'pkgname': 'gnome-terminal',
            'summary': 'Terminal emulator for GNOME',
            'description': 'Terminal for GNOME...',
            'review_url': 'http://bugzilla.redhat.com/1234',
            'status': 'Approved',
            'branches': 'master',
            'poc': 'mclasen',
            'upstream_url': 'http://www.gnome.org/',
            'critpath': False,
        }
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/new/', data=data)
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "messages": [
                        "Package created"
                    ],
                    "output": "ok"
                }
            )

    @patch('pkgdb2.lib.utils')
    @patch('pkgdb2.packager_login_required')
    def test_api_package_orphan(self, login_func, mock_func):
        """ Test the api_package_orphan function.  """
        login_func.return_value = None

        # Redirect as you are not a packager
        user = FakeFasUser()
        user.groups = []

        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/orphan/')
            self.assertEqual(output.status_code, 302)

        user = FakeFasUser()
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/orphan/')
            self.assertEqual(output.status_code, 500)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "error": "Invalid input submitted",
                    "error_detail": [
                        "pkgnames: This field is required.",
                        "branches: This field is required.",
                    ],
                    "output": "notok"
                }
            )

        data = {
            'pkgnames': 'guake',
            'branches': ['f18', 'master'],
            'poc': 'test',
        }
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/orphan/', data=data)
            self.assertEqual(output.status_code, 500)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "error": "No package found by this name",
                    "output": "notok"
                }
            )

        create_package_acl(self.session)
        mock_func.log.return_value = ''

        data = {
            'pkgnames': 'guake',
            'branches': ['el4', 'f18'],
            'poc': 'test',
        }
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/orphan/', data=data)
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    'error': 'The package guake could not be found in the '
                    'collection el4.',
                    'messages': [''],
                    'output': 'ok'
                }
            )
            pkg_acl = pkgdblib.get_acl_package(self.session, 'guake')
            self.assertEqual(pkg_acl[0].collection.branchname, 'f18')
            self.assertEqual(pkg_acl[0].package.name, 'guake')
            self.assertEqual(pkg_acl[0].point_of_contact, 'orphan')
            self.assertEqual(pkg_acl[0].status, 'Orphaned')

            self.assertEqual(pkg_acl[1].collection.branchname, 'master')
            self.assertEqual(pkg_acl[1].package.name, 'guake')
            self.assertEqual(pkg_acl[1].point_of_contact, 'pingou')

        data = {
            'pkgnames': 'guake',
            'branches': ['f18', 'master'],
            'poc': 'test',
        }
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/orphan/', data=data)
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "messages": ["", ""],
                    "output": "ok"
                }
            )
            pkg_acl = pkgdblib.get_acl_package(self.session, 'guake')
            self.assertEqual(pkg_acl[0].collection.branchname, 'f18')
            self.assertEqual(pkg_acl[0].package.name, 'guake')
            self.assertEqual(pkg_acl[0].point_of_contact, 'orphan')
            self.assertEqual(pkg_acl[0].status, 'Orphaned')

            self.assertEqual(pkg_acl[1].collection.branchname, 'master')
            self.assertEqual(pkg_acl[1].package.name, 'guake')
            self.assertEqual(pkg_acl[1].point_of_contact, 'orphan')
            self.assertEqual(pkg_acl[1].status, 'Orphaned')

    @patch('pkgdb2.lib.utils')
    @patch('pkgdb2.packager_login_required')
    def test_api_package_unorphan(self, login_func, mock_func):
        """ Test the api_package_unorphan function.  """
        login_func.return_value = None

        # Redirect as you are not a packager
        user = FakeFasUser()
        user.groups = []

        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/unorphan/')
            self.assertEqual(output.status_code, 302)

        user = FakeFasUser()
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/unorphan/')
            self.assertEqual(output.status_code, 500)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "error": "Invalid input submitted",
                    "error_detail": [
                        "pkgnames: This field is required.",
                        "branches: This field is required.",
                        "poc: This field is required.",
                    ],
                    "output": "notok"
                }
            )

        mock_func.get_packagers.return_value = ['test']

        data = {
            'pkgnames': 'guake',
            'branches': ['f18', 'master'],
            'poc': 'test',
        }
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/unorphan/', data=data)
            self.assertEqual(output.status_code, 500)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "error": "No package found by this name",
                    "output": "notok"
                }
            )

        create_package_acl(self.session)
        mock_func.log.return_value = ''

        # Unorphan a not-orphaned package
        data = {
            'pkgnames': 'guake',
            'branches': ['f18', 'master'],
            'poc': 'test',
        }
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/unorphan/', data=data)
            self.assertEqual(output.status_code, 500)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "error": [
                        'Package "guake" is not orphaned on f18',
                        'Package "guake" is not orphaned on master',
                    ],
                    "output": "notok"
                }
            )

        # Orphan the package
        data = {
            'pkgnames': 'guake',
            'branches': ['f18', 'master'],
            'poc': 'test',
        }
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/orphan/', data=data)
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "messages": ["", ""],
                    "output": "ok"
                }
            )
            pkg_acl = pkgdblib.get_acl_package(self.session, 'guake')
            self.assertEqual(pkg_acl[0].collection.branchname, 'f18')
            self.assertEqual(pkg_acl[0].package.name, 'guake')
            self.assertEqual(pkg_acl[0].point_of_contact, 'orphan')
            self.assertEqual(pkg_acl[0].status, 'Orphaned')

            self.assertEqual(pkg_acl[1].collection.branchname, 'master')
            self.assertEqual(pkg_acl[1].package.name, 'guake')
            self.assertEqual(pkg_acl[1].point_of_contact, 'orphan')
            self.assertEqual(pkg_acl[1].status, 'Orphaned')

        # Unorphan the package for someone else
        data = {
            'pkgnames': 'guake',
            'branches': ['f18', 'master'],
            'poc': 'test',
        }
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/unorphan/', data=data)
            self.assertEqual(output.status_code, 500)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "error": "You are not allowed to update ACLs of someone "
                    "else.",
                    "output": "notok"
                }
            )

        mock_func.get_packagers.return_value = ['pingou']

        # Unorphan the package on a branch where it is not
        data = {
            'pkgnames': 'guake',
            'branches': ['el4', 'f18'],
            'poc': 'pingou',
        }
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/unorphan/', data=data)
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    'error':
                    'Package "guake" is not in the collection el4',
                    "messages": [
                        "Package guake has been unorphaned on f18 by pingou"
                    ],
                    'output': 'ok'
                }
            )

            pkg_acl = pkgdblib.get_acl_package(self.session, 'guake')
            self.assertEqual(pkg_acl[0].collection.branchname, 'f18')
            self.assertEqual(pkg_acl[0].package.name, 'guake')
            self.assertEqual(pkg_acl[0].point_of_contact, 'pingou')
            self.assertEqual(pkg_acl[0].status, 'Approved')

            self.assertEqual(pkg_acl[1].collection.branchname, 'master')
            self.assertEqual(pkg_acl[1].package.name, 'guake')
            self.assertEqual(pkg_acl[1].point_of_contact, 'orphan')
            self.assertEqual(pkg_acl[1].status, 'Orphaned')

        # Unorphan the package
        data = {
            'pkgnames': 'guake',
            'branches': ['f18', 'master'],
            'poc': 'pingou',
        }
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/unorphan/', data=data)
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "error": 'Package "guake" is not orphaned on f18',
                    "messages": [
                        "Package guake has been unorphaned on master by pingou"
                    ],
                    "output": "ok"
                }
            )

            pkg_acl = pkgdblib.get_acl_package(self.session, 'guake')
            self.assertEqual(pkg_acl[0].collection.branchname, 'f18')
            self.assertEqual(pkg_acl[0].package.name, 'guake')
            self.assertEqual(pkg_acl[0].point_of_contact, 'pingou')
            self.assertEqual(pkg_acl[0].status, 'Approved')

            self.assertEqual(pkg_acl[1].collection.branchname, 'master')
            self.assertEqual(pkg_acl[1].package.name, 'guake')
            self.assertEqual(pkg_acl[1].point_of_contact, 'pingou')
            self.assertEqual(pkg_acl[1].status, 'Approved')

    @patch('pkgdb2.lib.utils')
    @patch('pkgdb2.packager_login_required')
    def test_api_package_retire(self, login_func, mock_func):
        """ Test the api_package_retire function.  """
        login_func.return_value = None

        # Redirect as you are not a packager
        user = FakeFasUser()
        user.groups = []

        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/retire/')
            self.assertEqual(output.status_code, 302)

        user = FakeFasUser()
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/retire/')
            self.assertEqual(output.status_code, 500)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "error": "Invalid input submitted",
                    "error_detail": [
                        "pkgnames: This field is required.",
                        "branches: This field is required.",
                    ],
                    "output": "notok"
                }
            )

        data = {
            'pkgnames': 'guake',
            'branches': ['f18', 'master'],
            'poc': 'test',
        }
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/retire/', data=data)
            self.assertEqual(output.status_code, 500)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "error": "No package found by this name",
                    "output": "notok"
                }
            )

        create_package_acl(self.session)
        mock_func.log.return_value = ''

        data = {
            'pkgnames': 'guake',
            'branches': ['f18', 'master'],
            'poc': 'test',
        }
        # User is not an admin
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/retire/', data=data)
            self.assertEqual(output.status_code, 500)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "error": "You are not allowed to retire the package: "
                    "guake on branch f18.",
                    "output": "notok"
                }
            )

        data = {
            'pkgnames': 'guake',
            'branches': ['master'],
            'poc': 'test',
        }
        # User is not the poc
        user.username = 'toshio'
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/retire/', data=data)
            self.assertEqual(output.status_code, 500)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "error": "You are not allowed to retire this package.",
                    "output": "notok"
                }
            )

        # Retire the package on a non-existant branch
        user = FakeFasUser()
        data = {
            'pkgnames': 'guake',
            'branches': ['el6'],
        }
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/retire/', data=data)
            self.assertEqual(output.status_code, 500)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "error": "No package guake found in collection el6",
                    "output": "notok"
                }
            )

        # Retire the package
        user = FakeFasUserAdmin()
        data = {
            'pkgnames': 'guake',
            'branches': ['f18', 'master'],
        }
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/retire/', data=data)
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "messages": ["", ""],
                    "output": "ok"
                }
            )

    @patch('pkgdb2.lib.utils')
    @patch('pkgdb2.packager_login_required')
    def test_api_package_retire2(self, login_func, mock_func):
        """ Test a second time the api_package_retire function.  """
        login_func.return_value = None
        create_package_acl(self.session)
        mock_func.log.return_value = ''

        # Redirect as you are not a packager
        user = FakeFasUser()
        user.groups = []

        # Add the EPEL 7 collection
        collection = model.Collection(
            name='Fedora EPEL',
            version='7',
            status='Active',
            owner='kevin',
            branchname='epel7',
            dist_tag='.el7',
        )
        self.session.add(collection)
        self.session.commit()

        # Add guake to epel7
        guake_pkg = model.Package.by_name(self.session, 'guake')
        el7_collec = model.Collection.by_name(self.session, 'epel7')

        pkgltg = model.PackageListing(
            point_of_contact='pingou',
            status='Approved',
            package_id=guake_pkg.id,
            collection_id=el7_collec.id,
        )
        self.session.add(pkgltg)
        self.session.commit()

        # Retire the package on an EPEL branch
        user = FakeFasUser()
        data = {
            'pkgnames': 'guake',
            'branches': ['master', 'epel7'],
        }
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/retire/', data=data)
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "messages": ["", ""],
                    "output": "ok"
                }
            )

    @patch('pkgdb2.lib.utils')
    @patch('pkgdb2.packager_login_required')
    def test_api_package_retire3(self, login_func, mock_func):
        """ Test a third time the api_package_retire function.  """
        login_func.return_value = None
        create_package_acl(self.session)
        mock_func.log.return_value = ''

        # Redirect as you are not a packager
        user = FakeFasUser()
        user.groups = []

        # Add the EPEL 7 collection
        collection = model.Collection(
            name='Fedora EPEL',
            version='7',
            status='Active',
            owner='kevin',
            branchname='epel7',
            dist_tag='.el7',
        )
        self.session.add(collection)
        self.session.commit()

        # Add guake to epel7
        guake_pkg = model.Package.by_name(self.session, 'guake')
        el7_collec = model.Collection.by_name(self.session, 'epel7')

        pkgltg = model.PackageListing(
            point_of_contact='orphan',
            status='Orphaned',
            package_id=guake_pkg.id,
            collection_id=el7_collec.id,
        )
        self.session.add(pkgltg)
        self.session.commit()

        # Retire an orphaned package on an EPEL branch
        user = FakeFasUser()
        data = {
            'pkgnames': 'guake',
            'branches': ['epel7'],
        }
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/retire/', data=data)
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "messages": [""],
                    "output": "ok"
                }
            )

    @patch('pkgdb2.lib.utils')
    @patch('pkgdb2.packager_login_required')
    def test_api_package_unretire(self, login_func, mock_func):
        """ Test the api_package_unretire function.  """
        login_func.return_value = None

        # Redirect as you are not a packager
        user = FakeFasUser()
        user.groups = []

        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/unretire/')
            self.assertEqual(output.status_code, 302)

        user = FakeFasUser()
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/unretire/')
            self.assertEqual(output.status_code, 500)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "error": "Invalid input submitted",
                    "error_detail": [
                        "pkgnames: This field is required.",
                        "branches: This field is required.",
                    ],
                    "output": "notok"
                }
            )

        data = {
            'pkgnames': 'guake',
            'branches': ['f18', 'master'],
            'poc': 'test',
        }
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/unretire/', data=data)
            self.assertEqual(output.status_code, 500)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "error": "No package found by this name",
                    "output": "notok"
                }
            )

        create_package_acl(self.session)
        mock_func.log.return_value = ''

        # User is not an admin
        data = {
            'pkgnames': 'guake',
            'branches': ['f18', 'master'],
        }
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/unretire/', data=data)
            self.assertEqual(output.status_code, 500)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "error": "You are not allowed to update the status of "
                             "the package: guake on branch f18 to "
                             "Approved.",
                    "output": "notok"
                }
            )

        # Unretire the package
        user = FakeFasUserAdmin()
        data = {
            'pkgnames': 'guake',
            'branches': ['f18', 'master'],
        }
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/unretire/', data=data)
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "messages": ["", ""],
                    "output": "ok"
                }
            )

    def test_api_package_info(self):
        """ Test the api_package_info function.  """

        output = self.app.get('/api/package/guake/')
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertEqual(
            data,
            {
                "error": "Package: guake not found",
                "output": "notok"
            }
        )

        create_package_acl(self.session)

        output = self.app.get('/api/package/guake/')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertEqual(data.keys(), ['output', 'packages'])
        self.assertEqual(len(data['packages']), 2)
        self.assertEqual(data['output'], 'ok')
        self.assertEqual(data['packages'][0]['collection']['branchname'],
                         'f18')
        self.assertEqual(data['packages'][0]['point_of_contact'],
                         'pingou')
        self.assertEqual(data['packages'][0]['package']['name'],
                         'guake')
        self.assertEqual(data['packages'][1]['collection']['branchname'],
                         'master')
        self.assertEqual(data['packages'][1]['point_of_contact'],
                         'pingou')
        self.assertEqual(data['packages'][1]['package']['name'],
                         'guake')

        output = self.app.get('/api/package/?pkgname=guake&branches=master')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertEqual(data.keys(), ['output', 'packages'])
        self.assertEqual(len(data['packages']), 1)
        self.assertEqual(data['output'], 'ok')
        self.assertEqual(
            set(data['packages'][0].keys()),
            set(['status', 'point_of_contact', 'package', 'collection',
                 'acls', 'status_change', 'critpath']))
        self.assertEqual(
            [acl['fas_name'] for acl in data['packages'][0]['acls']],
            ['pingou', 'pingou', 'pingou', 'toshio', 'ralph',
             'group::provenpackager'])
        self.assertEqual(data['packages'][0]['collection']['branchname'],
                         'master')
        self.assertEqual(data['packages'][0]['point_of_contact'],
                         'pingou')
        self.assertEqual(data['packages'][0]['package']['name'],
                         'guake')

        output = self.app.get(
            '/api/package/?pkgname=guake&branches=master&acls=0')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertEqual(data.keys(), ['output', 'packages'])
        self.assertEqual(len(data['packages']), 1)
        self.assertEqual(data['output'], 'ok')
        self.assertEqual(
            set(data['packages'][0].keys()),
            set(['status', 'point_of_contact', 'package', 'collection',
                 'status_change', 'critpath']))
        self.assertEqual(data['packages'][0]['collection']['branchname'],
                         'master')
        self.assertEqual(data['packages'][0]['point_of_contact'],
                         'pingou')
        self.assertEqual(data['packages'][0]['package']['name'],
                         'guake')

        output = self.app.get('/api/package/?pkgname=guake&branches=f19')
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertEqual(
            data,
            {
                "error": "No package found on these branches: f19",
                "output": "notok"
            }
        )

    def test_api_package_list(self):
        """ Test the api_package_list function.  """

        output = self.app.get('/api/packages/guake/')
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertEqual(
            data,
            {
                "error": "No packages found for these parameters",
                "packages": [],
                "output": "notok",
                "page_total": 1,
                "page": 1,
            }
        )

        create_package_acl(self.session)
        create_package_critpath(self.session)

        output = self.app.get('/api/packages/guake/')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertEqual(
            sorted(data.keys()),
            ['output', 'packages', 'page', 'page_total'])
        self.assertEqual(len(data['packages']), 1)
        self.assertEqual(data['output'], 'ok')
        self.assertEqual(
            data['packages'][0]['name'], 'guake')
        self.assertEqual(
            data['packages'][0]['status'], 'Approved')
        self.assertEqual(
            data['packages'][0]['summary'], 'Top down terminal for GNOME')

        output = self.app.get('/api/packages/g*/')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertEqual(len(data['packages']), 2)

        output = self.app.get('/api/packages/g*/?count=True')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertEqual(
            data,
            {
                "output": "ok",
                "packages": 2,
                "page": 1,
                "page_total": 1,
            }
        )

        output = self.app.get('/api/packages/g*/?limit=abc')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertEqual(
            sorted(data.keys()),
            ['output', 'packages', 'page', 'page_total'])
        self.assertEqual(len(data['packages']), 2)
        self.assertEqual(data['output'], 'ok')
        self.assertEqual(
            data['packages'][0]['name'], 'geany')
        self.assertEqual(
            data['packages'][0]['status'], 'Approved')
        self.assertEqual(
            data['packages'][1]['name'], 'guake')
        self.assertEqual(
            data['packages'][1]['status'], 'Approved')

        output = self.app.get('/api/packages/g*/?limit=5000')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertEqual(
            sorted(data.keys()),
            ['output', 'packages', 'page', 'page_total'])
        self.assertEqual(len(data['packages']), 2)
        self.assertEqual(data['output'], 'ok')
        self.assertEqual(
            data['packages'][0]['name'], 'geany')
        self.assertEqual(
            data['packages'][0]['status'], 'Approved')
        self.assertEqual(
            data['packages'][1]['name'], 'guake')
        self.assertEqual(
            data['packages'][1]['status'], 'Approved')

        output = self.app.get('/api/packages/g*/?critpath=1')
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertEqual(
            sorted(data.keys()),
            ['error', 'output', 'packages', 'page', 'page_total'])
        self.assertEqual(len(data['packages']), 0)
        self.assertEqual(data['output'], 'notok')

        output = self.app.get('/api/packages/k*/?critpath=1')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertEqual(
            sorted(data.keys()),
            ['output', 'packages', 'page', 'page_total'])
        self.assertEqual(len(data['packages']), 1)
        self.assertEqual(data['packages'][0]['name'], 'kernel')
        self.assertEqual(data['output'], 'ok')

        output = self.app.get('/api/packages/g*/?critpath=0')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertEqual(
            sorted(data.keys()),
            ['output', 'packages', 'page', 'page_total'])
        self.assertEqual(len(data['packages']), 2)
        self.assertEqual(data['output'], 'ok')

        output = self.app.get('/api/packages/g*/?page=abc')
        self.assertEqual(output.status_code, 500)
        data = json.loads(output.data)
        self.assertEqual(
            sorted(data.keys()),
            ['error', 'output', 'page', 'page_total'])
        self.assertEqual(data['error'], 'Wrong page provided')
        self.assertEqual(data['output'], 'notok')

        output = self.app.get('/api/packages/g*/?orphaned=False')
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertEqual(
            sorted(data.keys()),
            ['output', 'packages', 'page', 'page_total'])
        self.assertEqual(data['output'], 'ok')
        self.assertEqual(len(data['packages']), 2)
        self.assertEqual(data['packages'][0]['name'], 'geany')
        self.assertEqual(data['packages'][1]['name'], 'guake')

        output = self.app.get('/api/packages/g*/?orphaned=True')
        self.assertEqual(output.status_code, 404)
        data = json.loads(output.data)
        self.assertEqual(
            sorted(data.keys()),
            ['error', 'output', 'packages', 'page', 'page_total'])
        self.assertEqual(
            data['error'], 'No packages found for these parameters')
        self.assertEqual(data['output'], 'notok')
        self.assertEqual(data['packages'], [])

    @patch('pkgdb2.lib.utils')
    @patch('pkgdb2.is_admin')
    def test_api_package_edit(self, login_func, mock_func):
        """ Test the api_package_edit function.  """
        login_func.return_value = None

        # Redirect as you are not admin
        user = FakeFasUser()

        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/edit/')
            self.assertEqual(output.status_code, 302)

        user = FakeFasUserAdmin()

        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/edit/')
            self.assertEqual(output.status_code, 500)
            data = json.loads(output.data)
            self.assertEqual(
                sorted(data),
                ['error', 'error_detail', 'output']
            )
            self.assertEqual(
                data['error'], "Invalid input submitted")

            self.assertEqual(
                data['output'], "notok")

            self.assertEqual(
                sorted(data['error_detail']),
                [
                    "pkgname: This field is required.",
                ]
            )

        data = {
            'pkgname': 'gnome-terminal',
            'summary': 'Terminal emulator for GNOME',
            'description': 'Terminal for GNOME...',
            'review_url': 'http://bugzilla.redhat.com/1234',
            'status': 'Approved',
            'upstream_url': 'http://www.gnome.org/',
        }
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/edit/', data=data)
            self.assertEqual(output.status_code, 500)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "error": "No package of this name found",
                    "output": "notok"
                }
            )

        create_package_acl(self.session)
        create_package_critpath(self.session)

        # Before edit:
        output = self.app.get('/api/package/guake/', data=data)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertEqual(
            data['packages'][0]['package']['upstream_url'],
            'http://guake.org'
        )

        data = {
            'pkgname': 'guake',
            'upstream_url': 'http://www.guake.org',
        }

        # User is not an admin
        user = FakeFasUser()
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/edit/', data=data)
            self.assertEqual(output.status_code, 302)

        # User is an admin
        user = FakeFasUserAdmin()
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/edit/', data=data)
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "messages": ['Package "guake" edited'],
                    "output": "ok"
                }
            )

        # After edit:
        output = self.app.get('/api/package/guake/', data=data)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        self.assertEqual(
            data['packages'][0]['package']['upstream_url'],
            'http://www.guake.org'
        )

    @patch('pkgdb2.lib.utils')
    @patch('pkgdb2.is_admin')
    def test_api_package_critpath(self, login_func, mock_func):
        """ Test the api_package_critpath function.  """
        login_func.return_value = None

        # Redirect as you are not admin
        user = FakeFasUser()

        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/critpath/')
            self.assertEqual(output.status_code, 302)

        user = FakeFasUserAdmin()

        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/critpath/')
            self.assertEqual(output.status_code, 500)
            data = json.loads(output.data)
            self.assertEqual(
                sorted(data),
                ['error', 'error_detail', 'output']
            )
            self.assertEqual(
                data['error'], "Invalid input submitted")

            self.assertEqual(
                data['output'], "notok")

            self.assertEqual(
                sorted(data['error_detail']),
                [
                    'branches: This field is required.',
                    'pkgnames: This field is required.'
                ]
            )

        data = {
            'pkgnames': 'gnome-terminal',
            'branches': 'master'
        }
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/critpath/', data=data)
            self.assertEqual(output.status_code, 500)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "error": "No package found by this name",
                    "output": "notok"
                }
            )

        create_package_acl(self.session)
        create_package_critpath(self.session)

        # Before edit:
        output = self.app.get('/api/package/guake/', data=data)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        for pkg in data['packages']:
            self.assertFalse(pkg['critpath'])
            self.assertFalse(pkg['critpath'])

        data = {
            'pkgnames': 'guake',
            'branches': ['master', 'f18'],
        }

        # User is an admin - But not updating the critpath
        user = FakeFasUserAdmin()
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/critpath/', data=data)
            self.assertEqual(output.status_code, 500)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "error": "Nothing to update",
                    "output": "notok"
                }
            )

            # Still no update
            data = {
                'pkgnames': 'guake',
                'branches': ['master', 'f18'],
                'critpath': False,
            }

            output = self.app.post('/api/package/critpath/', data=data)
            self.assertEqual(output.status_code, 500)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "error": "Nothing to update",
                    "output": "notok"
                }
            )

        data = {
            'pkgnames': 'guake',
            'branches': ['foobar'],
        }

        # User is an admin - But not invalid collection the critpath
        user = FakeFasUserAdmin()
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/critpath/', data=data)
            self.assertEqual(output.status_code, 500)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    "error": "No collection found by the name of foobar",
                    "output": "notok"
                }
            )

        data = {
            'pkgnames': 'guake',
            'branches': ['master', 'f18'],
            'critpath': True,
        }

        # User is an admin and updating the critpath
        user = FakeFasUserAdmin()
        with user_set(pkgdb2.APP, user):
            output = self.app.post('/api/package/critpath/', data=data)
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.data)
            self.assertEqual(
                data,
                {
                    'messages': [
                        'guake: critpath updated on master to True',
                        'guake: critpath updated on f18 to True'
                    ],
                    'output': 'ok'
                }
            )

        # After edit:
        output = self.app.get('/api/package/guake/', data=data)
        self.assertEqual(output.status_code, 200)
        data = json.loads(output.data)
        for pkg in data['packages']:
            self.assertTrue(pkg['critpath'])
            self.assertTrue(pkg['critpath'])


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(FlaskApiPackagesTest)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
