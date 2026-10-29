"""Lay out one captured Power sheet without changing electrical definitions.

Only this packet's 38-file copy is written. Connected islands translate as a
unit; hierarchy boxes resize with explicit matching pin/wire endpoint changes.
No primary generator, router, board writer or live CAD is invoked.
"""
from pathlib import Path
import argparse, datetime, hashlib, json, re, shutil, subprocess, uuid
P=Path(__file__).resolve().parent
ROOT=P.parents[2]
BASE=ROOT/'reviews/codex/vservo_reservoir'
SOURCE=P/'source'
POWER=Path('hardware/kicad_v2/Power.kicad_sch')
CLI='C:/Users/Jay/AppData/Local/Programs/KiCad/9.0/bin/kicad-cli.exe'
REV='POWER-DOC-01'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,d): p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8',newline='\n')
def mapping(p): return {f.relative_to(ROOT).as_posix():sha(f) for f in sorted(p.rglob('*')) if f.is_file()}
def check(h):
    for n,v in h.items():
        if sha(ROOT/n)!=v: raise ValueError('Input changed: '+n)
def blocks(text):
    """Return exact root-child text; do not parse or rewrite embedded symbols."""
    level=0;quoted=False;escaped=False;start=None
    for i,c in enumerate(text):
        if quoted:
            if escaped: escaped=False
            elif c=='\\': escaped=True
            elif c=='"': quoted=False
        elif c=='"': quoted=True
        elif c=='(':
            level+=1
            if level==2: start=i
        elif c==')':
            if level==2: yield text[start:i+1]
            level-=1
    if level or quoted: raise ValueError('Unbalanced source')
def kind(b): return re.match(r'\(([^\s()]+)',b)[1]
def translate(b,dx,dy):
    return re.sub(r'\((at|xy) (-?[\d.]+) (-?[\d.]+)',lambda m:f'({m[1]} {float(m[2])+dx:.6f} {float(m[3])+dy:.6f}',b)
def replace_one(s,old,new):
    if s.count(old)!=1: raise ValueError('Expected one literal: '+old)
    return s.replace(old,new)
def place_at(b,x,y):
    return re.sub(r'\(at (-?[\d.]+) (-?[\d.]+)',f'(at {x:g} {y:g}',b,count=1)
def uid(name): return str(uuid.uuid5(uuid.NAMESPACE_URL,'lora-review/'+REV+'/'+name))
def note(name,x,y,value,size=1.4,bold=False):
    return f'(text {json.dumps(value)}\n\t\t(exclude_from_sim no)\n\t\t(at {x:g} {y:g} 0)\n\t\t(effects (font (size {size:g} {size:g})'+(' (bold yes)' if bold else '')+f') (justify left bottom))\n\t\t(uuid "{uid(name)}")\n\t)'
def frame(name,x,y,w,h):
    pts=' '.join(f'(xy {a:g} {b:g})' for a,b in [(x,y),(x+w,y),(x+w,y+h),(x,y+h),(x,y)])
    return f'(polyline (pts {pts}) (stroke (width 0.2) (type solid)) (fill (type none)) (uuid "{uid(name)}"))'
