# ChroMagician macOS patch

Upstream: https://github.com/cursedtoast2/ChroMagician
Base commit: `7e3dbe92aacd030a811f2343c350ef73949ded7d`
Upstream license: GPL-3.0 (retain upstream LICENSE when using its source).

Clone upstream, check out the base commit, and apply `macos-serial-alias.patch`
with `git apply`. The patch prefers macOS callout ports over duplicate tty aliases.
Installed binaries, dependencies, firmware downloads and personal backups are
excluded from this repository. Scripts require those local dependencies and are
tailored to the original device, firmware versions and pinned backup hashes.
