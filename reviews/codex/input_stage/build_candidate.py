"""Create only an isolated input-stage schematic; preserve all live CAD/copper."""
from pathlib import Path
import hashlib,json,math,shutil,sys,uuid
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ROOT=P.parents[2];S=P/'source';PROJ='LoRa_Boat_Controller_V2';DEST=S/'hardware/kicad_v2'
sys.path.insert(0,str(P/'inputs/hardware/kicad/tools'));import kicad_sym as ks
Str=ks.Str

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def uid(key):return str(uuid.uuid5(uuid.NAMESPACE_URL,'lora-input-stage-A1/'+key))
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8',newline='\n')
def parse(s):return ks.parse(s)[0]
def child(t,k):return next(c for c in t if isinstance(c,list) and c and c[0]==k)
def children(t,k):return [c for c in t if isinstance(c,list) and c and c[0]==k]
def spans(text):
    depth=0;quoted=False;escape=False;start=None;result=[]
    for i,c in enumerate(text):
        if quoted:
            if escape:escape=False
            elif c=='\\':escape=True
            elif c=='"':quoted=False
            continue
        if c=='"':quoted=True
        elif c=='(':
            depth+=1
            if depth==2:start=i
        elif c==')':
            if depth==2:result.append((start,i+1))
            depth-=1
    return result

