"""Reject incorrect bias-filter amendments using captured native netlists."""
from pathlib import Path
import unittest,xml.etree.ElementTree as ET
from verify_amendment import validate
OUT=Path(__file__).resolve().parent
class AmendmentTests(unittest.TestCase):
 def setUp(self):
  self.before=ET.parse(OUT.parent/'imu_interface/native/netlist.xml');self.after=ET.parse(OUT/'native/netlist.xml')
 def part(self,ref):return next(c for c in self.after.findall('./components/comp') if c.get('ref')==ref)
 def node(self,ref,pin):return next((n,node) for n in self.after.findall('./nets/net') for node in n.findall('node') if node.get('ref')==ref and node.get('pin')==pin)
 def test_exact_delta(self):self.assertEqual(validate(self.before,self.after)['preserved_memberships'],398)
 def test_wrong_capacitance(self):
  self.part('C43').find('value').text='100nF'
  with self.assertRaises(ValueError):validate(self.before,self.after)
 def test_wrong_package(self):
  self.part('C43').find('footprint').text='Capacitor_SMD:C_0402_1005Metric'
  with self.assertRaises(ValueError):validate(self.before,self.after)
 def test_wrong_filter_rail(self):
  n,node=self.node('C43','1');n.remove(node);next(n for n in self.after.findall('./nets/net') if n.get('name')=='+3V3').append(node)
  with self.assertRaises(ValueError):validate(self.before,self.after)
 def test_existing_membership_changed(self):
  n,node=self.node('U6','8');n.remove(node);next(n for n in self.after.findall('./nets/net') if n.get('name')=='+3V3').append(node)
  with self.assertRaises(ValueError):validate(self.before,self.after)
 def test_missing_filter_pin(self):
  n,node=self.node('C43','2');n.remove(node)
  with self.assertRaises(ValueError):validate(self.before,self.after)
 def test_duplicated_filter_pin(self):
  import copy
  n,node=self.node('C43','2');n.append(copy.deepcopy(node))
  with self.assertRaises(ValueError):validate(self.before,self.after)
if __name__=='__main__':unittest.main()
