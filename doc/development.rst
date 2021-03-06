Development
===========

Get the sources
---------------

Anonymous:

::

  git clone http://git.fedorahosted.org/git/pkgdb2.git

Contributors:

::

  git clone ssh://<FAS user>@git.fedorahosted.org/git/pkgdb2.git


Dependencies
------------

The dependencies of pkgdb2 are listed in the file ``requirements.txt``
at the top level of the sources.


.. note:: if you work in a `virtualenv <http://www.virtualenv.org/en/latest/>`_
          the installation of python-fedora might fail the first time you
          try, just try to run the command twice, the second time it should
          work.


Run pkgdb for development
-------------------------
Copy the configuration file::

 cp pkgdb2.cfg.sample pkgdb2.cfg

Adjust the configuration file (secret key, database URL, admin group...)
See :doc:`configuration` for more detailed information about the
configuration.


Create the database scheme::

  ./createdb

Run the server::

  ./runserver

You should be able to access the server at http://localhost:5000


Every time you save a file, the project will be automatically restarted
so you can see your change immediatly.


Get a working database
----------------------

We provide a daily dump of the pkgdb2 database used in `production in Fedora
<https://admin.fedoraproject.org/pkgdb/>`_. You can load this database dump
and use it for your tests and hacking.

You will need to set up your postgresql server first.


Once you postgresql database is running, download the latest database dump::

    wget http://infrastructure.fedoraproject.org/infra/db-dumps/pkgdb2.db

Create the database itself::

    createdb pkgdb2

Load the dump::

    pg_restore -d pkgdb2 pkgdb2.db

Please refer to ``createdb --help`` and ``pg_restore --help`` for further
help on using these commands.


Coding standards
----------------

We are trying to make the code `PEP8-compliant
<http://www.python.org/dev/peps/pep-0008/>`_.  There is a `pep8 tool
<http://pypi.python.org/pypi/pep8>`_ that can automatically check
your source.


We are also inspecting the code using `pylint
<http://pypi.python.org/pypi/pylint>`_ and aim of course for a 10/10 code
(but it is an assymptotic goal).

.. note:: both pep8 and pylint are available in Fedora via yum:

          ::

            yum install python-pep8 pylint


Send patch
----------

The easiest way to work on pkgdb2 is to make your own branch in git, make
your changes to this branch, commit whenever you want, rebase on master,
whenever you need and when you are done, send the patch either by email,
via the trac or a pull-request (using git or github).


The workflow would therefore be something like:

::

   git branch <my_shiny_feature>
   git checkout <my_shiny_feature>
   <work>
   git commit file1 file2
   <more work>
   git commit file3 file4
   git checkout master
   git pull
   git checkout <my_shiny_feature>
   git rebase master
   git format-patch -2

This will create two patch files that you can send by email to submit in the
trac.

.. note:: You can send your patch by email to the `packagedb mailing-list
          <https://lists.fedorahosted.org/mailman/listinfo/packagedb>`_


Unit-tests
----------

Pkgdb2 has a number of unit-tests providing at the moment a full
coverage of the backend library (pkgdb.lib).


We aim at having a full (100%) coverage of the whole code (including the
Flask application) and of course a smart coverage as in we want to check
that the functions work the way we want but also that they fail when we
expect it and the way we expect it.


Tests checking that function are failing when/how we want are as important
as tests checking they work the way they are intended to.

``runtests.sh``, located at the top of the sources, helps to run the
unit-tests of the project with coverage information using `python-nose
<https://nose.readthedocs.org/>`_.


.. note:: You can specify additional arguments to the nose command used
          in this script by just passing arguments to the script.

          For example you can specify the ``-x`` / ``--stop`` argument:
          `Stop running tests after the first error or failure` by just doing

          ::

            ./runtests.sh --stop


Each unit-tests files (located under ``tests/``) can be called
by alone, allowing easier debugging of the tests. For example:

::

  python tests/test_collection.py

Similarly as for nose you can also ask that the unit-test stop at the first
error or failure. For example, the command could be:

::

  PKGDB_CONFIG=tests/pkgd2b_test.cfg python -m unittest -f -v pkgdb2.tests.test_collection


.. note:: In order to have coverage information you might have to install
          ``python-coverage``

          ::

            yum install python-coverage



Troubleshooting
---------------

+ Login fails in development mode

  The Flask FAS extension requires a secure cookie which ensures that it is
  always encrypted during client/server exchanges.
  This makes the authentication cookie less likely to be exposed to cookie
  theft by eavesdropping.

  You can disable the secure cookie for testing purposes by setting the
  configuration key ``FAS_HTTPS_REQUIRED`` to False.

  .. WARNING::
     Do not use this option in production as it causes major security issues

