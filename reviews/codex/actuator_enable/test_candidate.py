#!/usr/bin/env python3
"""ACT-02 rejection tests. In-memory fixtures are not captured native evidence."""
import copy
import json
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_candidate import (BASELINE, PARTS, MEMBERSHIPS, ENABLE, EXPECTED_CONTRACT,
                              POPULATION_PATH, ValidationError, load_contract,
                              validate_contract, validate_netlists, validate_erc,
                              validate_population)


def find_node(tree, ref, pin):
    return next((net, node) for net in tree.getroot().find("nets") for node in net
                if node.get("ref") == ref and node.get("pin") == pin)


def target_net(tree, name):
    nets = tree.getroot().find("nets")
    net = next((net for net in nets if net.get("name") == name), None)
    return net if net is not None else ET.SubElement(nets, "net", name=name, code=str(2000 + len(nets)))


def move_pin(tree, ref, pin, name):
    net, node = find_node(tree, ref, pin)
    net.remove(node)
    if not list(net):
        tree.getroot().find("nets").remove(net)
    target_net(tree, name).append(node)


def synthetic_candidate(baseline):
    """Exact proposed topology applied in memory, without writing fake evidence."""
    result = copy.deepcopy(baseline)
    root = result.getroot()
    comps = root.find("components")
    comps.remove(comps.find("comp[@ref='U5']"))
    for net in list(root.find("nets")):
        for node in list(net):
            if node.get("ref") in {"U4", "U5"}:
                net.remove(node)
        if not list(net):
            root.find("nets").remove(net)
    u4 = comps.find("comp[@ref='U4']")
    resistor = copy.deepcopy(next(comp for comp in comps if comp.find("libsource").get("lib") == "Device" and comp.find("libsource").get("part") == "R"))
    resistor.set("ref", "R40")
    resistor.find("sheetpath").set("names", "/Actuators/")
    comps.append(resistor)
    for comp, ref in [(u4, "U4"), (resistor, "R40")]:
        identity = PARTS[ref]
        for field in ["value", "footprint"]:
            comp.find(field).text = identity[field]
        comp.find("libsource").set("lib", identity["library"][0])
        comp.find("libsource").set("part", identity["library"][1])
        for name, key in [("MPN", "mpn"), ("Manufacturer", "manufacturer")]:
            for prop in comp.findall(f"./property[@name='{name}']"):
                comp.remove(prop)
            ET.SubElement(comp, "property", name=name, value=identity[key])
        for pin, name in MEMBERSHIPS[ref].items():
            function, kind = identity["pins"][pin]
            attributes = {"ref": ref, "pin": pin, "pintype": kind}
            if function:
                attributes["pinfunction"] = function
            ET.SubElement(target_net(result, name), "node", attributes)
    libpart = ET.SubElement(root.find("libparts"), "libpart", lib=PARTS["U4"]["library"][0], part=PARTS["U4"]["library"][1])
    pins = ET.SubElement(libpart, "pins")
    for pin, (name, kind) in PARTS["U4"]["pins"].items():
        ET.SubElement(pins, "pin", num=pin, name=name, type=kind)
    move_pin(result, "C13", "1", "+3V3")
    move_pin(result, "U1", "24", ENABLE)
    find_node(result, "U1", "24")[1].set("pintype", "bidirectional")
    return result


class ActuatorEnableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = ET.parse(BASELINE / "netlist.xml")
        cls.contract = load_contract()
        cls.erc = json.loads((BASELINE / "erc.json").read_text(encoding="utf-8-sig"))
        cls.population = json.loads(POPULATION_PATH.read_text(encoding="utf-8-sig"))

    def setUp(self):
        self.candidate = synthetic_candidate(self.baseline)

    def validate(self):
        return validate_netlists(self.baseline, self.candidate, self.contract)

    def rejected(self, pattern):
        return self.assertRaisesRegex(ValidationError, pattern)

    def test_exact_fixture_passes(self):
        result = self.validate()
        self.assertEqual(result["candidate_components"], 119)
        self.assertEqual(result["candidate_physical_pins"], 398)
        self.assertEqual(result["preserved_outside_boundary_pin_memberships"], 383)
        self.assertEqual(result["preserved_existing_pin_memberships"], 386)
        self.assertEqual(result["removed_physical_pins"], 5)
        self.assertEqual(result["added_physical_pins"], 5)
        self.assertEqual(len(result["existing_pin_deltas"]), 7)

    def test_preexport_contract_passes(self):
        self.assertEqual(self.contract, EXPECTED_CONTRACT)

    def test_candidate_cannot_redefine_expectations(self):
        changed = copy.deepcopy(self.contract)
        changed["candidate_memberships"]["U4"]["6"] = "GND"
        move_pin(self.candidate, "U4", "6", "GND")
        with self.rejected("independent ACT-02 specification"):
            validate_netlists(self.baseline, self.candidate, changed)

    def test_contract_cannot_approve_hardware(self):
        data = copy.deepcopy(self.contract); data["qualified_for_power"] = True
        with self.rejected("independent ACT-02 specification"):
            validate_contract(data)

    def test_oe_tied_high_rejected(self):
        move_pin(self.candidate, "U4", "6", "+3V3")
        with self.rejected("exact ACT-02 contract"):
            self.validate()

    def test_pc4_left_unconnected_rejected(self):
        move_pin(self.candidate, "U1", "24", "unconnected-(U1-PC4-Pad24)")
        with self.rejected("exact ACT-02 contract"):
            self.validate()

    def test_pc4_nc_marker_left_rejected(self):
        find_node(self.candidate, "U1", "24")[1].set("pintype", "bidirectional+no_connect")
        with self.rejected("native pin metadata/NC marker.*U1.*24"):
            self.validate()

    def test_other_mcu_nc_marker_removed_rejected(self):
        node = next(node for net in self.candidate.getroot().find("nets") for node in net
                    if node.get("ref") == "U1" and "no_connect" in node.get("pintype", ""))
        node.set("pintype", "bidirectional")
        with self.rejected("native pin metadata/NC marker.*U1"):
            self.validate()

    def test_other_mcu_pin_repurposed_rejected(self):
        move_pin(self.candidate, "U1", "25", ENABLE)
        with self.rejected("Outside-boundary pin memberships"):
            self.validate()

    def test_pc4_pinfunction_changed_rejected(self):
        find_node(self.candidate, "U1", "24")[1].set("pinfunction", "PC5")
        with self.rejected("native pin metadata/NC marker"):
            self.validate()

    def test_pulldown_top_wrong_rejected(self):
        move_pin(self.candidate, "R40", "1", "+3V3")
        with self.rejected("exact ACT-02 contract"):
            self.validate()

    def test_pulldown_bottom_wrong_rejected(self):
        move_pin(self.candidate, "R40", "2", "+3V3")
        with self.rejected("exact ACT-02 contract"):
            self.validate()

    def test_wrong_pulldown_value_rejected(self):
        self.candidate.getroot().find("./components/comp[@ref='R40']/value").text = "100k"
        with self.rejected("Contract part identity.*R40"):
            self.validate()

    def test_wrong_orderable_buffer_rejected(self):
        comp = self.candidate.getroot().find("./components/comp[@ref='U4']")
        comp.find("./property[@name='MPN']").set("value", "TXU0202DCUR")
        with self.rejected("Contract part identity.*U4"):
            self.validate()

    def test_unreviewed_footprint_rejected(self):
        self.candidate.getroot().find("./components/comp[@ref='U4']/footprint").text = "Package_SO:VSSOP-8_2.3x2mm_P0.5mm"
        with self.rejected("Contract part identity.*U4"):
            self.validate()

    def test_input_channels_crossed_rejected(self):
        move_pin(self.candidate, "U4", "4", "/PWM_ESC_PC6")
        move_pin(self.candidate, "U4", "5", "/PWM_SERVO_PA8")
        with self.rejected("exact ACT-02 contract"):
            self.validate()

    def test_output_channels_crossed_rejected(self):
        move_pin(self.candidate, "U4", "1", "/Actuators/ESC_SIG_5V")
        move_pin(self.candidate, "U4", "8", "/Actuators/SERVO_SIG_5V")
        with self.rejected("exact ACT-02 contract"):
            self.validate()

    def test_wrong_buffer_voltage_domain_rejected(self):
        move_pin(self.candidate, "U4", "3", "/Power/+5V_BUCK")
        with self.rejected("exact ACT-02 contract"):
            self.validate()

    def test_output_supply_on_vservo_rejected(self):
        move_pin(self.candidate, "U4", "7", "VSERVO")
        with self.rejected("exact ACT-02 contract"):
            self.validate()

    def test_bypass_voltage_domain_rejected(self):
        move_pin(self.candidate, "C13", "1", "/Power/+5V_BUCK")
        with self.rejected("exact ACT-02 contract"):
            self.validate()

    def test_c14_changed_rejected(self):
        move_pin(self.candidate, "C14", "1", "+3V3")
        with self.rejected("exact ACT-02 contract"):
            self.validate()

    def test_missing_buffer_ground_rejected(self):
        net, node = find_node(self.candidate, "U4", "2"); net.remove(node)
        with self.rejected("Missing physical pin memberships"):
            self.validate()

    def test_missing_converter_stacked_pin_rejected(self):
        net, node = find_node(self.candidate, "U3", "21"); net.remove(node)
        with self.rejected("Missing physical pin memberships"):
            self.validate()

    def test_duplicate_physical_pin_rejected(self):
        net, node = find_node(self.candidate, "U4", "6"); net.append(copy.deepcopy(node))
        with self.rejected("Duplicate physical pin membership"):
            self.validate()

    def test_wrong_new_pin_metadata_rejected(self):
        find_node(self.candidate, "U4", "1")[1].set("pintype", "input")
        with self.rejected("New native pin metadata differs"):
            self.validate()

    def test_wrong_library_pin_definition_rejected(self):
        pin = self.candidate.getroot().find("./libparts/libpart[@part='TXU0102DCU']/pins/pin[@num='6']")
        pin.set("type", "power_in")
        with self.rejected("Contract part identity.*U4"):
            self.validate()

    def test_removed_buffer_restored_rejected(self):
        comp = copy.deepcopy(self.baseline.getroot().find("./components/comp[@ref='U5']"))
        self.candidate.getroot().find("components").append(comp)
        for pin in ["1", "2", "3", "4", "5"]:
            net, node = find_node(self.baseline, "U5", pin)
            target_net(self.candidate, net.get("name")).append(copy.deepcopy(node))
        with self.rejected("Unexpected candidate component set"):
            self.validate()

    def test_converter_net_changed_rejected(self):
        move_pin(self.candidate, "U3", "8", "/Power/+5V_BUCK")
        with self.rejected("Outside-boundary pin memberships"):
            self.validate()

    def test_converter_identity_changed_rejected(self):
        self.candidate.getroot().find("./components/comp[@ref='U2']/value").text = "DifferentRegulator"
        with self.rejected("Existing identity.*U2"):
            self.validate()

    def test_converter_nc_marker_changed_rejected(self):
        find_node(self.candidate, "U3", "10")[1].set("pintype", "input")
        with self.rejected("native pin metadata/NC marker.*U3"):
            self.validate()

    def test_converter_sheet_changed_rejected(self):
        self.candidate.getroot().find("./components/comp[@ref='L1']/sheetpath").set("names", "/Power/")
        with self.rejected("sheet path changed"):
            self.validate()

    def test_pulldown_sheet_changed_rejected(self):
        self.candidate.getroot().find("./components/comp[@ref='R40']/sheetpath").set("names", "/MCU/")
        with self.rejected("new resistor misplaced"):
            self.validate()

    def test_diode_dnp_removed_rejected(self):
        comp = self.candidate.getroot().find("./components/comp[@ref='D4']")
        comp.remove(comp.find("./property[@name='dnp']"))
        with self.rejected("Master DNP state changed"):
            self.validate()

    def test_unrelated_part_dnp_rejected(self):
        comp = self.candidate.getroot().find("./components/comp[@ref='U3']")
        ET.SubElement(comp, "property", name="dnp")
        with self.rejected("Master DNP state changed"):
            self.validate()

    def test_diode_polarity_changed_rejected(self):
        move_pin(self.candidate, "D4", "1", "/Power/+5V_BUCK")
        move_pin(self.candidate, "D4", "2", "VSERVO")
        with self.rejected("Outside-boundary pin memberships"):
            self.validate()

    def test_unchanged_erc_passes(self):
        self.assertEqual(validate_erc(self.erc, copy.deepcopy(self.erc))["candidate"]["warnings"], 1)

    def test_additional_erc_finding_rejected(self):
        erc = copy.deepcopy(self.erc)
        erc["sheets"][0]["violations"].append({"severity": "warning", "type": "pin_not_driven", "description": "New OE warning", "items": []})
        with self.rejected("Native ERC findings changed"):
            validate_erc(self.erc, erc)

    def test_erc_warning_suppressed_rejected(self):
        erc = copy.deepcopy(self.erc)
        for sheet in erc["sheets"]:
            sheet["violations"] = []
        with self.rejected("Native ERC findings changed"):
            validate_erc(self.erc, erc)

    def test_held_population_contract_passes(self):
        self.assertFalse(validate_population(self.population)["procurement_approved"])

    def test_dual_population_rejected(self):
        data = copy.deepcopy(self.population)
        data["variants"]["BEC_ONLY"]["D4"] = "POPULATE"
        with self.rejected("single source"):
            validate_population(data)

    def test_default_variant_release_rejected(self):
        data = copy.deepcopy(self.population); data["default_released_variant"] = "ONBOARD"
        with self.rejected("No variant is released"):
            validate_population(data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
