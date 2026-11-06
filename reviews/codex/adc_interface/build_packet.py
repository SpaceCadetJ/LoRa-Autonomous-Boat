"""SENSE-04 immutable evidence, necessary arithmetic and proposed explorer."""
from pathlib import Path
import argparse,hashlib,json,xml.etree.ElementTree as ET
import model
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
ZERO=('candidate_electrical_delta','live_electrical_delta','live_copper_delta')
FALSE=('native_commands_rerun','hardware_accepted','fabrication_approved','procurement_approved','protection_qualified','qualification_ports_implemented','adc_implemented','interface_selected')
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,t):(P/n).write_text(t if isinstance(t,str) else json.dumps(t,indent=2)+'\n',encoding='utf-8',newline='\n')
def hashes(m):
    for n,h in m.items():assert sha(ROOT/n)==h,'Changed captured evidence: '+n

def collect():
    oldpath=ROOT/'reviews/codex/sensing_reference/packet_manifest.json'
    assert sha(oldpath)=='f823b54cf71fe9d58577719c5b24bdf454196172e5130b3745fb8f00acd013b3'
    old=read(oldpath);expected={**old['input_sha256'],**old['artifact_sha256'],oldpath.relative_to(ROOT).as_posix():sha(oldpath)}
    inputs=read(P/'input_manifest.json');assert inputs['input_sha256']==expected and len(expected)==675;hashes(expected)
    c=read(P/'contract.json');assert c['revision']=='SENSE-04' and c['native_candidate']=='SENSE-02'
    assert c['baseline_head']==inputs['baseline_head']=='f0f4702e46c14d55722e0ef01bdcd8966465b3cc'
    assert all(type(c[k]) is int and c[k]==0 for k in ZERO) and all(c[k] is False for k in FALSE)
    assert c['proposed_boundary']['actual_interface_mpn'] is None and c['proposed_boundary']['actual_component_refs'] is None
    assert c['proposed_boundary']['source_side']==['R31.2','R32.1','C36.1'] and c['proposed_boundary']['mcu_side']==['U1.16']
    assert c['required_qualifications']==list(model.REQUIRED_QUALIFICATIONS)
    assert [s['name'] for s in c['states']]==['HOLD','QUALIFY','SETTLE','ACQUIRE','TRIP','REARM']
    assert [s['connect_command'] for s in c['states']]==[False,False,True,True,False,False]
    assert [s['acquire_command'] for s in c['states']]==[False,False,False,True,False,False]
    path=ROOT/'reviews/codex/sensing_filter/native/netlist.xml';x=ET.parse(path)
    net=next(n for n in x.findall('./nets/net') if n.get('name')=='/VBAT_SENSE')
    members=sorted(n.get('ref')+'.'+n.get('pin') for n in net)
    assert members==c['present_complete_members']==['C36.1','R31.2','R32.1','U1.16']
    assert next(n for n in net if n.get('ref')=='U1').get('pinfunction')=='PA2'
    comp={n.get('ref'):n for n in x.findall('./components/comp')}
    assert comp['C36'].findtext('value')=='100nF' and comp['R32'].findtext('value')=='6.8k'
    a=model.collect();assert a['revision']=='SENSE-04'
    assert all(v is None for v in a['unknown_actual_inputs'].values()) and all(v is None for v in a['qualifications'].values())
    assert all(v['available'] is False for v in a['actual'].values()) and a['permission']['enabled'] is False
    assert a['permission']['state_control_implemented'] is False
    assert all(a[k]==0 for k in ZERO) and all(a[k] is False for k in FALSE if k in a)
    signal=read(ROOT/'reviews/codex/sensing_reference/evidence.json')['calculations']['static_cases'][1]['adc_max_v']
    assert all(v['inputs']['signal_peak_v']==signal for v in a['shutdown_examples'])
    return {'revision':'SENSE-04','classification':'proposed_interface_contract_and_necessary_arithmetic','native_candidate':'SENSE-02',**{k:c[k] for k in ZERO+FALSE},'preserved_input_count':675,'captured_topology':{'source':path.relative_to(ROOT).as_posix(),'sha256':sha(path),'net':'/VBAT_SENSE','members':members,'pin_function':'PA2'},'proposed_boundary':c['proposed_boundary'],'states':c['states'],'calculations':a}

