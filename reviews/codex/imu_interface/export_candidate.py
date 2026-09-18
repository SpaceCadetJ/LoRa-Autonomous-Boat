#!/usr/bin/env python3
"""Capture native exports and checks for the isolated IMU candidate only."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, importlib.util, json, shutil, subprocess, sys
sys.dont_write_bytecode=True
PACKET=Path(__file__).resolve().parent
ROOT=PACKET.parents[2]
PROJECT=PACKET/'source/hardware/kicad_v2'

def require(condition,message):
    if not condition: raise RuntimeError(message)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p): return p.relative_to(ROOT).as_posix()
def write(path,data): path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8',newline='\n')
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli',default=shutil.which('kicad-cli') or 'C:/Users/Jay/AppData/Local/Programs/KiCad/9.0/bin/kicad-cli.exe')
    args=parser.parse_args()
    build=json.loads((PACKET/'candidate_manifest.json').read_text(encoding='utf-8'))
    require(PROJECT.resolve().is_relative_to(PACKET.resolve()), 'Project path escapes candidate packet')
    for path,h in build['output_sha256'].items(): require(sha(PACKET/path)==h, f'Candidate changed: {path}')
    inputs={rel(p):sha(p) for p in sorted((PACKET/'source/hardware').rglob('*')) if p.is_file() and (p.suffix in {'.kicad_sch','.kicad_sym','.kicad_mod','.kicad_pro'} or p.name in {'fp-lib-table','sym-lib-table'})}
    live={p:sha(ROOT/p) for p in build['live_input_sha256']}
    native=PACKET/'native';native.mkdir(exist_ok=True)
    source=rel(PROJECT/'LoRa_Boat_Controller_V2.kicad_sch')
    commands=[['sch','export','netlist','--format','kicadxml','-o',rel(native/'netlist.xml'),source],['sch','erc','--format','json','--severity-all','-o',rel(native/'erc.json'),source],['sch','export','svg','-o',rel(native/'svg')+'/',source]]
    report={'schema_version':1,'created_utc':datetime.now(timezone.utc).isoformat(),'status':'incomplete','exporter_sha256':sha(Path(__file__)),'scope':'candidate schematic only; no PCB modification','input_sha256':inputs,'commands':[]}
    for command in commands:
        run=subprocess.run([args.cli]+command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
        report['commands'].append({'argv':[args.cli]+command,'returncode':run.returncode,'stdout':run.stdout,'stderr':run.stderr})
        if run.returncode: write(PACKET/'native_manifest.json',report);raise RuntimeError(f'Native command failed: {command}')
    require(inputs=={p:sha(ROOT/p) for p in inputs}, 'Candidate input changed during native export')
    require(live=={p:sha(ROOT/p) for p in live}, 'Live design changed during review')
    shutil.copyfile(native/'svg/LoRa_Boat_Controller_V2-Navigation.svg',PACKET/'v2_imu_candidate.svg')
    spec=importlib.util.spec_from_file_location('quality_review',ROOT/'tools/quality/review.py')
    quality=importlib.util.module_from_spec(spec);spec.loader.exec_module(quality)
    bounds={p.name:quality.coordinate_bounds(p) for p in sorted(PROJECT.glob('*.kicad_sch'))}
    write(native/'coordinate_bounds.json',bounds)
    require(all(v['passed'] for v in bounds.values()), 'Candidate page-coordinate bounds failed')
    import pcbnew
    fpname='TI_DCT0008A_PCA9306_3x3mm_P0.65mm'
    fpdir=PROJECT/'LoRa_Boat_Controller_V2.pretty'
    fp=pcbnew.FootprintLoad(str(fpdir),fpname)
    require(fp is not None, 'Native footprint load failed')
    pads=[]
    for pad in fp.Pads():
        n=int(pad.GetNumber());pos=pad.GetPosition();size=pad.GetSize()
        x,y,w,h=[round(pcbnew.ToMM(v),6) for v in [pos.x,pos.y,size.x,size.y]]
        expected_x=-1.9 if n<=4 else 1.9
        expected_y=round(-.975+(n-1)*.65 if n<=4 else .975-(n-5)*.65,6)
        require((x,y,w,h)==(expected_x,expected_y,1.1,.4), f'Unexpected pad geometry: {n,x,y,w,h}')
        pads.append({'pin':n,'x_mm':x,'y_mm':y,'width_mm':w,'height_mm':h})
    require(sorted(x['pin'] for x in pads)==list(range(1,9)), 'Footprint must have exactly pads 1-8')
    write(native/'footprint_check.json',{'status':'matches_recorded_TI_example_land_pattern','source':rel(fpdir/(fpname+'.kicad_mod')),'sha256':sha(fpdir/(fpname+'.kicad_mod')),'source_drawing':'TI DCT0008A 4220784/D October 2025; PCA9306 datasheet pages 28-30','pads':sorted(pads,key=lambda p:p['pin']),'assembly_qualified':False,'limitations':['Native pad-geometry check only; no assembled component or stencil qualification.','Package courtyard and pin-one marking still require first-article inspection.']})
    outputs=[native/'netlist.xml',native/'erc.json',native/'coordinate_bounds.json',native/'footprint_check.json',PACKET/'v2_imu_candidate.svg']+list((native/'svg').glob('*.svg'))
    report.update({'status':'exported_unqualified','kicad_version':subprocess.check_output([args.cli,'version'],text=True).strip(),'live_design_preserved':True,'output_sha256':{rel(p):sha(p) for p in outputs}})
    write(PACKET/'native_manifest.json',report)
    print('Native candidate export and eight-pad geometry check complete; live CAD preserved.')
if __name__=='__main__': main()
