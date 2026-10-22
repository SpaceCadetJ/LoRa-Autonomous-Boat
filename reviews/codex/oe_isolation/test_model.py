"""Independent arithmetic and fail-closed scope checks for ACT-10."""
import copy
import json
import math
from pathlib import Path
import tempfile
import unittest

import model


class DecayScreenTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads((Path(__file__).parent / "contract.json").read_text(encoding="utf-8"))

    def test_one_time_constant_without_feed(self):
        # A unit RC falls from e volts to one volt in exactly one second.
        self.assertAlmostEqual(model.decay_time_s(1, 1, math.e, 1, 0), 1, places=14)

    def test_independent_half_remaining_voltage(self):
        # Floor is one volt; starting at five gives four above floor, target at
        # three gives two. Two seconds RC therefore takes 2*ln(2).
        self.assertAlmostEqual(model.decay_time_s(2, 1, 5, 3, .5), 2 * math.log(2), places=14)

    def test_exact_asymptote_and_above_never_reached(self):
        self.assertIsNone(model.decay_time_s(10, .1, 4, 1, .1))
        self.assertIsNone(model.decay_time_s(10, .1, 4, 1, .2))
        changed = copy.deepcopy(self.contract)
        changed["assumptions"]["feed_current_A_allocated"] = .001
        result = model.calculate(changed)
        self.assertIsNone(result["maximum_C_pF_at_zero_margin"])
        for case in result["cases"]:
            self.assertIsNone(case["decay_ns"])
            self.assertIsNone(case["slope_at_target_ns_per_V"])
            self.assertFalse(case["fits_allocation_only"])

    def test_monotonic_capacitance_and_positive_feed(self):
        ideal = model.decay_time_s(1000, 1e-9, 4, 1, 0)
        larger = model.decay_time_s(1000, 2e-9, 4, 1, 0)
        fed = model.decay_time_s(1000, 1e-9, 4, 1, .0005)
        self.assertAlmostEqual(larger, ideal * 2, places=18)
        self.assertGreater(fed, ideal)

    def test_screen_expected_pass_fail_split_and_floor(self):
        result = model.calculate(self.contract)
        self.assertEqual(result["R_max_ohm"], 10100)
        self.assertEqual(result["fixed_screen_ns"], 91)
        self.assertEqual(result["available_decay_ns"], 154)
        self.assertAlmostEqual(result["maximum_feed_A_at_asymptote"], .8 / 10100, places=18)
        self.assertEqual([case["fits_allocation_only"] for case in result["cases"]], [True, False, False, False, False])
        self.assertTrue(9 < result["maximum_C_pF_at_zero_margin"] < 10)
        for case in result["cases"]:
            self.assertAlmostEqual(case["floor_V"], .0505, places=14)
            self.assertAlmostEqual(case["downstream_screen_ns"] - case["decay_ns"], 91, places=12)
            self.assertAlmostEqual(case["margin_ns"] + case["downstream_screen_ns"], 245, places=12)

    def test_zero_margin_ceiling_matches_budget(self):
        result = model.calculate(self.contract)
        cap = result["maximum_C_pF_at_zero_margin"] * 1e-12
        # Direct substitution into voltage equation at the budget's remaining
        # 154 ns must land at 0.8 V, independently of model's log formula.
        voltage = .0505 + (3.6 - .0505) * math.exp(-154e-9 / (10100 * cap))
        self.assertAlmostEqual(voltage, .8, places=13)

    def test_local_slope_matches_differential_equation(self):
        for case in model.calculate(self.contract)["cases"]:
            dVdt = (5e-6 - .8 / 10100) / (case["C_pF"] * 1e-12)
            self.assertLess(dVdt, 0)
            self.assertAlmostEqual(case["slope_at_target_ns_per_V"], abs(1 / dVdt) * 1e9, places=11)

    def test_no_positive_capacitance_when_fixed_delays_exhaust_budget(self):
        changed = copy.deepcopy(self.contract)
        changed["assumptions"]["downstream_budget_ns_allocated"] = 90
        result = model.calculate(changed)
        self.assertIsNone(result["maximum_C_pF_at_zero_margin"])
        self.assertTrue(all(not case["fits_allocation_only"] for case in result["cases"]))

    def test_reject_invalid_physical_inputs(self):
        base = [10, .1, 4, 1, .01]
        for index in range(5):
            for invalid in (True, False, "1", None, float("nan"), float("inf"), -1):
                with self.subTest(index=index, invalid=invalid):
                    args = base.copy()
                    args[index] = invalid
                    with self.assertRaises(ValueError):
                        model.decay_time_s(*args)
        for index in range(4):
            args = base.copy()
            args[index] = 0
            with self.assertRaises(ValueError):
                model.decay_time_s(*args)
        with self.assertRaises(ValueError):
            model.decay_time_s(10, .1, 1, 1, 0)
        with self.assertRaises(ValueError):
            model.decay_time_s(10, .1, 1, 2, 0)

    def test_reject_bad_allocations_and_false_qualification_claims(self):
        for key in model.FALSE_CLAIMS + ("native_accepted", "hardware_accepted", "physical_OE_proven"):
            changed = copy.deepcopy(self.contract)
            changed[key] = True
            with self.subTest(key=key), self.assertRaises(ValueError):
                model.calculate(changed)
        for key in model.DELTAS:
            changed = copy.deepcopy(self.contract)
            changed[key] = 1
            with self.subTest(key=key), self.assertRaises(ValueError):
                model.calculate(changed)
        for key, bad in (("capacitance_pF_cases", []), ("capacitance_pF_cases", [0]),
                         ("downstream_budget_ns_allocated", 0), ("TXU_disable_ns_screen", -1),
                         ("control_to_switch_start_ns_screen", float("nan")),
                         ("other_logic_ns_optimistic", -1), ("R40_tolerance_fraction_allocated", 1)):
            changed = copy.deepcopy(self.contract)
            changed["assumptions"][key] = bad
            with self.subTest(key=key, bad=bad), self.assertRaises(ValueError):
                model.calculate(changed)

    def test_saved_hashes_reject_contract_and_model_drift(self):
        with tempfile.TemporaryDirectory() as folder:
            contract = Path(folder) / "contract.json"
            source = Path(folder) / "model.py"
            text = json.dumps(self.contract)
            contract.write_text(text, encoding="utf-8")
            source.write_text("# captured source\n", encoding="utf-8")
            record = model.collect(contract, source)
            model.check_record(record, contract, source)
            contract.write_text(text + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "stale"):
                model.check_record(record, contract, source)
            contract.write_text(text, encoding="utf-8")
            source.write_text("# changed source\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "stale"):
                model.check_record(record, contract, source)

    def test_output_qualification_flags_remain_false(self):
        result = model.calculate(self.contract)
        for key in model.FALSE_CLAIMS + ("native_accepted", "hardware_accepted", "physical_OE_proven"):
            self.assertIs(result[key], False)
        for key in model.DELTAS:
            self.assertEqual(result[key], 0)
        tampered = model.collect()
        tampered["physical_OE_proven"] = True
        with self.assertRaisesRegex(ValueError, "stale"):
            model.check_record(tampered)


if __name__ == "__main__":
    unittest.main()