def view_model(e):
    a=e['calculations'];slow,fast=a['shutdown_examples'];leak=a['discharge_examples'][1];bleed=a['bleed_examples'][0]
    def card(label,value,note):return {'label':label,'value':value,'note':note}
    scenarios=[{'id':'actual','title':'Actual inputs — unavailable','note':'No example value is substituted for missing actual evidence.','cards':[card('Actual limits','Unavailable','Reference, source, power states, timing, leakage and acquisition remain unqualified.'),card('Proposed acquisition permission','Disabled','Every qualification must be explicitly true; this is no implemented controller.'),card('Native changes','None','SENSE-02, live PCB and firmware remain unchanged.')]},
      {'id':'slow','title':'Slow reference fall (example)','note':'Allocated release 3.35 V, reserve 50 mV, fall 100 V/s and total delay 200 µs. This release floor may be unavailable on the low rail.','cards':[card('Pre-opening margin',f"{slow['headroom_after_delay_v']*1000:.6f} mV",'Positive necessary arithmetic only; post-opening charge and discharge still need proof.'),card('Strict total-delay limit',f"< {slow['strict_delay_limit_s']*1e6:.6f} µs",'Detection plus physical switch opening; no device or delay selected.')]},
      {'id':'fast','title':'Fast reference fall (example)','note':'Same allocations but fall 10000 V/s. Unknown or step collapse cannot be covered by a finite-delay assertion.','cards':[card('Pre-opening margin',f"{fast['headroom_after_delay_v']*1000:.6f} mV",'The allocated 200 µs opening sequence fails this necessary window.'),card('Strict total-delay limit',f"< {fast['strict_delay_limit_s']*1e6:.6f} µs",'This is not a selected detector or switch specification.')]},
      {'id':'leak','title':'Leakage floor (example)','note':'Allocated 100 µA into 6.8 kΩ and 100 nF, starting at 3.2412 V; target 0.3 V is illustrative.','cards':[card('Leakage floor',f"{leak['leakage_floor_v']:.3f} V",'Above the allocated parking target; high impedance does not mean zero leakage.'),card('Finite time to 0.3 V','No','No finite discharge reaches the target under these ideal constant-leakage allocations.')]},
      {'id':'bleed','title':'Pull-resistor conflict (example)','note':'Nominal divider Rth, allocated Ron 10 Ω, loading error 0.1%, park 0.3 V and leakage 1 µA.','cards':[card('Loading requires',f"Rp ≥ {bleed['rp_min_ohm']/1e6:.6f} MΩ",'Weak enough to keep the allocated added attenuation small.'),card('Leakage parking requires',f"Rp ≤ {bleed['rp_max_ohm']/1e6:.6f} MΩ",'Strong enough to limit allocated positive leakage; no interval remains.')]}]
    return {'revision':'SENSE-04','permission':a['permission'],'required_qualifications':list(model.REQUIRED_QUALIFICATIONS),'states':e['states'],'scenarios':scenarios}

