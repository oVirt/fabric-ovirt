#!/usr/bin/env python
from os import path

from fabric.main import main as fabric_main


def main():
    ovirt_fabfile = path.join(path.dirname(__file__), 'fabfile.py')
    fabric_main(fabfile_locations=[ovirt_fabfile])
