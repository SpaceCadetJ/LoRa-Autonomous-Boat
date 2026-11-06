"""Portable captured-topology and conditional SENSE-01 replay; no native tools."""
from pathlib import Path
import argparse, hashlib, json, xml.etree.ElementTree as ET
import model
P = Path(__file__).resolve().parent
ROOT = P.parents[2]
ZERO = ('candidate_electrical_delta', 'live_electrical_delta', 'live_copper_delta')
FALSE = ('native_commands_rerun', 'hardware_accepted', 'fabrication_approved', 'procurement_approved', 'protection_qualified', 'qualification_ports_implemented', 'adc_implemented', 'current_range_qualified', 'voltage_range_qualified')
def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name, value): (P/name).write_text(value if isinstance(value,str) else json.dumps(value,indent=2)+'\n', encoding='utf-8',newline='\n')
def check_hashes(entries):
    for name, expected in entries.items():
        assert sha(ROOT/name) == expected, 'Changed captured evidence: '+name

def collect():
    inputs = read(P/'input_manifest.json'); check_hashes(inputs['input_sha256'])
    c = read(P/'contract.json')
    assert c['revision']=='SENSE-01' and c['electrical_candidate']=='VSERVO-01' and c['presentation_candidate']=='POWER-DOC-01'
    assert all(c[k]==0 for k in ZERO) and all(c[k] is False for k in FALSE)
    path=ROOT/'reviews/codex/power_sheet_polish/native/netlist.xml'; xml=ET.parse(path)
    comps={n.get('ref'): n for n in xml.findall('./components/comp')}; members={}; pins={}
    assert len(comps)==128
    for net in xml.findall('./nets/net'):
        members[net.get('name')]=[]
        for node in net.findall('node'):
            pin=node.get('ref')+'.'+node.get('pin'); assert pin not in pins
            pins[pin]={'net':net.get('name'),**node.attrib}; members[net.get('name')].append(pin)
    assert len(pins)==429
    for name, expected in c['expected_complete_members'].items():
        assert sorted(members[name])==sorted(expected), 'Net boundary changed: '+name
    identities={}
    for ref, expected in c['components'].items():
        comp=comps[ref]; fields={n.get('name'):n.text for n in comp.findall('./fields/field')}
        assert [comp.findtext('value'),fields['MPN']]==expected, 'Component identity changed: '+ref
        identities[ref]={'value':comp.findtext('value'),'MPN':fields['MPN'],'footprint':comp.findtext('footprint'),'datasheet_field':comp.findtext('datasheet')}
    returns={'R32.2':'GND','C36.2':'GND','C37.2':'GND','U8.2':'GND','U8.5':'+3V3','U1.13':'/MCU/VDDA','U1.12':'GND'}
    assert all(pins[pin]['net']==net for pin,net in returns.items())
    assert pins['U1.16']['pinfunction']=='PA2' and pins['U1.20']['pinfunction']=='PA4'
    pop=read(ROOT/'reviews/codex/power_sheet_polish/population_contract.json')
    assert pop['dual_population_allowed'] is False and pop['base_schematic_dnp_refs']==['D4','D9']
    assert pop['variants']['BEC_ONLY']['D4']=='DNP' and pop['variants']['BEC_ONLY']['D9']=='POPULATE'
    assert pop['variants']['ONBOARD']['D4']=='POPULATE' and pop['variants']['ONBOARD']['D9']=='DNP'
    firmware=read(P/'firmware_capture.json')
    for record in firmware['files'].values(): assert sha(ROOT/record['snapshot'])==record['sha256'], 'Firmware snapshot changed'
    a=model.collect()
    assert all(value is None for value in a['unknown_actual_inputs'].values())
    assert all(item['status']=='unavailable' and item['hardware_accepted'] is False for item in a['actual'].values())
    return {'revision':'SENSE-01','classification':'captured_topology_and_manufacturer_review_with_conditional_calculations',
        **{key:c[key] for key in ZERO+FALSE},'preserved_input_count':len(inputs['input_sha256']),
        'topology':{'source':path.relative_to(ROOT).as_posix(),'sha256':sha(path),'components':identities,'complete_net_members':c['expected_complete_members'],'additional_pins':returns,'checked_pin_count':sum(map(len,c['expected_complete_members'].values()))+len(returns),'source_populations_exclusive':True},
        'firmware':firmware,'calculations':a,
        'findings':[
            {'id':'SENSE-BND','status':'verified_captured_topology','finding':'Voltage is post-D12 VIN_RAW; current is shared converter-input branch. BEC_ONLY and external propulsion do not pass through R33.'},
            {'id':'SENSE-RANGE','status':'conditional_range_not_qualified','finding':'Worst1% divider ratio is compared to explicit illustrative reference floors; actual VDDA/transient/error budgets remain unavailable.'},
            {'id':'SENSE-LOAD','status':'source_review_stability_unqualified','finding':'Nominal100nF is100 times TI listed1nF typical capacitive-load capability. No measured oscillation or guaranteed maximum is inferred.'},
            {'id':'SENSE-PART','status':'source_review_identity_inconsistency','finding':'R33 field1W differs from exact Bourns MPN3W@70C rating. C36/C37 exact orderable identities remain unverified; no BOM or thermal release.'},
            {'id':'SENSE-OFF','status':'power_state_qualification_open','finding':'PA2 FT and PA4 TTa need distinct analog/off-state analysis; internal diodes and unpowered amplifier output are not qualified isolation/protection.'},
            {'id':'SENSE-SW','status':'reviewed_captured_source','finding':'Captured Stage A has no ADC acquisition/calibration; proposed future telemetry must name actual measurement boundaries.'}]}

