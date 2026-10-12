#!/usr/bin/env python3
"""ACT-04 mutations use in-memory fixtures, never synthetic native evidence."""
import copy
import json
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_candidate import (BASELINE, POPULATION_PATH, PARTS, MEMBERSHIPS,
    EXPECTED_DELTA, PRESERVED_SHEETS, CHILD, ARM, QUAL, ACK, READY, OE, QBAR_NC,
    INVERTER_NC, ValidationError, load_contract, validate_contract,
    validate_netlists, validate_erc, validate_population, validate_preservation,
    node_attributes)


def find_node(tree, ref, pin):
    return next((net, node) for net in tree.getroot().find("nets") for node in net
                if node.get("ref") == ref and node.get("pin") == pin)


def target_net(tree, name):
    nets = tree.getroot().find("nets")
    result = next((net for net in nets if net.get("name") == name), None)
    return result if result is not None else ET.SubElement(nets, "net", name=name, code=str(3000 + len(nets)))


def move_pin(tree, ref, pin, name):
    net, node = find_node(tree, ref, pin)
    net.remove(node)
    if not list(net):
        tree.getroot().find("nets").remove(net)
    target_net(tree, name).append(node)


def remove_component(tree, ref):
    root = tree.getroot()
    root.find("components").remove(root.find(f"./components/comp[@ref='{ref}']"))
    for net in list(root.find("nets")):
        for node in list(net):
            if node.get("ref") == ref:
                net.remove(node)
        if not list(net):
            root.find("nets").remove(net)


def synthetic_candidate(baseline):
    result = copy.deepcopy(baseline)
    root = result.getroot()
    comps, libparts = root.find("components"), root.find("libparts")
    for (ref, pin), (_, target) in EXPECTED_DELTA.items():
        move_pin(result, ref, pin, target)
    for ref, part in PARTS.items():
        template = root.find("./components/comp[@ref='U4']") if ref.startswith("U") else next(
            comp for comp in comps if comp.find("libsource").get("lib") == "Device"
            and comp.find("libsource").get("part") == ref[0])
        comp = copy.deepcopy(template)
        comp.set("ref", ref)
        for field in ["value", "footprint"]:
            comp.find(field).text = part[field]
        comp.find("sheetpath").set("names", CHILD)
        source = comp.find("libsource")
        source.set("lib", part["library"][0]); source.set("part", part["library"][1])
        for label, key in [("MPN", "mpn"), ("Manufacturer", "manufacturer")]:
            for prop in comp.findall(f"./property[@name='{label}']"):
                comp.remove(prop)
            ET.SubElement(comp, "property", name=label, value=part[key])
        comps.append(comp)
        if ref.startswith("U"):
            lp = ET.SubElement(libparts, "libpart", lib=part["library"][0], part=part["library"][1])
            pins = ET.SubElement(lp, "pins")
            for pin, (name, kind) in part["pins"].items():
                ET.SubElement(pins, "pin", num=pin, name=name, type=kind)
        for pin, net in MEMBERSHIPS[ref].items():
            ET.SubElement(target_net(result, net), "node", node_attributes(ref, pin))
    return result


class ActuatorLatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = ET.parse(BASELINE / "netlist.xml")
        cls.contract = load_contract()
        cls.erc = json.loads((BASELINE / "erc.json").read_text(encoding="utf-8-sig"))
        cls.population_bytes = POPULATION_PATH.read_bytes()
        cls.population = json.loads(cls.population_bytes.decode("utf-8-sig"))
        cls.sources = {name: (BASELINE.parent / "source/hardware/kicad_v2" / name).read_bytes() for name in PRESERVED_SHEETS}

    def setUp(self):
        self.candidate = synthetic_candidate(self.baseline)

    def validate(self):
        return validate_netlists(self.baseline, self.candidate, self.contract)

    def rejected(self, pattern):
        return self.assertRaisesRegex(ValidationError, pattern)

    def test_exact_contract_fixture_passes(self):
        result = self.validate()
        self.assertEqual(result["candidate_components"], 128)
        self.assertEqual(result["candidate_physical_pins"], 429)
        self.assertEqual(result["added_physical_pins"], 31)
        self.assertEqual(result["preserved_existing_pin_memberships"], 396)
        self.assertEqual(len(result["existing_pin_deltas"]), 2)
        self.assertEqual(result["updated_component_identities"], [])

    def test_q_and_qbar_swapped_rejected(self):
        move_pin(self.candidate, "U12", "5", QBAR_NC)
        move_pin(self.candidate, "U12", "3", READY)
        with self.rejected("exact ACT-04 contract"):
            self.validate()

    def test_wrong_and_ground_map_rejected(self):
        move_pin(self.candidate, "U14", "2", ARM)
        move_pin(self.candidate, "U14", "3", "GND")
        with self.rejected("exact ACT-04 contract"):
            self.validate()

    def test_wrong_and_library_pinmap_rejected(self):
        pins = self.candidate.getroot().find("./libparts/libpart[@part='SN74LVC1G11']/pins")
        pins.find("pin[@num='2']").set("name", "B")
        pins.find("pin[@num='2']").set("type", "input")
        with self.rejected("Contract part identity.*U14"):
            self.validate()

    def test_wrong_dff_orderable_part_rejected(self):
        comp = self.candidate.getroot().find("./components/comp[@ref='U12']")
        comp.find("./property[@name='MPN']").set("value", "SN74LVC1G74DCTR")
        with self.rejected("Contract part identity.*U12"):
            self.validate()

    def test_unreviewed_footprint_rejected(self):
        self.candidate.getroot().find("./components/comp[@ref='U14']/footprint").text = "Package_TO_SOT_SMD:SOT-23-6"
        with self.rejected("Contract part identity.*U14"):
            self.validate()

    def test_oe_bypass_rejected(self):
        move_pin(self.candidate, "U4", "6", ARM)
        with self.rejected("exact ACT-04 contract"):
            self.validate()

    def test_oe_pulldown_left_on_request_rejected(self):
        move_pin(self.candidate, "R40", "1", ARM)
        with self.rejected("exact ACT-04 contract"):
            self.validate()

    def test_missing_qualification_pulldown_rejected(self):
        remove_component(self.candidate, "R42")
        with self.rejected("Unexpected candidate component set"):
            self.validate()

    def test_qualification_pullup_rejected(self):
        move_pin(self.candidate, "R42", "2", "+3V3")
        with self.rejected("exact ACT-04 contract"):
            self.validate()

    def test_ack_pulldown_wrong_rejected(self):
        move_pin(self.candidate, "R43", "1", ARM)
        with self.rejected("exact ACT-04 contract"):
            self.validate()

    def test_request_pulldown_wrong_rejected(self):
        move_pin(self.candidate, "R41", "1", OE)
        with self.rejected("exact ACT-04 contract"):
            self.validate()

    def test_missing_clear_qualification_rejected(self):
        move_pin(self.candidate, "U12", "6", "+3V3")
        with self.rejected("exact ACT-04 contract"):
            self.validate()

    def test_missing_combinational_qualification_rejected(self):
        move_pin(self.candidate, "U14", "6", "+3V3")
        with self.rejected("exact ACT-04 contract"):
            self.validate()

    def test_gate_request_bypassed_rejected(self):
        move_pin(self.candidate, "U14", "3", "+3V3")
        with self.rejected("exact ACT-04 contract"):
            self.validate()

    def test_preset_asserted_rejected(self):
        move_pin(self.candidate, "U12", "7", "GND")
        with self.rejected("exact ACT-04 contract"):
            self.validate()

    def test_clock_on_request_rejected(self):
        move_pin(self.candidate, "U12", "1", ARM)
        with self.rejected("exact ACT-04 contract"):
            self.validate()

    def test_uninverted_data_rejected(self):
        move_pin(self.candidate, "U12", "2", ARM)
        with self.rejected("exact ACT-04 contract"):
            self.validate()

    def test_wrong_pulldown_identity_rejected(self):
        self.candidate.getroot().find("./components/comp[@ref='R42']/value").text = "100k"
        with self.rejected("Contract part identity.*R42"):
            self.validate()

    def test_wrong_bypass_rail_rejected(self):
        move_pin(self.candidate, "C56", "1", "/Power/+5V_BUCK")
        with self.rejected("exact ACT-04 contract"):
            self.validate()

    def test_missing_dff_ground_rejected(self):
        net, node = find_node(self.candidate, "U12", "4"); net.remove(node)
        with self.rejected("Missing physical pin memberships"):
            self.validate()

    def test_duplicate_pin_rejected(self):
        net, node = find_node(self.candidate, "U14", "6"); net.append(copy.deepcopy(node))
        with self.rejected("Duplicate physical pin membership"):
            self.validate()

    def test_qbar_nc_marker_missing_rejected(self):
        find_node(self.candidate, "U12", "3")[1].set("pintype", "output")
        with self.rejected("New native pin metadata.*U12.3"):
            self.validate()

    def test_inverter_nc_tied_ground_rejected(self):
        move_pin(self.candidate, "U13", "1", "GND")
        with self.rejected("exact ACT-04 contract"):
            self.validate()

    def test_existing_nc_removed_rejected(self):
        find_node(self.candidate, "U3", "16")[1].set("pintype", "open_collector")
        with self.rejected("Existing native pin metadata/NC marker"):
            self.validate()

    def test_mcu_pc4_type_changed_rejected(self):
        find_node(self.candidate, "U1", "24")[1].set("pintype", "input")
        with self.rejected("Existing native pin metadata/NC marker"):
            self.validate()

    def test_mcu_pc4_membership_changed_rejected(self):
        move_pin(self.candidate, "U1", "24", OE)
        with self.rejected("Unrelated existing pin memberships"):
            self.validate()

    def test_old_translator_identity_changed_rejected(self):
        self.candidate.getroot().find("./components/comp[@ref='U4']/value").text = "DifferentTranslator"
        with self.rejected("Existing identity.*U4"):
            self.validate()

    def test_converter_connection_changed_rejected(self):
        move_pin(self.candidate, "U3", "8", "/Power/+5V_BUCK")
        with self.rejected("Unrelated existing pin memberships"):
            self.validate()

    def test_existing_sheet_moved_rejected(self):
        self.candidate.getroot().find("./components/comp[@ref='U1']/sheetpath").set("names", CHILD)
        with self.rejected("Existing sheet path changed"):
            self.validate()

    def test_new_part_parent_sheet_rejected(self):
        self.candidate.getroot().find("./components/comp[@ref='U12']/sheetpath").set("names", "/Actuators/")
        with self.rejected("new part outside ArmInterlock"):
            self.validate()

    def test_diode_population_marker_removed_rejected(self):
        comp = self.candidate.getroot().find("./components/comp[@ref='D9']")
        comp.remove(comp.find("./property[@name='dnp']"))
        with self.rejected("Master DNP state changed"):
            self.validate()

    def test_new_pulldown_dnp_rejected(self):
        comp = self.candidate.getroot().find("./components/comp[@ref='R42']")
        ET.SubElement(comp, "property", name="dnp")
        with self.rejected("Master DNP state changed"):
            self.validate()

    def test_expectation_cannot_follow_bad_candidate(self):
        data = copy.deepcopy(self.contract)
        data["candidate_memberships"]["U14"]["6"] = "+3V3"
        move_pin(self.candidate, "U14", "6", "+3V3")
        with self.rejected("independent ACT-04 specification"):
            validate_netlists(self.baseline, self.candidate, data)

    def test_contract_cannot_claim_implemented_qualification(self):
        data = copy.deepcopy(self.contract); data["qualification_ports_implemented"] = True
        with self.rejected("independent ACT-04 specification"):
            validate_contract(data)

    def test_unchanged_erc_passes(self):
        self.assertEqual(validate_erc(self.erc, copy.deepcopy(self.erc))["candidate"]["warnings"], 1)

    def test_extra_erc_finding_rejected(self):
        erc = copy.deepcopy(self.erc)
        erc["sheets"][0]["violations"].append({"severity": "warning", "type": "pin_not_driven", "description": "New clear fault", "items": []})
        with self.rejected("Native ERC findings changed"):
            validate_erc(self.erc, erc)

    def test_erc_finding_hidden_rejected(self):
        erc = copy.deepcopy(self.erc)
        for sheet in erc["sheets"]:
            sheet["violations"] = []
        with self.rejected("Native ERC findings changed"):
            validate_erc(self.erc, erc)

    def test_preserved_source_bytes_pass(self):
        self.assertFalse(validate_preservation(self.sources, copy.deepcopy(self.sources), self.population_bytes, self.population_bytes)["procurement_approved"])

    def test_each_preserved_sheet_mutation_rejected(self):
        for name in PRESERVED_SHEETS:
            with self.subTest(name=name):
                after = dict(self.sources); after[name] += b"\n; changed"
                with self.rejected("Preserved source changed"):
                    validate_preservation(self.sources, after, self.population_bytes, self.population_bytes)

    def test_population_even_whitespace_change_rejected(self):
        with self.rejected("population contract changed"):
            validate_preservation(self.sources, self.sources, self.population_bytes, self.population_bytes + b"\n")

    def test_missing_preserved_sheet_rejected(self):
        after = dict(self.sources); del after["MCU.kicad_sch"]
        with self.rejected("Incomplete preserved-source set"):
            validate_preservation(self.sources, after, self.population_bytes, self.population_bytes)

    def test_dual_population_rejected(self):
        pop = copy.deepcopy(self.population); pop["variants"]["BEC_ONLY"]["D4"] = "POPULATE"
        with self.rejected("single source"):
            validate_population(pop)

    def test_unearned_assembly_release_rejected(self):
        pop = copy.deepcopy(self.population); pop["default_released_variant"] = "ONBOARD"
        with self.rejected("No variant is released"):
            validate_population(pop)


if __name__ == "__main__":
    unittest.main(verbosity=2)
