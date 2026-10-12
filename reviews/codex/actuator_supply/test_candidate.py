#!/usr/bin/env python3
"""ACT-01 mutation tests; synthetic fixtures do not constitute native evidence."""
import copy
import json
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_candidate import (BASELINE, POPULATION_PATH, EXPECTED_DELTA,
                              ValidationError, load_contract, validate_netlists,
                              validate_erc, validate_population)


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
    """Modify only an in-memory fixture using the pre-export expectation."""
    result = copy.deepcopy(baseline)
    for (ref, pin), (_, target) in EXPECTED_DELTA.items():
        move_pin(result, ref, pin, target)
    for ref in ["D4", "D9"]:
        comp = result.getroot().find(f"./components/comp[@ref='{ref}']")
        comp.find("footprint").text = contract["candidate_parts"][ref]["footprint"]
        ET.SubElement(comp, "property", name="dnp")
        next(p for p in comp.findall("property") if p.get("name") == "MPN").set("value", contract["candidate_parts"][ref]["mpn"])
    return result


class ActuatorCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = ET.parse(BASELINE / "netlist.xml")
        cls.contract = load_contract()
        cls.erc = json.loads((BASELINE / "erc.json").read_text(encoding="utf-8-sig"))
        cls.population = json.loads(POPULATION_PATH.read_text(encoding="utf-8-sig"))

    def setUp(self):
        self.candidate = synthetic_candidate(self.baseline, self.contract)

    def validate(self):
        return validate_netlists(self.baseline, self.candidate, self.contract)

    def test_exact_contract_fixture_passes(self):
        result = self.validate()
        self.assertEqual(result["candidate_components"], 119)
        self.assertEqual(result["candidate_physical_pins"], 398)
        self.assertEqual(result["preserved_outside_boundary_pin_memberships"], 380)
        self.assertEqual(result["preserved_existing_pin_memberships"], 394)
        self.assertEqual(len(result["existing_pin_deltas"]), 4)
        self.assertEqual(result["updated_component_identities"], ["D4", "D9"])

    def test_buffer_still_on_servo_rail_rejected(self):
        move_pin(self.candidate, "U4", "5", "VSERVO")
        with self.assertRaisesRegex(ValidationError, "exactly four authorized supply moves"):
            self.validate()

    def test_bypass_still_on_servo_rail_rejected(self):
        move_pin(self.candidate, "C14", "1", "VSERVO")
        with self.assertRaisesRegex(ValidationError, "exactly four authorized supply moves"):
            self.validate()

    def test_output_enable_altered_rejected(self):
        move_pin(self.candidate, "U4", "1", "/Power/+5V_BUCK")
        with self.assertRaisesRegex(ValidationError, "exactly four authorized supply moves"):
            self.validate()

    def test_buffer_input_cross_connection_rejected(self):
        move_pin(self.candidate, "U4", "2", "/PWM_SERVO_PA8")
        with self.assertRaisesRegex(ValidationError, "exactly four authorized supply moves"):
            self.validate()

    def test_diode_polarity_reversal_rejected(self):
        for ref, supply in [("D4", "/Power/+5V_BUCK"), ("D9", "/BEC_IN")]:
            with self.subTest(ref=ref):
                self.candidate = synthetic_candidate(self.baseline, self.contract)
                move_pin(self.candidate, ref, "1", supply)
                move_pin(self.candidate, ref, "2", "VSERVO")
                with self.assertRaisesRegex(ValidationError, "exactly four authorized supply moves"):
                    self.validate()

    def test_missing_master_diode_dnp_rejected(self):
        comp = self.candidate.getroot().find("./components/comp[@ref='D4']")
        comp.remove(comp.find("./property[@name='dnp']"))
        with self.assertRaisesRegex(ValidationError, "Master DNP state"):
            self.validate()

    def test_unrelated_converter_marked_dnp_rejected(self):
        comp = self.candidate.getroot().find("./components/comp[@ref='U3']")
        ET.SubElement(comp, "property", name="dnp")
        with self.assertRaisesRegex(ValidationError, "Master DNP state"):
            self.validate()

    def test_wrong_orderable_diode_rejected(self):
        comp = self.candidate.getroot().find("./components/comp[@ref='D9']")
        next(p for p in comp.findall("property") if p.get("name") == "MPN").set("value", "SS34")
        with self.assertRaisesRegex(ValidationError, "Contract part identity.*D9"):
            self.validate()

    def test_sma_footprint_regression_rejected(self):
        self.candidate.getroot().find("./components/comp[@ref='D4']/footprint").text = "Diode_SMD:D_SMA"
        with self.assertRaisesRegex(ValidationError, "Contract part identity.*D4"):
            self.validate()

    def test_buffer_part_swap_rejected(self):
        self.candidate.getroot().find("./components/comp[@ref='U5']/value").text = "74LVC1G125"
        with self.assertRaisesRegex(ValidationError, "Contract part identity.*U5"):
            self.validate()

    def test_5v_converter_connection_change_rejected(self):
        move_pin(self.candidate, "U3", "8", "/Power/+5V_BUCK")
        with self.assertRaisesRegex(ValidationError, "Outside-boundary pin memberships"):
            self.validate()

    def test_33v_converter_identity_change_rejected(self):
        self.candidate.getroot().find("./components/comp[@ref='U2']/value").text = "DifferentRegulator"
        with self.assertRaisesRegex(ValidationError, "Outside-boundary identity.*U2"):
            self.validate()

    def test_converter_sheet_change_rejected(self):
        self.candidate.getroot().find("./components/comp[@ref='L1']/sheetpath").set("names", "/Power/")
        with self.assertRaisesRegex(ValidationError, "sheet path changed"):
            self.validate()

    def test_missing_stacked_converter_pin_rejected(self):
        net, node = find_node(self.candidate, "U3", "21")
        net.remove(node)
        with self.assertRaisesRegex(ValidationError, "Missing physical pin memberships"):
            self.validate()

    def test_missing_buffer_ground_pin_rejected(self):
        net, node = find_node(self.candidate, "U4", "3")
        net.remove(node)
        with self.assertRaisesRegex(ValidationError, "Missing physical pin memberships"):
            self.validate()

    def test_duplicate_pin_rejected(self):
        net, node = find_node(self.candidate, "U4", "5")
        net.append(copy.deepcopy(node))
        with self.assertRaisesRegex(ValidationError, "Duplicate physical pin membership"):
            self.validate()

    def test_converter_nc_marker_removed_rejected(self):
        _, node = find_node(self.candidate, "U3", "10")
        node.set("pintype", "input")
        with self.assertRaisesRegex(ValidationError, "native pin definition/NC marker"):
            self.validate()

    def test_unexpected_component_rejected(self):
        root = self.candidate.getroot()
        comp = copy.deepcopy(root.find("./components/comp[@ref='C13']"))
        comp.set("ref", "C99")
        root.find("components").append(comp)
        for pin in ["1", "2"]:
            net, node = find_node(self.candidate, "C13", pin)
            extra = copy.deepcopy(node); extra.set("ref", "C99"); net.append(extra)
        with self.assertRaisesRegex(ValidationError, "Unexpected candidate component set"):
            self.validate()

    def test_supply_net_alias_change_rejected(self):
        net, _ = find_node(self.candidate, "U4", "5")
        net.set("name", "/+5V_BUCK")
        with self.assertRaisesRegex(ValidationError, "Outside-boundary pin memberships"):
            self.validate()

    def test_unchanged_erc_signature_passes(self):
        self.assertEqual(validate_erc(self.erc, copy.deepcopy(self.erc))["candidate"]["warnings"], 1)

    def test_additional_erc_finding_rejected(self):
        erc = copy.deepcopy(self.erc)
        erc["sheets"][0]["violations"].append({"severity": "warning", "type": "pin_not_driven", "description": "New unpowered input", "items": []})
        with self.assertRaisesRegex(ValidationError, "Native ERC findings changed"):
            validate_erc(self.erc, erc)

    def test_population_proposals_pass(self):
        result = validate_population(self.population)
        self.assertFalse(result["procurement_approved"])
        self.assertFalse(result["dual_population_allowed"])

    def test_both_sources_populated_rejected(self):
        data = copy.deepcopy(self.population)
        data["variants"]["BEC_ONLY"]["D4"] = "POPULATE"
        with self.assertRaisesRegex(ValidationError, "single source"):
            validate_population(data)

    def test_no_actuator_source_variant_rejected(self):
        data = copy.deepcopy(self.population)
        data["variants"]["ONBOARD"]["D4"] = "DNP"
        with self.assertRaisesRegex(ValidationError, "single source"):
            validate_population(data)

    def test_extra_dual_variant_rejected(self):
        data = copy.deepcopy(self.population)
        data["variants"]["DUAL"] = copy.deepcopy(data["variants"]["ONBOARD"])
        with self.assertRaisesRegex(ValidationError, "two exclusive"):
            validate_population(data)

    def test_master_population_dnp_hold_removed_rejected(self):
        data = copy.deepcopy(self.population); data["base_schematic_dnp_refs"] = ["D4"]
        with self.assertRaisesRegex(ValidationError, "both diode positions DNP"):
            validate_population(data)

    def test_dual_permission_flag_rejected(self):
        data = copy.deepcopy(self.population); data["dual_population_allowed"] = True
        with self.assertRaisesRegex(ValidationError, "Dual source population"):
            validate_population(data)

    def test_default_released_variant_rejected(self):
        data = copy.deepcopy(self.population); data["default_released_variant"] = "BEC_ONLY"
        with self.assertRaisesRegex(ValidationError, "No variant is released"):
            validate_population(data)

    def test_unearned_procurement_or_hardware_claim_rejected(self):
        for key in ["procurement_approved", "hardware_tested"]:
            with self.subTest(key=key):
                data = copy.deepcopy(self.population); data[key] = True
                with self.assertRaisesRegex(ValidationError, "cannot approve procurement or claim hardware"):
                    validate_population(data)

    def test_removed_parts_hold_rejected(self):
        data = copy.deepcopy(self.population); data["all_parts_held"] = False
        with self.assertRaisesRegex(ValidationError, "must remain held"):
            validate_population(data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
