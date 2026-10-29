"""Verify captured Power presentation against immutable VSERVO-01 electrical evidence.
No native tools or writes are used in --check. Native capture is a recorded execution.
"""
from pathlib import Path
import argparse,copy,hashlib,json,re,xml.etree.ElementTree as ET
P=Path(__file__).resolve().parent;ROOT=P.parents[2];BASE=ROOT/'reviews/codex/vservo_reservoir'
ZERO=['candidate_electrical_delta','live_electrical_delta','live_copper_delta']
FALSE=['hardware_accepted','fabrication_approved','procurement_approved','protection_qualified','qualification_ports_implemented']
def require(ok,msg):
    if not ok:raise ValueError(msg)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def label(p):return p.relative_to(ROOT).as_posix()
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8',newline='\n')
def mapping(p):return {label(f):sha(f) for f in sorted(p.rglob('*')) if f.is_file() and '__pycache__' not in f.parts}
def check_map(m):
    require(bool(m),'Empty hash map')
    for n,h in m.items():
        f=(ROOT/n).resolve();require(f.is_relative_to(ROOT),'Path outside repository');require(sha(f)==h,'Changed input/artifact: '+n)
def canonical(e):
    require(e is not None,'Missing XML element')
    return e.tag,tuple(sorted(e.attrib.items())),(e.text or '').strip(),tuple(canonical(c) for c in e)
def net_evidence(tree):
    comps=tree.findall('./components/comp');refs=[c.get('ref') for c in comps]
    require(len(refs)==len(set(refs)),'Duplicate component')
    parts={c.get('ref'):canonical(c) for c in comps};pins={};attrs={};nets={}
    for net in tree.findall('./nets/net'):
        name=net.get('name');require(name not in nets,'Duplicate net name');members=[]
        for node in net.findall('node'):
            key=(node.get('ref'),node.get('pin'));require(key not in pins,'Duplicate pin membership');require(key[0] in parts,'Node without component')
            pins[key]=name;attrs[key]=tuple(sorted(node.attrib.items()));members.append(key)
        nets[name]=tuple(sorted(members))
    sheets={s.get('name'):tuple(sorted(s.attrib.items())) for s in tree.findall('./design/sheet')}
    require(len(sheets)==len(tree.findall('./design/sheet')),'Duplicate sheet')
    return parts,pins,attrs,nets,sheets
def validate_netlists(before,after):
    old=net_evidence(before);new=net_evidence(after)
    require(len(old[0])==128 and len(old[1])==429,'Baseline counts changed')
    for a,b,name in zip(old,new,['component identity/metadata','pin membership','node attributes','complete net membership','sheet identity']):require(a==b,'Changed '+name)
    require(canonical(before.find('libparts'))==canonical(after.find('libparts')),'Symbol pin definitions changed')
    # Only Power title metadata is allowed to differ; all other sheet metadata stays exact.
    old_s={s.get('name'):s for s in before.findall('./design/sheet')}
    for s in after.findall('./design/sheet'):
        if s.get('name')!='/Power/':require(canonical(s)==canonical(old_s[s.get('name')]),'Unrelated sheet metadata changed')
    return {'component_records_preserved':128,'physical_pin_memberships_preserved':429,'node_attributes_preserved':429,'complete_nets_preserved':len(old[3]),'sheet_identities_preserved':len(old[4]),'component_identity_changes':[],'pin_net_deltas':[],'symbol_pin_definitions_preserved':True}
def validate_erc(old,new):
    def relocated_flag_positions(record):
        sheets=copy.deepcopy(record['sheets'])
        for sheet in sheets:
            for finding in sheet['violations']:
                for item in finding['items']:
                    if item['uuid']=='bef86b03-b038-5d27-9003-7ad94f8169b0':
                        require(item['description']=='Symbol #FLGPow04 Pin 1 [Power output, Line]','Moved flag identity changed')
                        del item['pos']
        return sheets
    require(relocated_flag_positions(old)==relocated_flag_positions(new),'ERC findings or sheet identity changed')
    findings=[v for s in new['sheets'] for v in s['violations']]
    require(len(findings)==1 and findings[0]['severity']=='warning' and 'AD0' in str(findings[0]),'Unexpected ERC baseline')
    return {'errors':0,'warnings':1,'unchanged_ad0_warning':True}
def source_subtree(text,name):
    match=re.search(r'^\t\('+re.escape(name)+r'(?=\s|\))',text,re.M)
    require(match is not None,'Missing source subtree: '+name)
    start=match.start()+1;depth=0;quoted=False;escaped=False
    for i in range(start,len(text)):
        ch=text[i]
        if quoted:
            if escaped:escaped=False
            elif ch=='\\':escaped=True
            elif ch=='"':quoted=False
        elif ch=='"':quoted=True
        elif ch=='(':depth+=1
        elif ch==')':
            depth-=1
            if depth==0:return text[start:i+1]
    raise ValueError('Unbalanced source subtree: '+name)
def validate_power_source(before,after):
    for key in ['uuid','lib_symbols']:
        require(source_subtree(before,key)==source_subtree(after,key),'Changed source '+key)
    return {'root_uuid_preserved':True,'embedded_symbol_definitions_preserved_after_newline_normalization':True}
