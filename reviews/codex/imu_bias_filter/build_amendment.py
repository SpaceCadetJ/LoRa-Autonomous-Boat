"""Add C43 to a captured schematic copy; no generators or live CAD writes."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,shutil,uuid
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
PRIOR=ROOT/'reviews/codex/imu_interface';PROJECT=OUT/'source/hardware/kicad_v2'
def require(v,m):
 if not v:raise RuntimeError(m)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p):return p.relative_to(ROOT).as_posix()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8',newline='\n')
def uid(key):return str(uuid.uuid5(uuid.NAMESPACE_URL,'lora-imu-bias-filter/'+key))
def clone(block,dy,key):
 block=re.sub(r'\(uuid "([^"]+)"\)',lambda m:'(uuid "'+uid(key+'/'+m[1])+'")',block)
 return re.sub(r'\(at ([\d.-]+) ([\d.-]+) ([\d.-]+)\)',lambda m:f'(at {m[1]} {float(m[2])+dy:.6f} {m[3]})',block)
def main():
 previous=json.loads((PRIOR/'native_manifest.json').read_text());prior_inputs=previous['input_sha256']
 live=json.loads((PRIOR/'candidate_manifest.json').read_text())['live_input_sha256']
 protected={rel(f):sha(f) for d in ['imu_interface','imu_placement'] for f in (ROOT/'reviews/codex'/d).rglob('*') if f.is_file() and f.suffix not in {'.pyc','.kicad_prl'}}
 protected.update(live)
 protected.update({p:sha(ROOT/p) for p in ['hardware/kicad/tools/v1_design.py','hardware/kicad_v2/tools/route_v2.py']})
 for name,h in {**prior_inputs,**live}.items():require(sha(ROOT/name)==h,'Changed baseline '+name)
 for name,h in prior_inputs.items():
  source=ROOT/name;relative=source.relative_to(PRIOR/'source');dest=OUT/'source'/relative
  require(dest.resolve().is_relative_to(OUT),'Output escapes packet')
  dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
 nav=PROJECT/'Navigation.kicad_sch';text=nav.read_text(encoding='utf-8');require('"C43"' not in text,'Reference C43 already exists')
 cap=next(line for line in text.splitlines() if line.startswith('(symbol (lib_id "Device:C")') and '(property "Reference" "C42"' in line)
 cap=clone(cap,-109.22,'cap').replace('"C42"','"C43"').replace('"100nF"','"100pF"').replace('"KGM15ACG1H104KT"','""').replace('"Kyocera AVX"','""').replace('"U11 VCCB bypass"','"PCA9306 bias filter; project target C0G +/-5%, >=25V; exact MPN held"')
 gnd=next(line for line in text.splitlines() if line.startswith('(symbol (lib_id "power:GND")') and '"#PWRNAV22"' in line)
 gnd=clone(gnd,-109.22,'ground').replace('"#PWRNAV22"','"#PWRNAVC43"')
 def wire(x1,y1,x2,y2,key):return f'(wire (pts (xy {x1} {y1}) (xy {x2} {y2})) (stroke (width 0) (type default)) (uuid "{uid(key)}"))'
 added=[cap,wire(530.86,95.25,530.86,90.17,'top'),wire(530.86,90.17,533.4,90.17,'label-wire'),f'(label "PCA9306_BIAS" (at 533.4 90.17 0) (effects (font (size 1.27 1.27)) (justify left bottom)) (uuid "{uid("bias-label")}"))',wire(530.86,102.87,530.86,107.95,'return'),gnd,f'(text "C43: 100pF at VREF2/EN; confirm bias settling at startup." (at 406.666667 160.7 0) (effects (font (size 1.27 1.27)) (justify left bottom)) (uuid "{uid("note")}"))']
 marker='(embedded_fonts no)';require(text.rstrip().endswith(marker+'\n)'), 'Expected schematic trailer')
 head,sep,tail=text.rpartition(marker);text=head+'\n'.join(added)+'\n'+sep+tail
 nav.write_text(text,encoding='utf-8',newline='\n')
 for f in [nav,PROJECT/'LoRa_Boat_Controller_V2.kicad_sch']:
  text=f.read_text(encoding='utf-8').replace('(rev "V2-IMU1")','(rev "V2-IMU2")').replace('IMU candidate: five U6 pin changes; not PCB integrated','IMU2: C43 bias filter added; not PCB integrated')
  f.write_text(text,encoding='utf-8',newline='\n')
 require(all(sha(ROOT/name)==h for name,h in protected.items()),'Protected input changed during build')
 outputs={rel(OUT/'source'/(ROOT/name).relative_to(PRIOR/'source')):sha(OUT/'source'/(ROOT/name).relative_to(PRIOR/'source')) for name in prior_inputs}
 changed=[(ROOT/name).relative_to(PRIOR/'source').as_posix() for name,h in prior_inputs.items() if sha(OUT/'source'/(ROOT/name).relative_to(PRIOR/'source'))!=h]
 require(sorted(changed)==['hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_sch','hardware/kicad_v2/Navigation.kicad_sch'],'Unexpected copied-file delta')
 write(OUT/'build_manifest.json',{'created_utc':datetime.now(timezone.utc).isoformat(),'source_revision':'10a07dd7e41b1645a7ad70490f2d3d18b2a3a5b0','status':'isolated_C43_schematic_amendment','builder_sha256':sha(Path(__file__)),'input_sha256':prior_inputs,'protected_sha256':protected,'output_sha256':outputs,'changed_files':changed,'expected_delta':{'new_components':['C43'],'new_memberships':{'C43.1':'/Navigation/PCA9306_BIAS','C43.2':'GND'},'changed_existing_memberships':0,'new_net_names':0},'c43':{'value':'100pF','footprint':'Capacitor_SMD:C_0603_1608Metric','selection_targets':{'dielectric':'C0G/NP0','tolerance':'+/-5%','voltage_rating_min_V':25},'mpn':'','procurement_status':'held_exact_part_not_selected'},'pcb_updated':False,'hardware_tested':False,'fabrication_approved':False})
 print(json.dumps({'copied_inputs':len(prior_inputs),'changed_schematic_files':changed,'prior_and_live_preserved':True}))
if __name__=='__main__':main()
