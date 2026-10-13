"""Render deterministic allocation evidence; verify exact preserved inputs."""
from pathlib import Path
import argparse, hashlib, json
from model import collect
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def read(name): return json.loads((HERE/name).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,text): (HERE/name).write_text(text,encoding='utf-8',newline='\n')
def outputs(a):
    rows=[]
    for rail in ('UV','OV'):
        for event in ('assert','recover'):
            lo,hi=a['thresholds_V'][rail][event]
            rows.append(f'| {rail} {event} | {lo:.9f} | {hi:.9f} |')
    ramp=[]
    for c in a['ramp_cases']:
        ramp.append(f"| {c['slew_V_per_us']:g} | {c['residual_V']['UV']*1000:.3f} | {c['residual_V']['OV']*1000:.3f} | {'Fits allocation' if c['conditional_allocation_pass'] else 'Exhausts allocation'} |")
    txt='''# ACT-07 calculated allocation

These are conditional requirements calculations. No component, circuit, arbitrary ramp or powered application is qualified. Source conditions and unverified allocations are in [the guide](README.md) and [contract](contract.json).

## Threshold bounds

| Event | Minimum V | Maximum V |
|---|---:|---:|
'''+ '\n'.join(rows)+'''\n
Reference 2.5 V +/-0.2%; comparator equivalent offset +/-10 mV; full hysteresis 0..4 mV; signed bias 5 nA; independent resistor errors+/-0.35%. Divider 249 ohm / 1k for UV and 402 ohm / 1k for OV. These are allocations, not sourced guarantees.

| Margin | mV |
|---|---:|
'''+ '\n'.join(f'| {k} | {v*1000:.3f} |' for k,v in a['margins_V'].items())+'''\n
## Overdrive before the time budget

Use latest assertion and maximum divider multiplier independently: a conservative cross-corner envelope, not necessarily one physical corner. Reserve 20 mV input overdrive converted to the rail, then 400 ns (55 ns detector + 245 ns downstream + 100 ns sensing allocation).

| Direction | Rail at allocated overdrive V | Headroom mV | Zero-margin slope ceiling V/us |
|---|---:|---:|---:|
'''+ '\n'.join(f"| {k} | {a['overdrive_screen']['rail_amplitude_V'][k]:.9f} | {a['overdrive_screen']['headroom_to_corridor_V'][k]*1000:.3f} | {a['maximum_slew_V_per_us'][k]:.9f} |" for k in ('UV','OV'))+'''\n
| Illustrative slew V/us | UV residual mV | OV residual mV | Arithmetic disposition |
|---|---:|---:|---|
'''+ '\n'.join(ramp)+'''\n
Strictly positive margin is required. The zero-margin slope ceiling is not an accepted waveform specification. This model does not establish that a step-test delay applies to ramps. Sense dynamics, pulse duration, supply/common mode/loading, retention, monitor shutdown and receiver response remain open. Negative residual means this allocation fails, not a prediction of measured hardware failure.

## Reproduction

Run `python -B reviews/codex/observation_3v3/model.py --check` to reproduce [analysis.json](analysis.json). The adjacent test_model.py exercises numerical fixtures and rejected claims. Follow [ACCEPTANCE.md](ACCEPTANCE.md) for unresolved conditions.
'''
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="1000" viewBox="0 0 1280 1000"><rect width="1280" height="1000" fill="#f4f7fb"/><style>text{font-family:Arial,sans-serif;fill:#172638}.h{font-size:30px;font-weight:bold}.sub{font-size:18px;fill:#425874}.t{font-size:20px}.s{font-size:17px}.line{stroke:#246789;stroke-width:3;fill:none}.box{fill:white;stroke:#9bb3c9;stroke-width:2}.hold{fill:#fff5e7;stroke:#b86e12;stroke-width:2;stroke-dasharray:8 5}</style>']
    def text(x,y,t,cls='s'): svg.append(f'<text x="{x}" y="{y}" class="{cls}">{t}</text>')
    def box(x,y,w,h,cls='box'): svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" class="{cls}"/>')
    text(40,52,'ACT-07 | 3.3 V observation allocation','h')
    text(40,86,'Functional proposal only · no native connection · ACT-04 QUAL_OK / ACK remain low','sub')
    box(40,115,1200,62,'hold');text(58,141,'Exact investigation parts: TLV3202AIDGKR + REF3425IDBVR','t');text(58,165,'Resistors, supply / EN strategy, bypass, retention and partial-power behavior are not accepted.')
    box(40,204,290,125);text(58,232,'UV divider: 249 ohm / 1k','t');text(58,262,'Observed +3V3 to top resistor');text(58,289,'Sense node to 1k to GND');text(58,314,'Nominal center: 3.1225 V')
    box(40,355,290,125);text(58,383,'OV divider: 402 ohm / 1k','t');text(58,413,'Observed +3V3 to top resistor');text(58,440,'Sense node to 1k to GND');text(58,465,'Nominal center: 3.5050 V')
    box(390,204,375,276);text(408,233,'Comparator · supply unresolved','t');text(408,268,'Channel 1: +pin3 UV / -pin2 REF');text(408,299,'pin1 UV_OK goes LOW on UV','t');text(408,368,'Channel 2: +pin5 REF / -pin6 OV');text(408,399,'pin7 OV_OK goes LOW on OV','t');text(408,446,'pin4 GND · pin8 monitor supply')
    svg.append('<path d="M330 273H384 M330 422H384" class="line"/>')
    box(825,204,415,276,'hold');text(843,235,'Separate push-pull outputs','t');text(843,268,'Do not wire outputs together.');text(843,299,'Future AND + retained-clear interface');text(843,336,'LOCAL_3V3_OK is only a proposal.','t');text(843,372,'Missing 5V / receiver / watchdog /');text(843,398,'stop / ACK qualifications stay disabled.');text(843,447,'No connection to QUAL_OK is made.')
    svg.append('<path d="M765 290H819 M765 391H819" stroke="#b86e12" stroke-width="2" stroke-dasharray="7 5"/>')
    box(40,508,1200,132);text(58,539,'Reference / power: settle before permission; include charged output capacitance','t');text(58,571,'REF3425: OUT_F6 / OUT_S5 at reference node; GND_F1 / GND_S2 at ground; IN4 and EN3 unresolved.');text(58,601,'0.2% reference allocation; about 0.14905% already consumed by initial error + full-span BOX drift.');text(58,626,'Slow supply ramps and dead-comparator input clamps require a power-state review.')
    box(40,667,1200,196);text(58,699,'Conditional fault budget: 20 mV sense overdrive, then 400 ns total response','t')
    for i,k in enumerate(('UV','OV')):
        x=58+i*590
        text(x,737,f"{k}: allocated overdrive at {a['overdrive_screen']['rail_amplitude_V'][k]:.6f} V",'t')
        text(x,771,f"Headroom to corridor: {a['overdrive_screen']['headroom_to_corridor_V'][k]*1000:.3f} mV")
        text(x,805,f"Zero-margin slope ceiling: {a['maximum_slew_V_per_us'][k]:.6f} V/us")
    text(58,842,'0.01 V/us fits the arithmetic · 0.1 V/us exhausts OV · 1 V/us exhausts both')
    box(40,890,1200,76,'hold');text(58,920,'A passing calculation is not a ramp-response or startup guarantee.','t');text(58,949,'Next: close comparator applicability and monitor/reference power states against this allocation.')
    svg.append('</svg>')
    return {'RESULTS.md':txt,'v2_observation_3v3.svg':'\n'.join(svg)+'\n'}
def check_inputs():
    inp=read('input_manifest.json');assert len(inp['input_sha256'])==218
    for name,h in inp['input_sha256'].items(): assert sha(ROOT/name)==h, 'Preserved input changed: '+name
    c=read('contract.json')
    for k in ['candidate_electrical_delta','live_electrical_delta','live_copper_delta']: assert c[k]==0,k
    for k in ['native_accepted','hardware_accepted','parts_selected','qualification_ports_implemented','native_commands_rerun']: assert c[k] is False,k
    assert read('analysis.json')==collect(), 'Stale analysis'
    return inp
if __name__=='__main__':
    ap=argparse.ArgumentParser();g=ap.add_mutually_exclusive_group(required=True);g.add_argument('--render',action='store_true');g.add_argument('--capture',action='store_true');g.add_argument('--check',action='store_true');args=ap.parse_args()
    for name,content in outputs(collect()).items():
        if args.render: write(name,content)
        else: assert (HERE/name).read_text(encoding='utf-8')==content, 'Stale rendered result: '+name
    inp=check_inputs()
    if not args.render:
        artifacts={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='packet_manifest.json' and '__pycache__' not in p.parts}
        manifest={'revision':'ACT-07','source_revision':inp['source_revision'],'input_sha256':inp['input_sha256'],'artifact_sha256':artifacts,'candidate_electrical_delta':0,'live_electrical_delta':0,'live_copper_delta':0,'parts_selected':False,'native_commands_rerun':False,'qualification_ports_implemented':False,'hardware_tested':False,'fabrication_approved':False}
        if args.capture: write('packet_manifest.json',json.dumps(manifest,indent=2)+'\n')
        else: assert read('packet_manifest.json')==manifest,'Packet artifacts changed'
    print('PASS ACT-07 rendering and 218 preserved inputs; conditional allocation only')