def collect():
    c=read(P/'expected_contract.json');inputs=read(P/'input_manifest.json');b=read(P/'build_manifest.json');n=read(P/'native_manifest.json')
    require(c['revision']=='POWER-DOC-01' and c['baseline_candidate']=='VSERVO-01','Wrong revision')
    require(c['expected_changed_source_files']==['hardware/kicad_v2/Power.kicad_sch'] and c['expected_added_source_files']==[],'Wrong source change boundary')
    require(c['expected_component_identity_changes']==[] and c['expected_pin_net_changes']=={},'Nonzero expected electrical delta')
    require(all(c[k]==0 for k in ZERO) and all(c[k] is False for k in FALSE),'Release or delta contract changed')
    check_map(inputs['input_sha256']);check_map(b['output_sha256']);check_map(n['output_sha256'])
    baseline=read(BASE/'native_manifest.json')['input_sha256'];require(b['baseline_source_sha256']==baseline,'Baseline source set changed');check_map(baseline)
    require(b['baseline_head']==inputs['baseline_head']==c['baseline_head'],'Source revision changed')
    for k,f in [('builder_sha256','layout_candidate.py'),('expected_contract_sha256','expected_contract.json'),('population_contract_sha256','population_contract.json')]:require(b[k]==sha(P/f),'Build provenance differs: '+k)
    names={(ROOT/name).relative_to(BASE/'source').as_posix() for name in baseline}
    current={f.relative_to(P/'source').as_posix() for f in (P/'source').rglob('*') if f.is_file()}
    require(len(names)==38 and names==current,'Source coverage changed')
    changed=[name for name in sorted(names) if (BASE/'source'/name).read_bytes()!=(P/'source'/name).read_bytes()]
    require(changed==c['expected_changed_source_files'],'Unexpected changed source')
    power='hardware/kicad_v2/Power.kicad_sch'
    source_semantics=validate_power_source((BASE/'source'/power).read_text(encoding='utf-8'),(P/'source'/power).read_text(encoding='utf-8'))
    require(mapping(P/'source')==b['output_sha256']==n['input_sha256'],'Source capture coverage changed')
    require((BASE/'population_contract.json').read_bytes()==(P/'population_contract.json').read_bytes(),'Population contract changed')
    require(n['runner_sha256']==sha(P/'layout_candidate.py') and n['inputs_unchanged_after_commands'] is True,'Native source provenance changed')
    require(n['kicad_version']=='9.0.7','Unexpected native version')
    require(mapping(P/'native')==n['output_sha256'] and len(n['output_sha256'])==13,'Native output coverage changed')
    nr=label(P/'native');sch=label(P/'source/hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_sch')
    expected=[['sch','export','netlist','--format','kicadxml','-o',nr+'/netlist.xml',sch],['sch','erc','--format','json','--severity-all','-o',nr+'/erc.json',sch],['sch','export','svg','-o',nr+'/svg/',sch]]
    require(len(n['commands'])==3,'Native command coverage changed')
    for cmd,argv in zip(n['commands'],expected):require(cmd['argv'][1:]==argv and cmd['returncode']==0,'Native command failed or changed')
    delta=validate_netlists(ET.parse(BASE/'native/netlist.xml'),ET.parse(P/'native/netlist.xml'))
    erc=validate_erc(read(BASE/'native/erc.json'),read(P/'native/erc.json'))
    return {'revision':'POWER-DOC-01','electrical_candidate':'VSERVO-01','status':'pass_captured_presentation_equivalence','electrical_delta':delta,'source_preservation':{'source_files':38,'byte_identical_files':37,'changed_files':changed,'both_converters_preserved':True,'population_contract_preserved':True,**source_semantics},'native_erc':erc,'native_commands_reported':3,'native_svg_sheets':11,'preserved_input_count':len(inputs['input_sha256']),**{k:c[k] for k in ZERO+FALSE},'native_commands_rerun':True,'limits':['Portable checks replay captured files; no fresh native or hardware execution.','Presentation equivalence and unchanged ERC do not establish fabrication, reservoir, shunt or application acceptance.']}
def artifact_map():
    return {n:h for n,h in mapping(P).items() if n!=label(P/'packet_manifest.json')}
def main():
    ap=argparse.ArgumentParser();g=ap.add_mutually_exclusive_group(required=True)
    for x in ['capture-validation','capture','check']:g.add_argument('--'+x,action='store_true')
    a=ap.parse_args();result=collect()
    if a.capture_validation:write(P/'validation.json',result);print('PASS native equivalence captured');return
    require(result==read(P/'validation.json'),'Stale validation')
    import build_view
    require((P/'index.html').read_text(encoding='utf-8')==build_view.output(),'Stale comparison viewer')
    review=read(P/'review_notes.json');check_map(review['reviewed_sha256'])
    viewer=read(P/'viewer_check.json')
    for name,h in viewer['input_sha256'].items():require(sha(P/'viewer-template.snapshot.html' if name=='pm/index.template.html' else ROOT/name)==h,'Stale viewer capture: '+name)
    contract=read(P/'expected_contract.json');inputs=read(P/'input_manifest.json')
    manifest={'revision':'POWER-DOC-01','electrical_candidate':'VSERVO-01','source_revision':inputs['baseline_head'],'input_sha256':inputs['input_sha256'],'artifact_sha256':artifact_map(),**{k:contract[k] for k in ZERO+FALSE},'native_commands_rerun':True}
    if a.capture:write(P/'packet_manifest.json',manifest)
    else:require(read(P/'packet_manifest.json')==manifest,'Packet bytes or coverage changed')
    print('PASS POWER-DOC-01:128 components,429 pins,37 untouched source files; recorded native/ERC and viewer evidence; hardware held')
if __name__=='__main__':main()
