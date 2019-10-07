#!/usr/bin/env bash

set -x -e
virtualenv python-env
python-env/bin/pip install --upgrade pip setuptools wheel
python-env/bin/pip install -r requirements.txt
