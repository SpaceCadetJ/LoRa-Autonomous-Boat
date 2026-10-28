"""Reproduce ACT-11 source-conditioned shutdown screen; no CAD commands."""
from pathlib import Path
from html import escape
import argparse, hashlib, importlib.util, json, math
import xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PRIOR=ROOT/'reviews/codex/oe_isolation/model.py'
spec=importlib.util.spec_from_file_location('act10_decay',PRIOR)
decay=importlib.util.module_from_spec(spec);spec.loader.exec_module(decay)
DELTAS=['candidate_electrical_delta','live_electrical_delta','live_copper_delta']
FALSE=['parts_selected','native_commands_rerun','hardware_tested','fabrication_approved','qualification_ports_implemented','supply_collapse_timing_qualified','continuous_partial_power_isolation_qualified']
def read(n):return json.loads((HERE/n).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,s):(HERE/n).write_text(s,encoding='utf-8',newline='\n')
def validate(c):
    assert c['packet']=='ACT-11'
    assert all(c[k]==0 for k in DELTAS)
    assert all(c[k] is False for k in FALSE)
    r=ET.parse(ROOT/'reviews/codex/actuator_latch/native/netlist.xml').getroot()
    pins={x.get('ref')+'.'+x.get('pin'):n.get('name') for n in r.findall('./nets/net') for x in n.findall('node')}
    vals={x.get('ref'):x.findtext('value') for x in r.findall('./components/comp')}
    assert all(pins[k]==v for k,v in c['existing_memberships'].items()),'Native membership mismatch'
    assert all(vals[k]==v for k,v in c['existing_values'].items()),'Native value mismatch'
    a=c['illustration'];assert a['corner_bound'] is False
    assert a['turnoff_delay_included'] is False and a['TXU_supply_isolation_delay_included'] is False
    # The archived illustration prose uses these fixed values; reject stale edits.
    fixed={'nominal_C13_F':100e-9,'R_QOD_ohm_typical':24,'initial_V':3.6,
           'target_V_allocated':.08,'feed_A_cases':[0,.0001,.001,.004],
           'downstream_budget_s_allocated':245e-9,'full_response_s_allocated':400e-9,
           'input_power_valid_assumed':True}
    assert all(a[k]==v for k,v in fixed.items()),'Illustration changed; revise prose and review contract together'
    return a
