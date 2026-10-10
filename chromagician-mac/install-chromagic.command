#!/bin/sh
set -eu
cd "$(dirname "$0")"
./python/bin/python install_custom.py --install
