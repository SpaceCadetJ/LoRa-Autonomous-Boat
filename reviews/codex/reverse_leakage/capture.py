"""Read-only capture of published INPUT-A1 boundary parts/nets."""
from pathlib import Path
import hashlib,json,sys,xml.etree.ElementTree as ET
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
def collect():
    source=ROOT/'reviews/codex/input_stage/native/netlist.xml';tree=ET.parse(source)
    wanted={'D12','C1','C2','R31','R32','R33','C36','U8','U1'};parts={}
    for c in tree.findall('./components/comp'):
        if c.get('ref') in wanted:
            fields={f.get('name'):f.text or '' for f in c.findall('./fields/field')}
            parts[c.get('ref')]={'value':c.findtext('value'),'mpn':fields.get('MPN',''),'footprint':c.findtext('footprint')}
    names={'VIN_RAW','/Power/VIN_BUCK','/VBAT_SENSE','/ISENSE'}
    nets={n.get('name'):[{'ref':x.get('ref'),'pin':x.get('pin'),'function':x.get('pinfunction')} for x in n.findall('node')] for n in tree.findall('./nets/net') if n.get('name') in names}
    assert set(parts)==wanted and set(nets)==names
    return {'source':source.relative_to(ROOT).as_posix(),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'captured_parts':parts,'captured_nets':nets,'scope':'INPUT-A1 existing connectivity; proposed replacement parts and future converters are not installed','live_electrical_delta':0,'candidate_electrical_delta':0,'hardware_tested':False}
if __name__=='__main__':
    result=collect();out=P/'capture.json'
    if '--check' in sys.argv:assert json.loads(out.read_text())==result
    else:out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('INPUT-A1 boundary capture matches; no CAD writes.')
