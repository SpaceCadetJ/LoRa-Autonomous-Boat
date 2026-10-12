"""Build only isolated ACT-01 buffer supply/population candidate; never edit live CAD."""
from pathlib import Path
import importlib.util,json,shutil,uuid
P=Path(__file__).resolve().parent;ROOT=P.parents[2];DEST=P/'source/hardware/kicad_v2';PROJ='LoRa_Boat_Controller_V2'
s=importlib.util.spec_from_file_location('input_helpers',P.parent/'input_stage/build_candidate.py');h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
parse=h.parse;child=h.child;children=h.children;sha=h.sha;Str=h.Str

def uid(k):return str(uuid.uuid5(uuid.NAMESPACE_URL,'lora-actuator-supply-01/'+k))
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8',newline='\n')
def props(t):return {str(c[1]):c for c in children(t,'property')}
def text(t,x,y,k,size=1.4):return parse(f'(text "{t}" (at {x} {y} 0) (effects (font (size {size} {size})) (justify left bottom)) (uuid "{uid(k)}"))')
def wire(x1,y1,x2,y2,k):return parse(f'(wire (pts (xy {x1} {y1}) (xy {x2} {y2})) (stroke (width 0) (type default)) (uuid "{uid(k)}"))')
def port(x,y,k,shape='input'):return parse(f'(hierarchical_label "+5V_BUCK" (shape {shape}) (at {x} {y} 0) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid(k)}"))')
def save(name,t):
    # KiCad quoted text needs escaped newlines; keep trailing format markers last.
    fonts=children(t,'embedded_fonts')
    for item in fonts:t.remove(item)
    t.extend(fonts)
    def escape(node):
        for i,item in enumerate(node):
            if isinstance(item,list):escape(item)
            elif isinstance(item,Str):node[i]=Str(item.replace(chr(10),r'\n'))
    escape(t)
    (DEST/name).write_text(h.ks.serialize(t)+'\n',encoding='utf-8',newline='\n')
