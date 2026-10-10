# Exact stock recovery evidence

Verified original images are in `backups/20261004-155840-680320/`.
Both reads of each 4 MiB flash chip match their pinned SHA-256 hashes in
`install_custom.py`. Original versions: Chromatic v4.6, MCU v0.13.8, FPGA 18.14.
These are raw full-flash dumps, not the older public stock release files.

Restoration has NOT been tested on hardware. Do not launch restoration automatically
following an uncertain write. Inspect `installation-attempt.json` and its referenced
logs, establish which process has exited and which components were written, and
re-identify the intended connected device first.

The source-supported restoration mechanisms, for review before use, are:

- MCU: esptool `write_flash` at offset 0 with the full `mcu-1.bin` dump. Preserve
  existing flash mode/frequency/size metadata (`keep`); do not use the custom
  application's 0x10000 offset for this full dump. Verify by a full readback hash.
- FPGA: openFPGALoader, cable gwu2x, `--external-flash --write-flash --verify`,
  with `fpga-1.bin` at offset 0. RawParser loads a .bin without reversing bytes;
  GW5A uses programExtFlash. Verify by a full 4 MiB readback hash afterward.
- Verify stock runtime version strings after restoring and rebooting.

The custom installer preserves the MCU bootloader/partition table by writing only
its application at 0x10000, following ChroMagician's firmware.dart sequence. It
journals before each write and blocks a repeated attempt. It does not touch the
Tetris cartridge. Tetris ROM/save backups are still required before cartridge work.
