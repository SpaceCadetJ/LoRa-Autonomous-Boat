"""Numerical and rejection tests for the selected cell; no hardware acceptance."""
import importlib.util
import json
import math
from pathlib import Path
import sys
import unittest
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("buck5_model", Path(__file__).with_name("model.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class ModelTests(unittest.TestCase):
    def test_actual_pwm_reference_and_leakage_bounds(self):
        x = m.feedback_corners()
        self.assertAlmostEqual(x["typical_pwm_v"], 5.046160642570281)
        self.assertAlmostEqual(x["initial_reference_resistor_lower_v"], 4.8723632351186925)
        self.assertAlmostEqual(x["initial_reference_resistor_upper_v"], 5.1838492150419855)
        self.assertAlmostEqual(x["conservative_leakage_output_shift_v"], .00606)
        self.assertAlmostEqual(x["initial_pwm_lower_including_leakage_v"], 4.866303235118692)
        self.assertAlmostEqual(x["initial_pwm_upper_including_leakage_v"], 5.189909215041986)
        self.assertIsNone(x["guaranteed_pfm_upper_v"])
        exact_ratio = m.feedback_corners(1, 1, tolerance=0, leakage_a=0)
        self.assertEqual(exact_ratio["typical_pwm_v"], 2.012)
        self.assertEqual(exact_ratio["initial_reference_resistor_lower_v"], 1.974)

    def test_selected_high_input_current_screen(self):
        x = m.converter_screen(44, vout_v=5, inductance_h=8e-6, frequency_hz=440000)
        self.assertAlmostEqual(x["ripple_pp_a"], 1.259039256198347)
        self.assertAlmostEqual(x["peak_a"], 2.6295196280991737)
        self.assertAlmostEqual(x["valley_a"], 1.3704803719008265)
        self.assertAlmostEqual(x["rms_a"]**2, 4+x["ripple_pp_a"]**2/12)
        self.assertAlmostEqual(x["dcr_loss_w_25c"], .12321917192389151)
        self.assertAlmostEqual(x["peak_margin_to_ihs_min_4p35a"], 4.35-x["peak_a"])
        self.assertAlmostEqual(x["valley_margin_to_ils_min_3p4a"], 3.4-x["valley_a"])

    def test_limiting_zero_ripple_and_non_ccm_conditions(self):
        x = m.converter_screen(5, vout_v=5)
        self.assertEqual(x["ripple_pp_a"], 0)
        self.assertEqual(x["rms_a"], 2)
        self.assertEqual(x["ideal_off_time_s"], 0)
        self.assertFalse(x["off_time_exceeds_130ns_maximum_comparison"])
        self.assertFalse(x["hardware_accepted"])
        low = m.converter_screen(44, output_current_a=0)
        self.assertFalse(low["ideal_ccm_condition_met"])
        self.assertIsNone(low["peak_margin_to_ihs_min_4p35a"])
        self.assertIsNone(low["valley_margin_to_ils_min_3p4a"])

    def test_lmr36520_no_inductance_interval_without_claiming_every_part_fails(self):
        x = m.lmr36520_exclusion()
        self.assertAlmostEqual(x["required_low_input_ripple_at_2a_a"], .4)
        self.assertAlmostEqual(x["allowed_high_input_ripple_at_2a_a"], .8)
        self.assertGreater(x["l_nominal_min_from_peak_h"], x["l_nominal_max_from_valley_h"])
        self.assertAlmostEqual(x["best_ideal_common_load_ceiling_a"], 1.8822392230519034)
        self.assertFalse(x["fixed_l_satisfies_both_screens"])
        self.assertFalse(x["every_physical_device_failure_proven"])

    def test_feed_conserves_power_and_uses_lower_current_root(self):
        x = m.feed_budget()
        self.assertTrue(x["dc_source_solution_exists"])
        self.assertAlmostEqual(x["source_power_w"], x["converter_input_power_w_assumed"]+x["diode_loss_w_fit"]+x["ohmic_loss_w_nominal"])
        self.assertAlmostEqual(x["source_current_a"]*x["converter_input_v_assumed"], x["converter_input_power_w_assumed"])
        self.assertLess(x["source_current_a"], (7-.6)/(2*(.027+.0367+.02)))
        self.assertGreater(x["source_current_a"], 2)
        self.assertFalse(x["within_feed_goal_arithmetic"])
        self.assertFalse(x["below_fuse_25c_1p5a_derating_screen"])

    def test_lossless_feed_limit_and_infeasible_source(self):
        ideal = m.feed_budget(efficiency_3v3=1, efficiency_5v=1, diode_v0=0,
                              diode_r_ohm=0, fuse_r_ohm=0, shunt_r_ohm=0)
        self.assertAlmostEqual(ideal["source_current_a"], 13.96/7)
        self.assertEqual(ideal["diode_loss_w_fit"], 0)
        self.assertEqual(ideal["ohmic_loss_w_nominal"], 0)
        failed = m.feed_budget(rail5_current_a=200)
        self.assertFalse(failed["dc_source_solution_exists"])
        self.assertIsNone(failed["source_current_a"])
        self.assertFalse(failed["within_feed_goal_arithmetic"])

    def test_feed_loss_monotonicity_and_auxiliary_load_accounting(self):
        base = m.feed_budget()
        wire = m.feed_budget(harness_r_ohm=.1)
        worse = m.feed_budget(efficiency_5v=.7)
        self.assertGreater(wire["source_current_a"], base["source_current_a"])
        self.assertGreater(worse["source_current_a"], base["source_current_a"])
        external = m.feed_budget(rail5_current_a=.02)
        self.assertLess(external["source_current_a"], 1)
        available_total = external["max_total_5v_current_at_feed_goal_a_assumed"]
        self.assertLess(available_total, .378)
        at_goal = m.feed_budget(rail5_current_a=available_total)
        self.assertAlmostEqual(at_goal["source_current_a"], 1)
        self.assertGreater(m.feed_budget(rail5_current_a=2.02)["source_current_a"], base["source_current_a"])

    def test_source_capacity_does_not_fall_when_current_ceiling_exceeds_power_peak(self):
        capacities = [m.feed_budget(feed_goal_a=i)["max_total_5v_current_at_feed_goal_a_assumed"] for i in (1, 10, 40, 100)]
        self.assertEqual(capacities, sorted(capacities))
        self.assertEqual(capacities[-1], capacities[-2])

    def test_corners_capacitance_and_qualification_remain_distinct(self):
        x = m.study()
        self.assertEqual(x["initial_corner_envelope"]["corner_count"], 24)
        self.assertEqual(len(x["operating_cases"]), 6)
        self.assertEqual(len(x["source_feed_cases"]), 6)
        self.assertEqual(x["capacitance"]["output_initial_tolerance_only_lower_uf"], 88)
        self.assertLess(88, x["capacitance"]["ti_typical_output_reference_uf"])
        self.assertIsNone(x["capacitance"]["output_effective_lower_bound_uf"])
        self.assertIsNone(x["capacitance"]["local_input_effective_requirement_uf"])
        self.assertFalse(any(x["acceptance_gates"].values()))
        self.assertEqual(json.loads(json.dumps(x, allow_nan=False)), m.study())

    def test_invalid_parameters_rejected(self):
        for bad in (float("nan"), float("inf"), -1, True, "5"):
            for key in ("vin_v", "vout_v", "output_current_a", "inductance_h", "frequency_hz", "dcr_ohm"):
                with self.subTest(key=key, bad=bad), self.assertRaises(ValueError):
                    m.converter_screen(**{"vin_v": 44, key: bad})
            for key in ("battery_v", "logic_current_a", "rail5_current_a", "efficiency_3v3", "diode_v0", "harness_r_ohm", "feed_goal_a"):
                with self.subTest(key=key, bad=bad), self.assertRaises(ValueError): m.feed_budget(**{key: bad})
            with self.assertRaises(ValueError): m.feedback_corners(tolerance=bad)
        for args in ({"vin_v": 4}, {"vin_v": 44, "frequency_hz": 0}, {"vin_v": 44, "inductance_h": 0},
                     {"vin_v": 44, "inductance_h": 1e-300, "frequency_hz": 1e-300}):
            with self.assertRaises(ValueError): m.converter_screen(**args)
        for args in ({"efficiency_5v": 0}, {"efficiency_3v3": 1.01}, {"battery_v": .5}, {"battery_v": 1e308}):
            with self.assertRaises(ValueError): m.feed_budget(**args)
        for args in ({"tolerance": 1}, {"bottom_ohm": 0}, {"top_ohm": 1e308, "bottom_ohm": 1e-300}):
            with self.assertRaises(ValueError): m.feedback_corners(**args)

if __name__ == "__main__":
    unittest.main(verbosity=2)
