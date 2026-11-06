"""SENSE-03 portable topology/reference review; no native or hardware actions."""
from pathlib import Path
import argparse, hashlib, json, math, xml.etree.ElementTree as ET
import model
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
ZERO=('candidate_electrical_delta','live_electrical_delta','live_copper_delta')
FALSE=('native_commands_rerun','hardware_accepted','fabrication_approved','procurement_approved','protection_qualified','qualification_ports_implemented','voltage_range_qualified')
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v):(P/n).write_text(v if isinstance(v,str) else json.dumps(v,indent=2)+'\n',encoding='utf-8',newline='\n')
def hashes(m):
    for n,h in m.items():assert sha(ROOT/n)==h,'Changed captured evidence: '+n

def collect():
    baseline=ROOT/'reviews/codex/sensing_filter/packet_manifest.json';old=read(baseline)
    assert sha(baseline)=='f7ea441043a1064f84ece329a4510da85a449d4c59b5efa2cb6ed52e50d3281a'
    expected={**old['input_sha256'],**old['artifact_sha256'],baseline.relative_to(ROOT).as_posix():sha(baseline)}
    inputs=read(P/'input_manifest.json');assert inputs['input_sha256']==expected and len(expected)==658;hashes(expected)
    c=read(P/'contract.json');assert c['revision']=='SENSE-03' and c['native_candidate']=='SENSE-02'
    assert c['baseline_head']==inputs['baseline_head']=='40955cdf2e2ab96b72dd4b113236f712a30c108f'
    assert all(type(c[k]) is int and c[k]==0 for k in ZERO) and all(c[k] is False for k in FALSE)
    path=ROOT/'reviews/codex/sensing_filter/native/netlist.xml';x=ET.parse(path)
    comps={n.get('ref'):n for n in x.findall('./components/comp')};pins={};nets={}
    assert len(comps)==130
    for n in x.findall('./nets/net'):
        nets[n.get('name')]=[]
        for z in n:
            key=z.get('ref')+'.'+z.get('pin');assert key not in pins
            pins[key]={'net':n.get('name'),**z.attrib};nets[n.get('name')].append(key)
    assert len(pins)==433 and len(nets)==122
    for n,expected in c['expected_complete_members'].items():assert sorted(nets[n])==sorted(expected),n
    for n,net in c['additional_pins'].items():assert pins[n]['net']==net,n
    assert pins['U1.16']['pinfunction']=='PA2' and pins['U1.13']['pinfunction']=='VDDA' and pins['U1.12']['pinfunction']=='VSSA'
    assert len(c['components'])==12 and len(c['expected_complete_members'])==4 and len(c['additional_pins'])==8
    identities={}
    for ref,expected in c['components'].items():
        comp=comps[ref];fields={z.get('name'):z.text for z in comp.findall('./fields/field')}
        actual=[comp.findtext('value'),fields['MPN']];assert actual==expected,ref;identities[ref]=actual
    assert identities['R4']==['100k 1%','CRCW0603100KFKEA'] and identities['R5']==['43.2k 1%','CRCW060343K2FKEA']
    assert identities['R31']==['47k','RC0603FR-0747KL'] and identities['R32']==['6.8k','RC0603FR-076K8L']
    a=model.collect();assert a['revision']=='SENSE-03' and a['feedback_reference_cross_check']['guaranteed_vdda_envelope'] is False
    assert all(v is None for v in a['unknown_actual_inputs'].values()) and all(not v['available'] for v in a['actual'].values())
    assert all(a[k]==0 for k in ZERO) and all(a[k] is False for k in FALSE if k in a)
    previous=read(ROOT/'reviews/codex/buck_3v3/analysis.json')['feedback']
    assert math.isclose(a['feedback_reference_cross_check']['output_min_v'],previous['lower_v'],rel_tol=1e-14)
    assert math.isclose(a['feedback_reference_cross_check']['output_max_v'],previous['upper_v'],rel_tol=1e-14)
    return {'revision':'SENSE-03','classification':'captured_topology_and_conditional_reference_review','native_candidate':'SENSE-02',**{k:c[k] for k in ZERO+FALSE},'preserved_input_count':658,'topology':{'source':path.relative_to(ROOT).as_posix(),'sha256':sha(path),'components':identities,'complete_net_members':c['expected_complete_members'],'additional_pins':c['additional_pins'],'checked_pin_count':sum(map(len,c['expected_complete_members'].values()))+len(c['additional_pins'])},'calculations':a,'findings':[{'id':'SENSE-REF','status':'conditional_overlap','finding':'Reference/initial-resistor low corner is below divider high corner at illustrative25.2Vraw; not an actualVDDA bound or measuredclipping.'},{'id':'SENSE-STATE','status':'manufacturer_review_not_hardware_acceptance','finding':'PA2FT stress/reset behavior differs from activeADC range; sequencing, capacitor charge and analog state need separate qualification.'}]}

