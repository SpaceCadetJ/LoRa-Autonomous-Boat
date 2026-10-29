"""VSERVO-02 captured topology and deterministic review; never generates CAD."""
from pathlib import Path
from html import escape
import argparse,hashlib,json,math,xml.etree.ElementTree as ET
import model
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DELTAS=['candidate_electrical_delta','live_electrical_delta','live_copper_delta']
FALSE=['native_commands_rerun','parts_selected','hardware_accepted','fabrication_approved','procurement_approved','protection_qualified','qualification_ports_implemented']
def read(n):return json.loads((HERE/n).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,s):(HERE/n).write_text(s,encoding='utf-8',newline='\n')
def collect():
    c=read('contract.json');assert c['revision']=='VSERVO-02' and c['baseline_candidate']=='VSERVO-01'
    assert all(c[k]==0 for k in DELTAS) and all(c[k] is False for k in FALSE)
    assert c['source_variants']==['BEC_ONLY','ONBOARD'] and c['missing_qualifications_default']=='disabled'
    netpath=ROOT/'reviews/codex/vservo_reservoir/native/netlist.xml';t=ET.parse(netpath)
    pins={(n.get('ref'),n.get('pin')):net.get('name') for net in t.findall('./nets/net') for n in net.findall('node')}
    expected={('D4','1'):'VSERVO',('D4','2'):'/Power/+5V_BUCK',('D9','1'):'VSERVO',('D9','2'):'/BEC_IN',('C11','1'):'VSERVO',('C11','2'):'GND',('C12','1'):'VSERVO',('C12','2'):'GND',('J2','2'):'/BEC_IN',('J2','3'):'GND',('J3','2'):'VSERVO',('J3','3'):'GND',('TP4','1'):'VSERVO',('U3','17'):'GND'}
    assert all(pins.get(k)==v for k,v in expected.items())
    assert {k for k,v in pins.items() if v=='VSERVO'}=={('C11','1'),('C12','1'),('D4','1'),('D9','1'),('J3','2'),('TP4','1')}
    assert t.findtext('./components/comp[@ref="U3"]/value')=='LM76003RNPR'
    pop=json.loads((ROOT/'reviews/codex/vservo_reservoir/population_contract.json').read_text(encoding='utf-8'))
    assert pop['variants']['BEC_ONLY']['D4']=='DNP' and pop['variants']['BEC_ONLY']['D9']=='POPULATE'
    assert pop['variants']['ONBOARD']['D4']=='POPULATE' and pop['variants']['ONBOARD']['D9']=='DNP'
    assert pop['dual_population_allowed'] is False and pop['default_released_variant'] is None
    a=model.collect()
    fixed={'start_V':5.0,'normal_max_V':5.1,'turnon_min_V':5.2,'turnon_max_V':5.3,'overshoot_V':0.1,'allowed_max_V':5.5,'C_F':80e-6,'return_current_A':0.5,'delay_s':10e-6,'net_event_energies_J':[1e-3,0.1e-3],'events_per_s':10.0}
    assert all(a['parameters'][k]==v for k,v in fixed.items()),'Update fixed diagram/report examples with model'
    assert all(x['status']=='unavailable' and all(v is None for v in x['inputs'].values()) for x in a['actual'].values())
    assert math.isclose(a['delay_case']['rise_V'],.0625) and math.isclose(a['sink_cases'][0]['result']['capacitor_energy_window_J'],.210e-3)
    assert math.isclose(a['sink_cases'][0]['result']['minimum_event_sink_J'],.790e-3) and math.isclose(a['sink_cases'][0]['result']['mean_local_sink_W'],.010)
    assert a['window_cases'][0]['result']['off_margin_V']==.1 and a['window_cases'][0]['result']['protection_margin_V']==.1
    assert a['window_cases'][1]['result']['protection_margin_V']==0
    a['topology']={'captured_candidate':'VSERVO-01','checked_pin_nets':{r+'.'+n:v for (r,n),v in expected.items()},'VSERVO_members':sorted(r+'.'+n for (r,n),v in pins.items() if v=='VSERVO'),'U3_value':'LM76003RNPR','U3_SYNC_MODE_pin17':'GND','source_population_preserved':True,'native_commands_rerun':False}
    files=[HERE/n for n in ['contract.json','sources.json','model.py','build_packet.py']]+[netpath,ROOT/'reviews/codex/vservo_reservoir/population_contract.json']
    a['input_sha256']={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    return a

def outputs(a):
    lines=['# VSERVO-02 - conditional clamp and sink calculations','', '[Guide](README.md) | [Explorer](index.html) | [Annotated boundary](v2_vservo_transients.svg)','',
    '## Captured topology, unchanged','',
    f"Verified {len(a['topology']['checked_pin_nets'])} explicit pin memberships and the complete six-member VSERVO net against VSERVO-01 XML. U3 is LM76003RNPR; SYNC/MODE pin 17 is GND. The existing automatic mode is not credited as a regenerative sink. D4/D9 remain exclusive forward sources. No native command was rerun and no circuit changed.",'',
    '## Actual envelopes remain unavailable','',
    '| Model | Missing actual inputs | Actual result |','|---|---|---|']
    for name,r in a['actual'].items():lines.append('| '+name+' | '+', '.join(r['missing_fields'])+' | Unavailable |')
    lines+=['','Examples below are allocations only. Unknowns are not replaced by C11 voltage ratings or arbitrary receiver limits.','',
    '## Necessary clamp window','',
    'Turn-on minimum must exceed the maximum normal rail. Turn-on maximum plus all remaining full-current/dynamic/local-path rise must remain below the allowed local maximum. The rise term is not delay alone; a breakdown number is not a loaded clamp voltage.','',
    '| Example | Off-state margin (V) | Protection margin (V) | Meaning |','|---|---:|---:|---|']
    for case in a['window_cases']:
        r=case['result'];available=r['status']=='calculated'
        lines.append(f"| {case['label']} | {r['off_margin_V'] if available else 'Unavailable'} | {r['protection_margin_V'] if available else 'Unavailable'} | "+('Positive arithmetic only' if r['strict_positive_arithmetic_margin'] else 'No accepted window')+' |')
    lines+=['','Allocated normal maximum 5.1 V, turn-on range 5.2-5.3 V, allowed ceiling 5.5 V. Combined remaining rise of 0.1 V leaves 0.1 V protection margin; 0.2 V consumes it exactly. Neither case qualifies the actual receiver, clamp or remote node.','',
    '## Delay and energy are separate constraints','',f"For 80 uF, 0.5 A constant net return current and 10 us delay, the capacitive rise is **{a['delay_case']['rise_V']:.6f} V**. This omits ESR/inductive peaks. The 80 uF value is only the inherited initial 120 Hz/20 C illustration, not an all-condition effective minimum.",'',
    '| Positive residual burst (mJ) | Finite storage to 5.5 V (mJ) | Minimum event sink, endpoint lower bound (mJ) | Full sink energy to restore same start (mJ) | Conditional mean at 10 events/s (mW) |','|---|---:|---:|---:|---:|']
    for case in a['sink_cases']:
        r=case['result'];lines.append(f"| {r['inputs']['net_event_energy_J']*1e3:g} | {r['capacitor_energy_window_J']*1e3:.3f} | {r['minimum_event_sink_J']*1e3:.3f} | {r['repeated_events_same_start_require_local_sink_J']*1e3:.3f} | {r['mean_local_sink_W']*1e3:.3f} |")
    lines+=['','The energy window assumes 80 uF initially at 5 V. Residual burst energy is after other paths, with no later offset inside the burst. The endpoint lower bound does not bound an earlier peak. Repeated-event values assume that the sole remaining local sink restores the same starting rail with no other later absorption credit. An event fitting the capacitor still needs a reset path before identical repetition.','',
    'Actual peak closure needs the maximum cumulative energy excursion and the time waveform. Do not double-count harness energy already present at the chosen port. Mean watts alone do not establish pulse current, hot-start SOA, thermal recovery or continuous-fault handling.','',
    '## Separate negative-terminal boundary','',
    'At the illustrative C11/receiver terminal minima of zero volts and receiver minimum allowance of zero, both equality boundaries are met with **zero positive margin**. No physical acceptance is inferred. Actual lower bounds remain unavailable. A local positive clamp does not establish remote overshoot, negative ringing, ground-loss or connector-sequencing behavior.','',
    'Next specify one independent local shunt cell with full-current voltage/current limits, startup/control-power behavior, maximum delay, recovery, SOA/thermal and failed-open/short behavior for both exclusive source populations. Keep missing actuator permissions disabled and all device/procurement/hardware decisions held.','']
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="980" viewBox="0 0 1280 980"><rect width="1280" height="980" fill="#f4f7fb"/><style>text{font-family:Arial,sans-serif;fill:#172638}.h{font-size:28px;font-weight:bold}.t{font-size:20px;font-weight:bold}.s{font-size:17px}.sub{font-size:18px;fill:#425874}.box{fill:white;stroke:#9bb3c9;stroke-width:2}.hold{fill:#fff5e7;stroke:#b86e12;stroke-width:2;stroke-dasharray:8 5}.wire{fill:none;stroke:#246789;stroke-width:3}</style>']
    def text(x,y,s,c='s'):svg.append(f'<text x="{x}" y="{y}" class="{c}">{escape(s)}</text>')
    def box(x,y,w,h,c='box'):svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" class="{c}"/>')
    text(40,48,'VSERVO-02 | Where must returned energy go?','h')
    text(40,80,'Captured VSERVO-01 topology + proposed protection boundary | No circuit change or selected device','sub')
    box(40,107,1200,63,'hold');text(58,135,'Finite capacitor storage does not replace a qualified sink or a return-capable source.','t');text(58,159,'Actual receiver, source and harness limits remain unavailable. All examples are allocations.')
    box(40,199,320,72);text(58,229,'ONBOARD: buck -> D4','t');text(58,254,'U3 SYNC/MODE pin 17 = GND')
    box(40,291,320,72);text(58,321,'BEC_ONLY: J2.2 -> D9','t');text(58,346,'Actual BEC sink behavior unknown')
    svg.append('<path class="wire" d="M360 235H410V327H360 M410 280H460 M780 280H850"/>')
    box(460,225,320,111);text(478,256,'VSERVO / C11 / C12','t');text(478,286,'J3.2 and TP4.1');text(478,315,'Exclusive source populations')
    box(850,225,390,111,'hold');text(868,256,'J3 servo supply + harness','t');text(868,286,'Returned energy is unmeasured.');text(868,315,'Propulsion energy is not assumed here.')
    box(40,396,590,158,'hold');text(58,428,'Next study: local dissipative shunt','t')
    for i,s in enumerate(['Proposed VSERVO -> controlled sink -> GND','Bound full-current clamp rise, delay and current.','Qualify pulse / repeated / continuous dissipation.','Control power must exist while energy can arrive.']):text(58,460+i*26,s)
    box(660,396,580,158,'hold');text(678,428,'Alternative: return to source remains held','t')
    for i,s in enumerate(['D4 / D9 do not provide an intended return path.','Existing buck mode is not an accepted energy sink.','BEC, input path and battery acceptance are unknown.','No diode bridging or population change is proposed.']):text(678,460+i*26,s)
    box(40,585,590,172);text(58,617,'Window: normal < threshold < allowed ceiling','t')
    for i,s in enumerate(['Allocated 5.1 V normal; turn-on range 5.2-5.3 V.','At 5.5 V ceiling: 0.1 V combined rise leaves 0.1 V.','0.2 V combined rise leaves zero margin.','10 us at 0.5 A / 80 uF adds 62.5 mV capacitive rise.']):text(58,650+i*28,s)
    box(660,585,580,172);text(678,617,'Storage is temporary; energy must leave','t')
    for i,s in enumerate(['80 uF: 0.210 mJ storage from 5 V to 5.5 V.','1 mJ burst: minimum event sink 0.790 mJ.','Same-start reset by sole sink: full 1 mJ each event.','At 10 events/s: 10 mW mean; peak limits unknown.']):text(678,650+i*28,s)
    box(40,789,1200,88);text(58,820,'Separate boundary: C11 reverse voltage and remote receiver voltage remain unqualified.','t');text(58,850,'Check maximum cumulative energy, local and remote waveforms, and ground/contact sequencing. Do not count energy twice.')
    box(40,908,1200,52,'hold');text(58,932,'Next: specify one independent local shunt cell before choosing parts or inserting circuitry.','t');text(58,953,'Preserve 6S, both converters, C11 candidate, exclusive populations and all default-disabled missing permissions.')
    svg.append('</svg>')
    html=(HERE/'explorer.template.html').read_text(encoding='utf-8').replace('@@DATA@@',json.dumps(a).replace('</','<\\/'))
    return {'analysis.json':json.dumps(a,indent=2)+'\n','RESULTS.md':'\n'.join(lines),'v2_vservo_transients.svg':'\n'.join(svg)+'\n','index.html':html}

def main():
    ap=argparse.ArgumentParser();g=ap.add_mutually_exclusive_group(required=True)
    for n in ['render','capture','check']:g.add_argument('--'+n,action='store_true')
    args=ap.parse_args();inputs=read('input_manifest.json')
    for n,h in inputs['input_sha256'].items():assert sha(ROOT/n)==h,'Preserved input changed: '+n
    a=collect()
    for n,s in outputs(a).items():
        if args.render:write(n,s)
        else:assert (HERE/n).read_text(encoding='utf-8')==s,'Stale output: '+n
    if not args.render:
        for n,h in read('review_notes.json')['reviewed_sha256'].items():assert sha(HERE/n)==h,'Stale review: '+n
        for n,h in read('viewer_check.json')['input_sha256'].items():
            source=HERE/'viewer-template.snapshot.html' if n=='pm/index.template.html' else ROOT/n
            assert sha(source)==h,'Stale captured viewer input: '+n
        # Current live-template binding is checked separately by check_viewer_replay.py.
        artifacts={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='packet_manifest.json' and '__pycache__' not in p.parts}
        c=read('contract.json');m={k:c[k] for k in DELTAS+FALSE};m.update(revision='VSERVO-02',native_candidate='VSERVO-01',source_revision=inputs['baseline_head'],input_sha256=inputs['input_sha256'],artifact_sha256=artifacts)
        if args.capture:write('packet_manifest.json',json.dumps(m,indent=2)+'\n')
        else:assert read('packet_manifest.json')==m,'Changed packet bytes'
    print(f"PASS VSERVO-02 symbolic boundaries, 14 captured pins and {len(inputs['input_sha256'])} preserved inputs; no native/hardware acceptance")
if __name__=='__main__':main()
