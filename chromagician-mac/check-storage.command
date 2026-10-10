#!/bin/sh
set -eu
cd "$(dirname "$0")"
./python/bin/python check_storage.py
