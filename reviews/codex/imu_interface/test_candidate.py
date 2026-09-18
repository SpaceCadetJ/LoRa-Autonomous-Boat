#!/usr/bin/env python3
"""Meaningful rejection tests for E-01 verification; no native evidence is emitted."""
import copy
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_candidate import (BASELINE, EXPECTED_DELTA, NEW_PARTS, U10_FOOTPRINT,
                              ValidationError, validate_netlists)


def move_pin(tree, ref, pin, target):
    nets = tree.getroot().find("nets")
    matches = [(net, node) for net in nets for node in net.findall("node")
               if node.get("ref") == ref and node.get("pin") == pin]
    assert len(matches) == 1
    net, node = matches[0]
    net.remove(node)
    if not net.findall("node"):
        nets.remove(net)
    new_net = next((net for net in nets if net.get("name") == target), None)
    if new_net is None:
        new_net = ET.SubElement(nets, "net", name=target, code=str(1000 + len(nets)))
    new_net.append(node)


def synthetic_candidate(baseline):
    """Build a contract fixture, not a claim that a real schematic is correct."""
    candidate = copy.deepcopy(baseline)
    root = candidate.getroot()
    for (ref, pin), (_, target) in EXPECTED_DELTA.items():
        move_pin(candidate, ref, pin, target)
    for ref, (value, pins) in NEW_PARTS.items():
        comp = ET.SubElement(root.find("components"), "comp", ref=ref)
        ET.SubElement(comp, "value").text = value
        ET.SubElement(comp, "footprint").text = U10_FOOTPRINT if ref == "U10" else "TEST:FixtureOnly"
        ET.SubElement(comp, "property", name="MPN", value=value)
        ET.SubElement(comp, "libsource", lib="fixture", part=ref)
        libpart = ET.SubElement(root.find("libparts"), "libpart", lib="fixture", part=ref)
        libpins = ET.SubElement(libpart, "pins")
        for pin, name in pins.items():
            ET.SubElement(libpins, "pin", num=pin, name=f"P{pin}", type="passive")
            net = next((net for net in root.find("nets") if net.get("name") == name), None)
            if net is None:
                net = ET.SubElement(root.find("nets"), "net", name=name, code=str(1000 + len(root.find("nets"))))
            ET.SubElement(net, "node", ref=ref, pin=pin, pintype="passive")
    return candidate


class CandidateVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = ET.parse(BASELINE / "netlist.xml")

    def setUp(self):
        self.candidate = synthetic_candidate(self.baseline)

    def validate(self):
        return validate_netlists(self.baseline, self.candidate)

    def test_exact_contract_fixture_passes(self):
        result = self.validate()
        self.assertEqual(len(result["existing_pin_deltas"]), 5)
        self.assertEqual(len(result["added_components"]), 12)
        self.assertEqual(result["added_physical_pins"], 37)
        self.assertEqual(result["preserved_existing_pin_memberships"], 356)

    def test_wrong_sensor_voltage_domain_rejected(self):
        move_pin(self.candidate, "U6", "8", "+3V3")
        with self.assertRaisesRegex(ValidationError, "five intended U6 pins"):
            self.validate()

    def test_dropped_original_pin_rejected(self):
        for net in self.candidate.getroot().find("nets"):
            for node in list(net):
                if node.get("ref") == "U1" and node.get("pin") == "1":
                    net.remove(node)
                    if not list(net):
                        self.candidate.getroot().find("nets").remove(net)
                    break
        with self.assertRaisesRegex(ValidationError, "Missing physical pin memberships"):
            self.validate()

    def test_unexpected_component_rejected(self):
        root = self.candidate.getroot()
        extra = copy.deepcopy(root.find("./components/comp[@ref='R39']"))
        extra.set("ref", "R99")
        root.find("components").append(extra)
        for pin, name in NEW_PARTS["R39"][1].items():
            net = next(net for net in root.find("nets") if net.get("name") == name)
            ET.SubElement(net, "node", ref="R99", pin=pin)
        with self.assertRaisesRegex(ValidationError, "Unexpected component set"):
            self.validate()

    def test_reversed_interrupt_translator_pin_rejected(self):
        move_pin(self.candidate, "U11", "3", "/IMU_INT")
        with self.assertRaisesRegex(ValidationError, "Wrong new pin net: U11.3"):
            self.validate()

    def test_duplicated_physical_pin_rejected(self):
        nets = self.candidate.getroot().find("nets")
        node = next(n for net in nets for n in net if n.get("ref") == "U10" and n.get("pin") == "2")
        next(net for net in nets if net.get("name") == "GND").append(copy.deepcopy(node))
        with self.assertRaisesRegex(ValidationError, "Duplicate physical pin membership"):
            self.validate()

    def test_original_part_swap_rejected(self):
        self.candidate.getroot().find("./components/comp[@ref='U6']/value").text = "DifferentIMU"
        with self.assertRaisesRegex(ValidationError, "Existing component identity"):
            self.validate()

    def test_unreviewed_generic_pca9306_footprint_rejected(self):
        self.candidate.getroot().find("./components/comp[@ref='U10']/footprint").text = "Package_SO:SSOP-8_2.95x2.8mm_P0.65mm"
        with self.assertRaisesRegex(ValidationError, "reviewed project-local DCT footprint"):
            self.validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
