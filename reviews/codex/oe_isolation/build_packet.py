"""Render ACT-10 source-conditioned screen; never invokes native CAD tools."""
from pathlib import Path
from html import escape
import argparse, hashlib, json
from model import collect
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def read(n): return json.loads((HERE/n).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,s): (HERE/n).write_text(s,encoding='utf-8',newline='\n')
def outputs(a):
    rows='\n'.join(f"| {r['C_pF']:g} | {r['decay_ns']:.3f} | {r['downstream_screen_ns']:.3f} | {r['margin_ns']:.3f} | {'Fits arithmetic only' if r['fits_allocation_only'] else 'Exceeds allocation'} |" for r in a['cases'])
    text=f'''# ACT-10 - OE discharge and timing screen

[Connection proposal and limits](README.md) | [Source conditions](sources.json) | [Annotated diagram](v2_oe_isolation.svg)

**The series-switch proposal is held.** Partial-power isolation and actual timing remain unqualified. No native circuit, hardware or production component is accepted. These calculations use explicit allocations and a single-pole model.

## R40 discharge after disconnection

R40 remains 10 kOhm. Allocated 1% tolerance gives Rmax={a['R_max_ohm']:g}ohm. Initial OE is 3.6 V, the low target 0.8 V and total positive feed 5 uA. Feed equilibrium is0.0505 V. Capacitance is the whole node, including switch, receiver, routing and probing.

`Vfloor = Ifeed * R`

`V(t) = Vfloor + (Vinitial - Vfloor) * exp(-t / (R * C))`

`t_target = R * C * ln((Vinitial - Vfloor) / (Vtarget - Vfloor))`

If Vfloor is at or above the target, there is no finite guaranteed crossing; the model returns an unreachable result. The asymptotic feed ceiling is **{a['maximum_feed_A_at_asymptote']*1e6:.6f}uA**. Equality is not a usable design point. No actual leakage envelope is asserted.

## Downstream allocation

The optimistic screen is55 ns switch transition + full RC decay +36 ns translator disable. Other logic/guard delay is set to zero. Against the245 ns allocation:

| Total node C (pF) | RC to target (ns) | Downstream screen (ns) | Margin (ns) | Arithmetic disposition |
|---|---:|---:|---:|---|
{rows}

The zero-margin total-capacitance ceiling is **{a['maximum_C_pF_at_zero_margin']:.6f}pF**. Positive guard/logic delay or injected charge reduces this ceiling. Do not infer hardware failure from an allocated case or hardware acceptance from a positive margin.

The source switch timing measurement uses a fast control edge and200 ohm/15 pF load. Its supply-off test measures only the first10% output drop; it is not a logic-low time. The translator disable table uses a fast OE edge and5 pF output load. At the allocated target, the model's OE inverse slew (time per volt) is `R*C/(Vtarget-Vfloor)` in seconds/volt. It is much slower than the translator timing test. Adding the two table values therefore **does not establish a guaranteed end-to-end bound**. The actual partial-power waveform, switching injection, output load and threshold behavior remain open.

## Circuit decision

A series switch avoids adding a sink against U14's active output, but isolation must persist through every observer-supply state. Neither the permitted signal-voltage range below 1.5 V nor the zero-supply leakage endpoint proves arbitrary dwell/bounce isolation. The normal range also limits the signal to twice VDD: a 3.6 V request requires VDD>=1.8 V while VDD>=1.5 V. Charge injection is not maximally bounded by this screen. Thus every case keeps physical acceptance false regardless of arithmetic margin.

Next evaluate translator VCCA gating/discharge under its own supply-isolation conditions, with a separate supply-collapse timing contract. Never substitute the36 ns OE table value for supply-collapse response. Keep VCCB and U12/U13/U14 supplies unchanged. [Restart and remaining gates](README.md#next-smallest-circuit-task).
'''
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="980" viewBox="0 0 1280 980"><rect width="1280" height="980" fill="#f4f7fb"/><style>text{font-family:Arial,sans-serif;fill:#172638}.h{font-size:28px;font-weight:bold}.t{font-size:20px;font-weight:bold}.s{font-size:16px}.sub{font-size:18px;fill:#425874}.box{fill:white;stroke:#9bb3c9;stroke-width:2}.hold{fill:#fff5e7;stroke:#b86e12;stroke-width:2;stroke-dasharray:8 5}.wire{fill:none;stroke:#246789;stroke-width:3}.proposal{fill:none;stroke:#a46d20;stroke-width:2;stroke-dasharray:7 4}</style>']
    def t(x,y,s,c='s'):svg.append(f'<text x="{x}" y="{y}" class="{c}">{escape(s)}</text>')
    def b(x,y,w,h,c='box'):svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" class="{c}"/>')
    t(40,48,'ACT-10 | Can opening a switch reliably remove actuator permission?','h')
    t(40,80,'Annotated connection proposal | ACT-04 stays native | No new wiring or parts are released','sub')
    b(40,108,1200,60,'hold');t(58,134,'HELD: intermediate-supply isolation and end-to-end disable time are unqualified.','t');t(58,157,'All unimplemented qualification sources remain disabled. Arithmetic margin does not establish physical acceptance.')
    b(40,204,300,157);t(58,234,'U14: existing main-rail logic','t');t(58,265,'QUAL_OK AND ARM AND READY');t(58,296,'Pin 4 -> proposed request net');t(58,327,'Original main 3V3 supply.')
    b(490,204,325,157,'hold');t(508,234,'TMUX1511PWR / channel 1','t');t(508,265,'S1 pin 2');t(692,265,'D1 pin 3');t(508,327,'SEL1 pin 1: independent permit')
    svg.append('<path class="wire" d="M340 283H490 M535 283H595 M595 283L650 262 M665 283H770 M815 283H960"/><circle cx="595" cy="283" r="4" fill="#246789"/><circle cx="665" cy="283" r="4" fill="#246789"/>')
    t(351,272,'ACT_OE_REQUEST');t(830,272,'ACT_OE')
    b(960,204,280,157);t(978,234,'U4 TXU0102: existing','t');t(978,265,'OE pin 6 at ACT_OE');t(978,299,'VCCA pin 3: original main 3V3');t(978,330,'VCCB pin 7: ACT-01 rail')
    svg.append('<path class="wire" d="M904 283V389H889V437H919V389H904 M904 437V465 M886 465H922 M892 473H916 M898 481H910"/>')
    t(947,410,'R40 = 10 kOhm, retained');t(947,439,'OE discharges after isolation.');t(947,468,'No clamp against U14 drive.')
    b(40,397,710,104,'hold');t(58,426,'Proposed island -> pin 14; GND -> pin 7; local 100 nF');t(58,455,'Independent guard -> SEL1, with external 10 kOhm pulldown.');t(58,483,'Authority and supply expiry remain unimplemented; default disabled.')
    svg.append('<path class="proposal" d="M652 397V361"/>')
    b(40,537,580,148);t(58,568,'A. Valid island; SEL low');t(58,598,'U14 disconnected only within applicable switch conditions.');t(58,628,'R40, total C and feed determine the OE waveform.');t(58,658,'Source timing is not a completed discharge time.')
    b(660,537,580,148,'hold');t(678,568,'B. Island collapses or dwells below 1.5 V');t(678,598,'3.6 V request also needs VDD >= 1.8 V in normal operation.');t(678,628,'Zero-volt leakage is one endpoint, not a full ramp contract.');t(678,658,'Stored energy cannot cover an indefinite brownout.')
    b(40,720,580,151);t(58,751,'C. Conditional 245 ns downstream budget','t');t(58,782,'55 ns switch + R40 decay +36 ns translator; no guard delay');t(58,813,f"Zero-margin total C: {a['maximum_C_pF_at_zero_margin']:.3f}pF");t(58,844,'Fast source-test edges differ from the proposed RC edge.')
    b(660,720,580,151);t(678,751,'D. Preserve the rest of the design','t');t(678,782,'Both converters, ACT-01 source options and corrected copper');t(678,813,'READY / ARM / ACK behavior and missing-source defaults');t(678,844,'V1 evidence, live firmware, BOM and assembly remain held.')
    b(40,904,1200,53,'hold');t(58,928,'Next: assess TXU VCCA gating/discharge with its own supply-collapse timing contract.','t');t(58,950,'Do not reuse OE delay as supply-isolation delay. Local rail voltage still does not prove remote readiness.')
    svg.append('</svg>')
    return {'RESULTS.md':text,'v2_oe_isolation.svg':'\n'.join(svg)+'\n'}
def preserved():
    i=read('input_manifest.json');assert len(i['input_sha256'])==279
    for p,h in i['input_sha256'].items():assert sha(ROOT/p)==h,p
    c=read('contract.json')
    for k in ['candidate_electrical_delta','live_electrical_delta','live_copper_delta']:assert c[k]==0,k
    for k in ['parts_selected','hardware_tested','fabrication_approved','native_commands_rerun','qualification_ports_implemented','partial_power_isolation_qualified','source_timing_applicable_to_RC_edge']:assert c[k] is False,k
    assert read('analysis.json')==collect(),'Stale analysis'
    return i
if __name__=='__main__':
    ap=argparse.ArgumentParser();g=ap.add_mutually_exclusive_group(required=True)
    for mode in ['render','capture','check']:g.add_argument('--'+mode,action='store_true')
    args=ap.parse_args();i=preserved()
    for n,s in outputs(collect()).items():
        if args.render:write(n,s)
        else:assert (HERE/n).read_text(encoding='utf-8')==s,'Stale output: '+n
    if not args.render:
        for n in ['review_notes.json','viewer_check.json']:assert (HERE/n).is_file(),n
        for n,h in read('review_notes.json')['reviewed_sha256'].items():assert sha(HERE/n)==h,'Stale review: '+n
        for n,h in read('viewer_check.json')['input_sha256'].items():assert sha(ROOT/n)==h,'Stale viewer evidence: '+n
        artifacts={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='packet_manifest.json' and '__pycache__' not in p.parts}
        c=read('contract.json');m={k:c[k] for k in ['candidate_electrical_delta','live_electrical_delta','live_copper_delta','parts_selected','hardware_tested','fabrication_approved','native_commands_rerun','qualification_ports_implemented','partial_power_isolation_qualified','source_timing_applicable_to_RC_edge']}
        m.update(revision='ACT-10',source_revision=i['baseline_head'],input_sha256=i['input_sha256'],artifact_sha256=artifacts)
        if args.capture:write('packet_manifest.json',json.dumps(m,indent=2)+'\n')
        else:assert read('packet_manifest.json')==m,'Artifact hashes changed'
    print('PASS ACT-10 outputs and279 preserved inputs; circuit remains held')
