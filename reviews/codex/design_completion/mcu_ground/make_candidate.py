"""Review-only local MCU ground escape: move one GND via, detour one NRST track."""
from pathlib import Path
import hashlib, json, shutil, uuid
import pcbnew

OUT=Path(__file__).resolve().parent
SOURCE=OUT.parent/'ground/candidate/LoRa_Boat_Controller_V2.kicad_pcb'
SOURCE_SHA='1b959ee8c2499d2a65359b695a2f70efd5a588f05ffcaf11f32cf9de18d0cce9'
NRST='c9389eec-ff39-4a32-a348-e01f86895af3'
GNDVIA='d5ca61cd-93b8-468a-be3a-6a8f5aa0d429'
PATH=[(87.3061,65.1717),(88.6661,65.1717),(92.35,68.8556),(92.35,69.819),(92.1517,70.0173)]
VIA=(91.65,69.0)
def vec(p):return pcbnew.VECTOR2I(pcbnew.FromMM(p[0]),pcbnew.FromMM(p[1]))
def main():
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=SOURCE_SHA:raise RuntimeError('Changed source candidate')
    pcbnew.KIID.SeedGenerator(20260918)
    b=pcbnew.LoadBoard(str(SOURCE)); tracks={t.m_Uuid.AsString():t for t in b.GetTracks()}
    old=tracks[NRST];code=old.GetNetCode();width=old.GetWidth();b.Remove(old)
    gnd=tracks[GNDVIA];gnd.SetPosition(vec(VIA))
    changes=[gnd]
    for index,(p,q) in enumerate(zip(PATH,PATH[1:])):
        t=pcbnew.PCB_TRACK(b);t.SetLayer(pcbnew.B_Cu);t.SetWidth(width);t.SetNetCode(code);t.SetStart(vec(p));t.SetEnd(vec(q))
        b.Add(t);changes.append(t)
    obstacles=list(b.GetTracks())+[p for fp in b.GetFootprints() for p in fp.Pads()]
    collisions=[]
    for changed in changes:
        for item in obstacles:
            if item.GetNetCode()==changed.GetNetCode():continue
            for layer in (pcbnew.F_Cu,pcbnew.B_Cu):
                if changed.IsOnLayer(layer) and item.IsOnLayer(layer) and changed.GetEffectiveShape(layer).Collide(item.GetEffectiveShape(layer),pcbnew.FromMM(.15)):
                    collisions.append({'changed':changed.m_Uuid.AsString(),'obstacle':item.m_Uuid.AsString(),'net':item.GetNetname(),'layer':b.GetLayerName(layer)})
    print('collision count',len(collisions),flush=True)
    (OUT/'candidate_collisions.json').write_text(json.dumps(collisions,indent=2)+'\n')
    if collisions:return
    dest=OUT/'candidate';dest.mkdir(exist_ok=True)
    for p in SOURCE.parent.iterdir():
        if p.is_file() and (p.suffix in ('.kicad_pro','.kicad_sch','.kicad_sym','.kicad_dru') or p.name in ('fp-lib-table','sym-lib-table')):shutil.copyfile(p,dest/p.name)
        elif p.is_dir() and p.suffix=='.pretty':shutil.copytree(p,dest/p.name,dirs_exist_ok=True)
    reference=OUT.parent/'ground/kicad'
    if reference.exists():shutil.copytree(reference,OUT/'kicad',dirs_exist_ok=True)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones());b.BuildConnectivity()
    path=dest/SOURCE.name;pcbnew.SaveBoard(str(path),b)
    report={'source_sha256':SOURCE_SHA,'candidate_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'removed_track_uuid':NRST,'replacement_nrst_path_mm':PATH,'replacement_width_mm':pcbnew.ToMM(width),'moved_gnd_via_uuid':GNDVIA,'gnd_via_old_mm':[92.0137,68.527],'gnd_via_new_mm':VIA,'native_unconnected_count':b.GetConnectivity().GetUnconnectedCount(True),'fabrication_approved':False}
    (OUT/'candidate_manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
