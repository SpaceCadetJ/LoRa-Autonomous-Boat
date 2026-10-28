"""Capture ACT-12 contract, topology and portable viewer; never invoke CAD."""
from pathlib import Path
from html import escape
import argparse, hashlib, json
import model
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DELTAS=['candidate_electrical_delta','live_electrical_delta','live_copper_delta']
FALSE=['native_commands_rerun','parts_selected','native_accepted','hardware_accepted','fabrication_approved','qualification_ports_implemented','receiver_contract_closed','timing_qualified']
def read(n):return json.loads((HERE/n).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,s):(HERE/n).write_text(s,encoding='utf-8',newline='\n')
def collect():
    c=read('contract.json')
    assert all(c[k]==0 for k in DELTAS) and all(c[k] is False for k in FALSE)
    assert c['total_allocated_ns']==400 and c['downstream_allocated_ns']==245
    assert c['missing_qualifications_default']=='disabled'
    assert all(c[k] is True for k in ['indefinite_hold_required','healthy_interval_restarts_on_fault','fresh_ack_after_fault_required','existing_act04_normal_disarm_retains_READY'])
    assert [(p['port'],p['role']) for p in c['receiver_profiles']]==[('J2','ESC'),('J3','servo')]
    a=model.collect(ROOT)
    a['receiver_profiles']=[dict(port=p['port'],role=p['role'],missing_fields=model.missing_evidence(p['evidence']),record_complete=not model.missing_evidence(p['evidence']),hardware_accepted=False) for p in c['receiver_profiles']]
    assert all(not p['record_complete'] for p in a['receiver_profiles']),'New evidence needs a separate reviewed packet'
    s=read('scenarios.json');assert s['hardware_tests_run'] is False
    a['scenarios']=s['scenarios']
    assert [s['id'] for s in a['scenarios']]==['ramp','pulse','dwell','restore','remote']
    a['source_sha256'].update({(HERE/n).relative_to(ROOT).as_posix():sha(HERE/n) for n in ['contract.json','scenarios.json','build_packet.py']})
    return a

