"""Render VSERVO-01 review evidence; no CAD generation or live amendment."""
from pathlib import Path
from html import escape
import argparse, hashlib, json, math
import model, verify_candidate
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
FLAGS=['hardware_accepted','fabrication_approved','procurement_approved','reservoir_qualified','qualification_ports_implemented']
def read(n):return json.loads((HERE/n).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,s):(HERE/n).write_text(s,encoding='utf-8',newline='\n')
def collect():
    c=read('expected_contract.json')
    assert all(c[k] is False for k in FLAGS)
    assert c['candidate_identity_changes']==1 and c['candidate_electrical_membership_delta']==0
    assert c['live_electrical_delta']==c['live_copper_delta']==0 and c['native_commands_rerun'] is True
    native=verify_candidate.collect();assert read('validation.json')==native
    a=model.collect()
    fixed={'initial_voltage_V':5.0,'allocated_floor_V':4.5,'allocated_ceiling_V':5.5,'current_deficit_A':0.5,'duration_s':100e-6,'allocated_constant_esr_ohm':0.2,'C12_credited_capacitance_F':0.0}
    assert all(a['parameters'][k]==v for k,v in fixed.items()),'Revise fixed diagram/report allocations with model'
    assert a['parameters']['net_retained_energies_J']==[0.1e-3,0.25e-3,1e-3]
    assert all(math.isclose(c['capacitance_F'],v) for c,v in zip(a['cases'],[56e-6,80e-6,100e-6])) and len(a['cases'])==3
    assert math.isclose(a['cases'][1]['load_step']['voltage_V'],4.275) and math.isclose(a['required_C_step']['required_capacitance_F'],125e-6)
    assert math.isclose(a['cases'][1]['energy_cases'][0]['allocated_energy_budget_J'],0.210e-3)
    a['native_summary']={k:native[k] for k in ['status','electrical_delta','source_preservation','native_erc','geometry']}
    a['input_sha256']={(HERE/n).relative_to(ROOT).as_posix():sha(HERE/n) for n in ['model.py','source_review.json','expected_contract.json','validation.json','build_packet.py']}
    return a