def outputs(e):
    a=e['calculations'];f=a['feedback_reference_cross_check'];d=a['divider']
    lines=['# SENSE-03 — conditional reference and divider results','','[Review guide](README.md) | [Annotated boundary](reference_boundary.svg) | [Captured evidence](evidence.json)','','## Reference corner, not actual VDDA','',f"Nominal converter feedback output: {f['output_nominal_v']:.9f} V. Reference/initial-resistor corners: {f['output_min_v']:.9f} to {f['output_max_v']:.9f} V. VFB limits apply at VIN=24 V, -40 to125 C; the calculation does not establish the full-line or actual VDDA envelope.",'','Vlow = VFBmin × [1 + R4min/R5max]; Vhigh = VFBmax × [1 + R4max/R5min]. Independent initial resistor tolerances are ±1%. No separate PFM system percentage is added. Distribution drop, drift, aging, leakage, ripple, dropout and transitions are absent.','','## Divider and inverse threshold','',f"Worst initial divider ratio kmax = {d['ratio_max']:.12f}. Margin = reference_floor - reserve - VIN_RAW × kmax. Required R31 nominal > R32 × (1+t32)/(1-t31) × [VIN_RAW/(reference_floor-reserve) - 1], with positive usable reference. Equality has zero margin. These equations select no resistor or protection circuit.",'','| Illustrative VIN_RAW | Worst divider | Conditional margin, zero reserve | Strict R31 threshold |','|---|---|---|---|']
    for v in a['static_cases']:lines.append(f"| {v['inputs']['vin']:.1f} V | {v['adc_max_v']:.9f} V | {v['headroom_v']*1000:.6f} mV | > {v['threshold']['rtop_threshold_ohm']:.6f} ohm |")
    q=a['allocated_reserve_case'];c=a['static_cases'][1]
    lines += ['',f"At25.2 V, conditional overlap is {c['headroom_v']*1000:.6f} mV. Existing-divider zero-reserve crossing: {c['vin_ceiling_v']:.9f} Vraw. The44 V row uses the previous unqualified protected-rail target; it is not an actual transient bound or an ADC stress permission.",'',f"An explicitly allocated50 mV reserve raises the25.2 V nominal R31 threshold to >{q['threshold']['rtop_threshold_ohm']:.6f} ohm. This reserve is not an accepted error budget, and the threshold does not select an available part or establish acquisition/source impedance.",'','## Actual acceptance remains unavailable','','Actual source maximum, transient maximum, minimum VDDA/VREF+, required reserve and power-sequence envelope remain null. Positive illustrative margin does not release a range. A lower resistor ratio alone does not qualify startup/reset/shutdown, analog activation, retained C36 charge or a clamp into an unpowered rail. PA2 FT absolute VDD+4 V must not be confused with active conversion0..VREF+ or a universal off-stateVDD+0.3 V rule.','','## Preservation and next task','',f"Checks cover {e['topology']['checked_pin_count']} pins,12 identities and658 prior hashes. SENSE-02, both converters, ACT-01 populations, disabled qualifications and all live CAD/copper/firmware are preserved. No native commands or hardware checks were rerun.",'','Next specify the ADC interface state/threshold/discharge contract before component selection or a new isolated SENSE-02 amendment. Preserve6S and separateIMU2; no procurement, fabrication or powered-application release.','']
    return {'evidence.json':json.dumps(e,indent=2)+'\n','RESULTS.md':'\n'.join(lines)}

def main():
    parser=argparse.ArgumentParser();g=parser.add_mutually_exclusive_group(required=True)
    for m in ('render','capture','check'):g.add_argument('--'+m,action='store_true')
    args=parser.parse_args();e=collect()
    for n,t in outputs(e).items():
        if args.render:write(n,t)
        else:assert (P/n).read_text(encoding='utf-8')==t,'Stale output: '+n
    if not args.render:
        hashes(read(P/'review_notes.json')['reviewed_sha256']);hashes(read(P/'viewer_check.json')['input_sha256'])
        m={'revision':'SENSE-03','source_revision':read(P/'contract.json')['baseline_head'],'native_candidate':'SENSE-02','input_sha256':read(P/'input_manifest.json')['input_sha256'],'artifact_sha256':{f.relative_to(ROOT).as_posix():sha(f) for f in sorted(P.rglob('*')) if f.is_file() and f.name!='packet_manifest.json' and '__pycache__' not in f.parts},**{k:e[k] for k in ZERO+FALSE}}
        if args.capture:write('packet_manifest.json',m)
        else:assert read(P/'packet_manifest.json')==m,'Packet bytes/coverage changed'
    print('PASS SENSE-03:26pins,12identities,658preserved inputs; conditional review only')
if __name__=='__main__':main()
