#!/bin/bash -ex

# install newer tox because the one shipped with el7 if far too old
pip install --upgrade --user tox
# Set PATH to point to local installs so we use the tox we just installed
export PATH="$HOME/.local/bin:$PATH"

tox
