"""Capture route conflicts and provenance after native placement checks."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter,defaultdict
import hashlib,json,subprocess,sys
import pcbnew as p
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
def write(name,v): (OUT/name).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8',newline='\n')
manifest=json.loads((OUT/'study_manifest.json').read_text())
for name,h in {**manifest['input_sha256'],**manifest['output_sha256'],**manifest['live_input_sha256'],**manifest['unrelated_local_edit_sha256']}.items():
 if sha(ROOT/name)!=h:raise RuntimeError('Changed evidence '+name)
native=json.loads((OUT/'native_manifest.json').read_text())
for name,h in {**native['input_sha256'],**native['output_sha256']}.items():
 if sha(ROOT/name)!=h:raise RuntimeError('Stale native evidence '+name)
if sha(OUT/'native_check.py')!=native['runner_sha256']:raise RuntimeError('Native runner changed')
base=p.LoadBoard(str(OUT/'inputs/LoRa_Boat_Controller_V2.kicad_pcb'))
tracks={t.m_Uuid.AsString():t for t in base.GetTracks()}
oldpads={q.m_Uuid.AsString():(f.GetReference(),q) for f in base.GetFootprints() for q in f.Pads()}
study=p.LoadBoard(str(OUT/'study/IMU_PLACEMENT_STUDY.kicad_pcb'))
newpads={q.m_Uuid.AsString():f.GetReference() for f in study.GetFootprints() if f.GetReference() in {'U9','U10','U11','R36','R37','R38','R39','C38','C39','C40','C41','C42'} for q in f.Pads()}
a=json.loads((OUT/'drc_baseline.json').read_text());b=json.loads((OUT/'drc_study.json').read_text())
def counts(r):return {'errors':sum(v['severity']=='error' for v in r['violations']),'warnings':sum(v['severity']=='warning' for v in r['violations']),'types':dict(Counter(v['type'] for v in r['violations'])),'unconnected_items':len(r['unconnected_items']),'schematic_parity_run':False}
conflicts=defaultdict(lambda:{'new_refs':set(),'types':set()});original_pad_conflicts=[]
for v in b['violations']:
 if v['severity']!='error':continue
 refs={newpads[i['uuid']] for i in v['items'] if i['uuid'] in newpads}
 for item in v['items']:
  if item['uuid'] in tracks:
   conflicts[item['uuid']]['new_refs'].update(refs);conflicts[item['uuid']]['types'].add(v['type'])
  if item['uuid'] in oldpads:original_pad_conflicts.append({'pad':'.'.join([oldpads[item['uuid']][0],oldpads[item['uuid']][1].GetNumber()]),'new_refs':sorted(refs),'type':v['type']})
def xy(v):return [round(p.ToMM(v.x),6),round(p.ToMM(v.y),6)]
records=[]
for uid,v in sorted(conflicts.items()):
 t=tracks[uid];records.append({'uuid':uid,'kind':t.GetClass(),'net':t.GetNetname(),'layer':t.GetLayerName(),'start':xy(t.GetStart()),'end':xy(t.GetEnd()),'new_refs':sorted(v['new_refs']),'finding_types':sorted(v['types'])})
u6=next(f for f in base.GetFootprints() if f.GetReference()=='U6');separation=[]
for n in ['8','22','23','24','12']:
 q=next(q for q in u6.Pads() if q.GetNumber()==n)
 contacts=[{'uuid':uid,'net':t.GetNetname(),'kind':t.GetClass(),'start':xy(t.GetStart()),'end':xy(t.GetEnd())} for uid,t in tracks.items() if (q.HitTest(t.GetStart()) or q.HitTest(t.GetEnd())) and t.IsOnLayer(p.F_Cu)]
 separation.append({'pin':'U6.'+n,'current_net':q.GetNetname(),'position':xy(q.GetPosition()),'endpoint_hits_on_pad':contacts,'scope':'Endpoint hit test only; not a complete connectivity/cut-set proof. 3.3 V power also requires zone review.'})
write('routing_review.json',{'classification':'courtyard_fit_only_copper_conflicts_block_integration','baseline_drc':counts(a),'study_drc':counts(b),'affected_existing_copper_items':len(records),'affected_existing_nets':sorted({v['net'] for v in records}),'copper_conflicts':records,'original_pad_conflicts':original_pad_conflicts,'u6_separation_review':separation,'limits':['New pad net0 can report GND overlaps that an eventual assigned/filled board would resolve. Never waive these findings instead of routing and refilling.','Existing filled zones are frozen and not recalculated.','Zero unconnected entries is non-evidence for new net0 pads. Electrical schematic parity was not run on this mechanical study.','Library resolution warnings in this isolated package are retained.','No source copper has been deleted, moved or reassigned.']})
cli=str(Path(sys.executable).parent/'kicad-cli.exe')
commands=[]
for target,report in [('inputs/LoRa_Boat_Controller_V2.kicad_pcb','drc_baseline.json'),('study/IMU_PLACEMENT_STUDY.kicad_pcb','drc_study.json')]:
 commands.append([cli,'pcb','drc','--format','json','--severity-all','--all-track-errors','-o',(OUT/report).relative_to(ROOT).as_posix(),(OUT/target).relative_to(ROOT).as_posix()])
files=[f for f in OUT.rglob('*') if f.is_file() and f.name not in {'packet_manifest.json'} and f.suffix not in {'.kicad_prl','.pyc'}]
write('packet_manifest.json',{'schema_version':1,'created_utc':datetime.now(timezone.utc).isoformat(),'status':'placement_fit_only_copper_conflicts_block_integration','native_version':native['version'],'native_commands':[v['argv'] for v in native['commands']],'input_sha256':manifest['live_input_sha256'],'artifact_sha256':{f.relative_to(ROOT).as_posix():sha(f) for f in sorted(files)},'preservation':json.loads((OUT/'preservation.json').read_text()),'baseline_drc':counts(a),'study_drc':counts(b),'courtyard_collisions':manifest['courtyard_collisions'],'new_outside_outline':manifest['new_outside_outline'],'electrically_integrated':False,'whole_board_6s_fit_verified':False,'fabrication_approved':False,'hardware_tested':False})
print(json.dumps({'before':counts(a),'after':counts(b),'affected_copper':len(records),'affected_nets':sorted({v['net'] for v in records})}))
