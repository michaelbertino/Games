"""Identify firmware storage; no flash writes. Resets MCU/FPGA temporarily."""
import datetime
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLIENT = ROOT / 'source/target/release/chromatic-backup'
LOADER = ROOT / 'fpga-build/openFPGALoader'
ESPTOOL = ROOT / 'python/bin/esptool.py'
LOGDIR = ROOT / 'diagnostics'
LOGDIR.mkdir(exist_ok=True)
log = LOGDIR / ('storage-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.txt')

def run(*args):
    with log.open('a') as out:
        out.write('\nCOMMAND: ' + ' '.join(str(x) for x in args) + '\n')
        out.flush()
        result = subprocess.run([str(x) for x in args], cwd=ROOT,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, timeout=90)
        out.write(result.stdout)
        out.write(f'\nEXIT: {result.returncode}\n')
    print(result.stdout, end='', flush=True)
    result.check_returncode()
    return result.stdout

ports = json.loads(run(CLIENT, '--devices', '--json'))['ports']
if len(ports) != 1:
    raise SystemExit('Connect exactly one Chromatic. Stopping.')
scan = run(LOADER, '--scan-usb')
matches = re.findall(r'^\s*(\d+)\s+(\d+)\s+0x33aa:0x0120\b', scan,
                     re.MULTILINE | re.IGNORECASE)
if len(matches) != 1:
    raise SystemExit('Expected exactly one GWU2X programmer. Stopping.')
print('Reading MCU flash identification; the handheld will reset.', flush=True)
run(ESPTOOL, '--chip', 'esp32', '--port', ports[0], '--before', 'default_reset',
    '--after', 'hard_reset', 'flash_id')
print('Reading FPGA flash identification; installed FPGA firmware will reload.', flush=True)
result = run(LOADER, '--cable', 'gwu2x', '--detect', '-f')
if 'Detect flash:' not in result or re.search(r'\b(?:Error|Fail|FAIL)\b', result):
    raise SystemExit('FPGA flash identification not confirmed. Preserve the log; do not retry automatically.')
print(f'Storage identification finished. Log: {log}')
print('No persistent firmware was erased or programmed. Send the output for backup sizing.')
