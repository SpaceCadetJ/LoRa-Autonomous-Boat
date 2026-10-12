#!/usr/bin/env python3
"""BUCK5-A1 mutation tests. Synthetic fixtures never produce native evidence."""
import copy
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_candidate import (BASELINE, BOUNDARY, CHILD_PATH, ValidationError,
                              load_contract, validate_erc, validate_netlists)
import json


def find_node(tree, ref, pin):
    return next((net, node) for net in tree.getroot().find("nets") for node in net
                if node.get("ref") == ref and node.get("pin") == pin)


def move_pin(tree, ref, pin, target):
    nets = tree.getroot().find("nets")
    net, node = find_node(tree, ref, pin)
    net.remove(node)
    if not list(net):
        nets.remove(net)
    dest = next((n for n in nets if n.get("name") == target), None)
    if dest is None:
        dest = ET.SubElement(nets, "net", name=target, code=str(1000 + len(nets)))
    dest.append(node)


def synthetic_candidate(baseline, contract):
    """Apply the written expectation to a fixture, not to CAD or actual XML."""
    result = copy.deepcopy(baseline)
    root = result.getroot()
    components, nets, libparts = root.find("components"), root.find("nets"), root.find("libparts")
    for comp in list(components):
        if comp.get("ref") in BOUNDARY:
            components.remove(comp)
    for net in list(nets):
        for node in list(net):
            if node.get("ref") in BOUNDARY:
                net.remove(node)
        if not list(net):
            nets.remove(net)
    for ref, part in contract["candidate_parts"].items():
        comp = ET.SubElement(components, "comp", ref=ref)
        ET.SubElement(comp, "value").text = part["value"]
        ET.SubElement(comp, "footprint").text = part["footprint"]
        ET.SubElement(comp, "property", name="MPN", value=part["mpn"])
        ET.SubElement(comp, "property", name="Manufacturer", value=part["manufacturer"])
        lib, symbol = part["library"]
        ET.SubElement(comp, "libsource", lib=lib, part=symbol)
        ET.SubElement(comp, "sheetpath", names=CHILD_PATH)
        libpart = next((p for p in libparts if p.get("lib") == lib and p.get("part") == symbol), None)
        if libpart is None:
            libpart = ET.SubElement(libparts, "libpart", lib=lib, part=symbol)
            pins = ET.SubElement(libpart, "pins")
            for pin, (name, ptype) in part["pins"].items():
                ET.SubElement(pins, "pin", num=pin, name=name, type=ptype)
        for pin, net_name in contract["candidate_memberships"][ref].items():
            net = next((n for n in nets if n.get("name") == net_name), None)
            if net is None:
                net = ET.SubElement(nets, "net", name=net_name, code=str(1000 + len(nets)))
            name, ptype = part["pins"][pin]
            if pin in contract.get("explicit_no_connects", {}).get(ref, []):
                ptype += "+no_connect"
            ET.SubElement(net, "node", ref=ref, pin=pin, pinfunction=name, pintype=ptype)
    return result