def main():
    m=json.loads((P/'input_manifest.json').read_text());live=json.loads((ROOT/'reviews/codex/design_completion/native-review/review.json').read_text())['input_manifest']
    protected={**live,**{n:sha(ROOT/n) for n in ['hardware/kicad/tools/v1_design.py','hardware/kicad_v2/tools/route_v2.py']}}
    for n,h in live.items():assert sha(ROOT/n)==h,n
    for n,h in m['sha256'].items():
        src=P/'inputs'/n;assert sha(src)==h,n
        if not n.endswith('.py'):
            target=S/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,target)
    for n,h in m['footprint_sha256'].items():
        assert sha(P/n)==h
        dest=DEST/(PROJ+'.pretty')/Path(n).name;dest.parent.mkdir(exist_ok=True);shutil.copyfile(P/n,dest)
    assert sha(P/'inputs/additional_symbols.kicad_sym')==m['additional_symbols_sha256']
    oldtext=(DEST/'Power.kicad_sch').read_text(encoding='utf-8');old=parse(oldtext)
    rootfile=DEST/(PROJ+'.kicad_sch');roottext=rootfile.read_text(encoding='utf-8');rootid=str(child(parse(roottext),'uuid')[1]);sheetid=uid('sheet')
    libs={str(c[1]):c for c in child(old,'lib_symbols')[1:]}
    libs.update({str(c[1]):c for c in parse((P/'inputs/additional_symbols.kicad_sym').read_text())[1:] if isinstance(c,list) and c[0]=='symbol'})
    oldcomponents={str(next(x for x in c if isinstance(x,list) and x[:2]==['property','Reference'])[2]):c for c in children(old,'symbol')}
    items=[];used={};serial=0
    def add(code):items.append(code)
    def wire(x1,y1,x2,y2):
        nonlocal serial;serial+=1;add(f'(wire (pts (xy {x1} {y1}) (xy {x2} {y2})) (stroke (width 0) (type default)) (uuid "{uid("w"+str(serial))}"))')
    def text(t,x,y,size=1.6):
        nonlocal serial;serial+=1;add(f'(text "{t}" (at {x} {y} 0) (effects (font (size {size} {size})) (justify left bottom)) (uuid "{uid("t"+str(serial))}"))')
    def label(t,x,y,global_=False):
        nonlocal serial;serial+=1;k='global_label' if global_ else 'label';shape='(shape passive)' if global_ else ''
        add(f'({k} "{t}" {shape} (at {x} {y} 0) (effects (font (size 1.6 1.6)) (justify left bottom)) (uuid "{uid("l"+str(serial))}"))')
    def junction(x,y):add(f'(junction (at {x} {y}) (diameter 0) (color 0 0 0 0) (uuid "{uid("j"+str(x)+str(y))}"))')
    def symbol(ref,lib,x,y,rot,value,fp,mpn,mfr,url,description,prop_xy=None):
        sym=libs[lib];used[lib]=sym;pins=ks.symbol_pins(sym);fields=[]
        for name,val in [('Reference',ref),('Value',value),('Footprint',fp),('MPN',mpn),('Manufacturer',mfr),('Datasheet',url),('Description',description)]:
            px,py=(prop_xy if prop_xy else (x,y-8));py+=4 if name=='Value' else 0
            hide='' if name in ['Reference','Value'] else '(hide yes)'
            align='(justify bottom)' if ref in ['F1','D12'] else '(justify left bottom)'
            fields.append(f'(property "{name}" "{val}" (at {px} {py} {90 if rot in (90,270) else 0}) (effects (font (size 1.6 1.6)) {align} {hide}))')
        suuid=str(child(oldcomponents[ref],'uuid')[1]) if ref in oldcomponents else uid(ref)
        ps=''.join(f'(pin "{p["number"]}" (uuid "{uid(ref+p["number"])}"))' for p in pins)
        add(f'(symbol (lib_id "{lib}") (at {x} {y} {rot}) (unit 1) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) (uuid "{suuid}") {" ".join(fields)} {ps} (instances (project "{PROJ}" (path "/{rootid}/{sheetid}" (reference "{ref}") (unit 1)))))')
        a=math.radians(rot);return {p['number']:(round(x+p['x']*math.cos(a)-p['y']*math.sin(a),6),round(y-p['x']*math.sin(a)-p['y']*math.cos(a),6)) for p in pins}
    text('INPUT A1  /  2S-6S BOARD FEED',16,22,3)
    text('ISOLATED CANDIDATE - do not power the retained legacy converter/sense circuits',16,33,2)
    text('This sheet defines the input boundary only. Native connectivity checks do not qualify protection or assembly.',16,42,1.6)
    jc=oldcomponents['J1'];jprops={str(c[1]):str(c[2]) for c in children(jc,'property')}
    j=symbol('J1','Connector_Generic:Conn_01x02',40.64,88.9,0,jprops['Value'],jprops['Footprint'],jprops['MPN'],jprops['Manufacturer'],jprops['Datasheet'],'7-25.2 V board input; initial external-BEC study <=1 A', (50.8,86))
    f=symbol('F1','Device:Fuse',86.36,63.5,90,'2A 125V',PROJ+':Fuse_Littelfuse-NANO2-451_453','0451002.MRL','Littelfuse','https://www.littelfuse.com/assetdocs/fuse-451-and-453-datasheet?assetguid=533cd5cc-956c-4243-867f-6ab5a62f6ba1','Candidate only; derating, inrush and fault coordination required',(86.36,51))
    d=symbol('D12','Device:D_Schottky',177.8,63.5,180,'STPS3H100U',PROJ+':D_SMB','STPS3H100U','STMicroelectronics','https://www.st.com/resource/en/datasheet/stps3h100.pdf','100 V series reverse diode; pin1 K downstream, pin2 A upstream; thermal qualification open',(177.8,51))
    tvs=symbol('D1','Device:D_TVS',124.46,88.9,270,'SMBJ26CA',PROJ+':D_SMB','SMBJ26CA','Littelfuse','https://www.littelfuse.com/~/media/electronics/datasheets/tvs_diodes/littelfuse_tvs_diode_smbj_datasheet.pdf.pdf','Bidirectional 26 V standoff; pre-diode fuse-side clamp; waveform and temperature bound required',(134,86))
    c1=symbol('C1','Device:C_Polarized',241.3,88.9,0,'47uF 63V',PROJ+':CP_Elec_8x10.5','EEEFK1J470P','Panasonic','https://industrial.panasonic.com/tw/products/pt/aluminum-cap-smd/models/EEEFK1J470P','8 mm body, 10.2 mm nominal length; polarity, ripple and land pattern held',(252,86))
    c2=symbol('C2','Device:C',307.34,88.9,0,'1uF 100V',PROJ+':C_1210_3225Metric','GRM32ER72A105KA01L','Murata','https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GRM32ER72A105KA01-01A.pdf','Local reservoir starting value; effective capacitance and converter bypass remain open',(318,86))
    wire(*j['1'],25.4,88.9);wire(25.4,88.9,25.4,63.5);wire(25.4,63.5,*f['1']);label('VBAT_IN',36,63.5)
    wire(*j['2'],30.48,91.44);wire(30.48,91.44,30.48,119.38)
    wire(*f['2'],124.46,63.5);wire(124.46,63.5,*d['2']);label('VBAT_FUSED',103,63.5)
    wire(124.46,63.5,*tvs['1']);junction(124.46,63.5)
    wire(*tvs['2'],124.46,119.38)
    wire(*d['1'],241.3,63.5);wire(241.3,63.5,307.34,63.5);wire(307.34,63.5,368.3,63.5);label('VIN_RAW',368.3,63.5,True)
    wire(241.3,63.5,*c1['1']);wire(307.34,63.5,*c2['1']);junction(241.3,63.5);junction(307.34,63.5)
    for cap in [c1,c2]:wire(*cap['2'],cap['2'][0],119.38)
    for x1,x2 in [(30.48,124.46),(124.46,241.3),(241.3,307.34),(307.34,368.3)]:wire(x1,119.38,x2,119.38)
    for x in [124.46,241.3,307.34]:junction(x,119.38)
    label('GND',368.3,119.38,True)
    for txt,x,y in [('Pin 1: battery +',18,124),('Pin 2: return',18,130),('Clamp before reverse diode',104,137),('Cathode band faces VIN_RAW',161,71),('To R33 / sense / future bucks',320,74)]:text(txt,x,y,1.35)
    notes=[('1  DESIGN BOUNDARY',155,2),('Normal battery: 7-25.2 V; initial external-BEC variant: <=1 A board feed. ESC motor current bypasses this board.',164,1.7),('Qualification target: VBAT_FUSED within +/-44 V and stored VIN_RAW <=44 V. These are required bounds, not measured results.',172,1.7),('At those bounds D12 blocks at most 88 V against 100 V rating. Do not infer an unlimited surge rating from the TVS value.',180,1.7),('2  TRADEOFFS AND REQUIRED CHECKS',195,2),('D12 loss model: about 0.627 W at 1 A DC; copper area, cold drop, leakage and temperature still need qualification.',204,1.7),('F1 is not a 1 A limiter. Verify inrush, source short-circuit current, fuse interrupt conditions and TVS/fuse energy coordination.',212,1.7),('C1/C2 values are candidate selections. Check ripple, effective capacitance, polarity, physical lands and discharged-output reversal.',220,1.7),('3  NEXT CIRCUIT PACKET',237,2),('Replace both buck cells and raw-side sensing/ADC protection before powered bring-up. E-01 through E-06 remain open in live CAD.',246,1.7),('Original PCB, corrected ground copper, V1 behavior, IMU2 candidate and purchasing package remain unchanged.',254,1.7)]
    for txt,y,size in notes:text(txt,16,y,size)
    header=f'(kicad_sch (version 20250114) (generator "input_stage_candidate") (generator_version "9.0") (uuid "{uid("screen")}") (paper "A3") (title_block (title "V2 input-stage A1 - isolated candidate") (date "2026-10-12") (rev "INPUT-A1") (comment 1 "Not integrated or approved for powered use")))'
    tree=parse(header);tree+= [['lib_symbols']+list(used.values())]+[parse(s) for s in items]+[['embedded_fonts','no']]
    (DEST/'PowerInput.kicad_sch').write_text(ks.serialize(tree)+'\n',encoding='utf-8',newline='\n')
    spl=spans(oldtext);start=next(i for i,(a,b) in enumerate(spl) if '13ee5d3c-096f-5c33-9455-5d937d4f0117' in oldtext[a:b]);end=next(i for i,(a,b) in enumerate(spl) if '899e6ac0-490b-5ec1-ad3f-fa5df872563a' in oldtext[a:b]);assert end-start+1==49
    removed=oldtext[spl[start][0]:spl[end][1]];assert sum('(property "Reference" "'+ref+'"' in removed for ref in ['J1','F1','Q1','D1','D2','R1','C1','C2'])==8
    replacement=f'(text "INPUT A1 moved to PowerInput sheet 8.\\nRetained circuits below remain electrically unqualified.\\nReplace buck cells and sensing before applying power." (at 18 55 0) (effects (font (size 2 2)) (justify left bottom)) (uuid "{uid("placeholder")}"))'
    updated=oldtext[:spl[start][0]]+replacement+oldtext[spl[end][1]:]
    updated=updated.replace('(rev "V2 draft")','(rev "INPUT-A1")').replace('Annotated functional groups; connectivity preserved','Input stage moved; other circuits unchanged and unqualified').replace('(date "2026-09-17")','(date "2026-10-12")')
    (DEST/'Power.kicad_sch').write_text(updated,encoding='utf-8',newline='\n')
    rootadd=f'(sheet (at 58.42 190.5) (size 66 26) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0)) (uuid "{sheetid}") (property "Sheetname" "PowerInput" (at 58.42 188.3 0) (effects (font (size 1.8 1.8)) (justify left bottom))) (property "Sheetfile" "PowerInput.kicad_sch" (at 58.42 218.5 0) (effects (font (size 1.1 1.1)) (justify left top))) (instances (project "{PROJ}" (path "/{rootid}" (page "8")))))'
    roottext=roottext.replace('(sheet_instances (path "/" (page "1")))',rootadd+'\n(sheet_instances (path "/" (page "1")))').replace('(rev "V2 draft")','(rev "INPUT-A1")')
    roottext=roottext.replace('Annotated functional groups; connectivity preserved','INPUT-A1 candidate; not PCB integrated or power approved').replace('(date "2026-09-17")','(date "2026-10-12")')
    rootfile.write_text(roottext,encoding='utf-8',newline='\n')
    assert all(sha(ROOT/n)==h for n,h in protected.items()),'Protected live input changed'
    outputs={f.relative_to(ROOT).as_posix():sha(f) for f in S.rglob('*') if f.is_file()}
    write(P/'build_manifest.json',{'source_revision':m['revision'],'builder_sha256':sha(Path(__file__)),'live_input_sha256':live,'local_preservation_sha256':{n:h for n,h in protected.items() if n not in live},'output_sha256':outputs,'removed_input_panel_objects':49,'expected_candidate_delta':{'removed_parts':['Q1','D2','R1'],'new_parts':['D12'],'changed_existing_memberships':['J1.1','F1.1','F1.2','D1.1'],'preserved_outside_boundary_pins':344,'retained_unchanged_memberships':350,'components':112,'pins':356},'live_electrical_delta':0,'pcb_updated':False,'hardware_tested':False,'fabrication_approved':False})
    print('Isolated input candidate saved; 49 old panel objects replaced; live CAD/copper preserved.')
if __name__=='__main__':main()
