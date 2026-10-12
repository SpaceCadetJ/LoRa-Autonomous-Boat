"""Build ACT-04 only from captured ACT-02; never generate or route live CAD."""
from pathlib import Path
import copy,importlib.util,json,math,shutil,uuid
P=Path(__file__).resolve().parent;ROOT=P.parents[2];B=P.parent/'actuator_enable';D=P/'source/hardware/kicad_v2';PROJ='LoRa_Boat_Controller_V2'
s=importlib.util.spec_from_file_location('h',P.parent/'input_stage/build_candidate.py');h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
parse=h.parse;child=h.child;children=h.children;Str=h.Str;sha=h.sha

def uid(k):return str(uuid.uuid5(uuid.NAMESPACE_URL,'lora-actuator-latch-04/'+k))
def props(t):return {str(c[1]):c for c in children(t,'property')}
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8',newline='\n')
def save(name,t):
    fonts=children(t,'embedded_fonts')
    for f in fonts:t.remove(f)
    t.extend(fonts);(D/name).write_text(h.ks.serialize(t)+'\n',encoding='utf-8',newline='\n')

def main():
    im=json.loads((P/'input_manifest.json').read_text());ct=json.loads((P/'expected_contract.json').read_text())
    live=json.loads((ROOT/'reviews/codex/design_completion/native-review/review.json').read_text())['input_manifest']
    preserved={**live,**im['baseline_source_sha256'],**im['additional_input_sha256'],**im['local_preservation_sha256']}
    for n,v in preserved.items():assert sha(ROOT/n)==v,n
    for n in im['baseline_source_sha256']:
        dst=P/'source'/Path(n).relative_to('reviews/codex/actuator_enable/source');dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,dst)
    for fp in (P/'inputs').glob('*.kicad_mod'):shutil.copyfile(fp,D/(PROJ+'.pretty')/fp.name)
    act=parse((D/'Actuators.kicad_sch').read_text());comps={str(props(c)['Reference'][2]):c for c in children(act,'symbol')};libs={str(c[1]):c for c in child(act,'lib_symbols')[1:]}
    root=parse((D/(PROJ+'.kicad_sch')).read_text());rootid=str(child(root,'uuid')[1]);sheetid=str(child(next(sh for sh in children(root,'sheet') if props(sh)['Sheetname'][2]=='Actuators'),'uuid')[1]);intid=uid('interlock-sheet')
    standalone=parse((D/(PROJ+'.kicad_sym')).read_text())
    positions={
      'U12':{'1':(-22.86,-10.16,0),'2':(-22.86,2.54,0),'3':(22.86,-10.16,180),'4':(7.62,-27.94,90),'5':(22.86,2.54,180),'6':(-7.62,-27.94,90),'7':(7.62,27.94,270),'8':(-7.62,27.94,270)},
      'U13':{'1':(7.62,-15.24,90),'2':(-12.7,0,0),'3':(0,-15.24,90),'4':(12.7,0,180),'5':(0,15.24,270)},
      'U14':{'1':(-17.78,10.16,0),'2':(0,-20.32,90),'3':(-17.78,0,0),'4':(17.78,0,180),'5':(0,20.32,270),'6':(-17.78,-10.16,0)}}
    for ref in ['U12','U13','U14']:
        part=ct['candidate_parts'][ref];name=part['value'];libid=PROJ+':'+name;defs=[]
        for n,(pn,typ) in part['pins'].items():
            x,y,a=positions[ref][n];shape='clock' if pn=='CLK' else 'line';defs.append(f'(pin {typ} {shape} (at {x} {y} {a}) (length 2.54) (name "{pn}" (effects (font (size 1.27 1.27)))) (number "{n}" (effects (font (size 1.27 1.27)))))')
        w,ht={'U12':(20.32,25.4),'U13':(10.16,12.7),'U14':(15.24,17.78)}[ref]
        sym=parse(f'(symbol "{libid}" (pin_names (offset 0.8)) (in_bom yes) (on_board yes) (property "Reference" "U" (at 0 {ht+7} 0) (effects (font (size 1.27 1.27)))) (property "Value" "{name}" (at 0 {ht+4} 0) (effects (font (size 1.27 1.27)))) (symbol "{name}_0_1" (rectangle (start {-w} {ht}) (end {w} {-ht}) (stroke (width 0.254) (type default)) (fill (type background)))) (symbol "{name}_1_1" {" ".join(defs)}))')
        libs[libid]=sym;stand=copy.deepcopy(sym);stand[1]=Str(name);standalone.append(stand)
    save(PROJ+'.kicad_sym',standalone)
    items=[];used={};serial=0;currentpath=f'/{rootid}/{sheetid}'
    def add(s):items.append(parse(s))
    def unique(k):
        nonlocal serial;serial+=1;return uid(k+str(serial))
    def wire(a,b):
        assert a!=b;add(f'(wire (pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})) (stroke (width 0) (type default)) (uuid "{unique("w")}"))')
    def text(t,x,y,size=1.3):add(f'(text "{t}" (at {x} {y} 0) (effects (font (size {size} {size})) (justify left bottom)) (uuid "{unique("t")}"))')
    def label(t,pt,kind='label',shape='input',angle=0):
        extra=f'(shape {shape})' if kind=='hierarchical_label' else ('(shape passive)' if kind=='global_label' else '')
        add(f'({kind} "{t}" {extra} (at {pt[0]} {pt[1]} {angle}) (effects (font (size 1.27 1.27)) (justify {"right" if kind=="hierarchical_label" and angle==0 else "left"} bottom)) (uuid "{unique("label")}"))')
    def dot(pt):add(f'(junction (at {pt[0]} {pt[1]}) (diameter 0) (color 0 0 0 0) (uuid "{unique("dot")}"))')
    def nc(pt):add(f'(no_connect (at {pt[0]} {pt[1]}) (uuid "{unique("nc")}"))')
    def symbol(ref,x,y,rot=0,px=None,py=None):
        part=ct['candidate_parts'].get(ref);base=comps[ref] if ref in comps else comps['R40' if ref.startswith('R') else 'C13' if ref.startswith('C') else 'U4'];c=copy.deepcopy(base);pr=props(c)
        if part:
            for f,k in [('Value','value'),('Footprint','footprint'),('MPN','mpn'),('Manufacturer','manufacturer')]:pr[f][2]=Str(part[k])
            child(c,'lib_id')[1]=Str(':'.join(part['library']));child(c,'uuid')[1]=Str(uid(ref));pr['Description'][2]=Str('ACT-04 isolated latch candidate; qualification held')
            if ref.startswith('U'):pr['Datasheet'][2]=Str('https://www.ti.com/lit/ds/symlink/'+part['value'].lower()+'.pdf')
            path=child(child(child(c,'instances'),'project'),'path');path[1]=Str(currentpath);child(path,'reference')[1]=Str(ref)
        pr['Reference'][2]=Str(ref);child(c,'at')[1:]=[str(x),str(y),str(rot)]
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
    def tree(title):return parse(f'(kicad_sch (version 20250114) (generator "act04_isolated") (generator_version "9.0") (uuid "{uid(title)}") (paper "A3") (title_block (title "{title}") (date "2026-10-12") (rev "ACT-04") (company "LoRa Controller Project") (comment 1 "Isolated review candidate; no PCB or hardware release")))')
    def finish(name,t):
        t.append(['lib_symbols']+list(used.values()));t.extend(items);t.append(['embedded_fonts','no']);save(name,t)
    # Recompose the ACT-02 parent using the same component identities and nets,
    # except the declared OE split. The child has no physical interface assignment.
    text('ACT-04 / ACTUATOR SIGNAL PATH',16,19,2.8);text('Isolated latch candidate - QUAL_OK and ACK are unimplemented and default low; valid-rail operation remains disabled',16,29,1.5)
    text('01  Local translator rails',24,43,1.8)
    for ref,xx,net,kind in [('C13',45.72,'+3V3','global_label'),('C14',106.68,'+5V_BUCK','hierarchical_label')]:
        c=symbol(ref,xx,60.96);a=(xx,50.8);wire(a,c['1']);label(net,a,kind);a=(xx,71.12);wire(c['2'],a);label('GND',a,'global_label')
    text('100 nF each; board 5 V is before D4.',24,81,1.2)
    text('02  Independent arm permission',24,98,1.8)
    add(f'(sheet (at 60.96 111.76) (size 55.88 35.56) (stroke (width 0.254) (type default)) (fill (color 0 0 0 0)) (uuid "{intid}") (property "Sheetname" "ArmInterlock" (at 60.96 109.5 0) (effects (font (size 1.5 1.5)) (justify left bottom))) (property "Sheetfile" "ArmInterlock.kicad_sch" (at 60.96 150 0) (effects (font (size 1.1 1.1)) (justify left top))) (pin "ARM_REQUEST" input (at 60.96 124.46 180) (effects (font (size 1.1 1.1)) (justify left)) (uuid "{uid("armpin")}")) (pin "ACT_OE" output (at 116.84 137.16 0) (effects (font (size 1.1 1.1)) (justify right)) (uuid "{uid("oepin")}")) (instances (project "{PROJ}" (path "/{rootid}/{sheetid}" (page "11")))))')
    wire((55.88,124.46),(60.96,124.46));label('ACT_EN_PC4',(55.88,124.46),'hierarchical_label');wire((116.84,137.16),(129.54,137.16));label('ACT_OE',(129.54,137.16))
    text('PC4 is a request. Only the latch gate drives OE.',24,159,1.2)
    text('03  Preserved signal defaults',24,174,1.8)
    for ref,xx,net,kind in [('R14',35.56,'PWM_ESC_PC6','hierarchical_label'),('R15',88.9,'PWM_SERVO_PA8','hierarchical_label'),('R40',137.16,'ACT_OE','label')]:
        r=symbol(ref,xx,193.04);a=(xx,182.88);wire(a,r['1']);label(net,a,kind);a=(xx,203.2);wire(r['2'],a);label('GND',a,'global_label')
    text('R40 remains on OE; R41 on the child holds PC4 low.',24,218,1.2)
    text('04  Dual-supply translator',150,43,1.8)
    u=symbol('U4',187.96,104.14,0,201,72)
    for pin,net,kind in [('3','+3V3','global_label'),('7','+5V_BUCK','hierarchical_label')]:
        a=(u[pin][0],u[pin][1]-10.16);wire(a,u[pin]);label(net,a,kind,angle=90)
    a=(u['2'][0],134.62);wire(u['2'],a);label('GND',a,'global_label')
    for pin,net,kind in [('5','PWM_ESC_PC6','hierarchical_label'),('4','PWM_SERVO_PA8','hierarchical_label'),('6','ACT_OE','label')]:
        a=(165.1,u[pin][1]);wire(a,u[pin]);label(net,a,kind)
    for pin,net in [('8','ESC_SIG_5V'),('1','SERVO_SIG_5V')]:
        a=(238.76,u[pin][1]);wire(u[pin],a);label(net,a)
    text('OE low = HiZ; output pulldowns retained.',155,150,1.2)
    for ref,xx,net in [('TP1',185.42,'PWM_ESC_PC6'),('TP2',228.6,'PWM_SERVO_PA8')]:
        t=symbol(ref,xx,185.42,0,xx,174);a=(xx,193.04);wire(t['1'],a);label(net,a,'hierarchical_label')
    text('05  Preserved output networks',268,43,1.8)
    for rs,rp,di,j,yy,sig,rail in [('R10','R11','D10','J2',76.2,'ESC','BEC_IN'),('R12','R13','D11','J3',139.7,'SERVO','VSERVO')]:
        r=symbol(rs,279.4,yy,90,271,yy-7);pul=symbol(rp,312.42,yy+15.24);d=symbol(di,350.52,yy+15.24,90,370,yy+11);con=symbol(j,388.62,yy+2.54,0,381,yy-12)
        a=(256.54,yy);wire(a,r['1']);label(sig+'_SIG_5V',a);nodes=[r['2'],(312.42,yy),(350.52,yy),con['1']]
        for a,b in zip(nodes,nodes[1:]):wire(a,b)
        label(sig+'_SIG',(315,yy));wire((312.42,yy),pul['1']);wire((350.52,yy),d['1']);dot((312.42,yy));dot((350.52,yy))
        for pin in [pul['2'],d['2']]:
            a=(pin[0],yy+27.94);wire(pin,a);label('GND',a,'global_label')
        a=(con['2'][0]-10.16,con['2'][1]);wire(a,con['2']);label(rail,a,'hierarchical_label' if rail=='BEC_IN' else 'global_label');a=(con['3'][0],con['3'][1]+12.7);wire(con['3'],a);label('GND',a,'global_label')
        text('1 signal / 2 '+('BEC input' if j=='J2' else 'VSERVO output')+' / 3 GND',255,yy+39,1.2)
    text('RELEASE GATES',270,202,1.8)
    for t,y in [('BEC_ONLY: D9 only. ONBOARD: D4 only.',212),('Master: both source diodes DNP.',219),('Receiver sensing and fault timing unimplemented.',226),('HiZ is not a proven stopped motor or zero volts.',233)]:text(t,270,y,1.2)
    text('NEXT: qualify supervisory source and conditioned ACK; preserve both converters and 6S requirement.',24,238,1.4)
    text('No firmware, live PCB or purchasing change. Receiver backdrive, C11 transients, feed, ADC and IMU2 remain open.',24,250,1.25)
    t=tree('LoRa multifunction vehicle node V2 - Actuators');child(t,'uuid')[1]=child(act,'uuid')[1];finish('Actuators.kicad_sch',t)
    # Child sheet: exact physical pin numbering, including Q=5 and AND GND=2.
    items=[];used={};currentpath=f'/{rootid}/{sheetid}/{intid}'
    text('ACT-04 / FAULT-CLEARED ARM LATCH',16,19,2.8);text('Timing qualification pending - receiver observation, watchdog and qualification source are not implemented',16,29,1.5)
    text('01  Arm-low capture',27,50,1.8);text('02  Acknowledge latches READY',158,50,1.8);text('03  Final enable gate',285,50,1.8)
    inv=symbol('U13',93.98,99.06,0,104,73.66)
    ff=symbol('U12',203.2,109.22,0,225,78.74)
    gate=symbol('U14',327.66,116.84,0,348,78.74)
    for u,vc,gn in [(inv,'5','3'),(ff,'8','4'),(gate,'5','2')]:
        a=(u[vc][0],u[vc][1]-7.62);wire(a,u[vc]);label('+3V3',a,'global_label',angle=90);a=(u[gn][0],u[gn][1]+7.62);wire(u[gn],a);label('GND',a,'global_label')
    nc(inv['1']);nc(ff['3']);a=(ff['7'][0],ff['7'][1]-7.62);wire(a,ff['7']);label('+3V3',a,'global_label',angle=90)
    a=(inv['2'][0]-10.16,inv['2'][1]);wire(a,inv['2']);label('ARM_REQUEST',a,'hierarchical_label');a=(inv['4'][0]+12.7,inv['4'][1]);wire(inv['4'],a);label('ARM_LOW',a)
    a=(ff['2'][0]-12.7,ff['2'][1]);wire(a,ff['2']);label('ARM_LOW',a);a=(ff['1'][0]-12.7,ff['1'][1]);wire(a,ff['1']);label('ACK',a)
    a=(ff['6'][0],ff['6'][1]+7.62);wire(ff['6'],a);label('QUAL_OK',a,angle=90)
    wire(ff['5'],gate['1']);label('READY',(260,ff['5'][1]))
    a=(gate['3'][0]-12.7,gate['3'][1]);wire(a,gate['3']);label('ARM_REQUEST',a,'hierarchical_label');a=(gate['6'][0]-12.7,gate['6'][1]);wire(a,gate['6']);label('QUAL_OK',a)
    a=(gate['4'][0]+15.24,gate['4'][1]);wire(gate['4'],a);label('ACT_OE',a,'hierarchical_label','output',180)
    text('D = NOT ARM_REQUEST',30,160,1.25);text('New ACK rise with stable low ARM sets Q.',158,160,1.25);text('OE = QUAL_OK AND ARM AND READY',285,160,1.25)
    text('ACK while ARM high clears READY.',158,167,1.25);text('QUAL_OK low clears Q and inhibits OE.',285,167,1.25)
    text('04  Local bypass / layout pending',24,186,1.8)
    for ref,xx in [('C56',40.64),('C57',96.52),('C58',152.4)]:
        c=symbol(ref,xx,208.28);a=(xx,198.12);wire(a,c['1']);label('+3V3',a,'global_label');a=(xx,218.44);wire(c['2'],a);label('GND',a,'global_label')
    text('C56 / U12     C57 / U13     C58 / U14',24,231,1.2)
    text('05  Default-disabled boundary',213,186,1.8)
    for ref,xx,net,kind in [('R41',251.46,'ARM_REQUEST','hierarchical_label'),('R42',307.34,'QUAL_OK','label'),('R43',363.22,'ACK','label')]:
        r=symbol(ref,xx,208.28);a=(xx,198.12);wire(a,r['1']);label(net,a,kind);a=(xx,218.44);wire(r['2'],a);label('GND',a,'global_label')
    text('QUAL_OK and ACK have no source: remain LOW.',213,231,1.25)
    text('QUAL_OK must represent qualified rails, remote receivers, stop and fresh command service. No tie-high or test bypass.',24,246,1.2)
    text('Require fault pulse stretching, clean ACK, reset-release and ACK/ARM timing. See TIMING.md; no asynchronous safety claim.',24,254,1.2)
    finish('ArmInterlock.kicad_sch',tree('LoRa multifunction vehicle node V2 - ArmInterlock'))
    child(child(root,'title_block'),'rev')[1]=Str('ACT-04');save(PROJ+'.kicad_sch',root)
    for name in ct['preserved_sheets']:assert sha(D/name)==sha(B/'source/hardware/kicad_v2'/name)
    for n,v in preserved.items():assert sha(ROOT/n)==v,n
    write(P/'build_manifest.json',{'source_revision':im['source_revision'],'baseline_source_sha256':im['baseline_source_sha256'],'builder_sha256':sha(Path(__file__)),'expected_contract_sha256':sha(P/'expected_contract.json'),'population_contract_sha256':sha(P/'population_contract.json'),'input_footprint_sha256':{f.relative_to(ROOT).as_posix():sha(f) for f in (P/'inputs').glob('*.kicad_mod')},'live_input_sha256':live,'local_preservation_sha256':im['local_preservation_sha256'],'output_sha256':{f.relative_to(ROOT).as_posix():sha(f) for f in (P/'source').rglob('*') if f.is_file()},'live_electrical_delta':0,'pcb_updated':False,'hardware_tested':False,'fabrication_approved':False})
    print('Built isolated ACT-04; preserved ACT-02, converters, MCU, population and live hardware.')
if __name__=='__main__':main()
