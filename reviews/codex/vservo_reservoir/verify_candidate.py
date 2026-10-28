"""Independent isolated C11 native delta verifier. --check and collect() are read-only.

Captured command metadata is a provenance record, not independent proof of execution.
"""
from pathlib import Path
import argparse,copy,hashlib,importlib.util,json,sys,xml.etree.ElementTree as ET
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;ROOT=P.parents[2];BASE=ROOT/'reviews/codex/actuator_latch'
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
prior=load('c11_prior_verifier',BASE/'verify_candidate.py')
geometry=load('c11_geometry',P/'inspect_geometry.py')
require=prior.require
IDENTITY={'value':'100uF 16V','mpn':'EEEFK1C101P','manufacturer':'Panasonic','footprint':'LoRa_Boat_Controller_V2:CP_Panasonic_FK_D_6.3x5.8','datasheet':'https://industrial.panasonic.com/cdbs/www-data/pdf/RDE0000/ABA0000C1181.pdf','description':'VSERVO-01 held C11 candidate; reservoir and assembly unqualified'}
OLD={'value':'100uF 10V','mpn':'EEE-FK1A101P','manufacturer':'Panasonic','footprint':'Capacitor_SMD:CP_Elec_6.3x7.7','datasheet':'~','description':'VSERVO bulk'}
FIELD={'Value':'value','MPN':'mpn','Manufacturer':'manufacturer','Footprint':'footprint','Datasheet':'datasheet','Description':'description'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def label(p):return p.relative_to(ROOT).as_posix()
def hashes(paths):return {label(p):sha(p) for p in sorted(paths)}
def check_map(h):
    require(bool(h),'Empty hash map')
    for n,v in h.items():
        f=(ROOT/n).resolve();require(f.is_relative_to(ROOT),'Manifest path escapes repository');require(sha(f)==v,'Hash differs: '+n)
def validate_contract(c):
    require(c['revision']=='VSERVO-01' and c['baseline_candidate']=='ACT-04','Wrong candidate revision')
    require(c['candidate_identity']==IDENTITY,'Candidate identity differs from independent expectation')
    require(c['expected_changed_components']==['C11'] and c['expected_pin_net_changes']=={},'Unexpected intended component or membership delta')
    require(c['candidate_identity_changes']==1 and c['candidate_electrical_membership_delta']==0 and c['live_electrical_delta']==0 and c['live_copper_delta']==0,'Unexpected electrical/copper delta')
    require(c['candidate_pad_contract_mm']=={'centers_x':[-2.5,2.5],'centers_y':[0,0],'size':[3.2,1.6],'inner_gap':1.8,'outer_span':8.2,'pad1':'positive VSERVO','pad2':'negative GND'},'Wrong independent land contract')
    require(c['native_commands_rerun'] is True,'Native evidence required')
    for k in ['hardware_accepted','fabrication_approved','procurement_approved','reservoir_qualified','qualification_ports_implemented']:require(c[k] is False,'Acceptance cannot be claimed: '+k)
def canonical(e):
    return (e.tag,tuple(sorted(e.attrib.items())),(e.text or '').strip(),tuple(canonical(x) for x in e))
def components(tree):return {c.get('ref'):c for c in tree.findall('./components/comp')}
def expected_component(c):
    c=copy.deepcopy(c)
    for tag in ['value','footprint','datasheet','description']:require(c.findtext(tag)==OLD[tag],'Unexpected baseline C11 '+tag);c.find(tag).text=IDENTITY[tag]
    for name,key in FIELD.items():
        if name=='Value':continue
        field=c.find('./fields/field[@name="'+name+'"]');require(field is not None and field.text==OLD[key],'Unexpected baseline C11 field '+name);field.text=IDENTITY[key]
    for name,key in [('MPN','mpn'),('Manufacturer','manufacturer')]:
        prop=c.find('./property[@name="'+name+'"]');require(prop is not None and prop.get('value')==OLD[key],'Unexpected baseline C11 property '+name);prop.set('value',IDENTITY[key])
    return c
def validate_netlists(before,after):
    oldparts,oldpins=prior.parse_netlist(before);newparts,newpins=prior.parse_netlist(after)
    require(len(oldparts)==128 and len(oldpins)==429,'Unexpected baseline counts')
    require(set(newparts)==set(oldparts) and newpins==oldpins,'Physical component/pin memberships changed')
    a,b=components(before),components(after)
    require(len(a)==len(b)==128,'Duplicate native component reference')
    for ref,c in a.items():require(canonical(b[ref])==canonical(expected_component(c) if ref=='C11' else c),'Unexpected full component metadata/identity delta: '+ref)
    require(canonical(before.find('libparts'))==canonical(after.find('libparts')),'Physical symbol pin definitions changed')
    oldnodes,newnodes=prior.prior.nodes(before),prior.prior.nodes(after)
    require(set(oldnodes)==set(newnodes),'Native node set changed')
    for key,node in oldnodes.items():require(node.attrib==newnodes[key].attrib,'Native pin/NC attributes changed: '+str(key))
    require(prior.sheets(before)==prior.sheets(after),'Sheet membership changed')
    dnp=prior.dnp_refs(before);require(dnp=={'D4','D9'} and prior.dnp_refs(after)==dnp,'Master population changed')
    require(newpins[('C11','1')]=='VSERVO' and newpins[('C11','2')]=='GND','C11 polarity/net membership differs')
    return {'baseline_components':128,'candidate_components':128,'preserved_other_component_identities':127,'candidate_identity_changes':['C11'],'physical_pin_memberships_preserved':429,'pin_net_deltas':[],
      'native_node_attributes_preserved':429,'symbol_pin_definitions_preserved':True,'master_dnp_refs':['D4','D9'],'c11_polarity':{'1':'VSERVO','2':'GND'}}
def validate_power(before,after):
    marker='(property "Reference" "C11"'
    require(before.count(marker)==after.count(marker)==1,'C11 reference must be unique')
    def isolate(text):
        i=text.index(marker);start=text.rfind('\n\t(symbol\n',0,i)+1;end=text.index('\n\t)\n',i)+4;require(start>0 and end>start,'Malformed C11 source');return start,end
    x,y=isolate(before);a,b=isolate(after);require(before[:x]==after[:a] and before[y:]==after[b:],'Source outside C11 changed')
    old=before[x:y];new=after[a:b]
    for name,key in FIELD.items():
        needle='(property '+json.dumps(name)+' '+json.dumps(IDENTITY[key]);replace='(property '+json.dumps(name)+' '+json.dumps(OLD[key]);require(new.count(needle)==1,'C11 expected field missing: '+name);new=new.replace(needle,replace)
    require(new==old,'C11 has an out-of-contract source change')
def validate_population(old,new):
    require(old==new,'ACT-01 population contract bytes changed');return prior.validate_population(json.loads(new))
def source_check(build):
    baseline=read(BASE/'native_manifest.json')['input_sha256'];require(build['baseline_source_sha256']==baseline,'Baseline source set changed');check_map(baseline)
    source=P/'source';original=BASE/'source';land='hardware/kicad_v2/LoRa_Boat_Controller_V2.pretty/CP_Panasonic_FK_D_6.3x5.8.kicad_mod';power='hardware/kicad_v2/Power.kicad_sch'
    oldnames={(ROOT/n).relative_to(original).as_posix() for n in baseline};actual={p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()}
    require(len(oldnames)==37 and actual==oldnames|{land},'Candidate source files differ')
    for name in oldnames:
        if name==power:validate_power((original/name).read_bytes().decode('utf-8'),(source/name).read_bytes().decode('utf-8'))
        else:require((original/name).read_bytes()==(source/name).read_bytes(),'Preserved source changed: '+name)
    require(build['output_sha256']==hashes([p for p in source.rglob('*') if p.is_file()]),'Build source hash coverage differs')
    return {'baseline_source_files':37,'candidate_source_files':38,'byte_identical_source_files':36,'changed_files':[power],'added_files':[land],'both_converters_byte_identical':True,'actuator_sheets_byte_identical':True}
def collect():
    contract=read(P/'expected_contract.json');validate_contract(contract);inputs=read(P/'input_manifest.json');check_map(inputs['input_sha256']);build=read(P/'build_manifest.json');native=read(P/'native_manifest.json')
    require(build['baseline_head']==inputs['baseline_head'],'Baseline head differs')
    for key,name in [('builder_sha256','build_candidate.py'),('expected_contract_sha256','expected_contract.json'),('population_contract_sha256','population_contract.json')]:require(build[key]==sha(P/name),'Build provenance differs: '+key)
    sources=source_check(build);require(native['input_sha256']==build['output_sha256'] and native['runner_sha256']==sha(P/'build_candidate.py'),'Native input provenance differs');require(native['inputs_unchanged_after_commands'] is True,'Native input stability missing')
    require(native['kicad_version']=='9.0.7','Unexpected captured KiCad version');check_map(native['output_sha256']);out={label(p) for p in (P/'native').rglob('*') if p.is_file()};require(out==set(native['output_sha256']) and len(out)==13,'Native output coverage differs')
    commands=native['commands'];require(len(commands)==3,'Expected three native commands')
    nr=label(P/'native');sch=label(P/'source/hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_sch')
    args=[['sch','export','netlist','--format','kicadxml','-o',nr+'/netlist.xml',sch],['sch','erc','--format','json','--severity-all','-o',nr+'/erc.json',sch],['sch','export','svg','-o',nr+'/svg/',sch]]
    for c,a in zip(commands,args):require(c['returncode']==0 and c['argv'][1:]==a,'Unexpected native command/result')
    delta=validate_netlists(ET.parse(BASE/'native/netlist.xml'),ET.parse(P/'native/netlist.xml'))
    erc=prior.validate_erc(read(BASE/'native/erc.json'),read(P/'native/erc.json'))
    population=validate_population((BASE/'population_contract.json').read_bytes(),(P/'population_contract.json').read_bytes());g=geometry.check()
    own=[P/n for n in ['expected_contract.json','input_manifest.json','build_manifest.json','native_manifest.json','population_contract.json','geometry_native.json','build_candidate.py','verify_candidate.py','inspect_geometry.py']]
    h=hashes(own);check_map(inputs['input_sha256']);check_map(build['output_sha256']);check_map(h)
    return {'revision':'VSERVO-01','status':'pass_isolated_c11_identity_land_only','electrical_delta':delta,'source_preservation':sources,'native_erc':erc,'population_contract_byte_preserved':True,'population_contract':population,'geometry':g,'input_sha256':h,'preserved_input_count':len(inputs['input_sha256']),'native_commands_reported':3,'native_svg_sheets':11,
      'live_electrical_delta':0,'live_copper_delta':0,'hardware_tested':False,'hardware_accepted':False,'fabrication_approved':False,'procurement_approved':False,'reservoir_qualified':False,'qualification_ports_implemented':False,
      'limitations':['Portable verification checks captured bytes, XML and recorded command results; it does not rerun native commands or independently prove their execution.','Only the isolated schematic identity and candidate land are amended. No PCB, live CAD, V1, firmware or assembly release is changed.','Native footprint parsing and ERC do not qualify reservoir capacity, load or regenerative transients, temperature, leakage, soldering, fit, pulse integrity, backdrive or physical hardware.','Both exclusive ACT-01 variants and default-disabled qualifications remain held.']}
if __name__=='__main__':
    ap=argparse.ArgumentParser();mode=ap.add_mutually_exclusive_group(required=True);mode.add_argument('--capture',action='store_true');mode.add_argument('--check',action='store_true');args=ap.parse_args()
    r=collect()
    if args.check:require(read(P/'validation.json')==r,'Captured validation is stale')
    else:(P/'validation.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'status':r['status'],'delta':r['electrical_delta'],'native_erc':r['native_erc']},indent=2))
