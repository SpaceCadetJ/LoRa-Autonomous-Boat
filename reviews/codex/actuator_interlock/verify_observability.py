"""Verify ACT-02 actuator observability from its captured native netlist; no CAD writes."""
from pathlib import Path
import hashlib,json,sys,xml.etree.ElementTree as ET
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
SOURCE='reviews/codex/actuator_enable/native/netlist.xml'
EXPECTED={
 '/BEC_IN':['D9.2','J2.2'],
 'VSERVO':['C11.1','C12.1','D4.1','D9.1','J3.2','TP4.1'],
 '/ACT_EN_PC4':['R40.1','U1.24','U4.6'],
 '/Power/+5V_BUCK':['C14.1','C49.1','C50.1','C51.1','C55.1','C8.1','C9.1','D4.2','L2.2','R8.1','U3.9','U4.7'],
 '+3V3':['C13.1','C15.1','C16.1','C17.1','C18.1','C19.1','C23.1','C34.1','C35.1','C47.1','C5.1','C6.1','FB1.1','FB2.1','J5.1','J5.6','J7.1','L1.2','R23.1','R24.1','R29.1','R4.1','TP3.1','U1.1','U1.19','U1.32','U1.48','U1.64','U4.3','U6.13','U6.22','U6.8','U8.5'],
 '/Actuators/ESC_SIG':['D10.1','J2.1','R10.2','R11.1'],
 '/Actuators/SERVO_SIG':['D11.1','J3.1','R12.2','R13.1'],
 'unconnected-(U2-PG-Pad4)':['U2.4'],
 'unconnected-(U3-PGOOD-Pad16)':['U3.16']}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def collect():
 r=ET.parse(ROOT/SOURCE).getroot();nets={n.get('name'):sorted(x.get('ref')+'.'+x.get('pin') for x in n.findall('node')) for n in r.findall('./nets/net')};pins={x.get('ref')+'.'+x.get('pin'):n.get('name') for n in r.findall('./nets/net') for x in n.findall('node')}
 for n,p in EXPECTED.items():assert nets[n]==sorted(p),(n,nets[n])
 connectors={'J2':{'1':'/Actuators/ESC_SIG','2':'/BEC_IN','3':'GND'},'J3':{'1':'/Actuators/SERVO_SIG','2':'VSERVO','3':'GND'}}
 for ref,ps in connectors.items():
  for pin,net in ps.items():assert pins[ref+'.'+pin]==net
 for ref,pin in [('U2','4'),('U3','16')]:
  node=r.find(f"./nets/net/node[@ref='{ref}'][@pin='{pin}']");assert node.get('pintype')=='open_collector+no_connect'
 assert not any('READY' in n.upper() for n in nets)
 dnp=sorted(c.get('ref') for c in r.findall('./components/comp') if c.find("property[@name='dnp']") is not None);assert dnp==['D4','D9']
 return {'classification':'independently_checked_captured_connectivity','source':SOURCE,'source_sha256':sha(ROOT/SOURCE),'verifier_sha256':sha(Path(__file__)),'connectors':connectors,'exact_net_memberships':{n:nets[n] for n in EXPECTED},'master_dnp_refs':dnp,'receiver_ready_signal_present':False,'BEC_IN_or_VSERVO_connected_to_MCU':False,'converter_power_good_pins_connected':False,'ACT_EN_independent_hardware_gate_present':False,'electrical_delta':0,'copper_delta':0,'native_commands_rerun':False,'hardware_tested':False}
if __name__=='__main__':
 result=collect();out=P/'observability.json'
 if '--check' in sys.argv:assert result==json.loads(out.read_text());print('PASS captured ACT-02 connector/net/NC/population observability; no native rerun or circuit change')
 else:out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');print('Captured ACT-02 observability')
