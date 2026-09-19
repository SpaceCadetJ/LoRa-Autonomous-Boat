"""Export native schematic evidence and reject stale source snapshots."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,importlib.util,json,shutil,subprocess,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent;PROJECT=OUT/'source/hardware/kicad_v2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p):return p.relative_to(ROOT).as_posix()
def dump(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8',newline='\n')
def main():
 build=json.loads((OUT/'build_manifest.json').read_text());inputs=build['output_sha256']
 for name,h in {**inputs,**build['protected_sha256']}.items():
  if sha(ROOT/name)!=h:raise RuntimeError('Changed input '+name)
 native=OUT/'native';native.mkdir(exist_ok=True)
 cli=str(Path(sys.executable).parent/'kicad-cli.exe');source=rel(PROJECT/'LoRa_Boat_Controller_V2.kicad_sch')
 commands=[['sch','export','netlist','--format','kicadxml','-o',rel(native/'netlist.xml'),source],['sch','erc','--format','json','--severity-all','-o',rel(native/'erc.json'),source],['sch','export','svg','-o',rel(native/'svg')+'/',source]]
 report={'created_utc':datetime.now(timezone.utc).isoformat(),'exporter_sha256':sha(Path(__file__)),'input_sha256':inputs,'commands':[],'scope':'Isolated schematic amendment only; no PCB generation, routing or hardware access'}
 for c in commands:
  r=subprocess.run([cli]+c,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace');report['commands'].append({'argv':[cli]+c,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
  if r.returncode:dump(OUT/'native_manifest.json',report);raise RuntimeError('Native export failed')
 spec=importlib.util.spec_from_file_location('bounds',ROOT/'tools/quality/review.py');q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
 bounds={p.name:q.coordinate_bounds(p) for p in sorted(PROJECT.glob('*.kicad_sch'))}
 if not all(v['passed'] for v in bounds.values()):raise RuntimeError(bounds)
 dump(native/'coordinate_bounds.json',bounds)
 shutil.copyfile(native/'svg/LoRa_Boat_Controller_V2-Navigation.svg',OUT/'v2_imu_bias_filter.svg')
 for name,h in {**inputs,**build['protected_sha256']}.items():
  if sha(ROOT/name)!=h:raise RuntimeError('Input changed during export '+name)
 outputs=[native/'netlist.xml',native/'erc.json',native/'coordinate_bounds.json',OUT/'v2_imu_bias_filter.svg']+sorted((native/'svg').glob('*.svg'))
 report.update({'version':subprocess.check_output([cli,'version'],text=True).strip(),'status':'native_exports_complete_unqualified','output_sha256':{rel(p):sha(p) for p in outputs},'prior_and_live_preserved':True})
 dump(OUT/'native_manifest.json',report);print('Native netlist/ERC/SVG and page bounds complete; protected evidence unchanged.')
if __name__=='__main__':main()
