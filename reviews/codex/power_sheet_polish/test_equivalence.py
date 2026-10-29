import copy,unittest,xml.etree.ElementTree as ET
from verify_packet import BASE,P,validate_netlists,validate_erc,read,validate_power_source,source_subtree
class EquivalenceTests(unittest.TestCase):
    def setUp(self):
        self.before=ET.parse(BASE/'native/netlist.xml');self.after=copy.deepcopy(self.before)
    def reject(self):
        with self.assertRaises(ValueError):validate_netlists(self.before,self.after)
    def test_identical(self):self.assertEqual(validate_netlists(self.before,self.after)['physical_pin_memberships_preserved'],429)
    def test_c11_identity(self):self.after.find('./components/comp[@ref="C11"]/value').text='100uF 10V';self.reject()
    def test_pin_reassignment(self):self.after.find('./nets/net').set('name','wrong');self.reject()
    def test_duplicate_pin(self):
        n=self.after.find('./nets/net');n.append(copy.deepcopy(n.find('node')));self.reject()
    def test_missing_component(self):
        c=self.after.find('./components');c.remove(c[0]);self.reject()
    def test_duplicate_component(self):
        c=self.after.find('./components');c.append(copy.deepcopy(c[0]));self.reject()
    def test_changed_pin_type(self):self.after.find('./nets/net/node').set('pintype','output');self.reject()
    def test_changed_symbol(self):self.after.find('./libparts/libpart/pins/pin').set('num','999');self.reject()
    def test_changed_sheet_identity(self):self.after.find('./design/sheet').set('tstamps','/wrong/');self.reject()
    def test_allowed_power_metadata(self):
        self.after.find('./design/sheet[@name="/Power/"]/title_block/rev').text='POWER-DOC-01'
        self.assertEqual(validate_netlists(self.before,self.after)['component_records_preserved'],128)
    def test_unrelated_metadata(self):self.after.find('./design/sheet[@name="/"]/title_block/rev').text='other';self.reject()
    def test_relocated_flag_warning(self):
        a=read(BASE/'native/erc.json');b=copy.deepcopy(a)
        item=next(i for s in b['sheets'] for f in s['violations'] for i in f['items'] if i['uuid']=='bef86b03-b038-5d27-9003-7ad94f8169b0')
        item['pos']={'x':2.667,'y':2.6289}
        self.assertEqual(validate_erc(a,b)['errors'],0)
    def test_changed_warning_identity(self):
        a=read(BASE/'native/erc.json');b=copy.deepcopy(a)
        item=next(i for s in b['sheets'] for f in s['violations'] for i in f['items'])
        item['uuid']='wrong'
        with self.assertRaises(ValueError):validate_erc(a,b)
    def test_source_definitions_preserved(self):
        text=(BASE/'source/hardware/kicad_v2/Power.kicad_sch').read_text()
        self.assertTrue(validate_power_source(text,text)['embedded_symbol_definitions_preserved_after_newline_normalization'])
    def test_embedded_geometry_change(self):
        text=(BASE/'source/hardware/kicad_v2/Power.kicad_sch').read_text()
        original=source_subtree(text,'lib_symbols');changed=original.replace('(xy ','(xy 999',1)
        self.assertNotEqual(original,changed)
        with self.assertRaises(ValueError):validate_power_source(text,text.replace(original,changed))
    def test_root_uuid_change(self):
        text=(BASE/'source/hardware/kicad_v2/Power.kicad_sch').read_text()
        changed=text.replace(source_subtree(text,'uuid'),'(uuid "wrong")',1)
        with self.assertRaises(ValueError):validate_power_source(text,changed)
    def test_new_erc_finding(self):
        a=read(BASE/'native/erc.json');b=copy.deepcopy(a);b['sheets'][0]['violations'].append({'severity':'error','description':'new','items':[]})
        with self.assertRaises(ValueError):validate_erc(a,b)
if __name__=='__main__':unittest.main()
