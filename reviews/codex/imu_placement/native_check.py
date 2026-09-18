"""Run native DRC on captured boards; bind each report to exact board/project inputs."""
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,subprocess,sys
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p):return p.relative_to(ROOT).as_posix()
cli=str(Path(sys.executable).parent/'kicad-cli.exe')
boards=[OUT/'inputs/LoRa_Boat_Controller_V2.kicad_pcb',OUT/'study/IMU_PLACEMENT_STUDY.kicad_pcb']
inputs={rel(f):sha(f) for b in boards for f in [b,b.with_suffix('.kicad_pro')]}
commands=[[cli,'pcb','drc','--format','json','--severity-all','--all-track-errors','-o',rel(OUT/name),rel(b)] for b,name in zip(boards,['drc_baseline.json','drc_study.json'])]
def run(command):
 r=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
 return {'argv':command,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,commands))
if any(sha(ROOT/f)!=h for f,h in inputs.items()):raise RuntimeError('Native input changed during DRC')
if any(r['returncode'] for r in results):raise RuntimeError(results)
report={'created_utc':datetime.now(timezone.utc).isoformat(),'version':subprocess.check_output([cli,'version'],text=True).strip(),'runner_sha256':sha(Path(__file__)),'input_sha256':inputs,'output_sha256':{rel(OUT/name):sha(OUT/name) for name in ['drc_baseline.json','drc_study.json']},'commands':results,'scope':'Native DRC only, no schematic parity or zone refill; a successful command exit does not mean zero violations.'}
(OUT/'native_manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({'native_reports':len(results),'input_hashes':len(inputs),'command_exit_codes':[r['returncode'] for r in results]}))
