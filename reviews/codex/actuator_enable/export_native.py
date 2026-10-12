"""Native schematic evidence for ACT-02; never checks or writes a PCB."""
from pathlib import Path
import json,hashlib,subprocess,shutil,datetime
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    cli='C:/Users/Jay/AppData/Local/Programs/KiCad/9.0/bin/kicad-cli.exe'
    native=P/'native';native.mkdir(exist_ok=True);build=json.loads((P/'build_manifest.json').read_text())
    assert all(sha(ROOT/n)==h for n,h in build['output_sha256'].items())
    sch=(P/'source/hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_sch').relative_to(ROOT).as_posix();nr=native.relative_to(ROOT).as_posix()
    cmds=[['sch','export','netlist','--format','kicadxml','-o',nr+'/netlist.xml',sch],['sch','erc','--format','json','--severity-all','-o',nr+'/erc.json',sch],['sch','export','svg','-o',nr+'/svg/',sch]]
    report={'date':datetime.datetime.now(datetime.timezone.utc).isoformat(),'kicad_version':subprocess.check_output([cli,'version'],text=True).strip(),'runner_sha256':sha(Path(__file__)),'input_sha256':build['output_sha256'],'commands':[]}
    for cmd in cmds:
        r=subprocess.run([cli]+cmd,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace');report['commands'].append({'argv':[cli]+cmd,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr});assert r.returncode==0,r.stderr
    out=P/'v2_actuator_enable.svg';shutil.copyfile(native/'svg/LoRa_Boat_Controller_V2-Actuators.svg',out)
    report['output_sha256']={f.relative_to(ROOT).as_posix():sha(f) for f in native.rglob('*') if f.is_file()};report['output_sha256'][out.relative_to(ROOT).as_posix()]=sha(out)
    assert all(sha(ROOT/n)==h for n,h in build['live_input_sha256'].items())
    assert all(sha(ROOT/n)==h for n,h in build['output_sha256'].items())
    (P/'native_manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    erc=json.loads((native/'erc.json').read_text());print('Native ERC:',sum(v['severity']=='error' for s in erc['sheets'] for v in s['violations']),'errors;',sum(v['severity']=='warning' for s in erc['sheets'] for v in s['violations']),'warnings')
    import cairosvg;cairosvg.svg2png(url=str(out),write_to=str(P/'actuator-enable-review.png'),output_width=2000)
    for name in ['LoRa_Boat_Controller_V2','LoRa_Boat_Controller_V2-Power']:
        cairosvg.svg2png(url=str(native/'svg'/(name+'.svg')),write_to=str(P/(name+'-review.png')),output_width=1500)
if __name__=='__main__':main()