def outputs(e):
    a=e['calculations']; d=a['divider']; f=a['divider_filter_nominal']; adc=a['adc_illustration']
    lines=['# SENSE-01 — conditional ADC calculations','','[Review guide](README.md) | [Measurement boundary](sensing_boundary.svg) | [Machine-readable evidence](evidence.json)','','All actual supply, transient, sample-time and error-budget fields remain unavailable. These are nominal or resistor-corner calculations, not accepted limits. No native circuit or firmware was changed.','','## Divider range','','| VIN_RAW allocation | Assumed VDDA minimum | Worst resistor output | Arithmetic headroom |','|---|---|---|---|']
    for v in a['voltage_cases']:
        lines.append(f"| {v['inputs']['vin_raw_max_v']:.3f} V | {v['inputs']['vdda_min_v']:.3f} V | {v['adc_max_v']:.6f} V | {v['headroom_v']:.6f} V |")
    lines += ['',f"R31/R32 nominal ratio {d['ratio_nominal']:.9f}; independent ±1% bounds {d['ratio_min']:.9f}…{d['ratio_max']:.9f}. Both reference floors are illustration inputs, not measured or guaranteed board rails. Positive margin excludes leakage, temperature, reference and ADC error.",'','| Assumed reference | Raw-input equality ceiling at worst ratio |','|---|---|']
    for v in a['voltage_cases'][:2]:lines.append(f"| {v['inputs']['vdda_min_v']:.3f} V | {v['input_ceiling_v']:.6f} V |")
    lines += ['','Equality leaves zero margin. These ceilings do not supersede U8 common-mode limits or protection requirements. Battery-terminal voltage is different from VIN_RAW.','','## Distinct settling models','',f"Nominal Rth = {f['rth_ohm']:.6f} Ω; with assumed 100nF, τ = {f['tau_s']*1e6:.6f} µs and cutoff = {f['fc_hz']:.6f} Hz. Exact C36 identity/effective capacitance remain unqualified.",'','| Ideal external RC step | Time to ¼ LSB at 12 bits / 3.3V |','|---|---|']
    for case in a['divider_settling_cases']:lines.append(f"| {case['description']} | {case['settling_time_s']*1000:.6f} ms |")
    lines += ['',f"Separately, ST's resistive-source expression with allocated 30MHz, RAIN={f['rth_ohm']:.3f}Ω, RADC=6kΩ, CADC=7pF and N=12 gives k_min={adc['k_min_cycles']:.6f} cycles ({adc['equivalent_time_s']*1e6:.6f}µs). It does not model the external 100nF capacitor, amplifier dynamics, channel kickback or repeated scanning. No sample-time setting is selected or validated.",'','The current channel has no captured output-series resistor: do not assign it a fictitious passive RC cutoff. Direct nominal C37 load is 100× TI listed typical capability, with stability unmeasured.','','## Current-channel ideal transfer','','| Converter input current allocation | Ideal OUT | Shunt drop | Shunt loss |','|---|---|---|---|']
    for v in a['shunt_examples']:lines.append(f"| {v['inputs']['current_a']:.1f} A | {v['ideal_output_v']:.3f} V | {v['shunt_drop_v']:.3f} V | {v['shunt_loss_w']:.3f} W |")
    lines += ['','Ideal 0.4V/A is not an accepted measurement range. Gain/offset/common-mode/swing, reverse current, thermal capability, sequence and ADC errors remain open. The exact R33 MPN 3W rating does not raise board-current permission.','','## Evidence and next task','',f"Portable comparison checks {e['topology']['checked_pin_count']} pin memberships across four complete sensing/feed nets plus supply/return pins, seven component identities and exclusive source populations. It preserves {e['preserved_input_count']} previous hashes and replays three captured Stage A files. No fresh native or hardware checks are claimed.",'','Next qualify exact C36/C37 identities and U8 isolation/filter/bypass values, then amend a new isolated copy with explicit net delta and native checks; reconcile R33 rating annotation. Preserve 6S, both converter sheets, C11 lands, populations, disabled qualifications and separate IMU2.','']
    return {'evidence.json':json.dumps(e,indent=2)+'\n','RESULTS.md':'\n'.join(lines)}

def main():
    parser=argparse.ArgumentParser(); modes=parser.add_mutually_exclusive_group(required=True)
    for mode in ('render','capture','check'):modes.add_argument('--'+mode,action='store_true')
    args=parser.parse_args(); e=collect()
    for name,value in outputs(e).items():
        if args.render:write(name,value)
        else:assert (P/name).read_text(encoding='utf-8')==value,'Stale output: '+name
    if not args.render:
        check_hashes(read(P/'review_notes.json')['reviewed_sha256'])
        check_hashes(read(P/'viewer_check.json')['input_sha256'])
        if args.capture:
            for original,record in read(P/'firmware_capture.json')['files'].items():assert sha(ROOT/original)==record['sha256'],'Live firmware changed before capture'
        artifacts={f.relative_to(ROOT).as_posix():sha(f) for f in sorted(P.rglob('*')) if f.is_file() and f.name!='packet_manifest.json' and '__pycache__' not in f.parts}
        m={'revision':'SENSE-01','source_revision':read(P/'input_manifest.json')['baseline_head'],'electrical_candidate':'VSERVO-01','presentation_candidate':'POWER-DOC-01','input_sha256':read(P/'input_manifest.json')['input_sha256'],'artifact_sha256':artifacts,**{k:e[k] for k in ZERO+FALSE}}
        if args.capture:write('packet_manifest.json',m)
        else:assert read(P/'packet_manifest.json')==m,'Packet bytes/coverage changed'
    print(f"PASS SENSE-01: {e['topology']['checked_pin_count']} pins, seven identities, {e['preserved_input_count']} preserved inputs; conditional ADC review only")
if __name__=='__main__': main()
