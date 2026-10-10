"""Detect the Chromatic programmer without erasing or programming firmware."""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLIENT = ROOT / 'source/target/release/chromatic-backup'
LOADER = ROOT / 'fpga-build/openFPGALoader'

def run(*args):
    result = subprocess.run([str(x) for x in args], cwd=ROOT,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, timeout=30)
    print(result.stdout, end='', flush=True)
    result.check_returncode()
    return result.stdout

ports = json.loads(run(CLIENT, '--devices', '--json'))['ports']
if len(ports) != 1:
    raise SystemExit('Connect exactly one Chromatic before continuing.')
run(CLIENT, '--firmware-info', '--port', ports[0], '--json')
scan = run(LOADER, '--scan-usb')
matches = re.findall(r'^\s*(\d+)\s+(\d+)\s+0x33aa:0x0120\b', scan,
                     re.MULTILINE | re.IGNORECASE)
if len(matches) != 1:
    raise SystemExit('Expected exactly one GWU2X programmer. No firmware commands sent.')
detected = run(LOADER, '--cable', 'gwu2x', '--detect')
if not re.search(r'GW5A-25|0x0*1281b\b', detected, re.IGNORECASE):
    raise SystemExit('Expected Chromatic FPGA was not identified. Stop here.')
print('PROGRAMMER CHECK PASSED. No firmware was erased or programmed.')