def amend(text):
    out=[];electrical_count=0
    for b in blocks(text):
        k=kind(b)
        if k in ['text','polyline']: continue
        if k=='paper': b='(paper "A3")'
        elif k=='title_block':
            b=b.replace('(date "2026-10-12")','(date "2026-10-29")').replace('(rev "ACT-01")','(rev "PD-01")')
            b=b.replace('Input stage moved; other circuits unchanged and unqualified','Presentation only; electrical baseline VSERVO-01')
            b=b.replace('Build and review: docs/build/README.md','Review: reviews/codex/power_sheet_polish/README.md')
        elif k=='sheet':
            if '"Buck3V3.kicad_sch"' in b:
                b=translate(b,-195.58,-13.97)
                b=re.sub(r'\(size [\d.]+ [\d.]+\)','(size 129.54 30.48)',b,count=1)
                b=re.sub(r'(\(property "Sheetfile" "[^"]+"\s*\(at )[^)]+',r'\g<1>45.72 89.83 0',b,count=1)
            elif '"Buck5V.kicad_sch"' in b:
                b=translate(b,-187.96,-13.97)
                b=re.sub(r'\(size [\d.]+ [\d.]+\)','(size 106.68 30.48)',b,count=1)
                b=re.sub(r'(\(property "Sheetfile" "[^"]+"\s*\(at )[^)]+',r'\g<1>241.3 89.83 0',b,count=1)
                b=replace_one(b,'(at 373.380000 92.710000 0)','(at 347.98 80.01 0)')
            else: raise ValueError('Unknown sheet')
            electrical_count+=1
        elif k in ['symbol','wire','label','global_label','hierarchical_label','junction','no_connect']:
            electrical_count+=1
            identity=re.search(r'\(uuid "([^"]+)"',b)[1]
            if identity=='50f81f75-e4f0-53ba-b842-586d177f6059':
                coords=iter(['(xy 347.98 80.01)','(xy 391.16 80.01)']);b=re.sub(r'\(xy [^)]+\)',lambda m:next(coords),b)
            elif identity=='abc036fc-2afa-598b-a1b9-b6fcebeaf6c0': b=place_at(b,373.38,80.01)
            elif identity=='4b78073a-2a56-55da-9ee9-9f686bd51a1c':
                coords=iter(['(xy 391.16 80.01)','(xy 391.16 96.52)']);b=re.sub(r'\(xy [^)]+\)',lambda m:next(coords),b)
            elif identity=='70beb6a5-09dc-5f59-9d88-a550fce964f5': b=place_at(b,391.16,96.52)
            else:
                pos=re.search(r'\((?:at|xy) (-?[\d.]+) (-?[\d.]+)',b);x,y=float(pos[1]),float(pos[2])
                if y>=350:
                    oldxs=[17.78,50.8,81.28,114.3,144.78];ix=min(range(5),key=lambda i:abs(x-oldxs[i]))
                    if abs(x-oldxs[ix])>.0001: raise ValueError('Flag island x changed')
                    b=translate(b,213.36+17.78*ix-x,-102.87)
                elif x<200: b=translate(b,0,-83.82)
                elif x<400 and y>240:
                    b=translate(b,-73.66 if y>=300 else -203.2,-50.8 if y>=300 else -20.32)
                elif x<400: b=translate(b,-195.58,-13.97)
                elif y<170: b=translate(b,-187.96,-13.97)
                elif y>=214: b=translate(b,-91.44,-38.1) # C12 island
                elif x>500: b=translate(b,-276.86,-2.54) # C11 island
                elif x>450: b=translate(b,-139.7,-43.18) # D9 island
                else: b=translate(b,-182.88,-43.18) # D4 island
        out.append(b)
    if electrical_count!=98: raise ValueError(f'Unexpected electrical object count: {electrical_count}')
    out+=[note('title',12,16,'V2 / POWER DISTRIBUTION',3,True),
      note('subtitle',12,23,'POWER-DOC-01 | Presentation revision; electrical baseline VSERVO-01',1.5),
      note('scope',12,30,'6S requirement retained. Input protection is on PowerInput. Review draft: no fabrication or powered-use acceptance.',1.35)]
    frames=[('logic',12,37,188,78,'01  LOGIC CONVERTER / BUCK33-A1'),('actuator',208,37,200,78,'02  ACTUATOR CONVERTER / BUCK5-A1'),
      ('sense',12,123,188,109,'03  CURRENT + BATTERY SENSING'),('reservoir',208,123,200,118,'04  EXCLUSIVE VSERVO FEED + RESERVOIR'),
      ('test',12,238,188,45,'05  TEST POINTS / NODE LABELS'),('flags',208,247,90,36,'06  ERC DECLARATIONS')]
    for n,x,y,w,h,t in frames: out.extend([frame(n,x,y,w,h),note(n+'-title',x+4,y+7,t,1.7,True)])
    notes=[
      ('logic-box-title',60,68,'3.3 V logic rail',1.8),
      ('logic-box-identity',60,75,'LMR36520 / global +3V3 output',1.4),
      ('logic-box-detail',60,82,'Full circuit retained in the child sheet.',1.3),
      ('actuator-box-title',253,68,'5 V actuator + translator rail',1.7),
      ('actuator-box-identity',253,75,'LM76003 / +5V_BUCK output',1.4),
      ('actuator-box-detail',253,82,'Full circuit in the child sheet.',1.3),
      ('logic-desc',20,98,'LMR36520 cell: open Buck3V3 for the full circuit.',1.4),
      ('logic-limits',20,104,'Global +3V3 / GND unchanged. Input-feed and ADC gates remain open.',1.35),
      ('logic-sink',20,110,'Independent converter review does not qualify the complete board.',1.35),
      ('actuator-desc',216,104,'LM76003 cell: open Buck5V for the full circuit.',1.4),
      ('actuator-limits',216,110,'ACT-01: translator VCCB is fed before D4; VSERVO is a separate rail.',1.35),
      ('sense-shunt',20,219,'Nominal: R33 = 20 mOhm; INA180A1 gain 20; 0.4 V/A.',1.35),
      ('sense-divider',20,224,'Battery divider: 6.8k / (47k + 6.8k). ADC limits remain unqualified.',1.35),
      ('sense-hold',20,229,'Circuit retained for review; correct the full 6S sensing path before use.',1.35),
      ('population',216,137,'Master: D4 and D9 DNP. Future qualified variants use exactly one feed.',1.35),
      ('onboard',216,165,'ONBOARD (held): D4 fitted; D9 DNP.',1.35),
      ('bec',310,165,'BEC_ONLY (held): D9 fitted; D4 DNP.',1.35),
      ('reservoir-subtitle',216,175,'VSERVO TO J3.2 / TP4.1 | capacitor branches share named nets',1.4),
      ('c11-id',216,214,'C11: EEEFK1C101P; Panasonic D lands.',1.25),
      ('c12-credit',310,214,'C12: no effective-capacitance credit.',1.25),
      ('diode',216,222,'D4 / D9: SS34-E3/57T, SMC; pad 1 cathode connects to VSERVO.',1.3),
      ('voltage',216,227,'16 V is the capacitor rating; it does not define the receiver voltage limit.',1.3),
      ('sink',216,232,'No accepted sink / clamp. Reservoir, reverse-voltage and thermal gates open.',1.3),
      ('reference',216,237,'See VSERVO-01 / VSERVO-02 review packets. Missing permissions stay disabled.',1.3),
      ('test-hold',20,273,'Expected nets only. Measure rail limits, ripple and sequencing before acceptance.',1.3),
      ('test-labels',20,279,'Matching global names connect; hierarchy ports retain cross-sheet signals.',1.3),
      ('flags-hold',212,277,'Flags assert ERC supply intent;',1.1),
      ('flags-hold2',212,281,'they do not prove real power.',1.1)]
    out.extend(note(*n) for n in notes)
    return '(kicad_sch\n\t'+'\n\t'.join(out)+'\n)\n'
