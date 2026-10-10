"""Back up Tetris and identify its flash chip; never erase or program it."""
import datetime,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CLIENT=ROOT/'source/target/release/chromatic-backup'

def main():
 folder=ROOT/'cartridge-backups'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
 folder.mkdir(parents=True,exist_ok=False)
 marker=folder/'INCOMPLETE.txt';marker.write_text('Backup incomplete; do not overwrite cartridge.\n')
 def run(label,*args):
  print(label+' ...',flush=True)
  r=subprocess.run([str(CLIENT),*map(str,args)],capture_output=True,text=True,timeout=900)
  (folder/(label+'.log')).write_text(r.stdout+r.stderr)
  print(r.stdout+r.stderr,flush=True);r.check_returncode()
  events=[json.loads(line) for line in r.stdout.splitlines() if line.startswith('{')]
  if any(e.get('event')=='error' for e in events):raise RuntimeError(label+' failed')
  return events
 try:
  devices=run('devices','--devices','--json')[0]['ports']
  if len(devices)!=1:raise RuntimeError('Connect exactly one Chromatic')
  common=['--port',devices[0],'--timeout','600','--json']
  events=run('inspect',*common,'--inspect')
  cart=next(e['cartridge'] for e in events if e.get('event')=='cartridge_inspected')
  if 'TETRIS' not in cart['title'].upper():raise RuntimeError('Expected Tetris; detected '+cart['title'])
  args=[*common,'--rom',str(folder/'Tetris.gbc')]
  if cart['save_size']:args+=['--sav',str(folder/'Tetris.sav')]
  events=run('backup',*args)
  if not any(e.get('event')=='complete' for e in events):raise RuntimeError('Backup completion missing')
  files={}
  for name,size in [('Tetris.gbc',cart['rom_size']),('Tetris.sav',cart['save_size'])]:
   if not size:continue
   data=(folder/name).read_bytes()
   if len(data)!=size:raise RuntimeError('Wrong backup size: '+name)
   files[name]={'size_bytes':size,'sha256':hashlib.sha256(data).hexdigest()}
  # Identify the flash only after the original game/save have been saved.
  probe=run('flash-identification',*common,'--probe-flash')
  chip=next(e for e in probe if e.get('event')=='flash_detected')
  if not any(e.get('event')=='complete' for e in probe):raise RuntimeError('Flash probe completion missing')
  (folder/'manifest.json').write_text(json.dumps({'cartridge':cart,'files':files,'flash':chip},indent=2)+'\n')
  marker.unlink()
  print('TETRIS BACKUP COMPLETE. Cartridge was not erased or programmed.\nSaved in: '+str(folder),flush=True)
 except BaseException as e:
  with marker.open('a') as f:f.write(str(e)+'\n')
  print('STOPPED: '+str(e)+'\nKeep the logs; do not repeat automatically. Folder: '+str(folder),flush=True)
  raise
if __name__=='__main__':main()