def outputs(a):
    channels=a['topology']['channels'];timing=a['timing']
    lines=['# ACT-12 - verified connector paths and conditional timing','', '[Guide](README.md) | [Explorer](index.html) | [Future measurement plan](MEASUREMENT_PLAN.md)','',
    '## Captured native topology','',f"Checked {len(a['topology']['checked_pin_nets'])} explicit pin memberships, four complete output signal nets and {len(a['topology']['checked_values'])} component values against ACT-04 XML. These are captured schematic facts, not a new native or board test.",'',
    '| Channel | Driver through series resistor | Connector signal / pull / ESD | Supply / ground |','|---|---|---|---|']
    for c in channels:lines.append(f"| {c['role']} | {c['driver_pin']} through {c['series_component']} ({c['series_value']}) | {c['signal_pin']}; {c['pulldown_component']} ({c['pulldown_value']}); {c['protection_component']} ({c['protection_value']}) | {c['supply_pin']} {c['supply_net']}; {c['ground_pin']} GND |")
    lines+=['','U4 VCCB remains /Power/+5V_BUCK before D4. J2/J3 are schematic pin identities; harness orientation and real receiver identities remain unverified.','',
    '## Preserve the existing time allocation','',
    '100 ns sensing + 55 ns detector + 245 ns for the entire downstream path = **400 ns**. Origin: the upstream rail reaches the allocated overdrive point, under the inherited conditional monotone-ramp assumptions. Endpoint: a physical inhibit boundary that remains unqualified. This is not a measured connector-low or actuator-stop deadline. The separate 100 us handover allocation permits no undefined-output interval.','',
    '| Screen | Overdrive point (V) | Validity boundary (V) | Headroom (mV) | Zero-margin slew ceiling (V/us) |','|---|---:|---:|---:|---:|']
    for label in ['UV','OV']:
        t=timing[label];lines.append(f"| {label} | {t['overdrive_V']:.9f} | {t['valid_boundary_V']:.3f} | {t['headroom_V']*1000:.6f} | {t['maximum_slew_V_per_us']:.9f} |")
    lines+=['','Slew must be strictly below the ceiling with explicit margin. The UV boundary comes from ACT-09 (3.005 V), while OV retains ACT-07 (3.6 V). These are model applicability boundaries, not measured failure thresholds.','',
    '| Slew (V/us) | UV residual (mV) | OV residual (mV) | Arithmetic only |','|---|---:|---:|---|']
    for uv,ov in zip(timing['UV']['cases'],timing['OV']['cases']):
        label='Both margins positive' if uv['conditional_margin_positive'] and ov['conditional_margin_positive'] else 'At least one allocation exhausted'
        lines.append(f"| {uv['slew_V_per_us']:.2f} | {uv['residual_V']*1000:.6f} | {ov['residual_V']*1000:.6f} | {label} |")
    lines+=['','`residual = headroom - slew * 0.4 us`. Positive residual does not qualify the actual ramp response, partial-power behavior, output waveform, receiver pulse rejection or physical stop.','',
    '## Receiver evidence remains incomplete','', '| Port | Missing field groups | Record completeness | Hardware acceptance |','|---|---:|---|---|']
    for p in a['receiver_profiles']:lines.append(f"| {p['port']} / {p['role']} | {len(p['missing_fields'])} | Incomplete | Unavailable |")
    lines+=['','Required fields: '+', '.join('`'+f+'`' for f in model.MEASUREMENT_FIELDS)+'.','',
    'Completeness is a documentation check only. Neither populated fields nor the source-only topology check grant circuit, fabrication or hardware acceptance. No measurement rows have been executed.','',
    'The inherited pulldowns require bounds for receiver thresholds, feed, capacitance and ground offsets. A truncated PWM pulse includes its pre-fault high interval. No universal no-pulse response or stop command is assumed. Fault recovery must clear READY and require fresh acknowledgement; normal disarm retains READY under ACT-04.','']
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="980" viewBox="0 0 1280 980"><rect width="1280" height="980" fill="#f4f7fb"/><style>text{font-family:Arial,sans-serif;fill:#172638}.h{font-size:28px;font-weight:bold}.t{font-size:20px;font-weight:bold}.s{font-size:17px}.sub{font-size:18px;fill:#425874}.box{fill:white;stroke:#9bb3c9;stroke-width:2}.hold{fill:#fff5e7;stroke:#b86e12;stroke-width:2;stroke-dasharray:8 5}.wire{fill:none;stroke:#246789;stroke-width:3}</style>']
    def text(x,y,s,c='s'):svg.append(f'<text x="{x}" y="{y}" class="{c}">{escape(s)}</text>')
    def box(x,y,w,h,c='box'):svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" class="{c}"/>')
    text(40,48,'ACT-12 | Define the fault response at the actuator connector','h')
    text(40,80,'Verified ACT-04 signal paths | No circuit change | Receiver interpretation and stop behavior unresolved','sub')
    box(40,110,1200,65,'hold');text(58,138,'An inactive driver does not establish a low signal, rejected pulse or stopped actuator.','t');text(58,162,'400 ns remains a conditional inhibit allocation. Actual connector and receiver limits still need evidence.')
    for y,mc,pin,r,pull,d,j,role,power in [(215,'PC6 / U1.37','5 -> 8','R10','R11','D10','J2','ESC','BEC_IN'),(365,'PA8 / U1.41','4 -> 1','R12','R13','D11','J3','Servo','VSERVO')]:
        for x,w in [(40,215),(315,200),(575,150),(785,240)]:box(x,y,w,90)
        text(58,y+32,mc,'t');text(58,y+66,'PWM input')
        text(333,y+32,'U4 TXU0102','t');text(333,y+66,'Pins '+pin)
        text(593,y+32,r+' 100 ohm','t');text(593,y+66,'Series resistor')
        text(803,y+32,j+'.1 '+role+' signal','t');text(803,y+66,pull+' 10k + '+d+' to GND')
        svg.append(f'<path class="wire" d="M255 {y+45}H315 M515 {y+45}H575 M725 {y+45}H785 M1025 {y+45}H1070"/>')
        box(1070,y,170,90,'hold');text(1086,y+31,'Receiver','t');text(1086,y+64,'Unidentified')
        text(785,y+119,j+'.2 '+power+'; '+j+'.3 GND')
    box(40,530,1200,65);text(58,559,'Preserve U4 VCCB = +5V_BUCK before D4; BEC_ONLY / ONBOARD remain exclusive.','t');text(58,583,'Pin numbers are schematic evidence. Physical harness orientation and receiver-ground behavior require verification.')
    for x,title,ls in [(40,'1. Fast inhibit',['100 ns + 55 ns + 245 ns = 400 ns','After the allocated overdrive point.','Whole downstream path shares 245 ns.','Actual waveform remains unqualified.']),(450,'2. Continuous disabled hold',['No gap after island hold-up expires.','Bound every allowed feed and dwell.','High-Z alone does not mean low.','Receiver loss policy remains unknown.']),(860,'3. Fresh rearm',['Fault must clear retained READY.','New health interval after any bounce.','Fresh ACK with ARM low; then ARM.','Normal disarm is a separate case.'])]:
        box(x,635,380,180);text(x+18,668,title,'t')
        for i,l in enumerate(ls):text(x+18,701+i*29,l)
    box(40,855,1200,99,'hold');text(58,885,'Next evidence: exact ESC/BEC/servo, voltage/pulse/loss limits, readiness and harness.','t');text(58,916,'No hardware test or application release. Independent next packet: C11 identity and VSERVO reservoir/transients.');text(58,942,'Preserve 6S, both converters and all default-disabled qualifications.')
    svg.append('</svg>')
    html=(HERE/'explorer.template.html').read_text(encoding='utf-8').replace('@@DATA@@',json.dumps(a).replace('</','<\\/'))
    return {'analysis.json':json.dumps(a,indent=2)+'\n','RESULTS.md':'\n'.join(lines),'v2_connector_fault_contract.svg':'\n'.join(svg)+'\n','index.html':html}

def main():
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    for n in ['render','capture','check']:g.add_argument('--'+n,action='store_true')
    args=p.parse_args();a=collect();inputs=read('input_manifest.json')
    for n,h in inputs['input_sha256'].items():assert sha(ROOT/n)==h,'Preserved input changed: '+n
    for n,s in outputs(a).items():
        if args.render:write(n,s)
        else:assert (HERE/n).read_text(encoding='utf-8')==s,'Stale generated output: '+n
    if not args.render:
        for n,h in read('review_notes.json')['reviewed_sha256'].items():assert sha(HERE/n)==h,'Stale review: '+n
        for n,h in read('viewer_check.json')['input_sha256'].items():assert sha(ROOT/n)==h,'Stale viewer: '+n
        artifacts={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='packet_manifest.json' and '__pycache__' not in p.parts}
        c=read('contract.json');m={k:c[k] for k in DELTAS+FALSE};m.update(revision='ACT-12',source_revision=inputs['baseline_head'],input_sha256=inputs['input_sha256'],artifact_sha256=artifacts)
        if args.capture:write('packet_manifest.json',json.dumps(m,indent=2)+'\n')
        else:assert read('packet_manifest.json')==m,'Changed packet bytes'
    print(f"PASS ACT-12 deterministic contract and {len(inputs['input_sha256'])} preserved inputs; no hardware acceptance")
if __name__=='__main__':main()
