"""Verify that the candidate changes only the declared local copper items."""
from collections import Counter
from pathlib import Path
import hashlib,json,math
import pcbnew
from make_candidate import SOURCE,OUT,NRST,GNDVIA,PATH
candidate=OUT/'candidate'/SOURCE.name
a=pcbnew.LoadBoard(str(SOURCE));b=pcbnew.LoadBoard(str(candidate))
def fp_signature(board):
    return sorted((f.m_Uuid.AsString(),f.GetReference(),f.GetValue(),f.GetFPIDAsString(),str(f.GetPosition()),f.GetOrientationDegrees(),f.GetLayer(),
      sorted((p.m_Uuid.AsString(),p.GetNumber(),p.GetNetname(),str(p.GetPosition()),str(p.GetSize()),str(p.GetDrillSize()),p.GetOrientationDegrees(),str(p.GetLayerSet().FmtBin())) for p in f.Pads())) for f in board.GetFootprints())
def track_signature(t):
    if t.GetClass()=='PCB_VIA':return (t.GetClass(),t.GetNetname(),str(t.GetPosition()),t.GetWidth(pcbnew.F_Cu),t.GetDrill(),t.GetLayerSet().FmtBin())
    return (t.GetClass(),t.GetNetname(),str(t.GetStart()),str(t.GetEnd()),t.GetWidth(),t.GetLayer())
at={t.m_Uuid.AsString():t for t in a.GetTracks()};bt={t.m_Uuid.AsString():t for t in b.GetTracks()}
removed=sorted(set(at)-set(bt));added=sorted(set(bt)-set(at));changed=sorted(k for k in set(at)&set(bt) if track_signature(at[k])!=track_signature(bt[k]))
assert fp_signature(a)==fp_signature(b),'Footprint or pad mutation'
assert removed==[NRST] and changed==[GNDVIA] and len(added)==4,'Unexpected track edits'
assert all(bt[k].GetNetname()=='NRST' and bt[k].GetLayer()==pcbnew.B_Cu and bt[k].GetWidth()==pcbnew.FromMM(.25) for k in added)
def counts(path):
    r=json.loads(path.read_text())
    return {'violations':dict(Counter((e['severity'] for e in r['violations']))),'unconnected_items':len(r['unconnected_items']),'schematic_parity':len(r['schematic_parity']),'violation_types':dict(Counter(e['type'] for e in r['violations']))}
before=counts(OUT.parent/'ground/drc_after.json');after=counts(OUT/'drc_after.json')
assert before['violations']==after['violations'] and before['violation_types']==after['violation_types']
assert before['schematic_parity']==after['schematic_parity']==212
assert before['unconnected_items']==1 and after['unconnected_items']==0
old=at[NRST]
old_length=math.dist([pcbnew.ToMM(old.GetStart().x),pcbnew.ToMM(old.GetStart().y)],[pcbnew.ToMM(old.GetEnd().x),pcbnew.ToMM(old.GetEnd().y)])
report={'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'candidate_sha256':hashlib.sha256(candidate.read_bytes()).hexdigest(),'footprints_and_all_pad_nets_positions_sizes_drills_unchanged':True,'footprint_count':len(list(a.GetFootprints())),'removed_track_uuids':removed,'added_track_uuids':added,'changed_via_uuids':changed,'original_nrst_segment_length_mm':old_length,'replacement_nrst_length_mm':sum(math.dist(p,q) for p,q in zip(PATH,PATH[1:])),'native_before':before,'native_after':after,'fabrication_approved':False}
(OUT/'comparison.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
