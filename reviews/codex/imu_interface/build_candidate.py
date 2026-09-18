#!/usr/bin/env python3
"""Generate only an isolated E-01 schematic candidate; never modify live CAD."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, importlib, json, os, shutil, subprocess, sys
sys.dont_write_bytecode = True
PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[2]
REVISION = 'a66980cb9728d30c38aa93c44303feee83f3ab08'
SOURCE = PACKET / 'source'
INPUTS = PACKET / 'inputs'
PROJECT = 'LoRa_Boat_Controller_V2'
FP_NAME = 'TI_DCT0008A_PCA9306_3x3mm_P0.65mm'
CAPTURE = ['hardware/kicad/tools/'+n for n in ['gen_sch.py','kicad_sym.py','kicad_write.py','schematic_layout.py','v1_design.py']]
CAPTURE += ['hardware/kicad_v2/tools/'+n for n in ['gen_v2.py','v2_design.py']]
CAPTURE += ['hardware/kicad/LoRa_Boat_Controller.kicad_sym']
CAPTURE += ['hardware/kicad/LoRa_Boat_Controller.pretty/'+n+'.kicad_mod' for n in ['SOT-23-6W_PE-SOT23-6W-0512_NMD','M-FLAT_TOS-L','CONN5_1LFBN-RC_SUL']]
CAPTURE += ['hardware/kicad_v2/'+n for n in [PROJECT+'.kicad_sym',PROJECT+'.kicad_pro','fp-lib-table','sym-lib-table',PROJECT+'.pretty/QFN-24_3x3mm_P0.4mm_NoEP.kicad_mod']]

def require(condition, message):
    if not condition: raise RuntimeError(message)
def owned(p):
    resolved=Path(p).resolve()
    require(resolved.is_relative_to(PACKET.resolve()), f'Write outside candidate packet: {p}')
    return resolved
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p, data):
    p=owned(p)
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8',newline='\n')
def capture():
    manifest_path = PACKET/'input_manifest.json'
    if manifest_path.exists():
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
        require(manifest['revision']==REVISION, 'Unexpected captured revision')
        for name, expected in manifest['sha256'].items():
            require(name in CAPTURE, f'Unexpected captured path: {name}')
            require(sha(owned(INPUTS/name))==expected, f'Changed captured input: {name}')
    else:
        manifest={'revision':REVISION,'sha256':{}}
    for name in CAPTURE:
        if name in manifest['sha256']: continue
        data=subprocess.check_output(['git','show',f'{REVISION}:{name}'],cwd=ROOT)
        dest=owned(INPUTS/name);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        manifest['sha256'][name]=sha(dest)
    dump(manifest_path,manifest)
    for name in CAPTURE:
        dest=owned(SOURCE/name);dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(INPUTS/name,dest)
    return manifest

def clone_symbol(ks, lib, old, new, datasheet, footprint):
    s=ks.load_symbol(lib,old);tree=s['tree'];tree[1]=ks.Str(new)
    for item in tree:
        if not isinstance(item,list) or not item: continue
        if item[0]=='symbol' and str(item[1]).startswith(old+'_'):
            item[1]=ks.Str(new+str(item[1])[len(old):])
        if item[0]=='property' and item[1] in ('Value','Footprint','Datasheet'):
            item[2]=ks.Str({'Value':new,'Footprint':footprint,'Datasheet':datasheet}[str(item[1])])
    return tree

def footprint():
    # TI DCT0008A, drawing 4220784/D (October 2025), example land pattern.
    lines=[f'(footprint "{FP_NAME}" (version 20241229) (generator "imu_candidate") (layer "F.Cu")',
      ' (descr "PCA9306 DCT0008A: TI 4220784/D Oct 2025; 3x3 mm body, 0.65 mm pitch, 1.1x0.4 mm lands, row centers 3.8 mm. Candidate; stencil/assembly unqualified.")',
      ' (attr smd)',
      ' (fp_text reference "REF**" (at 0 -2.5) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))',
      f' (fp_text value "PCA9306DCTR" (at 0 2.5) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))',
      ' (fp_rect (start -2.7 -1.8) (end 2.7 1.8) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))',
      ' (fp_line (start -1.5 -1.0) (end -1.0 -1.5) (stroke (width 0.1) (type default)) (layer "F.Fab"))',
      ' (fp_line (start -1.0 -1.5) (end 1.5 -1.5) (stroke (width 0.1) (type default)) (layer "F.Fab"))',
      ' (fp_line (start 1.5 -1.5) (end 1.5 1.5) (stroke (width 0.1) (type default)) (layer "F.Fab"))',
      ' (fp_line (start 1.5 1.5) (end -1.5 1.5) (stroke (width 0.1) (type default)) (layer "F.Fab"))',
      ' (fp_line (start -1.5 1.5) (end -1.5 -1.0) (stroke (width 0.1) (type default)) (layer "F.Fab"))',
      ' (fp_line (start -1.5 -1.67) (end 1.5 -1.67) (stroke (width 0.12) (type default)) (layer "F.SilkS"))',
      ' (fp_line (start -1.5 1.67) (end 1.5 1.67) (stroke (width 0.12) (type default)) (layer "F.SilkS"))',
      ' (fp_circle (center -2.5 -1.5) (end -2.4 -1.5) (stroke (width 0.12) (type default)) (fill none) (layer "F.SilkS"))']
    for n in range(1,9):
        x=-1.9 if n<=4 else 1.9
        y=-0.975+(n-1)*0.65 if n<=4 else 0.975-(n-5)*0.65
        lines.append(f' (pad "{n}" smd roundrect (at {x} {y:.3f}) (size 1.1 0.4) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))')
    return '\n'.join(lines+[')'])+'\n'

def main():
    live_manifest=json.loads((ROOT/'reviews/codex/design_completion/native-review/review.json').read_text(encoding='utf-8-sig'))['input_manifest']
    before={name:sha(ROOT/name) for name in live_manifest}
    require(before==live_manifest, 'Live CAD changed since the integrated review; recapture deliberately before continuing')
    owned(SOURCE);owned(INPUTS)
    capture()
    # Isolated presentation patch: different vertical supply/reference labels need separate rows.
    primitive=owned(SOURCE/'hardware/kicad/tools/gen_sch.py')
    primitive_text=primitive.read_text(encoding='utf-8')
    old='            if net in POWER_NETS:\n                # Adjacent unlike supply pins'
    require(old in primitive_text, 'Expected vertical-label layout changed')
    primitive_text=primitive_text.replace(old, '            if net in POWER_NETS or self.name == "Navigation":\n                # Adjacent unlike supply pins', 1)
    primitive_text=primitive_text.replace('Annotated functional groups; connectivity preserved', 'IMU candidate: five U6 pin changes; not PCB integrated')
    primitive_text=primitive_text.replace('V2 draft','V2-IMU1').replace('2026-09-17','2026-09-18')
    primitive_text=primitive_text.replace("        ry, vy = y - bb[3] - 12 - top_clearance, y - bb[3] - 8.5 - top_clearance", "        if self.name == 'Navigation' and ref in {'U6','U10','U11'}: top_clearance += 3\n        ry, vy = y - bb[3] - 12 - top_clearance, y - bb[3] - 8.5 - top_clearance")
    primitive.write_text(primitive_text,encoding='utf-8',newline='\n')
    sys.path.insert(0,str(SOURCE/'hardware/kicad/tools'))
    sys.path.insert(0,str(SOURCE/'hardware/kicad_v2/tools'))
    import gen_v2 as v
    import kicad_sym as ks
    import schematic_layout as layout
    for module in [v,ks,layout,v.D,v.gen_sch]:
        require(Path(module.__file__).resolve().is_relative_to(SOURCE.resolve()), f'Imported generator outside isolated source: {module.__file__}')
    owned(v.V2DIR);owned(v.V2LIB_SYM);owned(v.V2PRETTY);owned(v.BUILD)
    d=v.D
    libfile=Path(v.V2LIB_SYM)
    lib=ks.parse(libfile.read_text(encoding='utf-8'))[0]
    lib.append(clone_symbol(ks,'Logic_LevelTranslator','SN74LVC1T45DBV','SN74AXC1T45DBV','https://www.ti.com/lit/ds/symlink/sn74axc1t45.pdf','Package_TO_SOT_SMD:SOT-23-6'))
    lib.append(clone_symbol(ks,'Interface','PCA9306','TI_PCA9306DCT','https://www.ti.com/lit/ds/symlink/pca9306.pdf',PROJECT+':'+FP_NAME))
    libfile.write_text(ks.serialize(lib)+'\n',encoding='utf-8',newline='\n')
    (Path(v.V2PRETTY)/(FP_NAME+'.kicad_mod')).write_text(footprint(),encoding='utf-8',newline='\n')
    additions={
      'U9':(('Regulator_Linear','TLV75518PDBV'),'Package_TO_SOT_SMD:SOT-23-5','TLV75518PDBVR','TLV75518PDBVR','Texas Instruments','Navigation','1.8 V IMU I/O supply; effective input/output capacitance >=1uF required'),
      'U10':((PROJECT,'TI_PCA9306DCT'),PROJECT+':'+FP_NAME,'PCA9306DCTR','PCA9306DCTR','Texas Instruments','Navigation','1.8/3.3 V I2C translator; VREF2/EN biased through 200k, not directly powered'),
      'U11':((PROJECT,'SN74AXC1T45DBV'),'Package_TO_SOT_SMD:SOT-23-6','SN74AXC1T45DBVR','SN74AXC1T45DBVR','Texas Instruments','Navigation','INT1 1.8-to-3.3 V translation; DIR high, PB5 input only'),
    }
    for ref,value,mpn,desc in [('R36','4.7k','RC0603FR-074K7L','IMU-side SCL pull-up'),('R37','4.7k','RC0603FR-074K7L','IMU-side SDA pull-up'),('R38','200k','','PCA9306 VREF2/EN bias; exact ordering part held'),('R39','100k','RC0603FR-07100KL','1.8 V bias-current bleeder')]:
        additions[ref]=(('Device','R'),'Resistor_SMD:R_0603_1608Metric',value,mpn,'Yageo' if mpn else '', 'Navigation',desc)
    for ref,rail in [('C38','LDO input'),('C39','LDO output')]:
        additions[ref]=(('Device','C'),'Capacitor_SMD:C_0805_2012Metric','2.2uF','','','Navigation',rail+': >=1uF effective required; nominal starting value only; selection held for DC-bias/tolerance')
    for ref,desc in [('C40','U6 VDDIO bypass'),('C41','U11 VCCA bypass'),('C42','U11 VCCB bypass')]:
        additions[ref]=(('Device','C'),'Capacitor_SMD:C_0603_1608Metric','100nF','KGM15ACG1H104KT','Kyocera AVX','Navigation',desc)
    require(not(set(additions)&set(d.PARTS)), 'Added references conflict with baseline')
    d.PARTS.update(additions)
    c34=list(d.PARTS['C34']);c34[6]='U6 VDD 3.3 V bypass; VDDIO has separate C40';d.PARTS['C34']=tuple(c34)
    d.NETS['+3V3'].remove('U6-8');d.NETS['+3V3'].remove('U6.~{CS}')
    for net,token in [('I2C1_SCL','U6.SCL/SCLK'),('I2C1_SDA','U6.SDA/SDI'),('IMU_INT','U6.INT1')]: d.NETS[net].remove(token)
    d.NETS['+3V3'] += ['U9-1','U9-3','U11-6','R38-1','C38-1','C42-1']
    d.NETS['GND'] += ['U9-2','U10-1','U11-2','R39-2']+[r+'-2' for r in ['C38','C39','C40','C41','C42']]
    d.NETS['+1V8_IMU']=['U9-5','U6-8','U6-22','U10-2','U11-1','U11-5','R36-1','R37-1','R39-1','C39-1','C40-1','C41-1']
    d.NETS['IMU_SCL_1V8']=['U6-23','U10-3','R36-2']
    d.NETS['IMU_SDA_1V8']=['U6-24','U10-4','R37-2']
    d.NETS['IMU_INT_1V8']=['U6-12','U11-3']
    d.NETS['PCA9306_BIAS']=['R38-2','U10-7','U10-8']
    d.NETS['I2C1_SCL']+=['U10-6'];d.NETS['I2C1_SDA']+=['U10-5'];d.NETS['IMU_INT']+=['U11-4']
    d.NC_PINS.add('U9-4')
    layout.PLANS[('v2','Navigation')]=[
      ('01  GNSS UART and timing pulse','J5 R20 R21 R22 TP7','Existing GNSS circuit unchanged. Connector pin numbers are electrical numbering, not a cable-face view.'),
      ('02  Dedicated 1.8 V I/O supply','U9 C38 C39 R39','CANDIDATE: require >=1uF effective; qualify the 2.2uF parts. R39 sinks reference bias. Verify ramp and rail-collapse limits.'),
      ('03  IMU voltage domains','U6 C33 C34 C35 C40','VDD=3.3 V; VDDIO/CS=1.8 V. AD0=GND selects address 0x68. REGOUT must not power external loads.'),
      ('04  Bidirectional I2C translation','U10 R38 R23 R24 R36 R37','MCU pull-ups: 2.2k; sensor: 4.7k. Bias VREF2/EN through 200k, never directly to 3.3 V. Begin at 100 kHz.'),
      ('05  Interrupt translation','U11 C41 C42','DIR=1.8 V selects A-to-B. Use INT1 push-pull and PB5 input-only. Measure startup/shutdown before release.')]
    original_flags=layout.source_flags
    # VREF2 is a reference/bias terminal driven through R38; its flag records that intentional passive feed.
    original_decorate=layout.decorate_and_place
    def decorate(sh,*args):
        result=original_decorate(sh,*args)
        if sh.name=='Navigation': original_flags(sh,['PCA9306_BIAS'],args[2],v.D.POWER_NETS)
        return result
    layout.decorate_and_place=decorate
    pins,syms,errors=v.resolve_pins()
    if errors: raise ValueError(errors)
    # The AXC symbol's geometry is derived from the same-pin LVC drawing; electrical identity/pins are explicitly checked.
    expected={'U9':{'1':'IN','2':'GND','3':'EN','4':'NC','5':'OUT'},'U10':{'1':'GND','2':'VREF1','3':'SCL1','4':'SDA1','5':'SDA2','6':'SCL2','7':'VREF2','8':'EN'},'U11':{'1':'VCCA','2':'GND','3':'A','4':'B','5':'DIR','6':'VCCB'}}
    maps={r:{p['number']:p['name'] for p in syms[r]['pins']} for r in expected}
    for ref, exp in expected.items():
        require(maps[ref]==exp, f'Unexpected library pin map: {ref}: {maps[ref]}')
    v.gen_schematic(pins,syms)
    after={name:sha(ROOT/name) for name in live_manifest}
    require(before==after, 'Live design input changed during candidate build')
    outputs={str(p.relative_to(PACKET)).replace('\\','/'):sha(p) for p in sorted((SOURCE/'hardware/kicad_v2').glob('*.kicad_sch'))}
    outputs.update({str(libfile.relative_to(PACKET)).replace('\\','/'):sha(libfile)})
    outputs['source/hardware/kicad_v2/'+PROJECT+'.pretty/'+FP_NAME+'.kicad_mod']=sha(Path(v.V2PRETTY)/(FP_NAME+'.kicad_mod'))
    standards={}
    for lib in ks._lib_cache:
        p=Path(lib) if Path(lib).is_file() else Path(ks.KICAD_SHARE)/(lib+'.kicad_sym')
        if not p.is_relative_to(SOURCE): standards[p.name]=sha(p)
    dump(PACKET/'candidate_manifest.json',{'status':'schematic_candidate_only','generator_sha256':sha(Path(__file__)),'baseline_revision':REVISION,'created_utc':datetime.now(timezone.utc).isoformat(),'live_design_preserved':before==after,'live_input_sha256':before,'output_sha256':outputs,'source_script_sha256':{str(p.relative_to(PACKET)).replace('\\','/'):sha(p) for p in sorted(SOURCE.rglob('*.py'))},'standard_library_sha256':standards,'added_references':sorted(additions),'new_ic_pin_names':maps,'parts':{r:list(v) for r,v in additions.items()},'pcb_updated':False,'fabrication_approved':False,'limitations':['No PCB placement or routing performed.','C38/C39 and R38 exact orderable parts remain held.','No hardware, startup, rail collapse or I2C/IRQ measurement.','Five other electrical findings remain open.']})
    print('PASS: isolated IMU schematic generated; 12 added components; live CAD preserved')

if __name__=='__main__': main()
