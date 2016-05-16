oVirt infra team fabric tasks
=============================

This is the repo that will hold all our fabric tasks and related libs

Installation
------------

If you don't have an rpm (check the `oVirt ci tools
repo <http://resources.ovirt.org/repos/ci-tools/>`__) you can generate
one running
`mock\_runner.sh <http://www.ovirt.org/develop/dev-process/build-and-test-standards>`_
from the root of the repo with::

    mock_runner.sh -b fc23

Where you can change fc23 with any distro you want, it will leave the
rpms under ``exported-artifacts`` dir.

Usage
-----

From command line
~~~~~~~~~~~~~~~~~

Once installed, you'll have three new commands installed, all three are
just aliases for the same python routine, that is a wrapper around
fabric.main to add the ovirt fabfile so you don't have to.

To see all the available taks run any of them as if you would run fab::

    ofab -l
    ovirt-fabric -l
    fab-ovirt -l

As a library
~~~~~~~~~~~~

If you want to include the tasks defined here to your own fabfile, you
can just import the ovirt fabfile to yours, for example:

::

    ---- myfabfile.py
    from fabric_ovirt import fabfile

    ----

And you will have all the tasks that are defined there defined also in
your custom fabfile:

::

    fab --fabfile myfabfile.py -l


Configuring it
~~~~~~~~~~~~~~~~

You can specify a config file with the `-c` option, like::

    ofab -c ~/.fabric_ovirt

Some helpful options are::

    timeout = 60
    skip_bad_hosts = True
    disable_known_hosts = True  # if you deal with ad-hoc vms
    gateway = my.jump.host

Development
-----------

Running automated tests
~~~~~~~~~~~~~~~~~~~~~~~

This repo includes some automated test and build scripts. Those were
written to conform to the
`oVirt CI standards <http://www.ovirt.org/develop/dev-process/build-and-test-standards>`_.
To run the tests, follow the `mock\_runner.sh` setup instruction in the
given link and run the following command::

    mock_runner.sh -b fc23

Running tests directly with tox
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When developing code to add to this repo it may be desireable to run the
tests directly instead of via `mock\_runner.sh`.
To do that the following packages need to be installed via your
distribution's package manager:

* python-tox
* libxml2-devel
* libxslt-devel

Once the packages are installed, you should be able to run the tests by
simply running the following command::

    tox

Setting up a deveopment environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To setup a deveopment environment, please follow the instructions above
for running `tox`, as you will need the same distribution packages
listed there. In addition it is recommended to also install the
following packages to make build processes a little faster:

* python-pbr
* fabric
* python-foreman
* python-lxml

It is recommended to use
`virtualenvwrapper <https://virtualenvwrapper.readthedocs.io>`_
when devepoing code for adding to this repo.
`virtualenvwrapper` is packaged in many distributions. For example on
RedHat, Fedora or CentOS it is packaged as `python-virtualenvwrapper`.

One `virtualenvwrapper` is installed and you're configured your shell
environment to use it, you can run the following command from within the
root directory of this Git repo to create a development environment::

    mkvirtualenv -a $PWD -r requirements.txt --system-site-packages fabric-ovirt

After running the command above you should be places in the newly
created environment, you can now install this package in 'development mode'::

    python setup.py develop

Once the package is installed in development mode, you can run the
command-line commands such as `ofab` when the virtualenv is active.
Changes in the source code will be reflected immediately in the command
line commands.
