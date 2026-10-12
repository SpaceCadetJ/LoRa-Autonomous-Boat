"""Capture candidate pad/courtyard geometry with KiCad; not an assembly approval."""
from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parent

def collect():
    import pcbnew
    d=P/'source/hardware/kicad_v2/LoRa_Boat_Controller_V2.pretty';entries=[]
    for ref,name in [('F1','Fuse_Littelfuse-NANO2-451_453'),('D1','D_SMB'),('D12','D_SMB'),('C1','CP_Elec_8x10.5'),('C2','C_1210_3225Metric')]:
        f=pcbnew.FootprintLoad(str(d.resolve()),name);assert f
        pads=[]
        for pad in f.Pads():
            pos=pad.GetPosition();size=pad.GetSize();pads.append({'number':pad.GetNumber(),'x_mm':pcbnew.ToMM(pos.x),'y_mm':pcbnew.ToMM(pos.y),'width_mm':pcbnew.ToMM(size.x),'height_mm':pcbnew.ToMM(size.y)})
        assert sorted(x['number'] for x in pads)==['1','2']
        boxes=[g.GetBoundingBox() for g in f.GraphicalItems() if g.GetLayer()==pcbnew.F_CrtYd]
        xmin=min(pcbnew.ToMM(b.GetLeft()) for b in boxes);xmax=max(pcbnew.ToMM(b.GetRight()) for b in boxes);ymin=min(pcbnew.ToMM(b.GetTop()) for b in boxes);ymax=max(pcbnew.ToMM(b.GetBottom()) for b in boxes)
        entries.append({'ref':ref,'footprint':name,'sha256':hashlib.sha256((d/(name+'.kicad_mod')).read_bytes()).hexdigest(),'pads':pads,'courtyard_bounds_mm':[xmin,ymin,xmax,ymax],'courtyard_rectangle_area_mm2':round((xmax-xmin)*(ymax-ymin),4)})
    return {'schema':1,'scope':'Captured library pad numbering and courtyard bounds only; not footprint manufacturer matching, fit, stencil or thermal approval','kicad_version':pcbnew.Version(),'parts':entries,'sum_rectangle_area_mm2':sum(e['courtyard_rectangle_area_mm2'] for e in entries),'excluded':['J1 existing connector','inter-part routing/clearance','TVS loop','thermal copper spreading','downstream converters'],'pcb_updated':False,'thermal_planning':{'assumed_ambient_c':60,'chosen_junction_design_target_c':125,'diode_dc_current_a':1,'st_loss_model_w':.6+.027,'required_theta_ja_at_assumptions_c_per_w':(125-60)/(.6+.027),'st_theta_jl_c_per_w':25,'is_measured':False}}
if __name__=='__main__':
    import sys
    result=collect();out=P/'package_budget.json'
    if '--check' in sys.argv:assert json.loads(out.read_text())==result
    else:out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('Candidate library geometry checked; no physical or thermal qualification.')
