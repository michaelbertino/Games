#!/bin/sh
set -eu
cd "$(dirname "$0")"
./python/bin/python flash_harvest.py --write
