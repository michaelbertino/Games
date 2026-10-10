#!/bin/sh
set -eu
cd "$(dirname "$0")"
./python/bin/python backup_tetris.py
