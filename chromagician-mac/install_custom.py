"""Pinned ChroMagic installer derived from ChroMagician's firmware.dart.
Default is offline validation only. --install dispatches one journaled attempt.
"""
import argparse, datetime, hashlib, json, re, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BACKUP=ROOT/'backups/20261004-155840-680320'
CLIENT=ROOT/'source/target/release/chromatic-backup'
LOADER=ROOT/'fpga-build/openFPGALoader'
ESP=ROOT/'python/bin/esptool.py'
CUSTOM=ROOT/'firmware/custom'
HASHES={'mcu.bin':'6c7f08c0b1b27f0a56dd412b1c891cc981f269a845dd3940e92bf5a3266cdb6a','fpga.fs':'79791d915060a9898c9be6adc7ab22f298cbea9619c6bb765b8667db62c337a2'}
BACKUP_HASHES={'mcu':'e09c3b6855cc22d733aa6076bb9d1c45e84d0d0171c8121ff84756594d204b6a','fpga':'3418e5470ff891e84097a55f1252722a9df14c010af65e14843bef4021fa5ecb'}
OLD={'chromatic':'v4.6','fpga':'18.14','mcu':'v0.13.8'}
NEW={'chromatic':'1.0.1 (4.2)','fpga':'18.38','mcu':'v0.13.4'}

def check_file(path,digest,size=None):
 data=path.read_bytes()
 if hashlib.sha256(data).hexdigest()!=digest or (size is not None and len(data)!=size):
  raise RuntimeError('Integrity check failed: '+str(path))
 return data

def validate():
 for chip,digest in BACKUP_HASHES.items():
  for n in (1,2): check_file(BACKUP/f'{chip}-{n}.bin',digest,4194304)
 for name,digest in HASHES.items(): check_file(CUSTOM/name,digest)
 mcu=(CUSTOM/'mcu.bin').read_bytes()
 if mcu[0]!=0xe9 or not 256<len(mcu)<=0x100000: raise RuntimeError('Invalid MCU application')
 r=subprocess.run([str(ESP),'--chip','esp32','image_info',str(CUSTOM/'mcu.bin')],capture_output=True,text=True,check=True)
 if not re.search(r'Checksum: .*\(valid\)',r.stdout) or not re.search(r'Validation Hash: .*\(valid\)',r.stdout):
  raise RuntimeError('MCU image internal validation failed')
 print('Offline validation passed: firmware checksums and both exact stock backups match.',flush=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('--install',action='store_true');args=p.parse_args()
 validate()
 if not args.install: return
 journal=ROOT/'installation-attempt.json'
 if journal.exists(): raise RuntimeError('An installation attempt already exists. Review its result before any further write.')
 logs=ROOT/'diagnostics'/('install-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
 logs.mkdir(parents=True,exist_ok=False)
 state={'status':'preflight','logs':str(logs),'backup':str(BACKUP),'mcu':'not-dispatched','fpga':'not-dispatched'}
 def save(): journal.write_text(json.dumps(state,indent=2)+'\n')
 with journal.open('x') as f: json.dump(state,f)
 def run(label,*cmd):
  print(label+' ...',flush=True)
  path=logs/(label.replace(' ','-')+'.log')
  with path.open('w') as f:
   f.write('COMMAND: '+' '.join(map(str,cmd))+'\n');f.flush()
   result=subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,timeout=1800)
  out=path.read_text(errors='replace').split('\n',1)[1];print(out,flush=True)
  result.check_returncode()
  if re.search(r'\b(?:Error|ERROR|FAIL|Fail|failed)\b',out): raise RuntimeError('Tool reported an error: '+label)
  return out
 try:
  ports=json.loads(run('USB enumeration',CLIENT,'--devices','--json'))['ports']
  if len(ports)!=1: raise RuntimeError('Connect exactly one Chromatic')
  port=ports[0]
  out=run('Stock version check',CLIENT,'--firmware-info','--port',port,'--json')
  versions=[json.loads(s)['version'] for s in out.splitlines() if s.startswith('{') and json.loads(s).get('event')=='firmware_info']
  if versions!=[OLD]: raise RuntimeError('Unexpected running stock versions')
  out=run('Programmer check',LOADER,'--scan-usb')
  if len(re.findall(r'^\s*\d+\s+\d+\s+0x33aa:0x0120\b',out,re.M|re.I))!=1: raise RuntimeError('Expected exactly one GWU2X')
  out=run('FPGA ID check',LOADER,'--cable','gwu2x','--detect')
  if not re.search(r'GW5A-25|0x0*1281b\b',out,re.I): raise RuntimeError('Unexpected FPGA')
  state['status']='writing';state['mcu']='dispatched-outcome-unverified';save()
  out=run('MCU installation',ESP,'--chip','esp32','--port',port,'--baud','460800','--before','default_reset','--after','hard_reset','write_flash','--flash_mode','dio','--flash_freq','40m','--flash_size','4MB','0x10000',CUSTOM/'mcu.bin')
  if 'Hash of data verified.' not in out: raise RuntimeError('MCU write checksum not confirmed')
  state['mcu']='write-verified';state['fpga']='dispatched-outcome-unverified';save()
  out=run('FPGA installation',LOADER,'--cable','gwu2x','--write-flash','--verify','--reset','--force-terminal-mode',CUSTOM/'fpga.fs')
  if 'Verifying write' not in out or not re.search(r'Reading.*100\.00%',out,re.S): raise RuntimeError('FPGA verification completion not confirmed')
  state['fpga']='write-verified';state['status']='checking-running-versions';save()
  out=run('Running version check',CLIENT,'--firmware-info','--after-flash','--expected-firmware',json.dumps(NEW),'--port',port,'--json')
  versions=[json.loads(s)['version'] for s in out.splitlines() if s.startswith('{') and json.loads(s).get('event')=='firmware_info']
  if versions!=[NEW]: raise RuntimeError('Both writes verified but running versions not confirmed')
  state['status']='complete';save()
  print('CHROMAGIC INSTALLED AND VERSIONS VERIFIED. Cartridge not written. Enable SYSTEM > C. MAGICIAN on the handheld next.')
 except BaseException as e:
  state['status']='stopped';state['error']=str(e);save()
  print('STOPPED. Keep connected. Do not rerun or restore automatically. Send installation-attempt.json and the logs.',flush=True)
  raise

if __name__=='__main__': main()
