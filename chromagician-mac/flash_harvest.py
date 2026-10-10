"""One explicitly authorized Harvest Quest cartridge write; never auto-retry."""
import argparse,datetime,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CLIENT=ROOT/'source/target/release/chromatic-backup'
ROM=ROOT.parent/'HarvestQuest/build/HarvestQuest.gbc'
BACKUP=ROOT/'cartridge-backups/20261004-161030-075737'
ROM_HASH='552f89b3f5e2c26988f33a809061d9f4f8b72ecef6e992d1b74420e15aebf956'
FILES={'Tetris.gbc':(262144,'c62248a77795c6ab276979bbef8159e9c587c4fe3e8d2592d2d769ca559dddfc'),'Tetris.sav':(32768,'0bbcfac6c8153167bad5310d8276f4b01d853e0c3d6a0242ff6a14a734162a61')}

def check(path,size,digest):
 data=path.read_bytes()
 if len(data)!=size or hashlib.sha256(data).hexdigest()!=digest:raise RuntimeError('Integrity mismatch: '+str(path))

def main():
 p=argparse.ArgumentParser();p.add_argument('--write',action='store_true');args=p.parse_args()
 check(ROM,262144,ROM_HASH)
 for name,(size,digest) in FILES.items():check(BACKUP/name,size,digest)
 print('Harvest Quest and both Tetris backup files verified.',flush=True)
 if not args.write:return
 journal=ROOT/'harvest-write-attempt.json'
 if journal.exists():raise RuntimeError('A previous attempt exists. Review its outcome before another write.')
 folder=ROOT/'diagnostics'/('harvest-write-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
 folder.mkdir(parents=True,exist_ok=False)
 state={'status':'preflight','write':'not-dispatched','rom':str(ROM),'rom_sha256':ROM_HASH,'backup':str(BACKUP),'logs':str(folder)}
 with journal.open('x') as f:json.dump(state,f,indent=2)
 def save():journal.write_text(json.dumps(state,indent=2)+'\n')
 def run(label,*args):
  print(label+' ...',flush=True)
  # Preserve every operation's output; do not repeat commands after uncertainty.
  r=subprocess.run([str(CLIENT),*map(str,args)],capture_output=True,text=True,timeout=900)
  (folder/(label+'.log')).write_text(r.stdout+r.stderr)
  print(r.stdout+r.stderr,flush=True);r.check_returncode()
  events=[json.loads(line) for line in r.stdout.splitlines() if line.startswith('{')]
  if any(e.get('event')=='error' for e in events):raise RuntimeError(label+' reported failure')
  return events
 try:
  ports=run('devices','--devices','--json')[0]['ports']
  if len(ports)!=1:raise RuntimeError('Connect exactly one Chromatic')
  common=['--port',ports[0],'--timeout','600','--json']
  versions=run('firmware',*common,'--firmware-info')
  v=next(e['version'] for e in versions if e.get('event')=='firmware_info')
  if v!={'chromatic':'1.0.1 (4.2)','fpga':'18.38','mcu':'v0.13.4'}:raise RuntimeError('Unexpected firmware versions')
  state['status']='waiting-for-cartridge-mode';state['firmware_verified']=v;save()
  print('Firmware verified. Now enable SYSTEM > C. MAGICIAN on the handheld, keeping Tetris inserted and USB connected.',flush=True)
  input('After enabling C. MAGICIAN, press Return here to continue: ')
  fresh_ports=run('devices-after-mode-change','--devices','--json')[0]['ports']
  if fresh_ports!=ports:raise RuntimeError('USB device changed during mode selection; stop for review')
  cart=next(e['cartridge'] for e in run('inspect',*common,'--inspect') if e.get('event')=='cartridge_inspected')
  if cart.get('header_sha1')!='ee2e2842653c02dce7e9c43d62b0c4df223a1484':raise RuntimeError('Cartridge header no longer matches backed-up Tetris')
  chip=next(e for e in run('probe',*common,'--probe-flash') if e.get('event')=='flash_detected')
  if chip.get('chip_id')!='bfc9' or chip.get('capacity')!=2097152:raise RuntimeError('Cartridge flash chip differs from the backed-up cartridge')
  # Recheck local input immediately before dispatch.
  check(ROM,262144,ROM_HASH)
  state['write']='dispatched-outcome-unverified';state['status']='writing';save()
  events=run('write',*common,'--write-rom',ROM,'--yes')
  if not any(e.get('event')=='complete' and e.get('operation')=='write_rom' for e in events):raise RuntimeError('Write completion was not reported')
  state['write']='tool-verified';state['status']='reading-back';save()
  readback=folder/'HarvestQuest-readback.gbc'
  events=run('readback',*common,'--rom',readback)
  if not any(e.get('event')=='complete' for e in events):raise RuntimeError('Readback incomplete')
  check(readback,262144,ROM_HASH)
  state['status']='complete';state['readback_sha256']=ROM_HASH;save()
  print('HARVEST QUEST FLASHED AND READBACK VERIFIED.\nDisable SYSTEM > C. MAGICIAN, then restart the Chromatic to play. Physical gameplay remains to be checked.',flush=True)
 except BaseException as e:
  state['status']='stopped';state['error']=str(e);save()
  print('STOPPED. Do not rerun or restore automatically. Send the output and harvest-write-attempt.json.',flush=True)
  raise
if __name__=='__main__':main()
