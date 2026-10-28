"""Mutation guards for the isolated C11 delta, preserving physical pin and population evidence."""
import copy,json,unittest,xml.etree.ElementTree as ET
import verify_candidate as v

class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.old=ET.parse(v.BASE/'native/netlist.xml');self.new=ET.parse(v.P/'native/netlist.xml')
    def reject(self,change):
        change(self.new)
        with self.assertRaises(ValueError):v.validate_netlists(self.old,self.new)
    def test_recorded_candidate(self):
        result=v.collect();self.assertEqual(result['electrical_delta']['physical_pin_memberships_preserved'],429);self.assertFalse(result['reservoir_qualified'])
    def test_unrelated_value(self):
        self.reject(lambda t:setattr(t.find('./components/comp[@ref="C13"]/value'),'text','220nF'))
    def test_unrelated_identity_field(self):
        self.reject(lambda t:setattr(t.find('./components/comp[@ref="U1"]/datasheet'),'text','unreviewed'))
    def test_c11_wrong_identity(self):
        self.reject(lambda t:setattr(t.find('./components/comp[@ref="C11"]/fields/field[@name="MPN"]'),'text','EEE-FK1A101P'))
    def test_pin_membership(self):
        def mutation(t):
            source=next(n for n in t.findall('./nets/net') if n.find('./node[@ref="C11"]') is not None and n.get('name')=='VSERVO')
            node=source.find('./node[@ref="C11"]');source.remove(node);t.find('./nets/net[@name="GND"]').append(node)
        self.reject(mutation)
    def test_pin_metadata(self):
        self.reject(lambda t:t.find('./nets/net/node[@ref="U12"][@pin="3"]').set('pintype','output'))
    def test_population_bytes(self):
        old=(v.BASE/'population_contract.json').read_bytes();new=json.loads(old);new['dual_population_allowed']=True
        with self.assertRaises(ValueError):v.validate_population(old,json.dumps(new).encode())
    def test_source_outside_c11(self):
        source='source/hardware/kicad_v2/Power.kicad_sch';old=(v.BASE/source).read_bytes().decode();new=(v.P/source).read_bytes().decode().replace('(property "Value" "100nF"','(property "Value" "220nF"',1)
        with self.assertRaises(ValueError):v.validate_power(old,new)
    def test_source_c11_unapproved_geometry(self):
        source='source/hardware/kicad_v2/Power.kicad_sch';old=(v.BASE/source).read_bytes().decode();new=(v.P/source).read_bytes().decode().replace('(at 520.7 195.58 0)','(at 521.7 195.58 0)',1)
        with self.assertRaises(ValueError):v.validate_power(old,new)
    def test_land_dimensions(self):
        d=copy.deepcopy(v.geometry.expected());d['pads'][0]['size_x_mm']=3.5
        with self.assertRaises(ValueError):v.geometry.validate(d)
    def test_polarity_mirror(self):
        d=copy.deepcopy(v.geometry.expected());d['pads'][0]['x_mm']=2.5;d['pads'][1]['x_mm']=-2.5
        with self.assertRaises(ValueError):v.geometry.validate(d)
    def test_mask_paste_layer_drift(self):
        d=copy.deepcopy(v.geometry.expected());d['pads'][0]['layers'].remove('F.Paste')
        with self.assertRaises(ValueError):v.geometry.validate(d)
    def test_acceptance_cannot_be_promoted(self):
        c=v.read(v.P/'expected_contract.json');c['reservoir_qualified']=True
        with self.assertRaises(ValueError):v.validate_contract(c)

if __name__=='__main__':unittest.main()
