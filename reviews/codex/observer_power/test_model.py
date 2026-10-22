"""Independent analytical fixtures and rejection tests for ACT-08."""
import copy
import json
import math
from pathlib import Path
import unittest

import model


def fixture():
    return {"native_accepted": False, "hardware_accepted": False, "parts_selected": False,
            "qualification_ports_implemented": False, "native_commands_rerun": False,
            "candidate_electrical_delta": 0, "live_electrical_delta": 0, "live_copper_delta": 0,
            "proposal": {
        "reference_V": [2.495, 2.505],
        "normal_rail_V": [3.219942244224422, 3.412002431724654],
        "bleeder_ohm": 2490, "resistor_fraction": .0035,
        "bias_abs_A": 5e-9, "reference_inputs": 2,
        "effective_C_F": [1e-7, 2.64e-7], "feed_cases_A": [0, 1e-5, 1e-4, 1e-3],
        "discharge_target_V": .3, "series_ohm": [1000, 10000],
        "input_C_allocated_F": 1e-11, "settle_fraction": .01,
        "sense_budget_ns": 100, "reference_spec_supply_max_V": 12,
        "load_regulation_ppm_per_mA": 30, "line_regulation_ppm_per_V": 15,
        "line_test_headroom_V": .05, "source_test_headroom_V": .5,
        "reference_total_fraction": .002, "initial_plus_BOX_fraction": .001490495,
    }}


