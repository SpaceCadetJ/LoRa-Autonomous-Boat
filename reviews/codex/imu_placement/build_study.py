"""Isolated mechanical placement study; never routes or edits live CAD."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,shutil,uuid,subprocess,sys,xml.etree.ElementTree as ET
import pcbnew as p
ROOT=Path(__file__).resolve().parents[3]; OUT=Path(__file__).resolve().parent
LIVE=ROOT/'hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_pcb'
SOURCE=ROOT/'reviews/codex/imu_interface'
LIB=Path(sys.executable).resolve().parents[1]/'share/kicad/footprints'
EXPECTED='49a8aa88cf61e8b6272ce13a0d5a5a6a3c6b81aeba057ebcd4ca15a6262c37b2'
PLACE={
 'U9':[110.5,67.3,0], 'C38':[108.5,64.4,0], 'C39':[113.65,67.0,90],
 'U11':[110.0,72.4,90], 'C41':[107.4,73.6,90], 'C42':[107.4,70.3,90],
 'U10':[115.3,71.6,90], 'R36':[114.6,75.3,0], 'R37':[112.6,72.8,90],
 'R38':[118.0,68.6,90], 'R39':[116.0,66.8,90], 'C40':[115.5,88.9,0],
}
RESERVED={'C43_bias_filter':[118.0,72.0,90]}
def require(v,msg):
 if not v:raise RuntimeError(msg)
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
def write(name,v): (OUT/name).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8',newline='\n')
def xy(v):return [round(p.ToMM(v.x),6),round(p.ToMM(v.y),6)]
def bbox(v):return xy(v.GetPosition())+xy(v.GetEnd())
def bounds(f):
 boxes=[bbox(g.GetBoundingBox()) for g in f.GraphicalItems() if g.GetLayer()==p.F_CrtYd]
 if not boxes:return bbox(f.GetBoundingBox(False,False))
 return [min(q[0] for q in boxes),min(q[1] for q in boxes),max(q[2] for q in boxes),max(q[3] for q in boxes)]
def uid(v):return v.m_Uuid.AsString()
def tracks(b):
 return {uid(t):[t.GetClass(),t.GetNetname(),xy(t.GetStart()),xy(t.GetEnd()),(t.GetWidth(p.F_Cu) if t.GetClass()=='PCB_VIA' else t.GetWidth()),t.GetLayer(),t.GetDrill() if t.GetClass()=='PCB_VIA' else None] for t in b.GetTracks()}
def footprints(b):
 return {f.GetReference():[uid(f),f.GetFPIDAsString(),f.GetValue(),xy(f.GetPosition()),f.GetOrientationDegrees(),f.GetLayer(),sorted([uid(q),q.GetNumber(),q.GetNetname(),xy(q.GetPosition()),xy(q.GetSize()),xy(q.GetDrillSize()),q.GetOrientationDegrees(),q.GetLayerSet().FmtBin()] for q in f.Pads())] for f in b.GetFootprints()}
def overlap(a,b):return a[0]<b[2] and a[2]>b[0] and a[1]<b[3] and a[3]>b[1]
def describe(f):return {'ref':f.GetReference(),'value':f.GetValue(),'footprint':f.GetFPIDAsString(),'xy':xy(f.GetPosition()),'rotation':f.GetOrientationDegrees(),'courtyard_aabb_mm':bounds(f),'pads':[{'pin':q.GetNumber(),'net':q.GetNetname(),'xy':xy(q.GetPosition()),'size':xy(q.GetSize())} for q in f.Pads()]}
def main():
 require(sha(LIVE)==EXPECTED,'Corrected live PCB changed: rebase the study deliberately')
 contract=json.loads((SOURCE/'candidate_manifest.json').read_text())
 before_live={name:sha(ROOT/name) for name in contract['live_input_sha256']}
 require(before_live==contract['live_input_sha256'],'Live CAD no longer matches candidate context')
 guard={f.relative_to(ROOT).as_posix():sha(f) for f in [ROOT/'hardware/kicad/tools/v1_design.py',ROOT/'hardware/kicad_v2/tools/route_v2.py']}
 (OUT/'inputs').mkdir(exist_ok=True);(OUT/'study').mkdir(exist_ok=True)
 for ext in ['kicad_pcb','kicad_pro']:
  original=LIVE.with_suffix('.'+ext);target=OUT/'inputs'/original.name
  if target.exists():require(sha(target)==sha(original),'Captured baseline changed')
  else:shutil.copyfile(original,target)
 board=p.LoadBoard(str(OUT/'inputs'/LIVE.name)); old=footprints(board);oldtracks=tracks(board)
 p.SaveBoard(str(OUT/'inputs/normalized_baseline.kicad_pcb'),board)
 comps={c.get('ref'):c for c in ET.parse(SOURCE/'native/netlist.xml').findall('./components/comp')}
 p.KIID.SeedGenerator(180926)
 loaded={};libhash={};reservations=[]
 for ref,placement in {**PLACE,**RESERVED}.items():
  reserve=ref in RESERVED
  identity='Capacitor_SMD:C_0603_1608Metric' if reserve else comps[ref].findtext('footprint')
  lib,name=identity.split(':');directory=(SOURCE/'source/hardware/kicad_v2/LoRa_Boat_Controller_V2.pretty') if lib=='LoRa_Boat_Controller_V2' else LIB/(lib+'.pretty')
  require((directory/(name+'.kicad_mod')).is_file(),f'Missing footprint {identity}')
  libhash[str(directory/(name+'.kicad_mod'))]=sha(directory/(name+'.kicad_mod'))
  f=p.FootprintLoad(str(directory),name);require(f is not None,'Footprint failed to load')
  f.SetReference(ref);f.SetValue('100pF RESERVE' if reserve else comps[ref].findtext('value'))
  f.SetFPID(p.LIB_ID(lib,name));f.SetPosition(p.VECTOR2I(p.FromMM(placement[0]),p.FromMM(placement[1])));f.SetOrientationDegrees(placement[2])
  # Pads intentionally remain net 0; UUID generator seeded for repeatable loads.
  f.Reference().SetVisible(False);f.Value().SetVisible(False)
  if reserve:reservations.append(describe(f));continue
  require(all(q.GetNetCode()==0 for q in f.Pads()),'Placement-only pads must remain unassigned')
  board.Add(f);loaded[ref]=f
 dest=OUT/'study/IMU_PLACEMENT_STUDY.kicad_pcb'
 p.SaveBoard(str(dest),board)
 shutil.copyfile(OUT/'inputs'/LIVE.with_suffix('.kicad_pro').name,dest.with_suffix('.kicad_pro'))
 check=p.LoadBoard(str(dest));new=footprints(check)
 require({r:new[r] for r in old}==old,'Existing footprint/pad mutation')
 require(tracks(check)==oldtracks,'Existing copper mutation')
 require(set(new)-set(old)==set(PLACE),'Unexpected footprint delta')
 existing=[describe(f) for f in check.GetFootprints() if f.GetReference() in old]
 added=[describe(f) for f in check.GetFootprints() if f.GetReference() in PLACE]
 collisions=[]
 objects=existing+added+reservations
 for i,a in enumerate(objects):
  for b in objects[i+1:]:
   if a in existing and b in existing:continue
   if overlap(a['courtyard_aabb_mm'],b['courtyard_aabb_mm']):collisions.append([a['ref'],b['ref']])
 edge=[a['ref'] for a in added+reservations if not (50<=a['courtyard_aabb_mm'][0] and 50<=a['courtyard_aabb_mm'][1] and a['courtyard_aabb_mm'][2]<=130 and a['courtyard_aabb_mm'][3]<=96)]
 require({name:sha(ROOT/name) for name in before_live}==before_live,'Live design changed during study')
 require(all(sha(ROOT/name)==h for name,h in guard.items()),'Unrelated local edit changed')
 write('geometry.json',{'existing':existing,'added':added,'reserved_only':reservations,'courtyard_collisions':collisions,'new_outside_outline':edge,'method':'Conservative axis-aligned bounds of native front courtyard graphics including stroke; mounting circles use full bounds. This does not establish routability or assembly access.'})
 write('study_manifest.json',{'schema_version':1,'created_utc':datetime.now(timezone.utc).isoformat(),'status':'mechanical_placement_only','electrically_integrated':False,'fabrication_approved':False,'hardware_tested':False,'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'builder_sha256':sha(Path(__file__)),'input_sha256':{f.relative_to(ROOT).as_posix():sha(f) for f in [OUT/'inputs/LoRa_Boat_Controller_V2.kicad_pcb',OUT/'inputs/LoRa_Boat_Controller_V2.kicad_pro',OUT/'inputs/normalized_baseline.kicad_pcb',SOURCE/'native/netlist.xml',SOURCE/'candidate_manifest.json']},'library_sha256':libhash,'output_sha256':{f.relative_to(ROOT).as_posix():sha(f) for f in [dest,dest.with_suffix('.kicad_pro'),OUT/'geometry.json']},'live_input_sha256':before_live,'unrelated_local_edit_sha256':guard,'preserved_original_footprints':len(old),'preserved_track_and_via_items':len(oldtracks),'added_footprints':len(added),'new_pad_net_code':0,'reserved_only_sites':list(RESERVED),'courtyard_collisions':collisions,'new_outside_outline':edge,'electrical_delta':'None on existing pads/nets/tracks. Twelve unassigned mechanical footprints added only to the isolated study. Frozen electrical candidate remains separate. C43 is only a reserved rectangle, not a PCB component. Zone fill has not been recalculated.'})
 print(json.dumps({'original_footprints':len(old),'added':len(added),'collisions':collisions,'outside':edge}))
if __name__=='__main__':main()