class Buck5VCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = ET.parse(BASELINE / "netlist.xml")
        cls.contract = load_contract()
        cls.erc = json.loads((BASELINE / "erc.json").read_text(encoding="utf-8-sig"))

    def setUp(self):
        self.candidate = synthetic_candidate(self.baseline, self.contract)

    def validate(self):
        return validate_netlists(self.baseline, self.candidate, self.contract)

    def test_exact_contract_fixture_passes(self):
        result = self.validate()
        self.assertEqual(result["candidate_components"], 119)
        self.assertEqual(result["candidate_physical_pins"], 398)
        self.assertEqual(result["preserved_outside_boundary_pin_memberships"], 339)
        self.assertEqual(result["removed_physical_pins"], 2)
        self.assertEqual(result["added_physical_pins"], 39)

    def test_enable_on_wrong_rail_rejected(self):
        move_pin(self.candidate, "U3", "18", "+3V3")
        with self.assertRaisesRegex(ValidationError, "pin memberships differ"):
            self.validate()

    def test_exposed_pad_not_grounded_rejected(self):
        move_pin(self.candidate, "U3", "31", "/Power/VIN_BUCK")
        with self.assertRaisesRegex(ValidationError, "pin memberships differ"):
            self.validate()

    def test_bootstrap_cap_grounded_rejected(self):
        move_pin(self.candidate, "C7", "1", "GND")
        with self.assertRaisesRegex(ValidationError, "pin memberships differ"):
            self.validate()

    def test_missing_original_external_pin_rejected(self):
        net, node = find_node(self.candidate, "U1", "19")
        net.remove(node)
        with self.assertRaisesRegex(ValidationError, "Missing physical pin memberships"):
            self.validate()

    def test_duplicate_physical_pin_rejected(self):
        net, node = find_node(self.candidate, "C52", "1")
        net.append(copy.deepcopy(node))
        with self.assertRaisesRegex(ValidationError, "Duplicate physical pin membership"):
            self.validate()

    def test_unrelated_component_swap_rejected(self):
        self.candidate.getroot().find("./components/comp[@ref='U6']/value").text = "DifferentIMU"
        with self.assertRaisesRegex(ValidationError, "Outside-boundary part identity"):
            self.validate()

    def test_unexpected_component_rejected(self):
        root = self.candidate.getroot()
        comp = copy.deepcopy(root.find("./components/comp[@ref='C54']"))
        comp.set("ref", "C99")
        root.find("components").append(comp)
        for pin in ["1", "2"]:
            net, node = find_node(self.candidate, "C54", pin)
            extra = copy.deepcopy(node)
            extra.set("ref", "C99")
            net.append(extra)
        with self.assertRaisesRegex(ValidationError, "Unexpected candidate component set"):
            self.validate()

    def test_wrong_output_capacitor_value_rejected(self):
        self.candidate.getroot().find("./components/comp[@ref='C49']/value").text = "10uF 25V"
        with self.assertRaisesRegex(ValidationError, "Contract part identity.*C49"):
            self.validate()

    def test_wrong_orderable_regulator_rejected(self):
        comp = self.candidate.getroot().find("./components/comp[@ref='U3']")
        next(p for p in comp.findall("property") if p.get("name") == "MPN").set("value", "DifferentRegulator")
        with self.assertRaisesRegex(ValidationError, "Contract part identity.*U3"):
            self.validate()

    def test_wrong_regulator_footprint_rejected(self):
        self.candidate.getroot().find("./components/comp[@ref='U3']/footprint").text = "Package_SO:SOIC-8"
        with self.assertRaisesRegex(ValidationError, "Contract part identity.*U3"):
            self.validate()

    def test_pg_without_explicit_no_connect_rejected(self):
        _, node = find_node(self.candidate, "U3", "16")
        node.set("pintype", "open_collector")
        with self.assertRaisesRegex(ValidationError, "explicit no-connect"):
            self.validate()

    def test_pg_ground_connection_rejected(self):
        move_pin(self.candidate, "U3", "16", "GND")
        with self.assertRaisesRegex(ValidationError, "pin memberships differ"):
            self.validate()

    def test_vin_hierarchy_disconnection_rejected(self):
        move_pin(self.candidate, "U3", "20", "/Power/Buck5V/VIN_BUCK")
        with self.assertRaisesRegex(ValidationError, "pin memberships differ"):
            self.validate()

    def test_outside_adc_sense_changed_rejected(self):
        move_pin(self.candidate, "R33", "2", "+3V3")
        with self.assertRaisesRegex(ValidationError, "Outside-boundary pin memberships"):
            self.validate()

    def test_wrong_child_sheet_rejected(self):
        self.candidate.getroot().find("./components/comp[@ref='C52']/sheetpath").set("names", "/Power/")
        with self.assertRaisesRegex(ValidationError, "expected child sheet"):
            self.validate()

    def test_rt_requires_explicit_no_connect(self):
        _, node = find_node(self.candidate, "U3", "10")
        node.set("pintype", "input")
        with self.assertRaisesRegex(ValidationError, "U3.10 needs an explicit no-connect"):
            self.validate()

    def test_soft_start_requires_explicit_no_connect(self):
        _, node = find_node(self.candidate, "U3", "11")
        node.set("pintype", "input")
        with self.assertRaisesRegex(ValidationError, "U3.11 needs an explicit no-connect"):
            self.validate()

    def test_stacked_pvin_physical_pin_cannot_disappear(self):
        net, node = find_node(self.candidate, "U3", "21")
        net.remove(node)
        with self.assertRaisesRegex(ValidationError, "Missing physical pin memberships"):
            self.validate()

    def test_reserved_ground_pins_cannot_float(self):
        for pin in ["7", "23"]:
            with self.subTest(pin=pin):
                self.candidate = synthetic_candidate(self.baseline, self.contract)
                move_pin(self.candidate, "U3", pin, f"unconnected-(U3-NC-Pad{pin})")
                with self.assertRaisesRegex(ValidationError, "pin memberships differ"):
                    self.validate()

    def test_reserved_ground_pin_type_cannot_revert_to_nc(self):
        for part in self.candidate.getroot().find("libparts"):
            if part.get("lib") == "LoRa_Boat_Controller_V2" and part.get("part") == "LM76003":
                next(pin for pin in part.find("pins") if pin.get("num") == "7").set("type", "no_connect")
        with self.assertRaisesRegex(ValidationError, "Contract part identity.*U3"):
            self.validate()

    def test_33v_regulator_identity_remains_unchanged(self):
        self.candidate.getroot().find("./components/comp[@ref='U2']/value").text = "Different3V3Regulator"
        with self.assertRaisesRegex(ValidationError, "Outside-boundary part identity.*U2"):
            self.validate()

    def test_33v_regulator_vin_remains_unchanged(self):
        move_pin(self.candidate, "U2", "2", "/Power/+5V_BUCK")
        with self.assertRaisesRegex(ValidationError, "Outside-boundary pin memberships"):
            self.validate()

    def test_33v_pg_no_connect_remains_unchanged(self):
        _, node = find_node(self.candidate, "U2", "4")
        node.set("pintype", "open_collector")
        with self.assertRaisesRegex(ValidationError, "Outside-boundary native pin definition/NC marker"):
            self.validate()

    def test_33v_inductor_sheet_remains_unchanged(self):
        self.candidate.getroot().find("./components/comp[@ref='L1']/sheetpath").set("names", "/Power/")
        with self.assertRaisesRegex(ValidationError, "Outside-boundary sheet.*L1"):
            self.validate()

    def test_unchanged_erc_signature_passes(self):
        result = validate_erc(self.erc, copy.deepcopy(self.erc))
        self.assertEqual(result["candidate"]["warnings"], 1)

    def test_added_erc_warning_rejected(self):
        erc = copy.deepcopy(self.erc)
        erc["sheets"][0]["violations"].append({"severity": "warning", "type": "pin_not_driven", "description": "New unpowered input", "items": []})
        with self.assertRaisesRegex(ValidationError, "Native ERC findings changed"):
            validate_erc(self.erc, erc)


if __name__ == "__main__":
    unittest.main(verbosity=2)
