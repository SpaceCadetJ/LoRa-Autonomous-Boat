"""Create only an isolated C11 identity/land amendment, then explicitly export native evidence.

Never calls primary generators, routes, writes a board, or edits live CAD.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,re,shutil,subprocess
P=Path(__file__).resolve().parent; ROOT=P.parents[2]
BASE=ROOT/'reviews/codex/actuator_latch'; SOURCE=P/'source'
CLI='C:/Users/Jay/AppData/Local/Programs/KiCad/9.0/bin/kicad-cli.exe'
NAME='CP_Panasonic_FK_D_6.3x5.8'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,d): p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8',newline='\n')
def mapping(p): return {f.relative_to(ROOT).as_posix():sha(f) for f in sorted(p.rglob('*')) if f.is_file()}
def check(h):
    for n,v in h.items():
        if sha(ROOT/n)!=v: raise ValueError('Input changed: '+n)
def c11_span(text):
    marker='(property "Reference" "C11"'
    if text.count(marker)!=1: raise ValueError('C11 reference must be unique')
    start=text.rfind('\n\t(symbol\n',0,text.index(marker))+1
    if start==0: raise ValueError('C11 symbol start not found')
    level=0; quoted=False; escape=False
    for i in range(start,len(text)):
        c=text[i]
        if quoted:
            if escape: escape=False
            elif c=='\\': escape=True
            elif c=='"': quoted=False
        elif c=='"': quoted=True
        elif c=='(': level+=1
        elif c==')':
            level-=1
            if level==0: return start,i+1
    raise ValueError('Unbalanced C11 symbol')
def amend(text,contract):
    start,end=c11_span(text); old=text[start:end]; new=old
    names={'Value':'value','MPN':'mpn','Manufacturer':'manufacturer','Footprint':'footprint','Datasheet':'datasheet','Description':'description'}
    for field,key in names.items():
        pattern=r'(\(property "'+field+r'" )"(?:\\.|[^"\\])*"'
        new,count=re.subn(pattern,lambda m:m[1]+json.dumps(contract['candidate_identity'][key]),new)
        if count!=1: raise ValueError('Unexpected property count: '+field)
    return text[:start]+new+text[end:]
def footprint():
    text=['(footprint "'+NAME+'"','  (version 20241229)','  (generator "codex_reviewed_proposal")','  (layer "F.Cu")',
      '  (descr "Panasonic FK standard D-size recommended lands: 3.2 x 1.6 mm, 1.8 mm inner gap. Local courtyard, mask, paste and polarity artwork are proposals; no assembly or reservoir acceptance.")',
      '  (tags "Panasonic EEEFK1C101P 100uF 16V FK D 6.3x5.8 held")','  (attr smd)',
      '  (property "Reference" "REF**" (at 0 -4.5) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))',
      '  (property "Value" "EEEFK1C101P" (at 0 4.5) (layer "F.Fab") (effects (font (size 0.7 0.7) (thickness 0.1))))',
      '  (fp_circle (center 0 0) (end 3.15 0) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))']
    groups=[('F.Fab',.1,[((-3.3,-3.3),(3.3,-3.3)),((3.3,-3.3),(3.3,3.3)),((3.3,3.3),(-3.3,3.3)),((-3.3,3.3),(-3.3,-3.3)),((-2.4,-1.5),(-1.6,-1.5)),((-2,-1.9),(-2,-1.1))]),
      ('F.SilkS',.12,[((-3.45,-1.1),(-3.45,-3.45)),((-3.45,-3.45),(3.45,-3.45)),((3.45,-3.45),(3.45,-1.1)),((3.45,1.1),(3.45,3.45)),((3.45,3.45),(-3.45,3.45)),((-3.45,3.45),(-3.45,1.1)),((-4.8,-1.5),(-4,-1.5)),((-4.4,-1.9),(-4.4,-1.1))]),
      ('F.CrtYd',.05,[((-5.1,-3.8),(4.6,-3.8)),((4.6,-3.8),(4.6,3.8)),((4.6,3.8),(-5.1,3.8)),((-5.1,3.8),(-5.1,-3.8))])]
    for layer,width,pairs in groups:
        for (x1,y1),(x2,y2) in pairs:
            text.append(f'  (fp_line (start {x1:g} {y1:g}) (end {x2:g} {y2:g}) (stroke (width {width:g}) (type solid)) (layer "{layer}"))')
    for n,x in [(1,-2.5),(2,2.5)]:
        text.append(f'  (pad "{n}" smd rect (at {x:g} 0) (size 3.2 1.6) (layers "F.Cu" "F.Paste" "F.Mask"))')
    return '\n'.join(text+[')'])+'\n'
def build():
    inputs=read(P/'input_manifest.json'); contract=read(P/'expected_contract.json');check(inputs['input_sha256'])
    basehash=read(BASE/'native_manifest.json')['input_sha256'];check(basehash)
    if len(basehash)!=37: raise ValueError('Expected37 captured source files')
    expected=set()
    for n,h in basehash.items():
        rel=(ROOT/n).relative_to(BASE/'source');dest=SOURCE/rel;expected.add(dest)
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,dest)
    power=SOURCE/'hardware/kicad_v2/Power.kicad_sch'
    power.write_bytes(amend(power.read_bytes().decode('utf-8'),contract).encode('utf-8'))
    land=SOURCE/('hardware/kicad_v2/LoRa_Boat_Controller_V2.pretty/'+NAME+'.kicad_mod')
    land.write_text(footprint(),encoding='utf-8',newline='\n');expected.add(land)
    if {f for f in SOURCE.rglob('*') if f.is_file()}!=expected: raise ValueError('Unexpected candidate source file')
    shutil.copyfile(BASE/'population_contract.json',P/'population_contract.json')
    check(basehash);check(inputs['input_sha256'])
    write(P/'build_manifest.json',{'revision':'VSERVO-01','baseline_head':inputs['baseline_head'],'baseline_candidate':'ACT-04','builder_sha256':sha(Path(__file__)),
      'expected_contract_sha256':sha(P/'expected_contract.json'),'population_contract_sha256':sha(P/'population_contract.json'),
      'baseline_source_sha256':basehash,'output_sha256':mapping(SOURCE),'changed_source_files':['hardware/kicad_v2/Power.kicad_sch'],
      'added_source_files':[land.relative_to(SOURCE).as_posix()],'candidate_pin_membership_delta':0,'live_electrical_delta':0,'live_copper_delta':0,'primary_generator_or_router_invoked':False})
    print('Built isolated38-file C11 identity/land candidate;37 ACT-04 inputs preserved')
def native():
    build=read(P/'build_manifest.json'); inputs=read(P/'input_manifest.json');check(build['output_sha256']);check(inputs['input_sha256'])
    out=P/'native';out.mkdir(exist_ok=True);nr=out.relative_to(ROOT).as_posix()
    sch=(SOURCE/'hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_sch').relative_to(ROOT).as_posix()
    commands=[['sch','export','netlist','--format','kicadxml','-o',nr+'/netlist.xml',sch],['sch','erc','--format','json','--severity-all','-o',nr+'/erc.json',sch],['sch','export','svg','-o',nr+'/svg/',sch]]
    report={'revision':'VSERVO-01','captured_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'kicad_version':subprocess.check_output([CLI,'version'],text=True).strip(),'runner_sha256':sha(Path(__file__)),'input_sha256':build['output_sha256'],'commands':[]}
    for command in commands:
        result=subprocess.run([CLI]+command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
        report['commands'].append({'argv':[CLI]+command,'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
        if result.returncode: raise ValueError(result.stderr or result.stdout)
    check(build['output_sha256']);check(inputs['input_sha256']);report['inputs_unchanged_after_commands']=True
    report['output_sha256']=mapping(out);write(P/'native_manifest.json',report)
    print('Captured3 native commands,',len(report['output_sha256']),'outputs; sources unchanged')
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--build',action='store_true');ap.add_argument('--native',action='store_true');args=ap.parse_args()
    if not(args.build or args.native): ap.error('Choose --build and/or --native explicitly')
    if args.build: build()
    if args.native: native()