def outputs(a):
    p=a['parameters'];delta=a['native_summary']['electrical_delta']
    lines=['# VSERVO-01 - native identity correction and reservoir limits','', '[Guide](README.md) | [Explorer](index.html) | [Source conditions](source_review.json) | [Native checks](validation.json)','',
    '## Captured native result','',
    f"KiCad 9.0.7 exports retain all **{delta['physical_pin_memberships_preserved']} physical pin memberships** and all **{delta['preserved_other_component_identities']} other component records**. C11 alone changes identity, value, datasheet, description and footprint. C11.1 remains VSERVO; C11.2 remains GND. ERC reports **zero errors and one unchanged U6 AD0 warning**. Both converter sheets, actuator sheets, D4/D9 DNP state and exclusive source population contract are preserved.",'',
    'The explicit candidate land has two 3.2 x 1.6 mm pads at x = +/-2.5 mm, 1.8 mm inner gap and 8.2 mm outer span. Native pcbnew inspection and portable geometry checks agree. This is an isolated schematic/library amendment: no PCB layout or DRC, assembly, procurement or hardware qualification is claimed. The separate IMU2 candidate is not integrated.','',
    '## Allocated load-step example','',
    f"Start {p['initial_voltage_V']:g} V; floor {p['allocated_floor_V']:g} V; capacitor current deficit {p['current_deficit_A']:g} A for {p['duration_s']*1e6:g} us; allocated constant series resistance {p['allocated_constant_esr_ohm']:g} ohm. These are illustrative allocations, not measured loads, receiver limits or an ESR specification. The catalog 360 mOhm value is AC impedance and is not used as ESR.",'',
    '| Capacitance illustration | Capacitive drop (V) | ESR allocation drop (V) | Endpoint (V) | Margin to allocated floor (V) |','|---|---:|---:|---:|---:|']
    for c in a['cases']:
        s=c['load_step'];lines.append(f"| {c['capacitance_F']*1e6:g} uF | {s['capacitive_drop_V']:.6f} | {s['esr_drop_V']:.6f} | {s['voltage_V']:.6f} | {s['headroom_V']:.6f} |")
    lines+=['',f"All three illustrative load cases exhaust the allocated floor. Strictly positive arithmetic margin needs **C > {a['required_C_step']['required_capacitance_F']*1e6:g} uF** under the fixed assumptions. Equality gives zero margin; it does not pass. This threshold is not a part recommendation.",'',
    p['source_conditions']+' The 100 uF case is nominal reference only. C12 receives zero effective-capacitance credit. None of the cases establishes an all-temperature, in-operation bound.','',
    '## Net returned energy','',
    'The ideal capacitor endpoint is sqrt(V_start^2 + 2 E_net / C). Net energy must already account for source contribution, load absorption and any sink. The endpoint omits ESR/inductive peaks and is not a transient peak prediction.','',
    '| C (uF) | Net energy (mJ) | Ideal endpoint (V) | Margin to allocated 5.5 V ceiling (V) |','|---|---:|---:|---:|']
    for c in a['cases']:
        for e in c['energy_cases']:lines.append(f"| {c['capacitance_F']*1e6:g} | {e['net_retained_energy_J']*1e3:g} | {e['voltage_V']:.6f} | {e['headroom_V']:.6f} |")
    lines+=['','| Net energy (mJ) | Equality capacitance threshold (uF) |','|---|---:|']
    for e in a['required_C_energy']:lines.append(f"| {e['net_retained_energy_J']*1e3:g} | {e['required_capacitance_F']*1e6:.6f} |")
    lines+=['','Positive margin requires capacitance strictly greater than the threshold and valid assumptions. At 80 uF the allocated 5 to 5.5 V energy budget is 0.210 mJ. No regenerative event or receiver voltage envelope has been measured.','',
    '## Remaining circuit obligation','',
    'D4/D9 forward-feed the rail; neither defines a controlled energy sink. The 16 V capacitor rating does not establish the permitted servo voltage, reverse-voltage immunity or pulse/ripple lifetime. The next packet must bound a sink or source-return path for both exclusive source populations, with unknown receiver/source/energy/inductance inputs explicitly unavailable. Native electrical checks, arithmetic tests and viewer checks do not release ordering or powered use.','']
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="980" viewBox="0 0 1280 980"><rect width="1280" height="980" fill="#f4f7fb"/><style>text{font-family:Arial,sans-serif;fill:#172638}.h{font-size:28px;font-weight:bold}.t{font-size:20px;font-weight:bold}.s{font-size:17px}.sub{font-size:18px;fill:#425874}.box{fill:white;stroke:#9bb3c9;stroke-width:2}.hold{fill:#fff5e7;stroke:#b86e12;stroke-width:2;stroke-dasharray:8 5}.wire{fill:none;stroke:#246789;stroke-width:3}.pad{fill:#b67420;stroke:#714614;stroke-width:1}</style>']
    def text(x,y,s,c='s'):svg.append(f'<text x="{x}" y="{y}" class="{c}">{escape(s)}</text>')
    def box(x,y,w,h,c='box'):svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" class="{c}"/>')
    text(40,48,'VSERVO-01 | C11 identity, land pattern and energy boundary','h')
    text(40,80,'Native isolated candidate | 429 pin memberships preserved | Live PCB and purchasing package unchanged','sub')
    box(40,107,1200,66,'hold');text(58,136,'EEEFK1C101P is a confirmed 100 uF / 16 V candidate, with explicit Panasonic lands.','t');text(58,161,'The higher capacitor rating does not raise the receiver voltage limit. Reservoir and assembly remain unqualified.')
    box(40,205,300,92);text(58,237,'ONBOARD: +5V_BUCK','t');text(58,271,'D4 populated; D9 DNP')
    box(40,322,300,92);text(58,354,'BEC_ONLY: BEC_IN','t');text(58,388,'D9 populated; D4 DNP')
    svg.append('<path class="wire" d="M340 251H430V368H340 M430 310H480 M800 310H900"/>')
    box(480,254,320,110);text(498,286,'VSERVO / J3.2 / TP4.1','t');text(498,320,'C11.1 + ; C11.2 GND');text(498,346,'C12: no effective-capacitance credit')
    box(900,254,340,110,'hold');text(918,286,'Servo + harness: unknown','t');text(918,319,'Load steps and returned energy');text(918,346,'No accepted sink / clamp path')
    text(480,403,'Forward source feed is not a controlled energy sink.','t')
    box(40,452,590,233);text(58,484,'Land correction | top view, dimensions in mm','t')
    for x,cx,pw,gap,span,title in [(185,2.7,3.5,1.9,8.9,'Existing stock'),(475,2.5,3.2,1.8,8.2,'Candidate')]:
        scale=22
        svg.append(f'<circle cx="{x}" cy="568" r="69.3" fill="none" stroke="#91a9ba" stroke-width="2"/>')
        for pad,center in [(1,-cx),(2,cx)]:
            svg.append(f'<rect x="{x+(center-pw/2)*scale}" y="550.4" width="{pw*scale}" height="35.2" class="pad"/>')
            text(x+center*scale-5,574,str(pad))
        text(x-110,534,'+');text(x-100,654,title,'t');text(x-114,678,f'{pw} x 1.6; gap {gap}; span {span}')
    box(660,452,580,233);text(678,484,'What native verification establishes','t')
    for i,s in enumerate(['One C11 identity / footprint amendment; zero pin changes.','Both converters and exclusive populations preserved.','ERC: zero errors, same AD0 warning.','Native pad inspection matches selected dimensions.','No PCB fit, stencil, assembly or reservoir acceptance.']):text(678,521+i*32,s)
    box(40,720,590,144);text(58,752,'Load step | illustrative allocations','t');text(58,783,'5 V start; 0.5 A deficit for 100 us; allocated R = 0.2 ohm');text(58,812,'80 uF endpoint = 4.275 V < allocated 4.5 V floor');text(58,841,'C > 125 uF needed for positive arithmetic margin.')
    box(660,720,580,144);text(678,752,'Returned energy | ideal endpoint, not peak','t');text(678,783,'80 uF: only 0.210 mJ from 5 V to allocated 5.5 V');text(678,812,'Source, load, sink, ripple and inductance remain unknown.');text(678,841,'56 / 80 uF are source-conditioned illustrations only.')
    box(40,898,1200,62,'hold');text(58,926,'Next: bound the VSERVO energy sink and reverse-voltage path for both source populations.','t');text(58,951,'Keep missing permissions disabled. Preserve 6S, both converters and the separate IMU2 review lineage.')
    svg.append('</svg>')
    html=(HERE/'explorer.template.html').read_text(encoding='utf-8').replace('@@DATA@@',json.dumps(a).replace('</','<\\/'))
    return {'analysis.json':json.dumps(a,indent=2)+'\n','RESULTS.md':'\n'.join(lines),'v2_vservo_reservoir.svg':'\n'.join(svg)+'\n','index.html':html}

def main():
    parser=argparse.ArgumentParser();g=parser.add_mutually_exclusive_group(required=True)
    for n in ['render','capture','check']:g.add_argument('--'+n,action='store_true')
    args=parser.parse_args();a=collect();inputs=read('input_manifest.json')
    for n,h in inputs['input_sha256'].items():assert sha(ROOT/n)==h,'Preserved input changed: '+n
    for n,s in outputs(a).items():
        if args.render:write(n,s)
        else:assert (HERE/n).read_text(encoding='utf-8')==s,'Stale output: '+n
    if not args.render:
        for n,h in read('review_notes.json')['reviewed_sha256'].items():assert sha(HERE/n)==h,'Stale review: '+n
        for n,h in read('viewer_check.json')['input_sha256'].items():assert sha(ROOT/n)==h,'Stale viewer: '+n
        artifacts={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='packet_manifest.json' and '__pycache__' not in p.parts}
        c=read('expected_contract.json');m={k:c[k] for k in FLAGS+['candidate_identity_changes','candidate_electrical_membership_delta','live_electrical_delta','live_copper_delta','native_commands_rerun']}
        m.update(revision='VSERVO-01',source_revision=inputs['baseline_head'],input_sha256=inputs['input_sha256'],artifact_sha256=artifacts)
        if args.capture:write('packet_manifest.json',json.dumps(m,indent=2)+'\n')
        else:assert read('packet_manifest.json')==m,'Changed packet bytes'
    print(f"PASS VSERVO-01 native replay, conditional reservoir and {len(inputs['input_sha256'])} preserved inputs; no hardware acceptance")
if __name__=='__main__':main()
