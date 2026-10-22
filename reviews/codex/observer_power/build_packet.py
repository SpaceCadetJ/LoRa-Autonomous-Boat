"""Render deterministic ACT-08 screens; preserve all prior circuit evidence."""
from pathlib import Path
import argparse, hashlib, json
from html import escape
from model import artifact
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
def read(name): return json.loads((HERE/name).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name, text): (HERE/name).write_text(text, encoding='utf-8', newline='\n')
def outputs(a):
    load, alloc, decay = a['reference_load'], a['reference_allocation'], a['discharge']
    cases = a['series_input']['cases']
    rows = []
    for c in decay['cases']:
        time = f"{c['time_to_target_s']*1000:.6f}" if c['target_reachable'] else 'Unreachable'
        rows.append(f"| {c['feed_A']*1e6:g} | {c['floor_V']:.9f} | {time} |")
    series = []
    for c in cases:
        current = c['ideal_zero_V_node_current_ceiling_A_per_input']*1000
        series.append(f"| {c['nominal_ohm']:g} | {current:.6f} | {current*2:.6f} | {c['steady_bias_error_V_per_input']*1e6:.4f} | {c['settling_time_ns']:.6f} | {'Fits this pole only' if c['fits_allocated_sense_budget_only'] else 'Exceeds allocation'} |")
    txt = f'''# ACT-08 calculated power-state screens

These calculations are conditional proposals. They do not establish startup, shutdown, diode behavior, rail voltage, valid outputs or hardware acceptance. Read the [connection and power-state guide](README.md), [source conditions](sources.json) and [explicit allocations](contract.json).

## Settled reference load and error allocation

| Quantity | Calculated value |
|---|---:|
| Bleeder minimum / maximum | {load['resistance_min_ohm']:.3f} / {load['resistance_max_ohm']:.3f} ohm |
| Sourcing current including two allocated input biases | {load['minimum_sourcing_A']*1000:.9f} .. {load['maximum_sourcing_A']*1000:.9f} mA |
| Bleeder maximum dissipation | {load['bleeder_power_max_W']*1000:.6f} mW |
| Sourcing-test supply boundary | {load['source_test_min_supply_V']:.3f} V |
| Minimum normal-rail headroom above that boundary | {load['minimum_normal_rail_headroom_margin_V']*1000:.6f} mV |
| Initial accuracy plus full-span BOX allocation | {alloc['initial_plus_BOX_fraction']*1e6:.6f} ppm |
| Full line test span | {alloc['specified_line_span_V']:.3f} V |
| Line term at 15 ppm/V | {alloc['line_regulation_fraction']*1e6:.6f} ppm |
| Sourcing-load term at 30 ppm/mA | {alloc['load_regulation_fraction']*1e6:.6f} ppm |
| Linear sum | {alloc['linear_sum_fraction']*1e6:.6f} ppm |
| Remaining within 0.2% allocation | {alloc['remaining_fraction']*1e6:.6f} ppm |

The REF34 electrical header uses VIN = VOUT + VDO. The 12 V endpoint is charged across the whole line-test span, not treated as the initial-accuracy test point. The 3.005 V boundary preserves 500 mV sourcing-test headroom at maximum allocated reference voltage; it is not actual dropout. The remaining allocation does not qualify aging, noise, assembly or unverified application conditions. The proposed effective capacitor range differs from the 10 uF table condition; transient applicability remains open.

## Discharge with constant feed

Worst allocated R = {decay['resistance_ohm']:.3f} ohm, effective C = {decay['capacitance_F']*1e6:.3f} uF, initial = {decay['initial_V']:.3f} V. Maximum RC time constant = {decay['time_constant_s']*1e6:.6f} us.

`V(t) = R*I_feed + (V_initial - R*I_feed)*exp(-t/(R*C))`

| Assumed continuing feed (uA) | Final floor (V) | Time to 0.3 V (ms) |
|---|---:|---:|
'''+ '\n'.join(rows)+'''

Finite discharge requires the floor to be strictly below the target. The 0.3 V endpoint is a calculation target, not a permitted pin voltage. All rows assume the reference has stopped driving, initial voltage is bounded and feed is constant. No listed feed is an accepted real leakage limit. Startup/shutdown anomalies or an active source invalidate this model.

## Series resistance tradeoff

Two independent reference inputs; each allocated 5 nA bias and 10 pF capacitance. Current ceilings assume a nonnegative receiving node and reference no higher than 2.505 V. They do not model a diode threshold or bound phantom supply voltage.

| Series resistance (ohm) | Current ceiling per input (mA) | Two-input ceiling (mA) | Added bias error per input (uV) | 1% settling (ns) | Against 100 ns allocation |
|---|---:|---:|---:|---:|---|
'''+ '\n'.join(series)+'''

This single-pole calculation excludes reference source impedance and other parasitics. The 1 kOhm option fits only that calculation; the 10 kOhm option exceeds it. Neither establishes total fault delay, a powered-off state or common-mode/bias applicability. Do not use TLV3202 absolute input-current limits as Ioff qualification. Comparator behavior below 2.7 V, differential input exceeding supply and both injection paths require explicit review.

## Reproduce

Run `python -B reviews/codex/observer_power/test_model.py`, `python -B reviews/codex/observer_power/model.py --check`, and `python -B reviews/codex/observer_power/build_packet.py --check`. The [analysis](analysis.json) binds the exact contract; the [packet manifest](packet_manifest.json) binds preserved inputs and artifacts. No native circuit or hardware check is represented by these commands.
'''
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="1040" viewBox="0 0 1280 1040"><rect width="1280" height="1040" fill="#f4f7fb"/><style>text{font-family:Arial,sans-serif;fill:#172638}.h{font-size:30px;font-weight:bold}.sub{font-size:18px;fill:#425874}.t{font-size:20px;font-weight:bold}.s{font-size:17px}.wire{stroke:#246789;stroke-width:3;fill:none}.hold{fill:#fff5e7;stroke:#b86e12;stroke-width:2;stroke-dasharray:8 5}.box{fill:white;stroke:#9bb3c9;stroke-width:2}</style>']
    def text(x,y,t,cls='s'): svg.append(f'<text x="{x}" y="{y}" class="{cls}">{escape(t)}</text>')
    def box(x,y,w,h,cls='box'): svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" class="{cls}"/>')
    text(40,50,'ACT-08 | Observer reference and power states','h')
    text(40,84,'Functional proposal only | No native connection | ACT-04 QUAL_OK / ACK stay low','sub')
    box(40,108,1200,64,'hold');text(58,135,'Passive loading narrows the problem; it does not guarantee default disable.','t');text(58,160,'Same observed +3V3 supply is proposed for REF3425 and TLV3202. Startup / retained clear are unresolved.')
    # Three separate cards avoid confusing symbolic wires with accepted native circuitry.
    box(40,200,370,246);text(58,232,'1. Reference and defined load','t');text(58,267,'REF3425IDBVR investigation');text(58,296,'IN4 to observed +3V3 (proposed)');text(58,325,'OUT_F6 / OUT_S5 tied at VREF');text(58,354,'GND_F1 / GND_S2 tied at ground');text(58,390,'VREF to 2.49k bleeder to GND');text(58,421,'VREF to effective 0.1..0.264 uF to GND')
    box(455,200,365,246);text(473,232,'2. Two independent input paths','t');text(473,270,'VREF -- 1k -- comparator pin2 (-)');text(473,309,'VREF -- 1k -- comparator pin5 (+)');text(473,348,'Keep ACT-07 UV / OV dividers.');text(473,382,'TLV3202 supply8 to observed +3V3');text(473,421,'Bias / capacitance bounds are allocated.')
    box(865,200,375,246,'hold');text(883,232,'3. Missing retained-low interface','t');text(883,270,'UV_OK pin1 and OV_OK pin7');text(883,309,'Separate push-pull outputs.');text(883,348,'Do not tie outputs together.');text(883,382,'REF EN3, valid delay, clear');text(883,409,'retention and total inhibit: OPEN');text(883,433,'No path to QUAL_OK is made.')
    svg.append('<path d="M410 280H449 M820 280H859" class="wire"/>')
    box(40,474,1200,95,'hold');text(58,504,'Backfeed path to evaluate: charged VREF -> each series resistor -> input clamp -> observed rail','t');text(58,533,'Both pins may inject. A resistor bounds conditional current, not rail voltage, Ioff isolation or output state.');text(58,557,'Bound all supply sources / sinks and retain clear before the 3.005 V reference test-condition boundary.')
    box(40,597,580,173);text(58,628,'Settled load and error screen','t');text(58,663,f"Maximum source load: {load['maximum_sourcing_A']*1000:.6f} mA");text(58,693,f"Bleeder dissipation: {load['bleeder_power_max_W']*1000:.6f} mW");text(58,723,f"Conditional error remainder: {alloc['remaining_fraction']*1e6:.3f} ppm");text(58,751,'Does not qualify startup, aging or reference anomalies.')
    box(660,597,580,173);text(678,628,'Series resistor comparison','t')
    for i,c in enumerate(cases):
        text(678,663+i*30,f"{c['nominal_ohm']:g} ohm: {c['settling_time_ns']:.3f} ns to 1% at allocated 10 pF")
    text(678,723,'1k fits this pole only; 10k exceeds the 100 ns budget.');text(678,751,'Two-input current and added bias are in RESULTS.md.')
    box(40,798,1200,105);text(58,829,'Discharge sensitivity: zero feed is not a shutdown guarantee','t');text(58,861,'Feed: 0 / 10 / 100 / 1000 uA | Time to 0.3 V: 1.400 / 1.451 / 2.511 ms / unreachable');text(58,887,'Model starts only after drive stops. No actual maximum leakage or shutdown waveform is accepted.')
    box(40,932,1200,76,'hold');text(58,961,'Next: explicit retained-low valid interface + reference shutdown / injection strategy.','t');text(58,990,'Define supply, sink / hold-up, feed bounds and timing before exact part selection or native insertion.')
    svg.append('</svg>')
    return {'RESULTS.md':txt,'v2_observer_power.svg':'\n'.join(svg)+'\n'}

def check_inputs():
    inp=read('input_manifest.json'); assert len(inp['input_sha256'])==238
    for name,h in inp['input_sha256'].items(): assert sha(ROOT/name)==h,'Preserved input changed: '+name
    c=read('contract.json')
    for k in ['candidate_electrical_delta','live_electrical_delta','live_copper_delta']: assert c[k]==0,k
    for k in ['native_accepted','hardware_accepted','parts_selected','qualification_ports_implemented','native_commands_rerun']: assert c[k] is False,k
    assert read('analysis.json')==artifact(HERE/'contract.json'),'Stale analysis'
    return inp
if __name__=='__main__':
    ap=argparse.ArgumentParser();g=ap.add_mutually_exclusive_group(required=True)
    for mode in ['render','capture','check']: g.add_argument('--'+mode,action='store_true')
    args=ap.parse_args()
    for name,content in outputs(artifact(HERE/'contract.json')).items():
        if args.render: write(name,content)
        else: assert (HERE/name).read_text(encoding='utf-8')==content,'Stale output: '+name
    inp=check_inputs()
    if not args.render:
        artifacts={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='packet_manifest.json' and '__pycache__' not in p.parts}
        manifest={'revision':'ACT-08','source_revision':inp['source_revision'],'input_sha256':inp['input_sha256'],'artifact_sha256':artifacts,'candidate_electrical_delta':0,'live_electrical_delta':0,'live_copper_delta':0,'parts_selected':False,'native_commands_rerun':False,'qualification_ports_implemented':False,'hardware_tested':False,'fabrication_approved':False}
        if args.capture: write('packet_manifest.json',json.dumps(manifest,indent=2)+'\n')
        else: assert read('packet_manifest.json')==manifest,'Packet artifacts changed'
    print('PASS ACT-08 outputs and 238 preserved inputs; conditional power-state screens only')
