"""Verify exactly one filter capacitor added to the previous IMU candidate."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,importlib.util,json,sys,xml.etree.ElementTree as ET
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent;PRIOR=ROOT/'reviews/codex/imu_interface'
spec=importlib.util.spec_from_file_location('imu_base_verifier',PRIOR/'verify_candidate.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
BASE_LIVE=ROOT/'reviews/codex/design_completion/native-review/v2/netlist.xml'
BIAS='/Navigation/PCA9306_BIAS'
def require(v,m):
 if not v:raise ValueError(m)
def validate(before_tree,after_tree):
 before,old=base.parse_netlist(before_tree);after,new=base.parse_netlist(after_tree)
 require(set(after)==set(before)|{'C43'} and 'C43' not in before,'Expected only one new component C43')
 require(all(after[r]==v for r,v in before.items()),'Existing part identity/pins changed')
 require(all(new[k]==v for k,v in old.items()),'Existing electrical membership changed')
 c=after['C43'];require(c['value']=='100pF','C43 value must be 100pF')
 require(c['footprint']=='Capacitor_SMD:C_0603_1608Metric','C43 package changed')
 require(c['library']==('Device','C') and set(c['pins'])=={'1','2'},'C43 symbol/pins changed')
 require(c['mpn']=='' and c['manufacturer']=='','Exact part selection is still held')
 require(set(new)-set(old)=={('C43','1'),('C43','2')},'Unexpected added pin set')
 require(new['C43','1']==BIAS and new['C43','2']=='GND','Wrong filter terminal nets')
 require(set(old.values())==set(new.values()),'Unexpected new or missing net')
 return {'before_components':len(before),'after_components':len(after),'before_pins':len(old),'after_pins':len(new),'preserved_memberships':len(old),'changed_existing_memberships':0,'added_components':['C43'],'added_memberships':{'C43.1':BIAS,'C43.2':'GND'},'existing_component_identities_preserved':True,'new_net_names':[]}
def cumulative(after_tree):
 # Reuse the independently tested first-revision contract with exactly one additional passive part.
 old=base.NEW_PARTS.copy()
 try:
  base.NEW_PARTS['C43']=('100pF',{'1':BIAS,'2':'GND'})
  return base.validate_netlists(ET.parse(BASE_LIVE),after_tree)
 finally:base.NEW_PARTS.clear();base.NEW_PARTS.update(old)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 build=json.loads((OUT/'build_manifest.json').read_text());native=json.loads((OUT/'native_manifest.json').read_text())
 for name,h in {**build['input_sha256'],**build['output_sha256'],**build['protected_sha256'],**native['input_sha256'],**native['output_sha256']}.items():require(sha(ROOT/name)==h,'Stale evidence '+name)
 require(sha(OUT/'build_amendment.py')==build['builder_sha256'],'Builder changed')
 require(sha(OUT/'export_native.py')==native['exporter_sha256'],'Exporter changed')
 delta=validate(ET.parse(PRIOR/'native/netlist.xml'),ET.parse(OUT/'native/netlist.xml'));total=cumulative(ET.parse(OUT/'native/netlist.xml'))
 a=base.erc_summary(json.loads((PRIOR/'native/erc.json').read_text()));b=base.erc_summary(json.loads((OUT/'native/erc.json').read_text()))
 require(b['errors']==0 and a['violations']==b['violations'],'ERC findings changed')
 report={'created_utc':datetime.now(timezone.utc).isoformat(),'status':'pass_isolated_schematic_only','verifier_sha256':sha(Path(__file__)),'comparison_input_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in [PRIOR/'native/netlist.xml',PRIOR/'native/erc.json',OUT/'native/netlist.xml',OUT/'native/erc.json',BASE_LIVE,PRIOR/'verify_candidate.py']},'amendment_delta':delta,'cumulative_delta':total,'native_erc':{'errors':b['errors'],'warnings':b['warnings'],'prior_findings_unchanged':True},'prior_and_live_preserved':True,'pcb_updated':False,'hardware_tested':False,'fabrication_approved':False}
 (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps({'amendment':delta,'erc':report['native_erc']}))
if __name__=='__main__':main()
