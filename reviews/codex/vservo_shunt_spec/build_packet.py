"""Replay VSERVO-03 proposed requirements; no CAD or hardware tools."""
from pathlib import Path
import argparse,hashlib,json,xml.etree.ElementTree as ET
import model
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
ZERO=['candidate_electrical_delta','live_electrical_delta','live_copper_delta']
FALSE=['native_commands_rerun','parts_selected','hardware_accepted','fabrication_approved','procurement_approved','protection_qualified','qualification_ports_implemented','actual_receiver_limits_available']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(name,text):(P/name).write_text(text,encoding='utf-8',newline='\n')
def check_inputs():
    for name,h in read(P/'input_manifest.json')['input_sha256'].items():assert sha(ROOT/name)==h,'Preserved input changed: '+name

def collect():
    check_inputs();c=read(P/'contract.json')
    assert c['revision']=='VSERVO-03' and c['electrical_candidate']=='VSERVO-01'
    assert all(c[k]==0 for k in ZERO) and all(c[k] is False for k in FALSE)
    path=ROOT/'reviews/codex/power_sheet_polish/native/netlist.xml';xml=ET.parse(path);pins={};members={}
    for net in xml.findall('./nets/net'):
        name=net.get('name');members[name]=set()
        for n in net.findall('node'):
            key=(n.get('ref'),n.get('pin'));assert key not in pins; pins[key]=name;members[name].add(key)
    assert len(pins)==429 and len(xml.findall('./components/comp'))==128
    assert members['VSERVO']=={('C11','1'),('C12','1'),('D4','1'),('D9','1'),('J3','2'),('TP4','1')}
    expected={('C11','2'):'GND',('C12','2'):'GND',('J3','3'):'GND',('J2','3'):'GND',('D4','2'):'/Power/+5V_BUCK',('D9','2'):'/BEC_IN',('J2','2'):'/BEC_IN',('U3','17'):'GND'}
    assert all(pins[k]==v for k,v in expected.items())
    pop=read(ROOT/'reviews/codex/power_sheet_polish/population_contract.json')
    assert pop['base_schematic_dnp_refs']==['D4','D9'] and pop['dual_population_allowed'] is False
    assert pop['variants']['BEC_ONLY']['D4']=='DNP' and pop['variants']['BEC_ONLY']['D9']=='POPULATE'
    assert pop['variants']['ONBOARD']['D4']=='POPULATE' and pop['variants']['ONBOARD']['D9']=='DNP'
    data=model.collect();data['captured_topology']={'source':path.relative_to(ROOT).as_posix(),'sha256':sha(path),'vservo_members':sorted('.'.join(k) for k in members['VSERVO']),'other_checked_pins':{'.'.join(k):v for k,v in expected.items()},'source_populations_exclusive':True,'new_native_connections':0}
    return data

