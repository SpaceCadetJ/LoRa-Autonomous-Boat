"""Build an isolated first-buck amendment; never write live CAD or copper."""
from pathlib import Path
import copy,importlib.util,json,math,shutil,sys,uuid
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ROOT=P.parents[2];DEST=P/'source/hardware/kicad_v2';PROJ='LoRa_Boat_Controller_V2'
s=importlib.util.spec_from_file_location('a1_helpers',P.parent/'input_stage/build_candidate.py');h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
ks=h.ks;Str=ks.Str;parse=h.parse;child=h.child;children=h.children;sha=h.sha

def uid(k):return str(uuid.uuid5(uuid.NAMESPACE_URL,'lora-buck33-A1/'+k))
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8',newline='\n')
def main():
    im=json.loads((P/'input_manifest.json').read_text());contract=json.loads((P/'expected_contract.json').read_text())
    live=json.loads((ROOT/'reviews/codex/design_completion/native-review/review.json').read_text())['input_manifest']
    protected={**live,**{n:sha(ROOT/n) for n in ['hardware/kicad/tools/v1_design.py','hardware/kicad_v2/tools/route_v2.py']}}
    for n,v in {**protected,**im['baseline_source_sha256'],**im['additional_input_sha256']}.items():assert sha(ROOT/n)==v,n
    for n in im['baseline_source_sha256']:
        rel=Path(n).relative_to('reviews/codex/input_stage/source');dst=P/'source'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,dst)
    fpdir=DEST/(PROJ+'.pretty');fpdir.mkdir(exist_ok=True)
    for f in (P/'inputs/footprints').glob('*.kicad_mod'):shutil.copyfile(f,fpdir/f.name)
    reg=parse((P/'inputs/LMR36520ADDA_reviewed.kicad_sym').read_text());standalone=copy.deepcopy(reg);standalone[1]=Str('LMR36520ADDA')
    symfile=DEST/(PROJ+'.kicad_sym');lib=parse(symfile.read_text());lib.append(standalone);symfile.write_text(ks.serialize(lib)+'\n',encoding='utf-8',newline='\n')
    power=DEST/'Power.kicad_sch';oldtext=power.read_text();old=parse(oldtext)
    rootfile=DEST/(PROJ+'.kicad_sch');roottext=rootfile.read_text();root=parse(roottext);rootid=str(child(root,'uuid')[1])
    psheet=next(c for c in children(root,'sheet') if any(p[1]=='Sheetname' and p[2]=='Power' for p in children(c,'property')));powerid=str(child(psheet,'uuid')[1]);sheetid=uid('sheet')
    libs={str(c[1]):c for c in child(old,'lib_symbols')[1:]};libs[str(reg[1])]=reg
    oldcomps={str(next(x for x in children(c,'property') if x[1]=='Reference')[2]):c for c in children(old,'symbol')}
    items=[];used={};serial=0
    def add(code):items.append(parse(code))
    def ident(k):
        nonlocal serial;serial+=1;return uid(k+str(serial))
    def wire(x1,y1,x2,y2):add(f'(wire (pts (xy {x1} {y1}) (xy {x2} {y2})) (stroke (width 0) (type default)) (uuid "{ident("wire")}"))')
    def text(t,x,y,size=1.6):add(f'(text "{t}" (at {x} {y} 0) (effects (font (size {size} {size})) (justify left bottom)) (uuid "{ident("text")}"))')
    def label(t,x,y,kind='label'):
        shape='(shape input)' if kind=='hierarchical_label' else ('(shape passive)' if kind=='global_label' else '')
        add(f'({kind} "{t}" {shape} (at {x} {y} 0) (effects (font (size 1.5 1.5)) (justify left bottom)) (uuid "{ident("label")}"))')
    def dot(x,y):add(f'(junction (at {x} {y}) (diameter 0) (color 0 0 0 0) (uuid "{ident("junction")}"))')
    def symbol(ref,x,y,rot,px,py):
        part=contract['candidate_parts'][ref];libid=':'.join(part['library']);sym=libs[libid];used[libid]=sym;pins=ks.symbol_pins(sym)
        url='https://www.ti.com/lit/ds/symlink/lmr36520.pdf' if ref=='U2' else ('https://www.coilcraft.com/getmedia/ea51f14b-7f32-4dc6-8dfe-d4b70549040f/xal60xx.pdf' if ref=='L1' else ('https://www.vishay.com/docs/20035/dcrcwe3.pdf' if ref.startswith('R') else ('https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no='+part['mpn'] if part['manufacturer']=='TDK' else 'https://www.ti.com/lit/ug/snvu677/snvu677.pdf')))
        fields=[]
        for name,val in [('Reference',ref),('Value',part['value']),('Footprint',part['footprint']),('MPN',part['mpn']),('Manufacturer',part['manufacturer']),('Datasheet',url),('Description','Held candidate; see reviews/codex/buck_3v3/README.md')]:
            yy=py+(4 if name=='Value' else 0);hide='' if name in ['Reference','Value'] else '(hide yes)'
            fields.append(f'(property "{name}" "{val}" (at {px} {yy} {90 if rot in (90,270) else 0}) (effects (font (size 1.6 1.6)) (justify left bottom) {hide}))')
        suuid=str(child(oldcomps[ref],'uuid')[1]) if ref in oldcomps else uid(ref)
        ps=''.join(f'(pin "{p["number"]}" (uuid "{uid(ref+p["number"])}"))' for p in pins)
        add(f'(symbol (lib_id "{libid}") (at {x} {y} {rot}) (unit 1) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) (uuid "{suuid}") {" ".join(fields)} {ps} (instances (project "{PROJ}" (path "/{rootid}/{powerid}/{sheetid}" (reference "{ref}") (unit 1)))))')
        a=math.radians(rot);return {p['number']:(round(x+p['x']*math.cos(a)-p['y']*math.sin(a),6),round(y-p['x']*math.sin(a)-p['y']*math.cos(a),6)) for p in pins}
    text('BUCK33-A1 / 3.3 V LOGIC SUPPLY',16,21,3)
    text('ISOLATED WIRED CANDIDATE - full-board protection and remaining circuits are not accepted',16,32,1.9)
    text('Design load 1.2 A. Battery intent 7-25.2 V; +44 V protected-rail target remains unverified.',16,42,1.65)
    text('LOCAL INPUT BANK',32,55,1.8);text('BOOTSTRAP / SWITCH',221,55,1.8);text('OUTPUT BANK',299,71,1.8)
    u=symbol('U2',205.74,91.44,0,194,70)
    caps=[symbol('C44',53.34,88.9,0,61,85),symbol('C45',96.52,88.9,0,104,85),symbol('C46',134.62,88.9,0,142,85)]
    cv=symbol('C48',172.72,119.38,0,181,117);cb=symbol('C3',236.22,76.2,0,250,74);ind=symbol('L1',269.24,88.9,90,278,99)
    outcaps=[symbol('C5',294.64,111.76,0,302,110),symbol('C6',335.28,111.76,0,343,110),symbol('C47',375.92,111.76,0,383,110)]
    label('VIN_BUCK',25.4,63.5,'hierarchical_label')
    xs=[25.4,53.34,96.52,134.62,190.5]
    for a,b in zip(xs,xs[1:]):wire(a,63.5,b,63.5)
    for cap in caps:wire(cap['1'][0],63.5,*cap['1']);wire(*cap['2'],cap['2'][0],139.7);dot(cap['1'][0],63.5)
    wire(190.5,63.5,190.5,u['2'][1]);wire(190.5,u['2'][1],*u['2']);wire(190.5,u['2'][1],190.5,u['3'][1]);wire(190.5,u['3'][1],*u['3']);dot(190.5,u['2'][1])
    wire(*u['6'],172.72,u['6'][1]);wire(172.72,u['6'][1],*cv['1']);wire(*cv['2'],172.72,139.7);label('VCC_3V3',172.72,106.68)
    wire(*u['1'],u['1'][0],139.7);wire(*u['9'],u['9'][0],139.7)
    wire(*u['7'],223.52,u['7'][1]);wire(223.52,u['7'][1],223.52,63.5);wire(223.52,63.5,245.11,63.5);wire(245.11,63.5,245.11,cb['2'][1]);wire(245.11,cb['2'][1],*cb['2']);label('BOOT_3V3',223.52,63.5)
    wire(*u['8'],232.41,u['8'][1]);wire(232.41,u['8'][1],*ind['1']);wire(*cb['1'],232.41,cb['1'][1]);wire(232.41,cb['1'][1],232.41,u['8'][1]);dot(232.41,u['8'][1]);label('SW_3V3',246.38,u['8'][1])
    xs=[ind['2'][0],294.64,335.28,375.92,398.78]
    for a,b in zip(xs,xs[1:]):wire(a,88.9,b,88.9)
    label('+3V3',398.78,88.9,'global_label')
    for cap in outcaps:wire(cap['1'][0],88.9,*cap['1']);wire(*cap['2'],cap['2'][0],139.7);dot(cap['1'][0],88.9)
    xs=[53.34,96.52,134.62,172.72,u['1'][0],u['9'][0],294.64,335.28,375.92,398.78]
    for a,b in zip(xs,xs[1:]):wire(a,139.7,b,139.7)
    for x in xs[1:-1]:dot(x,139.7)
    label('GND',398.78,139.7,'global_label')
    wire(*u['5'],223.52,u['5'][1]);wire(223.52,u['5'][1],223.52,116.84);label('FB_3V3',223.52,116.84)
    add(f'(no_connect (at {u["4"][0]} {u["4"][1]}) (uuid "{uid("pg_nc")}"))');text('PG unused; explicit NC',228,130,1.35)
    text('FEEDBACK - SENSE AT OUTPUT BANK',282,154,1.8)
    rt=symbol('R4',320.04,170.18,0,329,168);rb=symbol('R5',320.04,200.66,0,329,199)
    label('+3V3',320.04,160.02,'global_label');wire(320.04,160.02,*rt['1']);wire(*rt['2'],320.04,185.42);wire(320.04,185.42,*rb['1']);wire(287.02,185.42,320.04,185.42);label('FB_3V3',287.02,185.42);dot(320.04,185.42)
    wire(*rb['2'],320.04,213.36);label('GND',320.04,213.36,'global_label')
    for t,y in [('C44/C45: >=4.7 uF combined effective + separate HF bypass; capacitance held.',151),('U2 pins 1 and 9 both connect to ground. Thermal pad is not the sole return.',158),('C48 supplies VCC only. C3 connects BOOT to SW; old 51-ohm resistor removed.',165),('EN tied to VIN_BUCK: always-on cell, no battery discharge cutoff implemented.',180),('100k / 43.2k sets 3.3148 V nominal; resistor / VFB corner screen is documented.',188),('10 uH differs from TI 6.8 uH quick-start. Validate load steps and loop stability.',196),('Output: 3 x 22 uF rated, not 66 uF guaranteed effective. Ripple / bias / aging held.',204)]:text(t,18,y,1.45)
    text('INTEGRATION GATES / BEFORE POWERED USE',16,230,2)
    for t,y in [('This copy retains uncorrected input leakage, polarized C1, 5 V buck, sense/ADC and buffer circuits; IMU2 is separate.',240),('Confirm hot inductor behavior, losses, junction temperature, startup, source damping and actual capacitor bounds.',248),('Custom regulator and capacitor lands are candidates; thermal vias, assembly process and whole-board fit remain open.',256),('Native ERC / netlist delta prove recorded connections only. No routing, fabrication or hardware acceptance.',264)]:text(t,16,y,1.6)
    tree=parse(f'(kicad_sch (version 20250114) (generator "buck33_candidate") (generator_version "9.0") (uuid "{uid("screen")}") (paper "A3") (title_block (title "BUCK33-A1 - isolated first 3.3 V converter") (date "2026-10-12") (rev "BUCK33-A1") (comment 1 "Not integrated, routed or power approved")))')
    tree += [['lib_symbols']+list(used.values())]+items+[['embedded_fonts','no']]
    (DEST/'Buck3V3.kicad_sch').write_text(ks.serialize(tree)+'\n',encoding='utf-8',newline='\n')
    spans=h.spans(oldtext);a=next(i for i,(x,y) in enumerate(spans) if '52233813-85f2-59bf-bfdb-e23d674b872c' in oldtext[x:y]);b=next(i for i,(x,y) in enumerate(spans) if '9f5da5f7-0f11-5e2f-8424-3999ba48876a' in oldtext[x:y]);removed=oldtext[spans[a][0]:spans[b][1]]
    assert sum('(property "Reference" "'+r+'"' in removed for r in contract['boundary'])==len(contract['boundary'])
    replacement=f'''(text "03  FIRST 3.3 V CONVERTER / BUCK33-A1" (at 211.333333 41 0) (effects (font (size 2 2)) (justify left bottom)) (uuid "{uid('parent_title')}"))
(sheet (at 241.3 71.12) (size 129.54 63.5) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0)) (uuid "{sheetid}")
 (property "Sheetname" "Buck3V3" (at 241.3 68.92 0) (effects (font (size 1.8 1.8)) (justify left bottom)))
 (property "Sheetfile" "Buck3V3.kicad_sch" (at 241.3 137.5 0) (effects (font (size 1.3 1.3)) (justify left top)))
 (pin "VIN_BUCK" input (at 241.3 91.44 180) (effects (font (size 1.5 1.5)) (justify left)) (uuid "{uid('parent_vin')}"))
 (instances (project "{PROJ}" (path "/{rootid}/{powerid}" (page "9")))))
(wire (pts (xy 220.98 91.44) (xy 241.3 91.44)) (stroke (width 0) (type default)) (uuid "{uid('parent_wire')}"))
(label "VIN_BUCK" (at 220.98 91.44 0) (effects (font (size 1.5 1.5)) (justify left bottom)) (uuid "{uid('parent_label')}"))
(text "LMR36520 candidate; global +3V3 / GND retained.\\nOther circuits remain unchanged and unqualified.\\nNo full-board acceptance is implied." (at 213.333333 160 0) (effects (font (size 1.6 1.6)) (justify left bottom)) (uuid "{uid('parent_note')}"))'''
    updated=oldtext[:spans[a][0]]+replacement+oldtext[spans[b][1]:];updated=updated.replace('(rev "INPUT-A1")','(rev "BUCK33-A1")');power.write_text(updated,encoding='utf-8',newline='\n')
    roottext=roottext.replace('(rev "INPUT-A1")','(rev "BUCK33-A1")').replace('INPUT-A1 candidate; not PCB integrated or power approved','BUCK33-A1 candidate; input/sense/IMU gates remain open');rootfile.write_text(roottext,encoding='utf-8',newline='\n')
    assert all(sha(ROOT/n)==v for n,v in protected.items())
    write(P/'build_manifest.json',{'source_revision':im['source_revision'],'builder_sha256':sha(Path(__file__)),'expected_contract_sha256':sha(P/'expected_contract.json'),'baseline_source_sha256':im['baseline_source_sha256'],'live_input_sha256':live,'local_preservation_sha256':{n:v for n,v in protected.items() if n not in live},'output_sha256':{f.relative_to(ROOT).as_posix():sha(f) for f in (P/'source').rglob('*') if f.is_file()},'removed_panel_objects':b-a+1,'live_electrical_delta':0,'pcb_updated':False,'hardware_tested':False,'fabrication_approved':False})
    print('BUCK33-A1 isolated schematic built; expected delta saved and live copper preserved.')
if __name__=='__main__':main()
