"""Independent numeric, limiting-case and rejection checks; no qualification artifacts."""
import importlib.util
import json
import math
from pathlib import Path
import sys
import unittest
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("buck33_model", Path(__file__).with_name("model.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class ModelTests(unittest.TestCase):
    def test_feedback_extreme_resistor_polarities_and_reference(self):
        x = m.feedback_corners()
        self.assertAlmostEqual(x["nominal_v"], 3.314814814814815)
        self.assertAlmostEqual(x["lower_v"], 3.219942244224422)
        self.assertAlmostEqual(x["upper_v"], 3.412002431724)
        self.assertFalse(x["tcr_aging_leakage_and_dynamic_regulation_included"])
        exact = m.feedback_corners(1, 1, 0, 1, 1, 1)
        self.assertEqual([exact[k] for k in ("lower_v", "nominal_v", "upper_v")], [2, 2, 2])

    def test_unity_duty_zero_ripple_is_not_regulation_proof(self):
        x = m.buck_screen(3.3)
        self.assertEqual(x["ripple_pp_a"], 0)
        self.assertEqual(x["rms_a"], 1.2)
        self.assertAlmostEqual(x["dcr_loss_w_25c"], .0429408)
        self.assertEqual(x["ideal_off_time_s"], 0)
        self.assertFalse(x["off_time_exceeds_102ns_maximum_comparison"])
        self.assertFalse(x["fixed_frequency_proven"])

    def test_ripple_corner_scaling_and_rms(self):
        x = m.buck_screen(44, inductance_h=8e-6, frequency_hz=340000)
        self.assertAlmostEqual(x["ripple_pp_a"], 1.1222426470588234)
        self.assertAlmostEqual(x["peak_a"], 1.7611213235294116)
        self.assertAlmostEqual(x["rms_a"]**2, 1.2**2 + x["ripple_pp_a"]**2/12)
        self.assertGreater(x["dcr_loss_w_25c"], 1.2**2 * .02982)
        y = m.buck_screen(44, inductance_h=16e-6, frequency_hz=340000)
        self.assertAlmostEqual(y["ripple_pp_a"], x["ripple_pp_a"]/2)
        self.assertEqual(m.buck_screen(44, dcr_ohm=0)["dcr_loss_w_25c"], 0)

    def test_valley_and_peak_limits_are_distinct_and_max_is_not_safe_limit(self):
        x = m.buck_screen(44, output_current_a=1.7, inductance_h=8e-6, frequency_hz=340000)
        self.assertGreater(x["peak_a"], 1.8)
        self.assertTrue(x["valley_below_ilimit_min_1p8a_screen"])
        self.assertTrue(x["peak_below_isc_min_2p4a_screen"])
        overloaded = m.buck_screen(44, output_current_a=2.4, inductance_h=8e-6, frequency_hz=340000)
        self.assertFalse(overloaded["valley_below_ilimit_min_1p8a_screen"])
        self.assertFalse(overloaded["peak_below_isc_min_2p4a_screen"])
        self.assertTrue(overloaded["peak_below_isc_max_3p6a_comparison"])
        self.assertFalse(overloaded["hardware_accepted"])

    def test_light_load_has_no_ccm_current_limit_acceptance(self):
        for load in (0, .1):
            x = m.buck_screen(44, output_current_a=load)
            self.assertFalse(x["ideal_ccm_condition_met"])
            self.assertIsNone(x["valley_below_ilimit_min_1p8a_screen"])
            self.assertIsNone(x["peak_below_isc_min_2p4a_screen"])

    def test_timing_nominal_value_and_capacitor_rating_do_not_clear_gates(self):
        s = m.study()
        self.assertEqual(len(s["operating_cases"]), 6)
        self.assertIsNone(s["timing_corner"]["minimum_on_time_maximum_s"])
        self.assertAlmostEqual(s["timing_corner"]["shortest_on_time_screen"]["ideal_on_time_s"], 159.0880555446849e-9, delta=1e-15)
        self.assertIsNone(s["capacitance"]["output_effective_lower_bound_uf"])
        self.assertEqual(s["capacitance"]["output_rated_sum_uf"], 66)
        self.assertFalse(any(s["acceptance_gates"].values()))
        self.assertFalse(s["hardware_accepted"])
        self.assertFalse(s["headroom"]["pack_uvlo_implemented"])
        self.assertFalse(s["headroom"]["clamp_voltage_verified"])
        self.assertAlmostEqual(s["headroom"]["gross_voltage_budget_before_feed_losses_v"], 2.8)
        self.assertEqual(json.loads(json.dumps(s, allow_nan=False)), m.study())

    def test_initial_inductance_and_typical_saturation_are_not_hot_bounds(self):
        x = m.study()["inductor"]
        self.assertAlmostEqual(x["eq5_min_h_at_3p3v_340khz"], 4.076470588235294e-6, delta=1e-15)
        self.assertGreater(x["eq5_min_h_at_feedback_upper_340khz"], x["eq5_min_h_at_3p3v_340khz"])
        self.assertAlmostEqual(x["typical_isat_minus_isc_max_a"], 4)
        self.assertFalse(x["hot_saturation_bound_verified"])
        self.assertFalse(x["dc_bias_and_temperature_inductance_bound_verified"])

    def test_invalid_and_numerically_unusable_inputs_rejected(self):
        for bad in (float("nan"), float("inf"), -1, True, "10"):
            for key in ("vin_v", "vout_v", "output_current_a", "inductance_h", "frequency_hz", "dcr_ohm"):
                args = {"vin_v": 25.2, key: bad}
                with self.subTest(key=key, bad=bad), self.assertRaises(ValueError): m.buck_screen(**args)
            with self.assertRaises(ValueError): m.feedback_corners(resistor_tolerance=bad)
        for key in ("vin_v", "vout_v", "inductance_h", "frequency_hz"):
            with self.assertRaises(ValueError): m.buck_screen(**{"vin_v": 25.2, key: 0})
        for args in ({"vin_v": 2}, {"vin_v": 44, "inductance_h": 1e-300, "frequency_hz": 1e-300},
                     {"vin_v": 44, "output_current_a": 1e308}):
            with self.assertRaises(ValueError): m.buck_screen(**args)
        for args in ({"resistor_tolerance": 1}, {"bottom_ohm": 0}, {"vref_min_v": 2},
                     {"top_ohm": 1e308, "bottom_ohm": 1e-300}):
            with self.assertRaises(ValueError): m.feedback_corners(**args)

if __name__ == "__main__":
    unittest.main(verbosity=2)