class PowerModelTests(unittest.TestCase):
    def test_reference_load_fixture_and_KCL(self):
        result = model.calculate(fixture())["reference_load"]
        self.assertAlmostEqual(result["resistance_min_ohm"], 2481.285)
        self.assertAlmostEqual(result["resistance_max_ohm"], 2498.715)
        self.assertAlmostEqual(result["minimum_sourcing_A"], 2.495/2498.715-1e-8)
        self.assertAlmostEqual(result["maximum_sourcing_A"], 2.505/2481.285+1e-8)
        self.assertAlmostEqual(result["bleeder_power_max_W"], 6.275025/2481.285)
        self.assertAlmostEqual(result["source_test_min_supply_V"], 3.005)
        self.assertAlmostEqual(result["minimum_normal_rail_headroom_margin_V"], .214942244224422)

    def test_zero_feed_analytical_crossing(self):
        case = model.discharge_case(2, 0, 1000, 1e-6, .3)
        self.assertAlmostEqual(case["time_to_target_s"], .0018971199848858813)
        self.assertAlmostEqual(model.decay_voltage(2, 0, 1000, 1e-6, case["time_to_target_s"]), .3)

    def test_increasing_feed_and_unreachable_floor(self):
        cases = model.calculate(fixture())["discharge"]["cases"]
        times = [c["time_to_target_s"] for c in cases]
        self.assertTrue(0 < times[0] < times[1] < times[2])
        self.assertIsNone(times[3])
        self.assertFalse(cases[3]["target_reachable"])
        equal = model.discharge_case(2, .0003, 1000, 1e-6, .3)
        self.assertIsNone(equal["time_to_target_s"])
        case = model.discharge_case(2, .0001, 1000, 1e-6, .3)
        self.assertAlmostEqual(case["time_to_target_s"], .002251291798606495)
        json.dumps(cases, allow_nan=False)

    def test_decay_endpoints_and_rising_feed_case(self):
        self.assertEqual(model.decay_voltage(2, .0001, 1000, 1e-6, 0), 2)
        self.assertAlmostEqual(model.decay_voltage(2, .0001, 1000, 1e-6, 1), .1)
        self.assertGreater(model.decay_voltage(2, .003, 1000, 1e-6, .001), 2)
        self.assertIsNone(model.discharge_case(2, .003, 1000, 1e-6, .3)["time_to_target_s"])

    def test_series_current_bias_time_and_allocated_budget(self):
        cases = model.calculate(fixture())["series_input"]["cases"]
        low, high = cases
        self.assertAlmostEqual(low["ideal_zero_V_node_current_ceiling_A_per_input"], 2.505/996.5)
        self.assertAlmostEqual(low["steady_bias_error_V_per_input"], 5.0175e-6)
        self.assertAlmostEqual(low["settling_time_ns"], 46.21288281639050)
        self.assertAlmostEqual(high["settling_time_ns"], 462.1288281639050)
        self.assertTrue(low["fits_allocated_sense_budget_only"])
        self.assertFalse(high["fits_allocated_sense_budget_only"])
        self.assertAlmostEqual(low["ideal_zero_V_node_current_ceiling_A_per_input"],
                               10*high["ideal_zero_V_node_current_ceiling_A_per_input"])

    def test_capacitance_scales_time_not_current_or_floor(self):
        first = model.calculate(fixture())
        changed = fixture()
        changed["proposal"]["effective_C_F"] = [2e-7, 5.28e-7]
        changed["proposal"]["input_C_allocated_F"] *= 2
        second = model.calculate(changed)
        for a, b in zip(first["discharge"]["cases"], second["discharge"]["cases"]):
            self.assertEqual(a["floor_V"], b["floor_V"])
            if a["target_reachable"]:
                self.assertAlmostEqual(2*a["time_to_target_s"], b["time_to_target_s"])
        self.assertEqual(first["reference_load"], second["reference_load"])
        self.assertAlmostEqual(2*first["series_input"]["cases"][0]["settling_time_s"],
                               second["series_input"]["cases"][0]["settling_time_s"])

    def test_regulation_units_and_full_specified_line_span(self):
        result = model.calculate(fixture())["reference_allocation"]
        self.assertAlmostEqual(result["specified_line_span_V"], 9.455)
        self.assertAlmostEqual(result["line_regulation_fraction"], .000141825)
        expected_load = (2.505/2481.285+1e-8)*.03
        self.assertAlmostEqual(result["load_regulation_fraction"], expected_load)
        self.assertAlmostEqual(result["remaining_fraction"], .002-.001490495-.000141825-expected_load)
        changed = fixture()
        changed["proposal"]["reference_total_fraction"] = .001
        self.assertFalse(model.calculate(changed)["reference_allocation"]["positive_remaining_allocation_only"])

    def test_invalid_scalars_are_rejected(self):
        for key, values in {
            "bleeder_ohm": [0, -1, True, float("nan"), float("inf")],
            "resistor_fraction": [-.1, 1, float("nan")],
            "reference_inputs": [0, 1.5, True], "settle_fraction": [0, 1, -1],
            "sense_budget_ns": [0, -1], "bias_abs_A": [-1, float("inf")],
            "input_C_allocated_F": [0, -1], "line_test_headroom_V": [-1],
        }.items():
            for value in values:
                with self.subTest(key=key, value=value):
                    changed = fixture()
                    changed["proposal"][key] = value
                    with self.assertRaises(ValueError):
                        model.calculate(changed)

    def test_invalid_ranges_and_inconsistent_domains_are_rejected(self):
        for key, value in [
            ("reference_V", [3, 2]), ("reference_V", [2]),
            ("normal_rail_V", [0, 3]), ("effective_C_F", [0, 1e-6]),
            ("feed_cases_A", []), ("feed_cases_A", [-1]), ("series_ohm", [0]),
            ("reference_spec_supply_max_V", 2), ("discharge_target_V", 2.505),
            ("bias_abs_A", 1),
        ]:
            with self.subTest(key=key, value=value):
                changed = fixture()
                changed["proposal"][key] = value
                with self.assertRaises(ValueError):
                    model.calculate(changed)

    def test_input_annotations_cannot_promote_acceptance(self):
        original = fixture()
        baseline = model.calculate(original)
        for key in ("native_accepted", "hardware_accepted", "parts_selected",
                    "qualification_ports_implemented", "native_commands_rerun",
                    "native_implemented", "input_ports_qualified", "QUAL_OK_implemented", "ACK_implemented"):
            changed = copy.deepcopy(original)
            changed[key] = True
            with self.subTest(claim=key), self.assertRaises(ValueError):
                model.calculate(changed)
        for key in ("candidate_electrical_delta", "live_electrical_delta", "live_copper_delta"):
            for value in (1, True):
                changed = copy.deepcopy(original)
                changed[key] = value
                with self.subTest(delta=key, value=value), self.assertRaises(ValueError):
                    model.calculate(changed)
        for key in ("native_accepted", "candidate_electrical_delta"):
            changed = copy.deepcopy(original)
            del changed[key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                model.calculate(changed)
        changed = copy.deepcopy(original)
        changed["proposal"]["hardware_accepted"] = True
        changed["proposal"]["input_ports_qualified"] = True
        self.assertEqual(model.calculate(changed), baseline)
        flags = baseline["conditional_scope"]
        for name in ["native_implemented", "hardware_accepted", "input_ports_qualified",
                     "bias_applicability_qualified", "capacitance_bound_qualified",
                     "startup_shutdown_qualified"]:
            self.assertIs(flags[name], False)


if __name__ == "__main__":
    unittest.main()