def outputs(a):
    w=a['window_cases'][0]['result'];r=a['resistance_cases'][0]['result'];s=a['resistance_cases'][1]['result'];b=a['branch_case']
    lines=['# VSERVO-03 — conditional shunt bounds','',
    '**All values below are illustrative allocations. Actual source/receiver/device inputs remain unavailable. No nominal resistance, component, circuit or operating limit is selected.**','',
    '[Specification](README.md) | [Interactive explorer](index.html) | [Proposed cell](v2_shunt_spec.svg)','',
    '## Threshold margins','',
    'Normal maximum 5.0 V; falling threshold 5.10–5.15 V; rising threshold 5.25–5.30 V; disturbance 40 mV peak-to-peak; local ceiling 5.5 V. Normal maximum includes the worst sensed normal feed/ripple/disturbance.','',
    '| Necessary margin | Allocated result |','|---|---:|',f"| Release above normal | {w['release_margin_V']:.3f} V |",f"| Hysteresis after disturbance | {w['hysteresis_margin_V']:.3f} V |",f"| Protection with 0.1 V further rise | {w['protection_margin_V']:.3f} V |",'| Protection with 0.2 V further rise | 0 V; no positive margin |','',
    'The complete response delay to useful sink current and loaded/parasitic rise must fit the allocation. Turn-off delay and lower-rail excursion remain separate and uncalculated; these numbers do not qualify receiver undervoltage.','',
    '## Necessary nominal resistance interval','',
    '`Rnom > max(0, (rail_max / Ipath_allocation - Ron_min) / (1 - tolerance))`','',
    '`Rnom < (off_min / Iexcess - Ron_max) / (1 + tolerance)`','',
    'The upper bound ensures positive current margin at the lowest falling threshold, not just at the ceiling. Excess current includes all simultaneous source and return paths after justified load credits. The branch-current allocation is not a device rating.','',
    '| Excess allocation | Strict lower bound | Strict upper bound | Result |','|---|---:|---:|---|',
    f"| 0.5 A | {r['nominal_lower_exclusive_ohm']:.6f} ohm | {r['nominal_upper_exclusive_ohm']:.6f} ohm | Positive necessary interval only |",
    f"| 1.0 A | {s['nominal_lower_exclusive_ohm']:.6f} ohm | {s['nominal_upper_exclusive_ohm']:.6f} ohm | No interval |",'',
    'Both cases allocate 5.1 V falling minimum, 5.5 V rail maximum, 1 A branch-current ceiling, 0–0.1 ohm Ron and 5% resistor tolerance. An assumed rail bound must be established independently of this unimplemented clamp.','',
    '## Fixed 8.2 ohm illustration','',
    '| Bound | Conditional result |','|---|---:|',
    f"| Minimum fully-on sink current | {b['sink_current_min_A']:.6f} A |",f"| Maximum branch current | {b['branch_current_max_A']:.6f} A |",f"| Sink margin above 0.5 A | {b['sink_current_margin_A']:.6f} A |",f"| Conservative resistor instantaneous power | {b['resistor_instantaneous_upper_W']:.6f} W |",f"| Fully-on FET conduction-only bound | {b['fet_on_state_conduction_upper_W']*1000:.6f} mW |",'',
    'Resistor power is bounded by Vmax^2/Rmin. The FET figure uses Imax^2*Ronmax; it excludes transitions, partial gate drive, startup and linear-region SOA. Neither number is a component wattage or thermal rating. Pulse duration, hot-start temperature, repetition and continuous fault operation remain unknown.','',
    'Finite capacitor storage cannot be reused every event without restoration. No repeated-energy reset path or continuous-fault clearing time is inferred. A resistor nearly dissipating 3.9 W instantaneously cannot be chosen from mean event watts alone.','',
    '## Actual evidence','',
    'The threshold, resistance and branch models all remain unavailable because their actual inputs are null. Device selection, full-current startup/turn-off behavior, reverse voltage, remote receiver limits and source fault interruption are held. No native tools or hardware were run.','',
    'Next independent task: full 6S sensing/ADC range and protection review, preserving the latest native Power presentation and all existing electrical evidence.','']
    html=(P/'viewer.template.html').read_text(encoding='utf-8').replace('@@DATA@@',json.dumps(a).replace('</','<\\/'))
    return {'analysis.json':json.dumps(a,indent=2)+'\n','RESULTS.md':'\n'.join(lines),'index.html':html}

def main():
    ap=argparse.ArgumentParser();g=ap.add_mutually_exclusive_group(required=True)
    for name in ['render','capture','check']:g.add_argument('--'+name,action='store_true')
    args=ap.parse_args();a=collect()
    for name,text in outputs(a).items():
        if args.render:write(name,text)
        else:assert (P/name).read_text(encoding='utf-8')==text,'Stale output: '+name
    if not args.render:
        for name,h in read(P/'review_notes.json')['reviewed_sha256'].items():assert sha(ROOT/name)==h,'Stale review: '+name
        for name,h in read(P/'viewer_check.json')['input_sha256'].items():assert sha(P/'viewer-template.snapshot.html' if name=='pm/index.template.html' else P/'viewer-builder.snapshot.mjs' if name=='pm/tools/build.mjs' else ROOT/name)==h,'Stale captured viewer input: '+name
        artifacts={f.relative_to(ROOT).as_posix():sha(f) for f in sorted(P.rglob('*')) if f.is_file() and f.name!='packet_manifest.json' and '__pycache__' not in f.parts}
        c=read(P/'contract.json');inputs=read(P/'input_manifest.json');m={'revision':'VSERVO-03','electrical_candidate':'VSERVO-01','presentation_candidate':'POWER-DOC-01','source_revision':inputs['baseline_head'],'input_sha256':inputs['input_sha256'],'artifact_sha256':artifacts,**{k:c[k] for k in ZERO+FALSE}}
        if args.capture:write('packet_manifest.json',json.dumps(m,indent=2)+'\n')
        else:assert read(P/'packet_manifest.json')==m,'Packet bytes/coverage changed'
    print('PASS VSERVO-03 proposed shunt bounds,14 captured pins and532 preserved inputs; no device/native/hardware acceptance')
if __name__=='__main__':main()