def collect():
    c=read('contract.json');a=validate(c);r=a['R_QOD_ohm_typical'];cap=a['nominal_C13_F'];v0=a['initial_V'];target=a['target_V_allocated'];rows=[]
    for feed in a['feed_A_cases']:
        t=decay.decay_time_s(r,cap,v0,target,feed)
        rows.append({'feed_A_allocated':feed,'floor_V_typical_model':feed*r,'time_to_target_s_typical_model':t})
    charge=cap*(v0-target)
    return {'packet':'ACT-11','classification':'typical_parameter_illustration_not_delay_bound','cases':rows,'charge_C_at_nominal_C13':charge,'average_net_sink_A_for_245ns':charge/a['downstream_budget_s_allocated'],'maximum_feed_A_for_finite_80mV_crossing':target/r,'native_accepted':False,'hardware_accepted':False,'supply_collapse_timing_qualified':False,'input_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in [HERE/'contract.json',HERE/'build_packet.py',PRIOR,ROOT/'reviews/codex/actuator_latch/native/netlist.xml']}}
def outputs(a):
    rows='\n'.join('| %.3f | %.3f | %s |'%(r['feed_A_allocated']*1e3,r['floor_V_typical_model']*1e3,'Unreachable' if r['time_to_target_s_typical_model'] is None else '%.6f'%(r['time_to_target_s_typical_model']*1e6)) for r in a['cases'])
    states='\n'.join('| '+r['conditions']+' | '+r['source_result']+' | '+r['limitation']+' |' for r in read('states.json')['states'])
    result=f'''# ACT-11 - supply-state and discharge evidence

[Decision and proposed connections](README.md) | [Primary-source conditions](sources.json) | [Annotated review](v2_vcca_shutdown.svg)

## Supply-state applicability

These are source conditions and a logical restart counterexample, not simulated or measured waveforms. No supply-collapse deadline is qualified.

| Condition | Source result / inference | Limitation |
|---|---|---|
{states}

## Scale illustration using typical QOD resistance

Keep nominal C13 = 100 nF. With R = 24 ohm (typical only), starting voltage 3.6 V and an allocated 80 mV target, use ACT-10's tested constant-feed decay function:

`Vfloor = I * R; t = R*C*ln((Vstart-Vfloor)/(Vtarget-Vfloor))`

| Allocated positive feed (mA) | Modeled floor (mV) | Time to 80 mV after ideal disconnection (us) |
|---|---:|---:|
{rows}

The zero-feed illustration takes **9.135990 us** after ideal disconnection, before adding switch-control and translator supply-isolation delays. It uses no 100 ohm external load. This is neither a best-case lower bound nor a worst-case upper bound. Actual effective C, QOD resistance and feed vary and remain unqualified. The 4 mA example approaches 96 mV: it misses the allocated 80 mV guard target, although that modeled floor is below the source's 100 mV static condition. It does not prove failure or success of actual isolation.

For nominal C13, removing charge from 3.6 V to 80 mV requires **{a['charge_C_at_nominal_C13']*1e9:.3f} nC**. Doing that within the entire 245 ns downstream allocation requires an average **net** sink of **{a['average_net_sink_A_for_245ns']:.6f} A**, even with instantaneous disconnection and zero subsequent propagation delay. This requirement calculation is not a current rating or a suggested circuit. Removing bypass to improve this arithmetic is not justified.

The finite-crossing feed ceiling for this typical resistance is **{a['maximum_feed_A_for_finite_80mV_crossing']*1e3:.6f} mA**, strictly exclusive at equality. It is not an accepted leakage allowance. TPS22919's supply shutdown current does not establish total current feeding VCCA_SW through all pins and paths.

## Decision and restart consequence

The reviewed VCCA-gating option is **not accepted as the primary fast inhibit**. Source response maxima are missing; the typical scale is far longer than the inherited allocation. It remains only a possible secondary de-energization mechanism after an independent fast inhibit. That secondary role is also unqualified while input power, backfeed, transient output state and restoration remain open.

Cycling U4 alone leaves U12's separately powered READY state intact. With QUAL, ARM and READY still high, U14 can request enable again when U4 is repowered. Therefore fault handling must clear READY independently and require a new healthy interval and fresh ACK before later ARM. A completed discharge or fixed delay cannot grant rearm.

Do not silently replace the 400 ns total / 245 ns downstream allocation with a slower limit. First write a connector-level fault envelope distinguishing fast inhibit, indefinite disabled hold, and rearm; keep unknown receiver acceptance held. [Next bounded task](README.md#next-smallest-task).
'''
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="980" viewBox="0 0 1280 980"><rect width="1280" height="980" fill="#f4f7fb"/><style>text{font-family:Arial,sans-serif;fill:#172638}.h{font-size:28px;font-weight:bold}.t{font-size:20px;font-weight:bold}.s{font-size:17px}.sub{font-size:18px;fill:#425874}.box{fill:white;stroke:#9bb3c9;stroke-width:2}.hold{fill:#fff5e7;stroke:#b86e12;stroke-width:2;stroke-dasharray:8 5}.wire{fill:none;stroke:#246789;stroke-width:3}.proposed{fill:none;stroke:#a46d20;stroke-width:2;stroke-dasharray:7 4}</style>']
    def t(x,y,s,c='s'):svg.append(f'<text x="{x}" y="{y}" class="{c}">{escape(s)}</text>')
    def b(x,y,w,h,c='box'):svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" class="{c}"/>')
    t(40,48,'ACT-11 | Supply isolation is a state, not a proven shutdown deadline','h')
    t(40,80,'Proposed VCCA-only switch | ACT-04 stays native | Exact supply and restart boundaries','sub')
    b(40,108,1200,64,'hold');t(58,135,'NOT ACCEPTED as primary fast inhibit: no bounded supply-collapse response.','t');t(58,160,'Possible secondary shutdown remains unqualified. No new native circuit or purchasing part is released.')
    b(40,208,260,140);t(58,239,'Existing +3V3','t');t(58,271,'U12 / U13 / U14 stay here.');t(58,304,'READY remains powered.')
    b(440,208,345,140,'hold');t(458,239,'TPS22919DCKR proposal','t');t(458,271,'IN1 -> switch -> VOUT6');t(458,303,'QOD5 tied to VOUT; GND2')
    b(940,208,300,140);t(958,239,'TXU0102 U4','t');t(958,271,'VCCA3 + C13.1 -> VCCA_SW');t(958,303,'C13 remains 100 nF to GND.')
    svg.append('<path class="wire" d="M300 280H440 M785 280H940"/>');t(801,266,'VCCA_SW')
    b(40,391,745,102,'hold');t(58,421,'Independent SUPPLY_PERMIT -> ON3; external 10k pulldown');t(58,451,'ON source unimplemented: default disabled. NC4 left floating.');t(58,479,'Local input bypass proposed; QOD behavior below VIN 1.6 V is open.')
    svg.append('<path class="proposed" d="M610 391V348"/>')
    b(830,391,410,102);t(848,421,'Preserve VCCB7 and C14.1','t');t(848,451,'/Power/+5V_BUCK, before D4');t(848,479,'ACT-01 source populations unchanged.')
    b(40,533,580,142);t(58,565,'Static isolation condition','t');t(58,596,'VCCA below 100 mV, with VCCB valid');t(58,627,'A discharged node is not the floating-supply test.');t(58,658,'Entry time and continuous backfeed remain unqualified.')
    b(660,533,580,142,'hold');t(678,565,'Power-only restart counterexample','t');t(678,596,'U4 off does not clear the separately powered READY latch.');t(678,627,'Old enable can return when VCCA is restored.');t(678,658,'Independent fault clear + healthy interval + fresh ACK.')
    b(40,712,580,148);t(58,743,'Illustration, not a component timing bound','t');t(58,774,'100 nF / typical 24 ohm / no feed / 3.6 V -> 80 mV');t(58,805,'9.136 us after ideal disconnection; other delays omitted');t(58,836,'Do not remove bypass to force a timing fit.')
    b(660,712,580,148);t(678,743,'Fast inhibit allocation remains unchanged','t');t(678,774,'400 ns total; 245 ns downstream');t(678,805,'Nominal capacitor charge removal: 352 nC');t(678,836,'245 ns would require 1.437 A average net sink.')
    b(40,900,1200,62,'hold');t(58,926,'Next: define connector-level fault acceptance before choosing a third isolation circuit.','t');t(58,951,'Separate fast inhibit, indefinite disabled hold and rearm. Missing receiver qualifications stay disabled.')
    svg.append('</svg>')
    return {'analysis.json':json.dumps(a,indent=2)+'\n','RESULTS.md':result,'v2_vcca_shutdown.svg':'\n'.join(svg)+'\n'}
def main():
    ap=argparse.ArgumentParser();g=ap.add_mutually_exclusive_group(required=True)
    for k in ['render','capture','check']:g.add_argument('--'+k,action='store_true')
    args=ap.parse_args();a=collect();i=read('input_manifest.json');assert len(i['input_sha256'])==298
    for n,h in i['input_sha256'].items():assert sha(ROOT/n)==h,'Changed prior evidence: '+n
    for n,s in outputs(a).items():
        if args.render:write(n,s)
        else:assert (HERE/n).read_text(encoding='utf-8')==s,'Stale output: '+n
    if not args.render:
        for n,h in read('review_notes.json')['reviewed_sha256'].items():assert sha(HERE/n)==h,'Stale review: '+n
        for n,h in read('viewer_check.json')['input_sha256'].items():assert sha(ROOT/n)==h,'Stale viewer evidence: '+n
        artifacts={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='packet_manifest.json' and '__pycache__' not in p.parts}
        c=read('contract.json');m={k:c[k] for k in DELTAS+FALSE};m.update(revision='ACT-11',source_revision=i['baseline_head'],input_sha256=i['input_sha256'],artifact_sha256=artifacts)
        if args.capture:write('packet_manifest.json',json.dumps(m,indent=2)+'\n')
        else:assert read('packet_manifest.json')==m,'Changed packet bytes'
    print('PASS ACT-11 source-conditioned outputs and 298 preserved inputs; no circuit acceptance')
if __name__=='__main__':main()
