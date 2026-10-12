"""Build only the isolated BUCK5-A1 second-converter candidate."""
from pathlib import Path
import copy,importlib.util,json,math,shutil,sys,uuid
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ROOT=P.parents[2];DEST=P/'source/hardware/kicad_v2';PROJ='LoRa_Boat_Controller_V2'
s=importlib.util.spec_from_file_location('input_helpers',P.parent/'input_stage/build_candidate.py');h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
ks=h.ks;Str=ks.Str;parse=h.parse;child=h.child;children=h.children;sha=h.sha

def uid(k):return str(uuid.uuid5(uuid.NAMESPACE_URL,'lora-buck5-A1/'+k))
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8',newline='\n')
def main():
    im=json.loads((P/'input_manifest.json').read_text());contract=json.loads((P/'expected_contract.json').read_text())
    live=json.loads((ROOT/'reviews/codex/design_completion/native-review/review.json').read_text())['input_manifest']
    protected={**live,**{n:sha(ROOT/n) for n in ['hardware/kicad/tools/v1_design.py','hardware/kicad_v2/tools/route_v2.py']}}
    for n,v in {**protected,**im['baseline_source_sha256'],**im['additional_input_sha256']}.items():assert sha(ROOT/n)==v,n
    for n in im['baseline_source_sha256']:
        rel=Path(n).relative_to('reviews/codex/buck_3v3/source');dst=P/'source'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,dst)
    for f in (P/'inputs/footprints').glob('*.kicad_mod'):shutil.copyfile(f,DEST/(PROJ+'.pretty')/f.name)
    reg=parse((P/'inputs/LM76003_reviewed.kicad_sym').read_text());standalone=copy.deepcopy(reg);standalone[1]=Str('LM76003')
    symfile=DEST/(PROJ+'.kicad_sym');lib=parse(symfile.read_text());lib.append(standalone);symfile.write_text(ks.serialize(lib)+'\n',encoding='utf-8',newline='\n')
    power=DEST/'Power.kicad_sch';oldtext=power.read_text();old=parse(oldtext)
    rootfile=DEST/(PROJ+'.kicad_sch');roottext=rootfile.read_text();root=parse(roottext);rootid=str(child(root,'uuid')[1])
    psheet=next(c for c in children(root,'sheet') if any(p[1]=='Sheetname' and p[2]=='Power' for p in children(c,'property')));powerid=str(child(psheet,'uuid')[1]);sheetid=uid('sheet')
    libs={str(c[1]):c for c in child(old,'lib_symbols')[1:]};libs[str(reg[1])]=reg
    comps={str(next(p[2] for p in children(c,'property') if p[1]=='Reference')):c for c in children(old,'symbol')}
    items=[];used={};serial=0
    def add(code):items.append(parse(code))
    def ident(k):
        nonlocal serial;serial+=1;return uid(k+str(serial))
    def wire(x1,y1,x2,y2):
        assert (x1,y1)!=(x2,y2)
        add(f'(wire (pts (xy {x1} {y1}) (xy {x2} {y2})) (stroke (width 0) (type default)) (uuid "{ident("wire")}"))')
    def text(t,x,y,size=1.5):add(f'(text "{t}" (at {x} {y} 0) (effects (font (size {size} {size})) (justify left bottom)) (uuid "{ident("text")}"))')
    def label(t,x,y,kind='label',shape='input'):
        extra=f'(shape {shape})' if kind=='hierarchical_label' else ('(shape passive)' if kind=='global_label' else '')
        add(f'({kind} "{t}" {extra} (at {x} {y} 0) (effects (font (size 1.3 1.3)) (justify left bottom)) (uuid "{ident("label")}"))')
    def dot(x,y):add(f'(junction (at {x} {y}) (diameter 0) (color 0 0 0 0) (uuid "{ident("dot")}"))')
    def symbol(ref,x,y,rot,px,py):
        part=contract['candidate_parts'][ref];libid=':'.join(part['library']);sym=libs[libid];used[libid]=sym;pins=ks.symbol_pins(sym)
        url='https://www.ti.com/lit/ds/symlink/lm76003.pdf' if ref=='U3' else ('https://www.coilcraft.com/getmedia/ea51f14b-7f32-4dc6-8dfe-d4b70549040f/xal60xx.pdf' if ref=='L2' else ('https://www.vishay.com/docs/20035/dcrcwe3.pdf' if ref.startswith('R') else ('https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no='+part['mpn'] if part['manufacturer']=='TDK' else 'https://www.ti.com/lit/ug/snvu677/snvu677.pdf')))
        fields=[]
        for name,val in [('Reference',ref),('Value',part['value']),('Footprint',part['footprint']),('MPN',part['mpn']),('Manufacturer',part['manufacturer']),('Datasheet',url),('Description','Held candidate; see reviews/codex/buck_5v/README.md')]:
            yy=py+(3.5 if name=='Value' else 0);hide='' if name in ['Reference','Value'] else '(hide yes)'
            fields.append(f'(property "{name}" "{val}" (at {px} {yy} {90 if rot in (90,270) else 0}) (effects (font (size 1.4 1.4)) (justify left bottom) {hide}))')
        suuid=str(child(comps[ref],'uuid')[1]) if ref in comps else uid(ref)
        ps=''.join(f'(pin "{p["number"]}" (uuid "{uid(ref+p["number"])}"))' for p in pins)
        add(f'(symbol (lib_id "{libid}") (at {x} {y} {rot}) (unit 1) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) (uuid "{suuid}") {" ".join(fields)} {ps} (instances (project "{PROJ}" (path "/{rootid}/{powerid}/{sheetid}" (reference "{ref}") (unit 1)))))')
        a=math.radians(rot);return {p['number']:(round(x+p['x']*math.cos(a)-p['y']*math.sin(a),6),round(y-p['x']*math.sin(a)-p['y']*math.cos(a),6)) for p in pins}
    text('BUCK5-A1 / 5 V AUXILIARY AND ACTUATOR CONVERTER',16,21,2.8)
    text('ISOLATED WIRED CANDIDATE - input stage, OR-ing, buffer rail and hardware qualification remain open',16,32,1.8)
    text('2 A rail design goal; simultaneous full logic + actuator load is not accepted on the present 7 V feed.',16,42,1.6)
    text('SEPARATE LOCAL INPUT BANK',25,54,1.7);text('SWITCH / BOOT',231,54,1.7);text('OUTPUT BANK',311,82,1.7)
    u=symbol('U3',198.12,105.41,0,186,77)
    cin=[symbol('C10',40.64,104.14,0,48,101),symbol('C52',85.09,104.14,0,93,101),symbol('C53',129.54,104.14,0,137,101)]
    cb=symbol('C7',243.84,81.28,180,278,84);ind=symbol('L2',266.7,97.79,90,267,110)
    cv=symbol('C54',240.03,135.89,0,248,132)
    cout=[symbol(ref,x,124.46,0,x+6,121) for ref,x in zip(['C8','C9','C49','C50','C51'],[284.48,309.88,335.28,360.68,386.08])]
    label('VIN_BUCK',20.32,63.5,'hierarchical_label');xs=[20.32,40.64,85.09,129.54,175.26]
    for a,b in zip(xs,xs[1:]):wire(a,63.5,b,63.5)
    for cap in cin:wire(cap['1'][0],63.5,*cap['1']);wire(*cap['2'],cap['2'][0],151.13);dot(cap['1'][0],63.5)
    wire(175.26,63.5,175.26,u['20'][1]);wire(175.26,u['20'][1],*u['20']);wire(175.26,u['20'][1],175.26,u['18'][1]);wire(175.26,u['18'][1],*u['18']);dot(175.26,u['20'][1])
    wire(*u['9'],218.44,u['9'][1]);wire(218.44,u['9'][1],218.44,60.96);wire(218.44,60.96,238.76,60.96);label('+5V_BUCK',238.76,60.96)
    wire(*u['6'],231.14,u['6'][1]);wire(231.14,u['6'][1],231.14,68.58);wire(231.14,68.58,259.08,68.58);wire(259.08,68.58,259.08,cb['2'][1]);wire(259.08,cb['2'][1],*cb['2']);label('BOOT_5V',232,68.58)
    wire(*u['1'],243.84,u['1'][1]);wire(243.84,u['1'][1],*ind['1']);wire(*cb['1'],243.84,u['1'][1]);dot(243.84,u['1'][1]);label('SW_5V',246.38,u['1'][1])
    # CBOOT SW leg passes below BOOT loop without joining it; no hidden wire crossings.
    xs=[ind['2'][0],284.48,309.88,335.28,360.68,386.08,398.78]
    for a,b in zip(xs,xs[1:]):wire(a,97.79,b,97.79)
    label('+5V_BUCK',398.78,97.79,'hierarchical_label','output')
    for cap in cout:wire(cap['1'][0],97.79,*cap['1']);wire(*cap['2'],cap['2'][0],151.13);dot(cap['1'][0],97.79)
    wire(*u['8'],240.03,u['8'][1]);wire(240.03,u['8'][1],*cv['1']);wire(*cv['2'],240.03,151.13);label('VCC_5V',222.25,u['8'][1])
    gp=sorted(set(u[str(p)] for p in [7,13,14,15,19,23,24,25,26,27,28,29,30,31]))
    for x,y in gp:wire(x,y,x,151.13)
    wire(*u['17'],172.72,u['17'][1]);wire(172.72,u['17'][1],172.72,151.13)
    xs=sorted(set([40.64,85.09,129.54,172.72]+[x for x,y in gp]+[240.03,284.48,309.88,335.28,360.68,386.08,398.78]))
    for a,b in zip(xs,xs[1:]):wire(a,151.13,b,151.13)
    for x in xs[1:-1]:dot(x,151.13)
    label('GND',398.78,151.13,'global_label')
    for pin in ['10','11','16']:add(f'(no_connect (at {u[pin][0]} {u[pin][1]}) (uuid "{uid("nc"+pin)}"))')
    wire(*u['12'],222.25,u['12'][1]);label('FB_5V',222.25,u['12'][1])
    text('BIAS: LOCAL BYPASS AT PIN 9',30,171,1.7);bias=symbol('C55',48.26,191.77,0,57,189)
    wire(48.26,180.34,*bias['1']);label('+5V_BUCK',48.26,180.34);wire(*bias['2'],48.26,203.2);label('GND',48.26,203.2,'global_label')
    text('FEEDBACK: BEFORE D4, NOT AT VSERVO',268,169,1.7)
    rt=symbol('R8',309.88,182.88,0,319,180);rb=symbol('R9',309.88,215.9,0,319,213)
    label('+5V_BUCK',309.88,173.99);wire(309.88,173.99,*rt['1']);wire(*rt['2'],309.88,199.39);wire(309.88,199.39,*rb['1']);wire(284.48,199.39,309.88,199.39);label('FB_5V',284.48,199.39);dot(309.88,199.39);wire(*rb['2'],309.88,227.33);label('GND',309.88,227.33,'global_label')
    for t,y in [('RT10 open: 500 kHz nominal; SS11 open: internal soft start; PG16 unused.',167),('SYNC17 grounded: auto mode. EN18 tied to VIN; no pack cutoff.',175),('All NC ground pads incl. 7 and 23 + AGND/PGND/EP tied to GND.',183),('BOOT 470 nF; VCC 2.2 uF; BIAS 1 uF. Effective values held.',191),('Five output capacitors: 110 uF rated; loop / bias / thermal unqualified.',199),('10 uH differs from TI 6.8 uH quick-start at 500 kHz.',207),('100k / 24.9k: 5.046 V nominal; full tolerance envelope in guide.',215)]:text(t,100,y,1.25)
    used['power:PWR_FLAG']=libs['power:PWR_FLAG']
    add(f'(symbol (lib_id "power:PWR_FLAG") (at 114.3 228.6 0) (unit 1) (exclude_from_sim no) (in_bom no) (on_board yes) (dnp no) (uuid "{uid("output_flag")}") (property "Reference" "#FLG5V01" (at 114.3 226.06 0) (effects (font (size 1.27 1.27)) (hide yes))) (property "Value" "PWR_FLAG" (at 114.3 224.79 0) (effects (font (size 1.27 1.27)))) (pin "1" (uuid "{uid("flagpin")}")) (instances (project "{PROJ}" (path "/{rootid}/{powerid}/{sheetid}" (reference "#FLG5V01") (unit 1)))))')
    label('+5V_BUCK',114.3,228.6)
    text('PWR_FLAG describes drive through L2 for ERC only; no measured output is implied.',140,231,1.2)
    text('INTEGRATION GATES / PRESERVE 6S AND BOTH ACTUATOR SUPPLY VARIANTS',16,242,1.8)
    text('D4/D9 and VSERVO remain unchanged: diode loss, SMC/SMA mismatch and buffer supply are still held.',16,251,1.5)
    text('Full input loss, negative rail, source damping, capacitor bounds, thermal / short-circuit and PCB fit need closure.',16,259,1.5)
    text('3.3 V child preserved. IMU2 remains separate. Native checks do not establish fabrication or powered acceptance.',16,267,1.5)
    tree=parse(f'(kicad_sch (version 20250114) (generator "buck5_candidate") (generator_version "9.0") (uuid "{uid("screen")}") (paper "A3") (title_block (title "BUCK5-A1 - isolated 5 V converter") (date "2026-10-12") (rev "BUCK5-A1") (comment 1 "Not PCB integrated or power approved")))')
    tree += [['lib_symbols']+list(used.values())]+items+[['embedded_fonts','no']]
    (DEST/'Buck5V.kicad_sch').write_text(ks.serialize(tree)+'\n',encoding='utf-8',newline='\n')
    spans=h.spans(oldtext);a=next(i for i,(x,y) in enumerate(spans) if 'f8feded5-6ece-5c10-8671-42e40c01d007' in oldtext[x:y]);b=next(i for i,(x,y) in enumerate(spans) if '8e11362a-c181-55dc-ae3c-15446d054dd4' in oldtext[x:y]);removed=oldtext[spans[a][0]:spans[b][1]]
    assert sum('(property "Reference" "'+r+'"' in removed for r in contract['boundary'])==9
    replacement=f'''(sheet (at 429.26 71.12) (size 132.08 58.42) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0)) (uuid "{sheetid}")
 (property "Sheetname" "Buck5V" (at 429.26 68.92 0) (effects (font (size 1.8 1.8)) (justify left bottom)))
 (property "Sheetfile" "Buck5V.kicad_sch" (at 429.26 132 0) (effects (font (size 1.3 1.3)) (justify left top)))
 (pin "VIN_BUCK" input (at 429.26 91.44 180) (effects (font (size 1.4 1.4)) (justify left)) (uuid "{uid('parent_vin')}"))
 (pin "+5V_BUCK" output (at 561.34 106.68 0) (effects (font (size 1.4 1.4)) (justify right)) (uuid "{uid('parent_vout')}"))
 (instances (project "{PROJ}" (path "/{rootid}/{powerid}" (page "10")))))
(wire (pts (xy 414.02 91.44) (xy 429.26 91.44)) (stroke (width 0) (type default)) (uuid "{uid('parent_inwire')}"))
(label "VIN_BUCK" (at 414.02 91.44 0) (effects (font (size 1.4 1.4)) (justify left bottom)) (uuid "{uid('parent_inlabel')}"))
(wire (pts (xy 561.34 106.68) (xy 579.12 106.68)) (stroke (width 0) (type default)) (uuid "{uid('parent_outwire')}"))
(label "+5V_BUCK" (at 579.12 106.68 0) (effects (font (size 1.4 1.4)) (justify left bottom)) (uuid "{uid('parent_outlabel')}"))
(text "BUCK5-A1: LM76003 candidate, nominal 5.046 V before D4.\\nOR-ing and buffer-supply qualification remain open." (at 408 155 0) (effects (font (size 1.7 1.7)) (justify left bottom)) (uuid "{uid('parent_note')}"))'''
    updated=oldtext[:spans[a][0]]+replacement+oldtext[spans[b][1]:]
    updated=updated.replace('(rev "BUCK33-A1")','(rev "BUCK5-A1")').replace('Nominal buck output 5.08 V before OR-ing diode loss.','Nominal buck output 5.046 V before OR-ing diode loss.')
    power.write_text(updated,encoding='utf-8',newline='\n')
    roottext=roottext.replace('(rev "BUCK33-A1")','(rev "BUCK5-A1")').replace('BUCK33-A1 candidate; input/sense/IMU gates remain open','BUCK5-A1 candidate; input, OR-ing, sense and IMU gates remain open');rootfile.write_text(roottext,encoding='utf-8',newline='\n')
    assert sha(DEST/'Buck3V3.kicad_sch')==sha(P.parent/'buck_3v3/source/hardware/kicad_v2/Buck3V3.kicad_sch')
    assert all(sha(ROOT/n)==v for n,v in protected.items())
    write(P/'build_manifest.json',{'source_revision':im['source_revision'],'builder_sha256':sha(Path(__file__)),'expected_contract_sha256':sha(P/'expected_contract.json'),'baseline_source_sha256':im['baseline_source_sha256'],'live_input_sha256':live,'local_preservation_sha256':{n:v for n,v in protected.items() if n not in live},'output_sha256':{f.relative_to(ROOT).as_posix():sha(f) for f in (P/'source').rglob('*') if f.is_file()},'removed_panel_objects':b-a+1,'live_electrical_delta':0,'pcb_updated':False,'hardware_tested':False,'fabrication_approved':False})
    print('BUCK5-A1 isolated schematic built; first converter and live copper preserved.')
if __name__=='__main__':main()