def build():
    inputs=read(P/'input_manifest.json');contract=read(P/'expected_contract.json');check(inputs['input_sha256'])
    if contract['revision']!=REV or contract['expected_pin_net_changes'] or contract['expected_component_identity_changes']: raise ValueError('Unexpected contract')
    basehash=read(BASE/'native_manifest.json')['input_sha256'];check(basehash)
    if len(basehash)!=38: raise ValueError('Expected 38 captured source files')
    expected=set()
    for n in basehash:
        rel=(ROOT/n).relative_to(BASE/'source');dest=SOURCE/rel;expected.add(dest)
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,dest)
    power=SOURCE/POWER
    power.write_text(amend(power.read_text(encoding='utf-8')),encoding='utf-8',newline='\n')
    if {f for f in SOURCE.rglob('*') if f.is_file()}!=expected: raise ValueError('Unexpected source file')
    check(basehash);check(inputs['input_sha256'])
    changed=[(ROOT/n).relative_to(BASE/'source').as_posix() for n,h in basehash.items() if sha(SOURCE/(ROOT/n).relative_to(BASE/'source'))!=h]
    if changed!=[POWER.as_posix()]: raise ValueError('Unexpected changed source: '+str(changed))
    if sha(P/'population_contract.json')!=sha(BASE/'population_contract.json'): raise ValueError('Population contract changed')
    write(P/'build_manifest.json',{'revision':REV,'baseline_head':inputs['baseline_head'],'baseline_candidate':'VSERVO-01','builder_sha256':sha(Path(__file__)),
      'expected_contract_sha256':sha(P/'expected_contract.json'),'population_contract_sha256':sha(P/'population_contract.json'),
      'baseline_source_sha256':basehash,'output_sha256':mapping(SOURCE),'changed_source_files':changed,'added_source_files':[],
      'candidate_pin_membership_delta':0,'candidate_identity_changes':0,'live_electrical_delta':0,'live_copper_delta':0,'primary_generator_or_router_invoked':False})
    print('Built isolated 38-file presentation candidate; only Power.kicad_sch changed')
def native():
    built=read(P/'build_manifest.json');inputs=read(P/'input_manifest.json');check(built['output_sha256']);check(inputs['input_sha256'])
    if built['builder_sha256']!=sha(Path(__file__)): raise ValueError('Builder changed after build')
    out=P/'native';out.mkdir(exist_ok=True);nr=out.relative_to(ROOT).as_posix()
    sch=(SOURCE/'hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_sch').relative_to(ROOT).as_posix()
    commands=[['sch','export','netlist','--format','kicadxml','-o',nr+'/netlist.xml',sch],['sch','erc','--format','json','--severity-all','-o',nr+'/erc.json',sch],['sch','export','svg','-o',nr+'/svg/',sch]]
    report={'revision':REV,'captured_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'kicad_version':subprocess.check_output([CLI,'version'],text=True).strip(),'runner_sha256':sha(Path(__file__)),'input_sha256':built['output_sha256'],'commands':[]}
    for command in commands:
        result=subprocess.run([CLI]+command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
        report['commands'].append({'argv':[CLI]+command,'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
        if result.returncode: raise ValueError(result.stderr or result.stdout)
    check(built['output_sha256']);check(inputs['input_sha256']);report['inputs_unchanged_after_commands']=True
    report['output_sha256']=mapping(out);write(P/'native_manifest.json',report)
    print('Captured 3 native commands,',len(report['output_sha256']),'outputs; sources unchanged')
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--build',action='store_true');ap.add_argument('--native',action='store_true');args=ap.parse_args()
    if not(args.build or args.native): ap.error('Choose --build and/or --native explicitly')
    if args.build: build()
    if args.native: native()
