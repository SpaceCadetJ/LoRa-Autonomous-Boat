#!/usr/bin/env python3
"""Mutation tests reject unsafe or unrelated edits; fixtures are not CAD evidence."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("input_stage_verifier_test", Path(__file__).with_name("verify_candidate.py"))
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

def move_pin(tree, ref, pin, target):
    nets = tree.getroot().find("nets")
    matches = [(net, n) for net in nets for n in net.findall("node") if n.get("ref") == ref and n.get("pin") == pin]
    assert len(matches) == 1
    old, node = matches[0]
    old.remove(node)
    if not old.findall("node"):
        nets.remove(old)
    net = next((net for net in nets if net.get("name") == target), None)
    if net is None:
        net = ET.SubElement(nets, "net", name=target, code=str(1000 + len(nets)))
    net.append(node)

def synthetic_candidate(baseline):
    """Produce a contract fixture solely for rejection tests."""
    candidate = copy.deepcopy(baseline)
    root = candidate.getroot()
    components, nets, libraries = root.find("components"), root.find("nets"), root.find("libparts")
    for comp in list(components):
        if comp.get("ref") in v.REMOVED:
            components.remove(comp)
    for net in list(nets):
        for node in list(net):
            if node.get("ref") in v.REMOVED:
                net.remove(node)
        if not net.findall("node"):
            nets.remove(net)
    for (ref, pin), (_, target) in v.EXPECTED_DELTA.items():
        move_pin(candidate, ref, pin, target)
    for ref, expected in v.PARTS.items():
        comp = root.find(f"./components/comp[@ref='{ref}']")
        if comp is not None:
            components.remove(comp)
        comp = ET.SubElement(components, "comp", ref=ref)
        for tag in ("value", "footprint"):
            ET.SubElement(comp, tag).text = expected[tag]
        ET.SubElement(comp, "property", name="MPN", value=expected["mpn"])
        ET.SubElement(comp, "property", name="Manufacturer", value=expected["manufacturer"])
        lib, part = expected["library"]
        ET.SubElement(comp, "libsource", lib=lib, part=part)
        if not any(p.get("lib") == lib and p.get("part") == part for p in libraries):
            lp = ET.SubElement(libraries, "libpart", lib=lib, part=part)
            pins = ET.SubElement(lp, "pins")
            for number, (name, kind) in expected["pins"].items():
                ET.SubElement(pins, "pin", num=number, name=name, type=kind)
    for (ref, pin), target in v.NEW_PINS.items():
        net = next(n for n in nets if n.get("name") == target)
        ET.SubElement(net, "node", ref=ref, pin=pin)
    return candidate

class CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = ET.parse(v.BASELINE / "netlist.xml")

    def setUp(self):
        self.candidate = synthetic_candidate(self.baseline)

    def validate(self):
        return v.validate_netlists(self.baseline, self.candidate)

    def comp(self, ref):
        return self.candidate.getroot().find(f"./components/comp[@ref='{ref}']")

    def reject(self, message):
        with self.assertRaisesRegex(v.ValidationError, message):
            self.validate()

    def test_contract_fixture_passes_exact_counts(self):
        r = self.validate()
        self.assertEqual((r["candidate_components"], r["candidate_physical_pins"]), (112, 356))
        self.assertEqual((r["removed_physical_pins"], r["added_physical_pins"]), (7, 2))
        self.assertEqual(r["preserved_existing_pin_memberships"], 350)
        self.assertEqual(r["preserved_outside_boundary_pin_memberships"], 344)
        self.assertEqual(len(r["existing_pin_deltas"]), 4)

    def test_reversed_series_diode_rejected(self):
        move_pin(self.candidate, "D12", "1", v.NEW_FUSED)
        move_pin(self.candidate, "D12", "2", "VIN_RAW")
        self.reject("Wrong new diode pin memberships")

    def test_tvs_after_reverse_diode_rejected(self):
        move_pin(self.candidate, "D1", "1", "VIN_RAW")
        self.reject("Unexpected retained-pin delta")

    def test_unrelated_adc_rewire_rejected(self):
        move_pin(self.candidate, "U1", "16", "GND")
        self.reject("Unexpected retained-pin delta")

    def test_old_fuse_identity_rejected(self):
        self.comp("F1").find("property[@name='MPN']").set("value", "0468003.NR")
        self.reject("identity/pin definition differs.*F1")

    def test_old_50v_capacitor_rejected(self):
        self.comp("C1").find("property[@name='MPN']").set("value", "EEE-FK1H470P")
        self.reject("identity/pin definition differs.*C1")

    def test_unidirectional_tvs_identity_rejected(self):
        self.comp("D1").find("property[@name='MPN']").set("value", "SMBJ26A")
        self.reject("identity/pin definition differs.*D1")

    def test_wrong_diode_pad_names_rejected(self):
        p = self.candidate.getroot().find("./libparts/libpart[@part='D_Schottky']/pins/pin[@num='1']")
        p.set("name", "A")
        self.reject("identity/pin definition")

    def test_wrong_capacitor_footprint_rejected(self):
        self.comp("C1").find("footprint").text = "Capacitor_SMD:CP_Elec_6.3x7.7"
        self.reject("identity/pin definition differs.*C1")

    def test_connector_identity_change_rejected(self):
        self.comp("J1").find("value").text = "Different connector"
        self.reject("Unrelated component identity.*J1")

    def test_missing_pin_rejected(self):
        for net in self.candidate.getroot().find("nets"):
            for node in list(net):
                if node.get("ref") == "U1" and node.get("pin") == "16":
                    net.remove(node)
        self.reject("Missing physical pin memberships")

    def test_duplicate_pin_rejected(self):
        gnd = self.candidate.getroot().find("./nets/net[@name='GND']")
        ET.SubElement(gnd, "node", ref="D12", pin="1")
        self.reject("Duplicate physical pin membership")

    def test_removed_gate_resistor_return_rejected(self):
        root = self.candidate.getroot()
        comp = copy.deepcopy(self.baseline.getroot().find("./components/comp[@ref='R1']"))
        root.find("components").append(comp)
        gnd = root.find("./nets/net[@name='GND']")
        for pin in ("1", "2"):
            ET.SubElement(gnd, "node", ref="R1", pin=pin)
        self.reject("Unexpected component set")

    def test_old_local_net_name_rejected(self):
        move_pin(self.candidate, "J1", "1", v.OLD_IN)
        self.reject("Unexpected retained-pin delta")

if __name__ == "__main__":
    unittest.main(verbosity=2)