def outputs(e):
    a=e['calculations'];slow,fast=a['shutdown_examples'];d=a['discharge_examples'];b=a['bleed_examples']
    lines=['# SENSE-04 — necessary interface calculations','','[Guide](README.md) | [Interactive explorer](index.html) | [Functional boundary](interface_boundary.svg) | [Evidence](evidence.json)','','All actual numerical inputs and qualifications remain unavailable. These allocated examples do not choose a device, implement control or establish hardware acceptance.','','## Reference-loss window','','For the interval before physical isolation, let H0 = Vrelease,min − Vsignal,max − reserve. With a bounded linear fall S and total delay T = Tdetect + Topen, Hafter = H0 − S×T. Require strictly positive margin in this screen. For S > 0 the strict delay limit is H0/S. The equation does not cover subsequent residual-charge discharge or an unbounded/step collapse.','','| Allocated fall | Total delay | Margin at opening | Strict delay limit |','|---|---|---|---|']
    for v in a['shutdown_examples']:lines.append(f"| {v['inputs']['fall_slew_v_per_s']:.0f} V/s | {v['total_delay_s']*1e6:.3f} µs | {v['headroom_after_delay_v']*1000:.6f} mV | < {v['strict_delay_limit_s']*1e6:.6f} µs |")
    lines+=['','Both cases allocate release 3.35 V, signal 3.241200045 V and reserve 50 mV. The signal is the prior conditional 25.2 V divider corner, not a qualified transient maximum. A 3.35 V release level may be unavailable on the converter low corner; no threshold is selected.','','## Discharge with leakage','','Ideal V(t) = I×R + (V0−I×R)exp(−t/RC). The leakage floor is I×R. For a descending trajectory, a target at or below that floor is not reached in finite time. Being initially below the target does not imply it stays there if the equilibrium is higher; the model records attainment and retention separately.','','| Allocated capacitance / leakage | Floor | Time to allocated 0.3 V |','|---|---|---|']
    for v in d:
        t=f"{v['time_to_target_s']*1e6:.6f} µs" if v['finite_time_to_target'] else 'No finite crossing'
        lines.append(f"| {v['inputs']['cap_max_f']*1e9:.0f} nF / {v['inputs']['leakage_a']*1e6:.3f} µA | {v['leakage_floor_v']:.6f} V | {t} |")
    lines+=['','All cases allocate 6.8 kΩ and initial 3.241200045 V. The 0.3 V target is not a PA2 rating. C36 is 100 nF nominal, not a qualified maximum; 1 nF is a hypothetical downstream capacitance. No downstream capacitor or discharge resistor is selected.','','## Permanent pulldown tradeoff','','With unloaded-divider Thévenin resistance Rth and switch Ron, added attenuation = (Rth+Ron)/(Rp+Rth+Ron). An allocated loading error ε requires Rp ≥ (Rth+Ron)(1−ε)/ε. Positive leakage requires Rp ≤ Vpark/Ileak. A nonempty interval is necessary only; settling, tolerances and all power states still need review.','','| Allocated positive leakage | Minimum Rp for loading | Maximum Rp for parking | Necessary interval |','|---|---|---|---|']
    for v in b:lines.append(f"| {v['inputs']['leak_max_a']*1e6:.3f} µA | {v['rp_min_ohm']/1e6:.6f} MΩ | {v['rp_max_ohm']/1e6:.6f} MΩ | {'Exists conditionally' if v['necessary_interval_exists'] else 'None'} |")
    lines+=['','This uses nominal Rth=47k∥6.8k, allocated Ron 10 Ω, error 0.1% and park 0.3 V. It supplies no component tolerance or temperature guarantee. Switched discharge changes the tradeoff but adds default-state and transition obligations.','','## Charge and qualification','',f"The ideal |Q|/Cmin step for allocated 1 pC and hypothetical 1 nF is {a['injection_example']['glitch_magnitude_v']*1000:.3f} mV. Exact signed charge, feedthrough and minimum capacitance remain unqualified; maximum capacitance is separately needed for discharge.",'','All seven qualification inputs are null and proposed permission is disabled. The HOLD/QUALIFY/SETTLE/ACQUIRE/TRIP/REARM table is a requirements artifact, not an implemented or tested state controller. Physical isolation, parking and sample validity cannot be inferred from a displayed command.','','675 prior hashes and the four-member sensing net remain preserved. No native tool or hardware action occurred. Next screen exact device/arrangement limits against every state before selecting parts or amending an isolated SENSE-02 copy.','']
    html=(P/'explorer.template.html').read_text(encoding='utf-8').replace('__PACKET_DATA__',json.dumps(view_model(e),ensure_ascii=False).replace('<','\u003c'))
    return {'evidence.json':json.dumps(e,indent=2)+'\n','RESULTS.md':'\n'.join(lines),'index.html':html}

def main():
    parser=argparse.ArgumentParser();g=parser.add_mutually_exclusive_group(required=True)
    for m in ('render','capture','check'):g.add_argument('--'+m,action='store_true')
    args=parser.parse_args();e=collect()
    for n,t in outputs(e).items():
        if args.render:write(n,t)
        else:assert (P/n).read_text(encoding='utf-8')==t,'Stale generated artifact: '+n
    if not args.render:
        hashes(read(P/'review_notes.json')['reviewed_sha256']);hashes(read(P/'viewer_check.json')['input_sha256'])
        m={'revision':'SENSE-04','source_revision':read(P/'contract.json')['baseline_head'],'native_candidate':'SENSE-02','input_sha256':read(P/'input_manifest.json')['input_sha256'],'artifact_sha256':{f.relative_to(ROOT).as_posix():sha(f) for f in sorted(P.rglob('*')) if f.is_file() and f.name!='packet_manifest.json' and '__pycache__' not in f.parts},**{k:e[k] for k in ZERO+FALSE}}
        if args.capture:write('packet_manifest.json',m)
        else:assert read(P/'packet_manifest.json')==m,'Packet bytes/coverage changed'
    print('PASS SENSE-04:675 preserved inputs; default-disabled proposed contract; no native/hardware acceptance')
if __name__=='__main__':main()
