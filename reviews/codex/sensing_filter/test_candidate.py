"""Mutation checks for the independent SENSE-02 verifier; no CAD writes or tools.

The actual native capture is the valid fixture. Mutants are isolated in memory,
so a passing test demonstrates a rejected fault without editing review evidence.
"""
import copy
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import verify_candidate as v


class CandidateMutationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = ET.parse(v.BASE / 'native/netlist.xml')
        cls.after = ET.parse(v.P / 'native/netlist.xml')
        cls.old_erc = v.read(v.BASE / 'native/erc.json')
        cls.new_erc = v.read(v.P / 'native/erc.json')
        cls.native = v.read(v.P / 'native_manifest.json')
        cls.source_map = v.mapping(v.P / 'source')
        cls.native_map = v.mapping(v.P / 'native')
        cls.source_before = v.relative_mapping(v.BASE / 'source')
        cls.source_after = v.relative_mapping(v.P / 'source')
        cls.power_before = (v.BASE / 'source' / v.POWER).read_text(encoding='utf-8')
        cls.power_after = (v.P / 'source' / v.POWER).read_text(encoding='utf-8')

    def reject_netlist(self, mutate, reason):
        mutant = copy.deepcopy(self.after)
        mutate(mutant)
        with self.assertRaisesRegex(ValueError, reason):
            v.validate_netlists(self.before, mutant)

    @staticmethod
    def move_pin(tree, ref, pin, target):
        owner = next(net for net in tree.findall('./nets/net')
                     if net.find("node[@ref='%s'][@pin='%s']" % (ref, pin)) is not None)
        node = owner.find("node[@ref='%s'][@pin='%s']" % (ref, pin))
        owner.remove(node)
        tree.find("./nets/net[@name='%s']" % target).append(node)

    def test_01_actual_capture_passes_complete_pipeline(self):
        result = v.collect()
        self.assertEqual(result, v.read(v.P / 'validation.json'))
        self.assertEqual(result['preserved_input_count'], 580)
        self.assertEqual(result['native_erc']['finding_position_normalizations'], [])

    def test_02_accidental_bridge_bypassing_r44_is_rejected(self):
        self.reject_netlist(lambda t: self.move_pin(t, 'U8', '1', '/ISENSE'), 'Pin membership')

    def test_03_r44_pins_swapped_is_rejected(self):
        def mutate(tree):
            self.move_pin(tree, 'R44', '1', '/ISENSE')
            self.move_pin(tree, 'R44', '2', '/Power/ISENSE_DRV')
        self.reject_netlist(mutate, 'Pin membership')

    def test_04_c59_wrong_supply_is_rejected(self):
        self.reject_netlist(lambda t: self.move_pin(t, 'C59', '1', '/Power/+5V_BUCK'), 'Pin membership')

    def test_05_unrelated_existing_pin_move_is_rejected(self):
        self.reject_netlist(lambda t: self.move_pin(t, 'C36', '1', 'GND'), 'Pin membership')

    def test_06_missing_added_part_is_rejected(self):
        def mutate(tree):
            tree.find('components').remove(tree.find("./components/comp[@ref='C59']"))
        self.reject_netlist(mutate, 'Node without component|Candidate counts')

    def test_07_wrong_100nf_value_is_rejected(self):
        def mutate(tree):
            v.set_component_field(tree.find("./components/comp[@ref='C37']"), 'Value', '1uF')
        self.reject_netlist(mutate, 'Changed component record: C37')

    def test_08_r33_part_substitution_is_rejected(self):
        def mutate(tree):
            v.set_component_field(tree.find("./components/comp[@ref='R33']"), 'MPN', 'OTHER-SHUNT')
        self.reject_netlist(mutate, 'Changed component record: R33')

    def test_09_unrelated_metadata_change_is_rejected(self):
        def mutate(tree):
            v.set_component_field(tree.find("./components/comp[@ref='R32']"), 'Description', 'Edited')
        self.reject_netlist(mutate, 'Changed component record: R32')

    def test_10_old_node_attribute_change_is_rejected(self):
        def mutate(tree):
            tree.find("./nets/net/node[@ref='U8'][@pin='1']").set('pintype', 'passive')
        self.reject_netlist(mutate, 'Changed old node attributes: U8.1')

    def test_11_new_part_wrong_mpn_is_rejected(self):
        def mutate(tree):
            v.set_component_field(tree.find("./components/comp[@ref='C59']"), 'MPN', 'OTHER-1UF')
        self.reject_netlist(mutate, 'Unexpected new component record: C59')

    def test_12_duplicate_component_uuid_is_rejected(self):
        def mutate(tree):
            tree.find("./components/comp[@ref='C59']/tstamps").text = tree.findtext("./components/comp[@ref='C37']/tstamps")
        self.reject_netlist(mutate, 'Duplicate component UUID')

    def test_13_symbol_pin_definition_change_is_rejected(self):
        def mutate(tree):
            tree.find('./libparts/libpart/pins/pin').set('type', 'passive')
        self.reject_netlist(mutate, 'Symbol pin definitions changed')

    def test_14_sheet_identity_change_is_rejected(self):
        def mutate(tree):
            tree.find("./design/sheet[@name='/Power/']").set('tstamps', '/unexpected/')
        self.reject_netlist(mutate, 'Sheet identity changed')

    def test_15_net_class_change_is_rejected(self):
        def mutate(tree):
            tree.find("./nets/net[@name='/ISENSE']").set('class', 'Changed')
        self.reject_netlist(mutate, 'Net identity/class metadata changed')

    def test_16_duplicate_pin_membership_is_rejected(self):
        def mutate(tree):
            node = copy.deepcopy(tree.find("./nets/net/node[@ref='U8'][@pin='1']"))
            tree.find("./nets/net[@name='/ISENSE']").append(node)
        self.reject_netlist(mutate, 'Duplicate pin membership')

    def test_17_added_empty_net_is_rejected(self):
        def mutate(tree):
            ET.SubElement(tree.find('nets'), 'net', {'code': '9999', 'name': 'EXTRA', 'class': 'Default'})
        self.reject_netlist(mutate, 'Candidate counts')

    def test_18_erc_warning_removed_or_error_added_is_rejected(self):
        for fault in ['removed', 'error']:
            with self.subTest(fault=fault):
                mutant = copy.deepcopy(self.new_erc)
                violations = next(s['violations'] for s in mutant['sheets'] if s['violations'])
                if fault == 'removed':
                    violations.clear()
                else:
                    violations.append({'severity': 'error', 'description': 'new short', 'items': []})
                with self.assertRaisesRegex(ValueError, 'ERC findings'):
                    v.validate_erc(self.old_erc, mutant)

    def test_19_erc_flag_position_is_not_silently_normalized(self):
        mutant = copy.deepcopy(self.new_erc)
        finding = next(s['violations'][0] for s in mutant['sheets'] if s['violations'])
        flag = next(i for i in finding['items'] if i['uuid'] == 'bef86b03-b038-5d27-9003-7ad94f8169b0')
        flag['pos']['x'] += 1
        with self.assertRaisesRegex(ValueError, 'ERC findings'):
            v.validate_erc(self.old_erc, mutant)

    def test_20_root_uuid_and_embedded_library_drift_are_rejected(self):
        for name in ['uuid', 'lib_symbols']:
            with self.subTest(subtree=name):
                original = v.source_subtree(self.power_after, name)
                replacement = original.replace('(', '(changed_', 1)
                mutant = self.power_after.replace(original, replacement, 1)
                with self.assertRaisesRegex(ValueError, 'Missing source subtree|Changed source'):
                    v.validate_power_source(self.power_before, mutant)

    def test_21_untouched_converter_source_drift_is_rejected(self):
        mutant = dict(self.source_after)
        mutant['hardware/kicad_v2/Buck3V3.kicad_sch'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'Unexpected changed source'):
            v.validate_source_coverage(self.source_before, mutant)

    def test_22_source_coverage_omission_is_rejected(self):
        mutant = dict(self.source_after)
        del mutant['hardware/kicad_v2/Buck5V.kicad_sch']
        with self.assertRaisesRegex(ValueError, 'Source coverage changed'):
            v.validate_source_coverage(self.source_before, mutant)

    def test_23_retained_copper_byte_drift_is_rejected(self):
        inputs = v.read(v.P / 'input_manifest.json')
        name = next(n for n in inputs['input_sha256'] if n.endswith('.kicad_pcb'))
        original_sha = v.sha
        def changed_sha(path):
            return '0' * 64 if path.resolve() == (v.ROOT / name).resolve() else original_sha(path)
        # Simulate changed bytes returned by the filesystem without mutating live copper.
        with patch.object(v, 'sha', side_effect=changed_sha):
            with self.assertRaisesRegex(ValueError, 'Changed input/artifact'):
                v.validate_input_manifest(inputs)

    def test_24_preserved_input_hash_omission_or_rebaseline_is_rejected(self):
        for fault in ['omit', 'rebaseline']:
            with self.subTest(fault=fault):
                inputs = v.read(v.P / 'input_manifest.json')
                name = next(iter(inputs['input_sha256']))
                if fault == 'omit':
                    del inputs['input_sha256'][name]
                else:
                    inputs['input_sha256'][name] = '0' * 64
                with self.assertRaisesRegex(ValueError, 'Preserved 580-input coverage changed'):
                    v.validate_input_manifest(inputs)

    def test_25_native_command_failure_or_relaxed_erc_is_rejected(self):
        for fault in ['missing', 'failed', 'severity', 'version']:
            with self.subTest(fault=fault):
                native = copy.deepcopy(self.native)
                if fault == 'missing':
                    native['commands'].pop()
                elif fault == 'failed':
                    native['commands'][0]['returncode'] = 1
                elif fault == 'severity':
                    native['commands'][1]['argv'].remove('--severity-all')
                else:
                    native['kicad_version'] = '9.0.8'
                with self.assertRaisesRegex(ValueError, 'Native command|Unexpected native version'):
                    v.validate_native_manifest(native, self.source_map, self.native_map)

    def test_26_native_input_and_svg_coverage_are_exact(self):
        for fault in ['input', 'svg']:
            with self.subTest(fault=fault):
                native = copy.deepcopy(self.native)
                output_map = dict(self.native_map)
                if fault == 'input':
                    native['input_sha256'].pop(next(iter(native['input_sha256'])))
                else:
                    name = next(n for n in output_map if n.endswith('-Power.svg'))
                    del output_map[name]
                    del native['output_sha256'][name]
                with self.assertRaisesRegex(ValueError, 'Native input coverage|Native output coverage'):
                    v.validate_native_manifest(native, self.source_map, output_map)

    def test_27_contract_cannot_authorize_extra_delta_or_release(self):
        for fault in ['pin', 'hardware', 'copper']:
            with self.subTest(fault=fault):
                contract = v.read(v.P / 'expected_contract.json')
                if fault == 'pin':
                    contract['candidate_electrical_delta']['moved_existing_pins']['U1.20'] = ['/ISENSE', 'GND']
                elif fault == 'hardware':
                    contract['hardware_accepted'] = True
                else:
                    contract['live_copper_delta'] = 1
                with self.assertRaisesRegex(ValueError, 'Contract boundary|Release hold|Live delta'):
                    v.validate_contract(contract)


if __name__ == '__main__':
    unittest.main(verbosity=2)