def main():
    im=json.loads((P/'input_manifest.json').read_text());contract=json.loads((P/'expected_contract.json').read_text());pop=json.loads((P/'population_contract.json').read_text())
    live=json.loads((ROOT/'reviews/codex/design_completion/native-review/review.json').read_text())['input_manifest']
    local={n:sha(ROOT/n) for n in ['hardware/kicad/tools/v1_design.py','hardware/kicad_v2/tools/route_v2.py']}
    for n,v in {**live,**im['baseline_source_sha256'],**im['additional_input_sha256']}.items():assert sha(ROOT/n)==v,n
    for n in im['baseline_source_sha256']:
        dst=P/'source'/Path(n).relative_to('reviews/codex/buck_5v/source');dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,dst)
    shutil.copyfile(P/'inputs/D_SMC.kicad_mod',DEST/(PROJ+'.pretty')/'D_SMC.kicad_mod')
    act=parse((DEST/'Actuators.kicad_sch').read_text());removed=[]
    for sym in children(act,'symbol'):
        fields=props(sym);ref=str(fields['Reference'][2])
        if ref in ['#PWRACT01','#PWRACT04','#PWRACT08','#PWRACT11']:
            assert fields['Value'][2]=='VSERVO';at=child(sym,'at');act.append(port(at[1],at[2],'buffer_port_'+ref));removed.append(sym)
        if ref in ['U4','U5']:fields['Datasheet'][2]=Str('https://www.ti.com/lit/ds/symlink/sn74ahct1g125.pdf')
        if ref in ['R11','R14','R15','R18']:
            fields['Description'][2]=Str('Passive pull-down; startup/off-state behavior unqualified')
    assert len(removed)==4
    for sym in removed:act.remove(sym)
    for t in children(act,'text'):
        if str(t[1]).startswith('J3:'):t[1]=Str('J3: signal / VSERVO output / GND. Buffer VCC uses the separate +5V_BUCK rail.')
    act.extend([
      text('ACT-01 / BUFFER SUPPLY AND ASSEMBLY VARIANTS',18,213,'act_title',1.8),
      text('U4/U5 VCC and C13/C14 bypass: +5V_BUCK before D4; the board battery is needed in both variants.',18,222,'act_supply'),
      text('BEC_ONLY: D4 absent, D9 fitted. ONBOARD: D4 fitted, D9 absent. Master drawing marks both DNP.',18,230,'act_pop'),
      text('OE remains grounded. Passive pull-downs do not qualify reset, brownout, hot-plug or powered-off outputs.',18,238,'act_oe'),
      text('Do not power or order from this candidate. Verify actuator levels, inrush/stall current and regenerative energy.',18,246,'act_hold')])
    title=next(iter(children(act,'title_block')),None)
    if title is not None:
        child(title,'rev')[1]=Str('ACT-01');child(title,'date')[1]=Str('2026-10-12')
        for c in children(title,'comment'):
            if str(c[1])=='1':c[2]=Str('ACT-01: four supply pins moved; sequencing unqualified')
    save('Actuators.kicad_sch',act)
    power=parse((DEST/'Power.kicad_sch').read_text())
    for sym in children(power,'symbol'):
        fields=props(sym);ref=str(fields['Reference'][2])
        if ref in ['D4','D9']:
            fields['MPN'][2]=Str(contract['candidate_parts'][ref]['mpn']);fields['Footprint'][2]=Str(contract['candidate_parts'][ref]['footprint']);fields['Datasheet'][2]=Str('https://www.vishay.com/docs/88751/ss32.pdf');fields['Description'][2]=Str('ACT-01 held SMC candidate; fit only per mutually exclusive population contract');child(sym,'dnp')[1]='yes'
    for lab in children(power,'label'):
        if child(lab,'uuid')[1]=='abc036fc-2afa-598b-a1b9-b6fcebeaf6c0':child(child(lab,'effects'),'justify')[1]='right'
    power.append(text('D4/D9: SS34-E3/57T, SMC; pad 1 cathode to VSERVO. Part and thermal qualification pending.',408,244,'diode_identity',1.3))
    power.extend([wire(579.12,106.68,579.12,142.24,'pwr_buf_wire'),port(579.12,142.24,'pwr_buf_port','output')])
    for t in children(power,'text'):
        if str(t[1]).startswith('INPUT A1 moved'):t[1]=Str('INPUT A1 on PowerInput sheet 8. Candidate converter cells below require qualification.\\nCorrect input and sensing before applying power.')
        if str(t[1]).startswith('Nominal buck output'):t[1]=Str('ACT-01: D4 and D9 default DNP. Fit exactly one per variant; diode drop and actuator rail limits remain held.')
        if str(t[1]).startswith('BUCK5-A1:'):t[1]=Str('ACT-01: +5V_BUCK also feeds buffer VCC before D4.\nBoth converter source sheets are preserved.')
    child(child(power,'title_block'),'rev')[1]=Str('ACT-01');save('Power.kicad_sch',power)
    root=parse((DEST/(PROJ+'.kicad_sch')).read_text())
    for sh in children(root,'sheet'):
        name=str(props(sh)['Sheetname'][2])
        if name in ['Power','Actuators']:
            x,y,angle,shape=(124.46,60.96,0,'output') if name=='Power' else (187.96,132.08,180,'input')
            if name=='Power':child(sh,'size')[1]='66.04'
            sh.insert(len(sh)-1,parse(f'(pin "+5V_BUCK" {shape} (at {x} {y} {angle}) (effects (font (size 1.27 1.27)) (justify {"right" if name=="Power" else "left"})) (uuid "{uid("root_pin_"+name)}"))'))
    root.extend([wire(124.46,60.96,142.24,60.96,'root1'),wire(142.24,60.96,142.24,132.08,'root2'),wire(142.24,132.08,187.96,132.08,'root3'),text('ACT-01: dedicated buffer feed; VSERVO remains a separate actuator energy rail.',156,177,'root_note',1.25)])
    child(child(root,'title_block'),'rev')[1]=Str('ACT-01');save(PROJ+'.kicad_sch',root)
    for name in contract['source_sheets_preserved']:assert sha(DEST/name)==sha(P.parent/'buck_5v/source/hardware/kicad_v2'/name)
    for n,v in {**live,**local,**im['baseline_source_sha256']}.items():assert sha(ROOT/n)==v,n
    write(P/'build_manifest.json',{'source_revision':im['source_revision'],'builder_sha256':sha(Path(__file__)),'expected_contract_sha256':sha(P/'expected_contract.json'),'population_contract_sha256':sha(P/'population_contract.json'),'baseline_source_sha256':im['baseline_source_sha256'],'live_input_sha256':live,'local_preservation_sha256':local,'output_sha256':{f.relative_to(ROOT).as_posix():sha(f) for f in (P/'source').rglob('*') if f.is_file()},'live_electrical_delta':0,'pcb_updated':False,'hardware_tested':False,'fabrication_approved':False})
    print('Built isolated ACT-01; both converter sheets and all live CAD preserved.')
if __name__=='__main__':main()
