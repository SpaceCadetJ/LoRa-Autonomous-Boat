"""Build only ACT-02 from captured ACT-01. Never generate or route live CAD."""
from pathlib import Path
import copy,importlib.util,json,math,shutil,uuid
P=Path(__file__).resolve().parent;ROOT=P.parents[2];B=P.parent/'actuator_supply';D=P/'source/hardware/kicad_v2';PROJ='LoRa_Boat_Controller_V2'
s=importlib.util.spec_from_file_location('h',P.parent/'input_stage/build_candidate.py');h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
parse=h.parse;child=h.child;children=h.children;Str=h.Str;sha=h.sha

def uid(k):return str(uuid.uuid5(uuid.NAMESPACE_URL,'lora-actuator-enable-02/'+k))
def props(t):return {str(c[1]):c for c in children(t,'property')}
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8',newline='\n')
def save(name,t):
    fonts=children(t,'embedded_fonts')
    for f in fonts:t.remove(f)
    t.extend(fonts)
    (D/name).write_text(h.ks.serialize(t)+'\n',encoding='utf-8',newline='\n')
def main():
    im=json.loads((P/'input_manifest.json').read_text());ct=json.loads((P/'expected_contract.json').read_text());live=json.loads((ROOT/'reviews/codex/design_completion/native-review/review.json').read_text())['input_manifest']
    local={n:sha(ROOT/n) for n in ['hardware/kicad/tools/v1_design.py','hardware/kicad_v2/tools/route_v2.py']}
    for n,v in {**live,**local,**im['baseline_source_sha256'],**im['additional_input_sha256']}.items():assert sha(ROOT/n)==v,n
    for n in im['baseline_source_sha256']:
        dst=P/'source'/Path(n).relative_to('reviews/codex/actuator_supply/source');dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,dst)
    fp=P/'inputs/TI_DCU0008A_TXU0102.kicad_mod';shutil.copyfile(fp,D/(PROJ+'.pretty')/fp.name)
    act=parse((D/'Actuators.kicad_sch').read_text());comps={str(props(c)['Reference'][2]):c for c in children(act,'symbol')};libs={str(c[1]):c for c in child(act,'lib_symbols')[1:]}
    root=parse((D/(PROJ+'.kicad_sch')).read_text());rootid=str(child(root,'uuid')[1]);sheetid=str(child(next(sh for sh in children(root,'sheet') if props(sh)['Sheetname'][2]=='Actuators'),'uuid')[1])
    # Exact DCU physical pins. A inputs, B tri-state outputs; not a renamed bidirectional TXB symbol.
    pinxy={'1':(12.7,-5.08,180),'2':(0,-20.32,90),'3':(-5.08,20.32,270),'4':(-12.7,-5.08,0),'5':(-12.7,5.08,0),'6':(-12.7,-15.24,0),'7':(5.08,20.32,270),'8':(12.7,5.08,180)}
    defs=[]
    for n,(name,typ) in ct['candidate_parts']['U4']['pins'].items():
        x,y,a=pinxy[n];defs.append(f'(pin {typ} line (at {x} {y} {a}) (length 2.54) (name "{name}" (effects (font (size 1.27 1.27)))) (number "{n}" (effects (font (size 1.27 1.27)))))')
    libid=PROJ+':TXU0102DCU'
    sym=parse(f'(symbol "{libid}" (pin_names (offset 0.8)) (in_bom yes) (on_board yes) (property "Reference" "U" (at 0 25.4 0) (effects (font (size 1.27 1.27)))) (property "Value" "TXU0102" (at 0 22.86 0) (effects (font (size 1.27 1.27)))) (symbol "TXU0102DCU_0_1" (rectangle (start -10.16 17.78) (end 10.16 -17.78) (stroke (width 0.254) (type default)) (fill (type background)))) (symbol "TXU0102DCU_1_1" {" ".join(defs)}))')
    libs[libid]=sym;lib=parse((D/(PROJ+'.kicad_sym')).read_text());stand=copy.deepcopy(sym);stand[1]=Str('TXU0102DCU');lib.append(stand);save(PROJ+'.kicad_sym',lib)
    items=[];used={};serial=0
    def add(s):items.append(parse(s))
    def unique(k):
        nonlocal serial;serial+=1;return uid(k+str(serial))
    def wire(a,b):
        assert a!=b;add(f'(wire (pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})) (stroke (width 0) (type default)) (uuid "{unique("w")}"))')
    def text(t,x,y,size=1.5):add(f'(text "{t}" (at {x} {y} 0) (effects (font (size {size} {size})) (justify left bottom)) (uuid "{unique("t")}"))')
    def label(t,pt,kind='label',shape='input',angle=0):
        extra=f'(shape {shape})' if kind=='hierarchical_label' else ('(shape passive)' if kind=='global_label' else '')
        add(f'({kind} "{t}" {extra} (at {pt[0]} {pt[1]} {angle}) (effects (font (size 1.27 1.27)) (justify {"right" if kind=="hierarchical_label" and angle==0 else "left"} bottom)) (uuid "{unique("label")}"))')
    def dot(pt):add(f'(junction (at {pt[0]} {pt[1]}) (diameter 0) (color 0 0 0 0) (uuid "{unique("dot")}"))')
    def symbol(ref,x,y,rot=0,px=None,py=None):
        base=comps['R11'] if ref=='R40' else comps[ref];c=copy.deepcopy(base);pr=props(c)
        part=ct['candidate_parts'].get(ref)
        if part:
            for f,k in [('Value','value'),('Footprint','footprint'),('MPN','mpn'),('Manufacturer','manufacturer')]:pr[f][2]=Str(part[k])
            child(c,'lib_id')[1]=Str(':'.join(part['library']))
        pr['Reference'][2]=Str(ref);pr['Description'][2]=Str('ACT-02 held candidate; see review guide') if ref in ['U4','R40','C13','C14'] else pr['Description'][2]
        if ref=='U4':pr['Datasheet'][2]=Str('https://www.ti.com/lit/ds/symlink/txu0102.pdf')
        if ref=='R40':
            child(c,'uuid')[1]=Str(uid(ref));path=child(child(child(c,'instances'),'project'),'path');child(path,'reference')[1]=Str(ref)
        child(c,'at')[1:]=[str(x),str(y),str(rot)]
        if px is None:px=x+5
        if py is None:py=y-2
        for f in children(c,'property'):
            child(f,'at')[1:]=[str(px),str(py+(3 if f[1]=='Value' else 0)),str(90 if rot in [90,270] else 0)]
            eff=child(f,'effects');j=next(iter(children(eff,'justify')),None)
            if j:j[1:]=['left','bottom']
            else:eff.append(['justify','left','bottom'])
        li=str(child(c,'lib_id')[1]);used[li]=libs[li];pins=h.ks.symbol_pins(libs[li])
        for pin in children(c,'pin'):c.remove(pin)
        for p in pins:c.insert(len(c)-1,parse(f'(pin "{p["number"]}" (uuid "{uid(ref+"pin"+p["number"])}"))'))
        items.append(c);a=math.radians(rot)
        return {p['number']:(round(x+p['x']*math.cos(a)-p['y']*math.sin(a),6),round(y-p['x']*math.sin(a)-p['y']*math.cos(a),6)) for p in pins}
    text('ACT-02 / DEFAULT-DISABLED ACTUATOR SIGNALS',16,19,2.8)
    text('Isolated schematic candidate - no PCB integration, programming release or hardware acceptance',16,29,1.7)
    text('01  Separate local bypass',24,43,1.8)
    c13=symbol('C13',45.72,60.96);c14=symbol('C14',106.68,60.96)
    for cap,net,kind in [(c13,'+3V3','global_label'),(c14,'+5V_BUCK','hierarchical_label')]:
        top=(cap['1'][0],50.8);wire(top,cap['1']);label(net,top,kind);bottom=(cap['2'][0],71.12);wire(cap['2'],bottom);label('GND',bottom,'global_label')
    text('100 nF at each supply pin; effective value and placement held.',24,80,1.2)
    text('02  Fixed-direction translator',145,43,1.8)
    u=symbol('U4',165.1,101.6,0,183,74)
    for pin,net,kind in [('3','+3V3','global_label'),('7','+5V_BUCK','hierarchical_label')]:
        pt=(u[pin][0],u[pin][1]-10.16);wire(pt,u[pin]);label(net,pt,kind,angle=90)
    pt=(u['2'][0],132.08);wire(u['2'],pt);label('GND',pt,'global_label')
    for p,n in [('5','PWM_ESC_PC6'),('4','PWM_SERVO_PA8'),('6','ACT_EN_PC4')]:
        pt=(129.54,u[p][1]);wire(pt,u[p]);label(n,pt,'hierarchical_label')
    for p,n in [('8','ESC_SIG_5V'),('1','SERVO_SIG_5V')]:
        pt=(210.82,u[p][1]);wire(u[p],pt);label(n,pt)
    text('VCCA: board 3.3 V / VCCB: board 5 V before D4',145,147,1.3)
    text('OE low = HiZ. OE high = PWM follows A to B.',145,154,1.3)
    text('U5 removed; U4 is now an 8-pin dual translator.',145,161,1.3)
    text('03  Reset and input defaults',24,99,1.8)
    for ref,xx,net in [('R14',45.72,'PWM_ESC_PC6'),('R15',99.06,'PWM_SERVO_PA8'),('R40',45.72,'ACT_EN_PC4')]:
        yy=119.38 if ref!='R40' else 165.1;r=symbol(ref,xx,yy);top=(xx,yy-10.16);wire(top,r['1']);label(net,top,'hierarchical_label');bottom=(xx,yy+10.16);wire(r['2'],bottom);label('GND',bottom,'global_label')
    for ref,xx,net in [('TP1',96.52,'PWM_ESC_PC6'),('TP2',160.02,'PWM_SERVO_PA8')]:
        t=symbol(ref,xx,180.34,0,xx,169.5);pt=(t['1'][0],t['1'][1]+7.62);wire(t['1'],pt);label(net,pt,'hierarchical_label')
    text('R40 10k: active-high OE defaults low when PC4 is HiZ.',24,206,1.3)
    text('Firmware is unchanged. Stage A does not arm this candidate.',24,213,1.3)
    text('04  Preserved output networks and connectors',253,43,1.8)
    for rs,rp,di,j,yy,sig,rail in [('R10','R11','D10','J2',76.2,'ESC','BEC_IN'),('R12','R13','D11','J3',139.7,'SERVO','VSERVO')]:
        r=symbol(rs,279.4,yy,90,271,yy-7);pul=symbol(rp,312.42,yy+15.24);d=symbol(di,350.52,yy+15.24,90,370,yy+11);con=symbol(j,388.62,yy+2.54,0,381,yy-12)
        left=(256.54,yy);wire(left,r['1']);label(sig+'_SIG_5V',left)
        nodes=[r['2'],(312.42,yy),(350.52,yy),con['1']]
        for a,b in zip(nodes,nodes[1:]):wire(a,b)
        label(sig+'_SIG',(315,yy));wire((312.42,yy),pul['1']);wire((350.52,yy),d['1']);dot((312.42,yy));dot((350.52,yy))
        for pin in [pul['2'],d['2']]:
            bot=(pin[0],yy+27.94);wire(pin,bot);label('GND',bot,'global_label')
        p2=(con['2'][0]-10.16,con['2'][1]);wire(p2,con['2']);label(rail,p2,'hierarchical_label' if rail=='BEC_IN' else 'global_label')
        p3=(con['3'][0],con['3'][1]+12.7);wire(con['3'],p3);label('GND',p3,'global_label')
        text('1 signal / 2 '+('BEC input' if j=='J2' else 'VSERVO output')+' / 3 GND',255,yy+39,1.3)
    text('RELEASE GATES / READ BEFORE APPLYING POWER',253,202,1.8)
    for txt,y in [('Board 3.3/5 V rails required in both source variants.',211),('Preserve ACT-01: BEC_ONLY = D9; ONBOARD = D4.',218),('Both source diodes DNP in the unselected master.',225),('Ioff protects the unpowered translator, not the receiver.',232),('Actuator-off injection and brownout supervision remain held.',239),('Do not connect, arm or hot-plug from this candidate.',246)]:text(txt,253,y,1.25)
    text('NEXT: qualify receiver-power sensing / hardware disable; do not infer a failsafe from ERC.',24,237,1.4)
    text('6S power-feed, C11/VSERVO transients, ADC and combined IMU2 remain open. Both converter sheets preserved.',24,249,1.3)
    keep=[c for c in act if not isinstance(c,list) or c[0] in ['version','generator','generator_version','uuid','paper','title_block']]
    keep.append(['lib_symbols']+list(used.values()));keep.extend(items);keep.append(['embedded_fonts','no']);act=keep
    title=child(act,'title_block');child(title,'rev')[1]=Str('ACT-02');child(title,'date')[1]=Str('2026-10-12')
    for c in children(title,'comment'):
        if str(c[1])=='1':c[2]=Str('ACT-02: TXU0102, PC4 enable; sequencing qualification held')
    save('Actuators.kicad_sch',act)
    # PC4 is the sole MCU change. Keep all other no-connects and existing wiring.
    mcu=parse((D/'MCU.kicad_sch').read_text());found=[c for c in children(mcu,'no_connect') if child(c,'at')[1:]==['38.1','114.3']];assert len(found)==1; mcu.remove(found[0])
    mcu.append(parse(f'(wire (pts (xy 38.1 114.3) (xy 33.02 114.3)) (stroke (width 0) (type default)) (uuid "{uid("pc4wire")}"))'))
    mcu.append(parse(f'(hierarchical_label "ACT_EN_PC4" (shape output) (at 33.02 114.3 0) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid("pc4port")}"))'))
    save('MCU.kicad_sch',mcu)
    for sh in children(root,'sheet'):
        name=str(props(sh)['Sheetname'][2])
        if name in ['MCU','Actuators']:
            yy=93.98 if name=='MCU' else 137.16;direction='output' if name=='MCU' else 'input'
            sh.insert(next(i for i,c in enumerate(sh) if isinstance(c,list) and c[0]=='instances'),parse(f'(pin "ACT_EN_PC4" {direction} (at 187.96 {yy} 180) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid(name+"pin")}"))'))
            root.append(parse(f'(wire (pts (xy 182.88 {yy}) (xy 187.96 {yy})) (stroke (width 0) (type default)) (uuid "{uid(name+"wire")}"))'))
            root.append(parse(f'(label "ACT_EN_PC4" (at 182.88 {yy} 0) (effects (font (size 1.27 1.27)) (justify right bottom)) (uuid "{uid(name+"label")}"))'))
    child(child(root,'title_block'),'rev')[1]=Str('ACT-02');save(PROJ+'.kicad_sch',root)
    for n in ct['source_sheets_preserved']:assert sha(D/n)==sha(B/'source/hardware/kicad_v2'/n)
    for n,v in {**live,**local,**im['baseline_source_sha256']}.items():assert sha(ROOT/n)==v,n
    write(P/'build_manifest.json',{'source_revision':im['source_revision'],'builder_sha256':sha(Path(__file__)),'expected_contract_sha256':sha(P/'expected_contract.json'),'population_contract_sha256':sha(P/'population_contract.json'),'input_footprint_sha256':sha(fp),'baseline_source_sha256':im['baseline_source_sha256'],'live_input_sha256':live,'local_preservation_sha256':local,'output_sha256':{f.relative_to(ROOT).as_posix():sha(f) for f in (P/'source').rglob('*') if f.is_file()},'live_electrical_delta':0,'pcb_updated':False,'hardware_tested':False,'fabrication_approved':False})
    print('Built isolated ACT-02; live CAD, both converter sheets and ACT-01 population preserved.')
if __name__=='__main__':main()
