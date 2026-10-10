"""Read-only, double-read backup of the identified Chromatic's firmware flash.

Reads reset the console and temporarily clear/reload FPGA SRAM. No persistent
flash erase/program commands are used. Failures retain all evidence and never retry.
"""
import datetime
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLIENT = ROOT / 'source/target/release/chromatic-backup'
LOADER = ROOT / 'fpga-build/openFPGALoader'
ESPTOOL = ROOT / 'python/bin/esptool.py'
SIZE = 4 * 1024 * 1024
EXPECTED = {'chromatic': 'v4.6', 'fpga': '18.14', 'mcu': 'v0.13.8'}

def validate_pair(first, second):
    data = [p.read_bytes() for p in (first, second)]
    if any(len(b) != SIZE for b in data):
        raise RuntimeError('Backup size is not exactly 4 MiB.')
    if any(len(set(b)) < 2 for b in data):
        raise RuntimeError('Backup is uniform data; cannot accept as firmware.')
    digests = [hashlib.sha256(b).hexdigest() for b in data]
    if digests[0] != digests[1]:
        raise RuntimeError('The two reads differ. Keep both files; do not install firmware.')
    return {'file': first.name, 'second_read': second.name,
            'size_bytes': SIZE, 'sha256': digests[0]}

def main():
    target = ROOT / 'backups' / datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    target.mkdir(parents=True, exist_ok=False)
    marker = target / 'INCOMPLETE.txt'
    marker.write_text('Backup incomplete. Do not use these files for restoration yet.\n')
    print(f'Backup directory: {target}', flush=True)

    def run(*args, label):
        print(f'\n{label} — please wait; output is saved to the backup directory.', flush=True)
        log = target / (label.replace(' ', '-') + '.log')
        # Running a command exactly once is deliberate. No automatic retry.
        with log.open('w') as out:
            out.write('COMMAND: ' + ' '.join(str(a) for a in args) + '\n')
            out.flush()
            result = subprocess.run([str(a) for a in args], cwd=ROOT,
                                    stdout=out, stderr=subprocess.STDOUT,
                                    timeout=1800)
        text = log.read_text(errors='replace')
        print(text, flush=True)
        result.check_returncode()
        if re.search(r'\b(?:Error|ERROR|FAIL|Fail|failed)\b', text):
            raise RuntimeError(f'{label} reported an error. Inspect {log}.')
        return text.split('\n', 1)[1]

    try:
        ports = json.loads(run(CLIENT, '--devices', '--json', label='Device enumeration'))['ports']
        if len(ports) != 1:
            raise RuntimeError('Exactly one Chromatic must be connected.')
        version_text = run(CLIENT, '--firmware-info', '--port', ports[0], '--json', label='Original firmware')
        versions = [json.loads(line)['version'] for line in version_text.splitlines()
                    if line.startswith('{') and json.loads(line).get('event') == 'firmware_info']
        if versions != [EXPECTED]:
            raise RuntimeError('Firmware differs from the identified device. Stop for review.')
        scan = run(LOADER, '--scan-usb', label='Programmer enumeration')
        matches = re.findall(r'^\s*(\d+)\s+(\d+)\s+0x33aa:0x0120\b', scan, re.M | re.I)
        if len(matches) != 1:
            raise RuntimeError('Exactly one GWU2X programmer must be connected.')
        detected = run(LOADER, '--cable', 'gwu2x', '--detect', label='FPGA identification')
        if not re.search(r'GW5A-25|0x0*1281b\b', detected, re.I):
            raise RuntimeError('Unexpected FPGA.')
        for n in (1, 2):
            run(ESPTOOL, '--chip', 'esp32', '--port', ports[0], '--baud', '460800',
                '--before', 'default_reset', '--after', 'hard_reset',
                'read_flash', '0', str(SIZE), target / f'mcu-{n}.bin',
                label=f'MCU read {n}')
        mcu = validate_pair(target / 'mcu-1.bin', target / 'mcu-2.bin')
        print('MCU double-read hashes match.', flush=True)
        for n in (1, 2):
            run(LOADER, '--cable', 'gwu2x', '--dump-flash', '--file-size', str(SIZE),
                '--force-terminal-mode', target / f'fpga-{n}.bin', label=f'FPGA read {n}')
        fpga = validate_pair(target / 'fpga-1.bin', target / 'fpga-2.bin')
        manifest = {'schema_version': 1, 'versions_before_backup': versions[0],
                    'mcu': mcu, 'fpga': fpga, 'format': 'raw-full-flash',
                    'read_consistency_verified': True, 'restore_tested': False}
        (target / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        marker.unlink()
        print(f'BACKUP READS VERIFIED: {target}\nBoth 4 MiB chips read twice with matching SHA-256 hashes.\nRestoration is not yet tested. No custom firmware was installed.', flush=True)
    except Exception as error:
        with marker.open('a') as out:
            out.write(str(error) + '\n')
        print(f'STOPPED: {error}\nEvidence retained in {target}. Do not automatically retry.', flush=True)
        raise SystemExit(1)

if __name__ == '__main__':
    main()
