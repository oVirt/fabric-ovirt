oVirt infra team fabric tasks
=============================

This is the repo that will hold all our fabric tasks and related libs

Installation
------------

If you don't have an rpm (check the `oVirt ci tools
repo <http://resources.ovirt.org/repos/ci-tools/>`__) you can generate
one running
`mock\_runner.sh <http://www.ovirt.org/index.php?title=CI/Build_and_test_standards>`__
from the root of the repo with:

::

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

To see all the available taks run any of them as if you would run fab:

::

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
