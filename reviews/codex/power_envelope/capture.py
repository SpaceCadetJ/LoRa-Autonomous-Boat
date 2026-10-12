"""Capture the unchanged V2 power boundary. No CAD generator, board save or hardware."""
from pathlib import Path
import hashlib, json, re, xml.etree.ElementTree as ET, importlib.util
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
NETS={'VBAT_IN','VBAT_FUSED','PGATE','VIN_RAW','VIN_BUCK','SW_3V3','EN_3V3','EN_5V','VBAT_SENSE'}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads((ROOT/p).read_text())
def collect():
    baseline=read('reviews/codex/design_completion/native-review/review.json')['input_manifest']
    for p,h in baseline.items(): assert sha(ROOT/p)==h, 'Live CAD changed: '+p
    paths=['reviews/codex/design_completion/native-review/v2/netlist.xml','reviews/codex/imu_placement/geometry.json','reviews/codex/imu_placement/compare_study.py','docs/V2_REQUIREMENTS.md','hardware/kicad_v2/tools/v2_design.py','reviews/codex/power_envelope/inputs/CP_Elec_8x6.2.kicad_mod']
    source={p:sha(ROOT/p) for p in paths}
    assert source[paths[0]]=='6efc1c8b3daa008a6e21028b5341d95381270798c502e4abc184a42a5e239dd6'
    assert source[paths[1]]=='3fc7577d24ae02b42ab29b3f1c50bf51847ae9b939ae7ff31f6d6a720dfc0465'
    x=ET.parse(ROOT/paths[0]); geometry=read(paths[1])['existing']; g={f['ref']:f for f in geometry}
    nets={n.attrib['name']:[dict(p.attrib) for p in n.findall('node')] for n in x.findall('.//nets/net') if n.attrib['name'].split('/')[-1] in NETS}
    refs={p['ref'] for pins in nets.values() for p in pins}|{'L1','L2'}
    inventory=[]
    for c in x.findall('.//components/comp'):
        ref=c.attrib['ref']
        if ref not in refs: continue
        f=g[ref];a=f['courtyard_aabb_mm'];size=[round(a[2]-a[0],5),round(a[3]-a[1],5)]
        inventory.append({'ref':ref,'schematic_value':c.findtext('value'),'mpn':c.findtext("fields/field[@name='MPN']"),'description':c.findtext('description'),'footprint':c.findtext('footprint'),'pcb_value':f['value'],'xy_mm':f['xy'],'courtyard_aabb_mm':a,'courtyard_size_mm':size,'courtyard_aabb_area_mm2':round(size[0]*size[1],5),'all_pads':f['pads']})
    spec=importlib.util.spec_from_file_location('sexpr',ROOT/paths[2]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    coords=[]
    for block in m.children((ROOT/paths[-1]).read_text()):
        if '(layer "F.CrtYd")' in block:
            coords += [(float(a),float(b)) for a,b in re.findall(r'\((?:start|end) ([-.0-9]+) ([-.0-9]+)\)',block)]
    bounds=[min(p[0] for p in coords),min(p[1] for p in coords),max(p[0] for p in coords),max(p[1] for p in coords)]
    def overlaps(a,b): return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
    studies=[]
    for ref,b,kind in [('C1',bounds,'library courtyard AABB; package compatibility unqualified'),('U2',[-5,-5,5,5],'proposed 10 x 10 mm planning allowance, not a selected footprint'),('U3',[-5,-5,5,5],'proposed 10 x 10 mm planning allowance, not a selected footprint')]:
        xy=g[ref]['xy'];a=[b[0]+xy[0],b[1]+xy[1],b[2]+xy[0],b[3]+xy[1]]
        studies.append({'ref':ref,'basis':kind,'aabb_mm':a,'area_mm2':round((b[2]-b[0])*(b[3]-b[1]),4),'overlapping_existing_courtyard_aabbs':[f['ref'] for f in geometry if f['ref']!=ref and f['courtyard_aabb_mm'] and overlaps(a,f['courtyard_aabb_mm'])]})
    rtop=47000; rbot=6800; k=rbot*1.01/(rtop*.99+rbot*1.01)
    return {'schema':1,'source_revision':'28b216644f0ec2e9098d31abf8b5ed2be4c6ea41','status':'review_only_not_an_integrated_power_design','expected_electrical_delta':{'changed_existing_pins':0,'added_components':0,'changed_copper':0},'hardware_tested':False,'fabrication_approved':False,'cad_input_sha256':baseline,'input_sha256':source,'capturer_sha256':sha(Path(__file__)),'nets':nets,'inventory':inventory,'package_studies':studies,'calculations':{'six_s_full_charge_assumption_v':6*4.2,'ina180_common_mode_headroom_v':round(26-25.2,3),'divider_max_ratio_1percent':k,'divider_at_25_2v_worst_ratio_v':25.2*k,'divider_at_26v_worst_ratio_v':26*k,'shunt_drop_at_3a_v':3*.02,'shunt_power_at_3a_w':3**2*.02,'q1_nominal_gate_clamp_current_at_25_2v_a':(25.2-10)/100000}}
def main():
    import sys
    result=collect();dest=OUT/'evidence.json'
    if '--check' in sys.argv: assert json.loads(dest.read_text())==result,'Captured evidence differs'
    else: dest.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(f"PASS power inventory: {len(result['nets'])} boundary nets, {len(result['inventory'])} references; live CAD unchanged")
if __name__=='__main__': main()
