"""Executable regressions for ACT-12 topology and conditional allocations."""
import copy
from decimal import Decimal
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

import model

ROOT = Path(__file__).resolve().parents[3]


class ConnectorFaultContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.native = ET.parse(ROOT / model.SOURCE_PATHS[0]).getroot()

    def test_native_connections_and_values(self):
        result = model.verify_topology(self.native)
        self.assertEqual(result["driver_VCCB"]["net"], "/Power/+5V_BUCK")
        self.assertEqual([c["supply_net"] for c in result["channels"]], ["/BEC_IN", "VSERVO"])
        self.assertEqual(result["signal_net_memberships"]["/Actuators/ESC_SIG"],
                         ["D10.1", "J2.1", "R10.2", "R11.1"])
        self.assertEqual(len(result["checked_pin_nets"]), 30)

    def test_pin_net_drift_rejected(self):
        for pin in ("J2.2", "J3.3", "U4.7", "R11.2", "D10.1", "U1.37", "U1.41"):
            with self.subTest(pin=pin):
                native = copy.deepcopy(self.native)
                ref, number = pin.split(".")
                node = next(n for n in native.findall("./nets/net/node")
                            if n.attrib["ref"] == ref and n.attrib["pin"] == number)
                node.attrib["pin"] = "999"
                with self.assertRaises(ValueError):
                    model.verify_topology(native)

    def test_signal_branch_or_duplicate_pin_rejected(self):
        for ref, pin in (("NEW", "1"), ("J2", "1")):
            native = copy.deepcopy(self.native)
            net = next(n for n in native.findall("./nets/net")
                       if n.attrib["name"] == "/Actuators/ESC_SIG")
            ET.SubElement(net, "node", {"ref": ref, "pin": pin})
            with self.assertRaises(ValueError):
                model.verify_topology(native)

    def test_component_value_drift_rejected(self):
        for ref in ("R10", "R11", "D11", "U4", "C14"):
            native = copy.deepcopy(self.native)
            comp = next(c for c in native.findall("./components/comp") if c.attrib["ref"] == ref)
            comp.find("value").text = "unexpected"
            with self.assertRaises(ValueError):
                model.verify_topology(native)

    def test_arithmetic_against_independent_decimal_calculation(self):
        data = model.collect(ROOT)
        self.assertEqual(data["timing"]["total_budget_ns"], 400)
        inputs = (("UV", Decimal("3.0719380026289804") - Decimal("3.005")),
                  ("OV", Decimal("3.6") - Decimal("3.56404020970936")))
        for label, headroom in inputs:
            row = data["timing"][label]
            self.assertAlmostEqual(row["maximum_slew_V_per_us"], float(headroom / Decimal("0.4")), places=14)
            for case in row["cases"]:
                expected = headroom - Decimal(str(case["slew_V_per_us"])) * Decimal("0.4")
                self.assertAlmostEqual(case["residual_V"], float(expected), places=14)
        self.assertTrue(data["timing"]["UV"]["cases"][1]["conditional_margin_positive"])
        self.assertFalse(data["timing"]["OV"]["cases"][1]["conditional_margin_positive"])

    def test_zero_margin_and_faster_slew_never_pass(self):
        for headroom in (0.06693800262898053, 0.035959790290640115):
            ceiling = headroom / 0.4
            self.assertFalse(model.timing_case(headroom, 400, ceiling)["conditional_margin_positive"])
            self.assertFalse(model.timing_case(headroom, 400, ceiling * 1.01)["conditional_margin_positive"])
            self.assertTrue(model.timing_case(headroom, 400, ceiling * 0.99)["conditional_margin_positive"])

    def test_invalid_timing_inputs_rejected(self):
        for args in ((0, 400, 0.1), (0.1, 0, 0.1), (0.1, 400, -1),
                     (float("nan"), 400, 0.1), (0.1, float("inf"), 0.1), (0.1, 400, True)):
            with self.assertRaises(ValueError):
                model.timing_case(*args)

    def test_all_required_fields_remain_required(self):
        fields = model.MEASUREMENT_FIELDS
        self.assertIsInstance(fields, tuple)
        self.assertEqual(len(fields), 10)
        self.assertEqual(model.missing_evidence({}), list(fields))
        populated = {field: {"source": "reviewable record"} for field in fields}
        self.assertEqual(model.missing_evidence(populated), [])
        populated[fields[0]] = {"minimum": 0, "source": "reviewable record"}
        self.assertEqual(model.missing_evidence(populated), [])
        for field in fields:
            for empty in (None, "", "  ", {}, [], "UNRESOLVED", {"status": "pending"}, [None],
                          False, True, float("nan"), float("inf"), float("-inf"),
                          {"limit": float("nan")}, {"status": False}):
                profile = dict(populated)
                profile[field] = empty
                self.assertEqual(model.missing_evidence(profile), [field])
            profile = dict(populated)
            del profile[field]
            profile["optional_notes"] = "Evidence cannot replace the missing field"
            self.assertEqual(model.missing_evidence(profile), [field])

    def test_results_cannot_approve_hardware_or_receiver(self):
        data = model.collect(ROOT)
        for key in ("hardware_accepted", "native_accepted", "native_commands_rerun",
                    "timing_qualified", "receiver_contract_closed"):
            self.assertIs(data[key], False)
        for key in ("candidate_electrical_delta", "live_electrical_delta", "live_copper_delta"):
            self.assertEqual(data[key], 0)
        self.assertIs(data["evidence_gate"]["hardware_accepted"], False)
        self.assertIs(data["timing"]["allocation_is_system_stop_deadline"], False)
        for key in ("receiver_input_low_proven", "pulse_rejection_proven", "actuator_stop_time_known"):
            self.assertIs(data["topology"][key], False)


if __name__ == "__main__":
    unittest.main()
