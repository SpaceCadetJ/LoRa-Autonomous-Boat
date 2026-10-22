"""Reproduce ACT-09 architecture map, request explorer and numerical tables."""
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
    same=a['same_rail']; island=a['held_island']
    ramps='\n'.join(f"| {c['slew_V_per_us']:g} | {c['residual_V']*1000:.6f} | {'Fits allocation only' if c['fits_conditional_deadline_only'] else 'Exhausts allocation'} |" for c in same['cases'])
    hold='\n'.join(f"| {c['effective_capacitance_F']*1e6:g} | {c['time_to_valid_floor_s']*1e6:.6f} | {c['isolation_margin_s']*1e6:.6f} | {'Fits allocation only' if c['fits_allocated_isolation_deadline_only'] else 'Exhausts allocation'} |" for c in island['cases'])
    demos='\n'.join(f"| {name.replace('_',' ')} | {len(d['trace'])} | {'Modeled guards met' if d['timing_contract_met'] else 'Outside modeled guards'} | {'High requested' if d['trace'][-1]['OUTPUT_ENABLE_requested'] else 'Low requested'} |" for name,d in a['demonstrations'].items())
    results=f'''# ACT-09 retention and handover calculations

This is a conditional architecture and request model. Native circuitry is unchanged. No physical output-disable, indefinite brownout or hardware acceptance is established. Read the [architecture contract](README.md), [explicit assumptions](contract.json) and [interactive request traces](index.html).

## Same-rail observation deadline

Allocated overdrive point {same['overdrive_V']:.9f} V minus ACT-08 reference-validity boundary {same['valid_floor_V']:.3f} V leaves **{same['headroom_V']*1000:.6f} mV**. At {same['response_ns']:g} ns total allocated response, the zero-margin ceiling is **{same['maximum_slew_V_per_us']:.9f} V/us**. A strictly lower slope and qualified waveform response are required; this is not an accepted hardware slew specification.

`residual = overdrive_voltage - validity_floor - slew_V_per_us * response_ns / 1000`

| Illustrative falling slew (V/us) | Residual (mV) | Arithmetic disposition |
|---|---:|---|
{ramps}

This tightens the prior 3.000 V corridor calculation to the 3.005 V sourcing-test boundary. It applies to the same-rail proposal only. A separately held island changes supply/common-mode conditions and needs its own source applicability review. ACT-07's overvoltage and threshold/hysteresis gates remain open.

## Separate held-island charge budget

The proposed island starts from {island['source_min_V']:.9f} V minimum source, subtracts {island['blocking_drop_max_V']:.3f} V maximum allocated blocking loss, then {island['initial_ESR_drop_V']*1000:.6f} mV initial ESR sag. Result: {island['initial_after_drops_V']:.9f} V. The model uses {island['total_discharge_current_A']*1000:.3f} mA total allocated discharge, including reverse leakage, and stops at {island['valid_floor_V']:.3f} V.

`T = C_effective * (V_source_min - blocking_drop - I_total*ESR - V_valid_floor) / I_total`

| Effective capacitance (uF) | Time to validity floor (us) | Margin to 100 us allocation (us) | Arithmetic disposition |
|---|---:|---:|---|
{hold}

Zero-margin effective capacitance is {island['effective_capacitance_at_zero_margin_F']*1e6:.6f} uF. Strictly positive margin is needed. Effective values are not nominal component selections. A reference load, logic, conditioner, pin loads, bypass, storage leakage and reverse paths must all fit the current budget. A main-rail short needs actual reverse isolation; a capacitor across the shorted rail does not satisfy this equation.

The 3.005 V floor comes from reference sourcing-test headroom. This screen assumes every island guard, retention, conditioner and interface remains valid down to that voltage; the actual floor must be the highest applicable requirement across them. A higher floor reduces hold-up. The 100 us handover-finish budget is an unverified allocation. It does not permit a 100 us undefined-OE interval: the physical boundary must first suppress invalid U14 drive before main logic leaves its applicable supply range, then maintain disable continuously through handover. Observer hold-up does not relax the fast end-to-end inhibit deadline. A positive result does not bound a switch, reverse current, OV surge, recharge or unknown hold duration. A separate physical disabled condition must take over before the island becomes invalid. **Physical disable after hold-up remains unproven in every case.**

## Request-level sequence traces

| Scenario | Events/ticks | Modeled guard checks | Final output-enable request |
|---|---:|---|---|
{demos}

Only the listed events advance the model. The model defaults absent/unknown health inputs low, starts reference power from the independent guard, requires a fresh healthy interval with ACK/ARM low, and separates QUAL release, ACK and ARM. Faults invalidate requested READY. Conflicting edges latch the trace outside its modeled guard checks. ACK high/low pulse width and debounce are not modeled or qualified. These conservative software requests do not predict analog glitches, actual fault capture, metastability, physical OE or real motor stopping.

The model's allocated delays are not a timing characterization. A reference-valid predicate must be established externally; the healthy interval cannot make an invalid reference valid. All native and physical acceptance flags remain false.

## Reproduction

`python -B reviews/codex/observer_retention/test_model.py`

`python -B reviews/codex/observer_retention/model.py --check`

`python -B reviews/codex/observer_retention/build_packet.py --check`

[analysis.json](analysis.json) binds contract/model/prior allocations. [packet_manifest.json](packet_manifest.json) binds 257 preserved inputs and all packet artifacts. No native tools are invoked for this zero-delta packet.
'''
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="980" viewBox="0 0 1280 980"><rect width="1280" height="980" fill="#f4f7fb"/><style>text{font-family:Arial,sans-serif;fill:#172638}.h{font-size:29px;font-weight:bold}.t{font-size:20px;font-weight:bold}.s{font-size:17px}.sub{font-size:18px;fill:#425874}.box{fill:white;stroke:#9bb3c9;stroke-width:2}.hold{fill:#fff5e7;stroke:#b86e12;stroke-width:2;stroke-dasharray:8 5}.line{stroke:#246789;stroke-width:3;fill:none}</style>']
    def text(x,y,s,c='s'):svg.append(f'<text x="{x}" y="{y}" class="{c}">{escape(s)}</text>')
    def box(x,y,w,h,c='box'):svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" class="{c}"/>')
    text(40,50,'ACT-09 | Detect, retain, then isolate the physical output','h');text(40,84,'Proposed architecture | No native amendment | Missing QUAL_OK / ACK sources stay disabled','sub')
    box(40,112,1200,62,'hold');text(58,139,'Finite observer power does not guarantee disable through an indefinite brownout.','t');text(58,164,'A separate output boundary must take over before the stored energy expires. No circuit is accepted here.')
    box(40,202,365,125);text(58,234,'Main +3V3: sense upstream','t');text(58,268,'Keep actual UV / OV observation.');text(58,298,'A short must not drain held storage.')
    box(455,202,365,125);text(473,234,'Proposed reverse-blocked island','t');text(473,268,'Reference, observer and fault memory');text(473,298,'Independent guard starts reference.')
    box(870,202,370,125,'hold');text(888,234,'Charge, OV and input paths: OPEN','t');text(888,268,'Blocking is not OV protection.');text(888,298,'All injected current needs bounds.')
    svg.append('<path d="M405 263H449 M820 263H864" class="line"/>')
    box(40,365,365,183);text(58,397,'1. Detect before validity is lost','t');text(58,432,'Declared amplitude, duration and slew');text(58,464,'Sense / reference / supply applicability');text(58,496,'Fast inhibit is a separate path.');text(58,527,'400 ns is an allocation, not a guarantee.')
    box(455,365,365,183);text(473,397,'2. Retain a detected fault','t');text(473,432,'Keep clear through reference changes.');text(473,464,'Fresh healthy epoch after each loss');text(473,496,'QUAL release -> guard -> ACK');text(473,527,'ACK with ARM low -> guard -> ARM')
    box(870,365,370,183,'hold');text(888,397,'3. Establish physical disable','t');text(888,432,'U14 remains on original main +3V3.');text(888,464,'Do not clamp its push-pull output.');text(888,496,'Isolate invalid drive before TXU OE.');text(888,527,'Retain R40; exact circuit still OPEN.')
    svg.append('<path d="M405 455H449 M820 455H864" class="line"/>')
    box(40,586,580,150);text(58,618,'Same-rail observation deadline','t');text(58,653,f"3.071938 V to 3.005 V: {same['headroom_V']*1000:.3f} mV");text(58,684,f"400 ns zero-margin ceiling: {same['maximum_slew_V_per_us']:.6f} V/us");text(58,715,'This ceiling is not a held-island guarantee.')
    box(660,586,580,150);text(678,618,'Held island: a finite handover interval','t');text(678,653,'100 us handover budget; fast inhibit is still separate.');text(678,684,f"Zero-margin effective C: {island['effective_capacitance_at_zero_margin_F']*1e6:.3f} uF");text(678,715,'ESR, leakage, load and final disable remain unqualified.')
    box(40,774,1200,85);text(58,805,'Explorer: startup, bounce, held ACK, conflicting edges, unknown receiver and guard loss','t');text(58,837,'All displayed states are requests. Unknown inputs block qualification; timing conflicts invalidate the trace.')
    box(40,894,1200,58,'hold');text(58,920,'Next circuit task: exact U14-to-TXU0102 permission boundary under partial power.','t');text(58,944,'Then close island charging, reverse blocking, overvoltage and reference shutdown before native insertion.')
    svg.append('</svg>')
    html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ACT-09 request sequence explorer</title><style>
:root{font-family:system-ui,sans-serif;color:#172638;background:#edf3f7}*{box-sizing:border-box}body{margin:0}main{max-width:1120px;margin:auto;padding:28px}h1{font-size:clamp(1.6rem,4vw,2.5rem);margin:.3em 0}h2{font-size:1.2rem}p{line-height:1.6}a{color:#065f7d}.eyebrow{letter-spacing:.13em;font-size:.8rem;color:#425874}.notice{padding:16px;background:#fff5e7;border-left:4px solid #ac650a;border-radius:5px}.panel{padding:22px;margin:20px 0;background:white;border:1px solid #cbd8e3;border-radius:12px}.controls{display:flex;gap:12px;flex-wrap:wrap;align-items:end}label{display:grid;gap:7px;flex:1;min-width:180px}select,button{font:inherit;padding:10px;border:1px solid #91a9bd;border-radius:6px;max-width:100%;background:white}button{cursor:pointer}button:disabled{opacity:.45;cursor:default}select{width:100%}dl{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}dl div{background:#f0f6fa;border-radius:8px;padding:14px}dt{font-size:.85rem}dd{margin:8px 0 0;font-weight:700}.table-wrap{overflow:auto;max-width:100%}table{border-collapse:collapse;width:100%;min-width:650px;font-size:.9rem}th,td{text-align:left;padding:11px;border-bottom:1px solid #dbe4eb}th{background:#eaf1f6}tr.current{background:#dff1f4}#detail{overflow-wrap:anywhere}.muted{color:#496177}.status{font-weight:700}.links{display:flex;gap:18px;flex-wrap:wrap}@media(max-width:620px){main{padding:16px}.panel{padding:16px}dl{grid-template-columns:1fr 1fr}.controls label{flex-basis:100%}}
</style><main><p class="eyebrow">LORA LAB / ACT-09 / CONDITIONAL ARCHITECTURE</p><h1>Retain the fault through power loss</h1><p>Inspect the requested sequence before designing the physical permission boundary.</p><p class="notice"><strong>Request model only.</strong> This does not simulate physical OE, analog glitches or motor stopping. Finite hold-up cannot cover an indefinite brownout. ACT-04 remains the native candidate; missing qualification sources stay disabled.</p><div class="links"><a href="README.md">Architecture and source limits</a><a href="RESULTS.md">Calculation tables</a><a href="v2_observer_retention.svg">Annotated map</a><a href="../../../pm/index.html">Engineering workspace</a></div><section class="panel"><div class="controls"><label>Recorded scenario<select id="case"></select></label><button id="previous">Previous event</button><button id="next">Next event</button><button id="restart">Restart trace</button></div><p id="position" class="muted"></p><p id="status" class="status" aria-live="polite"></p><dl id="signals"></dl><p id="detail"></p></section><section class="panel"><h2>Event requests</h2><p class="muted">Time is relative to the trace start. Each tick evaluates a request; no continuous physical waveform is implied.</p><div class="table-wrap"><table><thead><tr><th>Time (us)</th><th>Reference</th><th>Qualification</th><th>READY</th><th>Output enable</th><th>Guard checks</th></tr></thead><tbody id="rows"></tbody></table></div></section><section class="panel"><h2>What must exist in circuitry</h2><p>Independent island-power authority, verified reference validity, main 3V3 and local 5V observation, receiver readiness, watchdog and stop continuity. After valid clear and a fresh healthy interval: release qualification, wait the recovery guard, accept a new ACK with ARM low, then accept a later ARM edge.</p><p>U14 still uses main 3V3. A hold-up capacitor on the observer does not make U14 valid during collapse. An exact output-isolation boundary must prevent invalid drive and remain disabled after stored energy expires.</p></section></main><script id="packet" type="application/json">__DATA__</script><script>
const DATA=JSON.parse(document.getElementById('packet').textContent);window.MODEL=DATA;const demos=DATA.demonstrations,select=document.getElementById('case');let step=0;const labels={healthy_startup_ack_arm:'Healthy startup, new ACK, then ARM',fault_bounce_fresh_requalification:'Fault and bounce require a fresh epoch',held_ack_blocks:'Held ACK cannot grant a new permission',coincident_release_ack_unqualified:'ACK at release: outside timing contract',unknown_receiver_blocks:'Unknown receiver blocks qualification',guard_loss_reference_off:'Guard loss requests reference shutdown'};const keys=['REF_EN_requested','QUAL_requested','READY_requested','OUTPUT_ENABLE_requested'];const names=['Reference power','Qualification','Latch READY','Output enable'];const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const level=v=>v?'High requested':'Low requested';for(const name of Object.keys(demos)){const o=document.createElement('option');o.value=name;o.textContent=labels[name]||name;select.append(o)}function render(){const d=demos[select.value],r=d.trace[step];window.CURRENT=r;document.getElementById('position').textContent=`Event ${step+1} of ${d.trace.length} | ${(r.t_ns/1000).toFixed(3)} us`;document.getElementById('status').textContent=r.timing_contract_met_so_far?'Modeled guards met; pulse widths unverified':'Outside modeled guards: actuator permission locked low; reference follows its guard';document.getElementById('signals').innerHTML=keys.map((k,i)=>`<div><dt>${names[i]}</dt><dd>${level(r[k])}</dd></div>`).join('');const absent=Object.entries(r.inputs).filter(([k,v])=>!['ack','arm'].includes(k)&&v!==true).map(([k])=>k);document.getElementById('detail').textContent=(r.note?r.note+' ':'')+(absent.length?'Unavailable health inputs: '+absent.join(', ')+'. ':'All modeled health predicates are true. ')+(r.new_timing_violations.length?'Timing conflicts: '+r.new_timing_violations.join(', ')+'.':'')+' Physical output state is unproven.';document.getElementById('rows').innerHTML=d.trace.map((v,i)=>`<tr class="${i===step?'current':''}"><td>${(v.t_ns/1000).toFixed(3)}</td>${keys.map(k=>`<td>${v[k]?'High':'Low'}</td>`).join('')}<td>${v.timing_contract_met_so_far?'Guards met':'Unqualified'}</td></tr>`).join('');document.getElementById('previous').disabled=step===0;document.getElementById('next').disabled=step===d.trace.length-1}select.onchange=()=>{step=0;render()};document.getElementById('previous').onclick=()=>{step--;render()};document.getElementById('next').onclick=()=>{step++;render()};document.getElementById('restart').onclick=()=>{step=0;render()};render();
</script></html>'''.replace('__DATA__',json.dumps(a,ensure_ascii=True,allow_nan=False).replace('<','\\u003c'))
    return {'RESULTS.md':results,'v2_observer_retention.svg':'\n'.join(svg)+'\n','index.html':html+'\n'}
def check_inputs():
    i=read('input_manifest.json');assert len(i['input_sha256'])==257
    for n,h in i['input_sha256'].items():assert sha(ROOT/n)==h,'Preserved input changed: '+n
    assert read('analysis.json')==collect(),'Stale analysis'
    c=read('contract.json')
    for k in ['candidate_electrical_delta','live_electrical_delta','live_copper_delta']:assert c[k]==0,k
    for k in ['native_accepted','hardware_accepted','parts_selected','qualification_ports_implemented','native_commands_rerun']:assert c[k] is False,k
    return i
if __name__=='__main__':
    ap=argparse.ArgumentParser();g=ap.add_mutually_exclusive_group(required=True)
    for mode in ['render','capture','check']:g.add_argument('--'+mode,action='store_true')
    args=ap.parse_args()
    for n,s in outputs(collect()).items():
        if args.render:write(n,s)
        else:assert (HERE/n).read_text(encoding='utf-8')==s,'Stale output: '+n
    inp=check_inputs()
    if not args.render:
        artifacts={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='packet_manifest.json' and '__pycache__' not in p.parts}
        m={'revision':'ACT-09','source_revision':inp['source_revision'],'input_sha256':inp['input_sha256'],'artifact_sha256':artifacts,'candidate_electrical_delta':0,'live_electrical_delta':0,'live_copper_delta':0,'parts_selected':False,'native_commands_rerun':False,'qualification_ports_implemented':False,'hardware_tested':False,'fabrication_approved':False}
        if args.capture:write('packet_manifest.json',json.dumps(m,indent=2)+'\n')
        else:assert read('packet_manifest.json')==m,'Artifact hashes changed'
    print('PASS ACT-09 deterministic outputs and 257 preserved inputs; no physical-output acceptance')
