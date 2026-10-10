# ChroMagician on Apple Silicon — local prototype

This workspace contains an ARM64 command-line build of ChroMagician's cartridge client. It does not install firmware automatically.

## Verified

- User ran the client from normal Terminal successfully: Chromatic v4.6, FPGA 18.14, MCU v0.13.8. The agent environment remains unable to open the serial port.
- Rust client builds in release mode for aarch64-apple-darwin.
- USB enumeration finds the connected Chromatic.
- Local patch prefers `/dev/cu.*` when macOS also exposes a matching `/dev/tty.*` alias, preventing a single device being counted twice.
- Isolated esptool 4.12.0 runs successfully.
- openFPGALoader 1.1.1 builds and runs natively on ARM64 with GWU2X/Gowin support. Its build requires `CMAKE_OSX_ARCHITECTURES=arm64` and linking IOKit, CoreFoundation and Security for the static libusb library.

## Outstanding

- Opening `/dev/cu.usbmodem0123456783` returns `Operation not permitted` from the agent environment, including after a device-path permission grant. Enumeration alone does not verify serial communication.
- Upstream core tests: 39 passed, 15 failed. Several failures involve macOS pseudo-terminal serial configuration (`Not a typewriter`); other failures include timeouts and broken pipes. They are unresolved, not waived. See tests.log.
- The user installed ChroMagic v1.0.1, verified its runtime versions, backed up Tetris ROM/save data, and flashed Harvest Quest from normal Terminal. The cartridge ROM readback matched the original SHA-256. Firmware and cartridge restoration have not been tested.
- ChroMagic requires both its MCU and FPGA images. Stock MCU firmware alone is insufficient for this client.

## Read-only check from a normal Terminal

Run `check-device.command` in this directory. It lists devices and reads firmware versions, with no flash operation or automatic reset. Close MR Updater first if it holds the serial connection. This check can help distinguish the agent's access restrictions from an actual driver/client problem.

## Sources and tooling

- source/: https://github.com/cursedtoast2/ChroMagician — GPL-3.0; original license retained. Local macOS serial-alias patch in crates/chromatic-backup-core/src/lib.rs.
- openFPGALoader/: pinned to c3a1232f8730dbde42453ab96d0275b29a384271, the revision used by ChroMagician's Linux tools manifest.
- libusb 1.0.29 built locally in deps/.
- Rust in cargo/ and rustup/; esptool in python/. Shell profiles and Applications were not modified.
- firmware/ contains ChroMagic v1.0.1 images and official public stock v4.5 / FPGA 18.13 fallback images. All five downloaded assets match their GitHub SHA-256 digests. These stock images are OLDER than the connected device; they are not an exact recovery set. Exact-version recovery or verified device backup remains required before installing.
- check-programmer.command performs firmware reading, USB enumeration and JTAG identification only. It does not program or erase firmware. Run in normal Terminal with MR Updater closed.

Do not flash until serial communication, installer validation, exact firmware checksums, backup and stock recovery are established.
