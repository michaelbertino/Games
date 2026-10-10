#!/bin/sh
set -eu
cd "$(dirname "$0")"
./source/target/release/chromatic-backup --devices --json
./source/target/release/chromatic-backup --firmware-info --json
