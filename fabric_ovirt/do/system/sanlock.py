#!/usr/bin/env python
# encoding: utf-8


from fabric.utils import (
    error as fail,
)
from fabric.api import (
    task,
    settings,
    hide,
    run,
)
from fabric_ovirt.lib.utils import (
    abort,
    info,
)


@task
def clear():
    with settings(
        hide('status', 'running', 'stdout', 'stderr', 'warnings'),
        warn_only=True,
    ):
        out = run("rpm -q sanlock")
    if not out.succeeded:
        info("Sanlock was not installed.")
        return

    out = run("sanlock client status")
    if out.failed:
        fail("Failed to check sanlock status")

    locks = [
        line.rsplit(' ', 1)[-1] for line in out.splitlines()
        if line.startswith('s ')
    ]
    info("Got %d locks" % len(locks))
    failed_locks = []
    for lock in locks:
        info("  Freeing lock %s" % lock)
        with settings(
            hide('running', 'stdout', 'stderr', 'warnings'),
            warn_only=True,
            disable_known_hosts=True
        ):
            res = run("sanlock rem_lockspace -s '%s'" % lock)
            if not res.succeeded:
                failed_locks.append(lock)

    if failed_locks:
        abort("Failed to freed locks: " + ','.join(failed_locks))

    info("Done")
