"""Independent analytical and missing-evidence checks for SENSE-01."""
import json
import math
import unittest
from fractions import Fraction

import model


class SensingModelTests(unittest.TestCase):
    def test_missing_actual_inputs_never_qualify_hardware(self):
        data = model.collect()
        self.assertTrue(all(value is None for value in data["unknown_actual_inputs"].values()))
        for result in data["actual"].values():
            self.assertEqual(result["status"], "unavailable")
            self.assertTrue(result["missing_fields"])
            self.assertFalse(result["hardware_accepted"])
        for key in ("hardware_accepted", "device_release_approved", "protection_qualified",
                    "native_commands_rerun"):
            self.assertIs(data[key], False)
        for key in ("candidate_electrical_delta", "live_electrical_delta", "live_copper_delta"):
            self.assertEqual(data[key], 0)
        self.assertIsNone(data["actual"]["voltage_range"]["strict_positive_arithmetic_margin"])
        self.assertIsNone(data["actual"]["current_transfer"]["validated_current_range_a"])

    def test_resistor_corners_match_exact_integer_ratios(self):
        result = model.divider(47000, 6800, .01, .01)
        # Independently constructed physical corners: 47k +/-470; 6.8k +/-68.
        self.assertAlmostEqual(result["ratio_min"], float(Fraction(6732, 47470 + 6732)))
        self.assertAlmostEqual(result["ratio_nominal"], float(Fraction(68, 538)))
        self.assertAlmostEqual(result["ratio_max"], float(Fraction(6868, 46530 + 6868)))
        self.assertAlmostEqual(result["inverse_nominal"], float(Fraction(538, 68)))
        self.assertLess(result["ratio_min"], result["ratio_nominal"])
        self.assertLess(result["ratio_nominal"], result["ratio_max"])
        zero = model.divider(47000, 6800, 0, 0)
        self.assertEqual(zero["ratio_min"], zero["ratio_max"])

    def test_voltage_reference_assumptions_change_the_margin(self):
        cases = model.collect()["voltage_cases"]
        by_inputs = {(r["inputs"]["vin_raw_max_v"], r["inputs"]["vdda_min_v"]): r for r in cases}
        r252 = by_inputs[25.2, 3.3]
        self.assertAlmostEqual(r252["adc_nominal_v"], 3.1851301115241633)
        self.assertAlmostEqual(r252["adc_max_v"], float(Fraction(252, 10) * Fraction(6868, 53398)))
        self.assertTrue(r252["strict_positive_arithmetic_margin"])
        self.assertFalse(by_inputs[25.2, 3.135]["strict_positive_arithmetic_margin"])
        self.assertFalse(by_inputs[26.0, 3.3]["strict_positive_arithmetic_margin"])
        self.assertFalse(by_inputs[26.0, 3.135]["strict_positive_arithmetic_margin"])
        self.assertTrue(all(not result["hardware_accepted"] for result in cases))

    def test_ceiling_equality_and_unknown_reference_are_not_positive(self):
        exact = model.range_headroom(24, 3, .125)
        self.assertEqual(exact["input_ceiling_v"], 24)
        self.assertEqual(exact["headroom_v"], 0)
        self.assertFalse(exact["strict_positive_arithmetic_margin"])
        unknown = model.range_headroom(24, None, .125)
        self.assertEqual(unknown["adc_max_v"], 3)
        self.assertIsNone(unknown["headroom_v"])
        self.assertIsNone(unknown["input_ceiling_v"])
        self.assertIsNone(unknown["strict_positive_arithmetic_margin"])
        ratio = model.collect()["divider"]["ratio_max"]
        self.assertAlmostEqual(model.range_headroom(None, 3.3, ratio)["input_ceiling_v"],
                               float(Fraction(33, 10) * Fraction(53398, 6868)))

    def test_filter_against_equal_resistors_and_captured_nominal(self):
        equal = model.divider_filter(1000, 1000, 1e-6)
        self.assertEqual(equal["rth_ohm"], 500)
        self.assertEqual(equal["tau_s"], .0005)
        self.assertAlmostEqual(equal["fc_hz"], 318.3098861837907)
        captured = model.collect()["divider_filter_nominal"]
        self.assertAlmostEqual(captured["rth_ohm"], 5940.520446096654)
        self.assertAlmostEqual(captured["tau_s"], .0005940520446096654)
        self.assertAlmostEqual(captured["fc_hz"], 267.91414074918555)

    def test_full_step_settling_has_required_residual(self):
        result = model.settling_to_quarter_lsb(.001, 3.3, 3.3, 12)
        self.assertEqual(result["quarter_lsb_v"], 3.3 / 16384)
        residual = 3.3 * math.exp(-result["settling_time_s"] / .001)
        self.assertAlmostEqual(residual, result["quarter_lsb_v"], places=15)
        self.assertGreater(3.3 * math.exp(-(result["settling_time_s"] - 1e-6) / .001),
                           result["quarter_lsb_v"])
        halved = model.settling_to_quarter_lsb(.001, 1.65, 3.3, 12)
        self.assertAlmostEqual(result["settling_time_s"] - halved["settling_time_s"], .001 * math.log(2))

    def test_small_zero_and_negative_steps(self):
        for step in (0, 3.3 / 32768, 3.3 / 16384):
            self.assertEqual(model.settling_to_quarter_lsb(.001, step, 3.3, 12)["settling_time_s"], 0)
        positive = model.settling_to_quarter_lsb(.001, 1, 3.3, 12)
        negative = model.settling_to_quarter_lsb(.001, -1, 3.3, 12)
        self.assertEqual(positive["settling_time_s"], negative["settling_time_s"])
        self.assertEqual(model.settling_to_quarter_lsb(.001, 1, None, 12)["status"], "unavailable")

    def test_adc_expression_floor_and_clock_scaling(self):
        ideal = model.adc_resistive_acquisition(30e6, 0, 0, 7e-12, 12)
        self.assertEqual(ideal["k_min_cycles"], .5)
        known = model.adc_resistive_acquisition(1e6, 1000, 0, 1e-9, 2)
        self.assertAlmostEqual(known["k_min_cycles"], .5 + math.log(16))
        double_clock = model.adc_resistive_acquisition(2e6, 1000, 0, 1e-9, 2)
        self.assertAlmostEqual(double_clock["k_min_cycles"] - .5, 2 * (known["k_min_cycles"] - .5))
        captured = model.collect()["adc_illustration"]
        self.assertGreater(captured["k_min_cycles"], 24)
        self.assertLess(captured["k_min_cycles"], 25)
        self.assertTrue(captured["illustrative_only"])
        self.assertFalse(captured["external_capacitance_modeled"])
        self.assertFalse(captured["acquisition_qualified"])
        self.assertIsNone(captured["actual_sample_cycles"])

    def test_shunt_nominal_transfer_and_loss_are_not_ratings(self):
        result = model.nominal_shunt(3, .02, 20)
        self.assertEqual(result["ideal_transfer_v_per_a"], .4)
        self.assertAlmostEqual(result["ideal_output_v"], 1.2)
        self.assertEqual(result["shunt_drop_v"], .06)
        self.assertEqual(result["shunt_loss_w"], .18)
        self.assertIsNone(result["validated_current_range_a"])
        self.assertFalse(result["values_are_device_ratings"])
        self.assertFalse(result["output_swing_qualified"])
        zero = model.nominal_shunt(0, .02, 20)
        self.assertEqual(zero["ideal_output_v"], 0)
        self.assertEqual(zero["shunt_loss_w"], 0)
        self.assertEqual(model.nominal_shunt(6, .02, 20)["shunt_loss_w"], 4 * result["shunt_loss_w"])

    def test_bad_values_rejected_even_with_an_unknown_peer(self):
        for bad in (math.nan, math.inf, -math.inf, True, "3.3", 10 ** 1000):
            with self.subTest(type=type(bad).__name__):
                with self.assertRaises(ValueError):
                    model.range_headroom(None, bad, .1)
                with self.assertRaises(ValueError):
                    model.nominal_shunt(None, bad, 20)
        with self.assertRaises(ValueError):
            model.adc_resistive_acquisition(None, -1, 6000, 7e-12, 12)

    def test_domains_and_bit_counts_rejected(self):
        for tolerance in (-.01, 1, 1.1):
            with self.assertRaises(ValueError):
                model.divider(47000, 6800, tolerance, .01)
        for bits in (0, 33, 12.0, True, "12"):
            with self.assertRaises(ValueError):
                model.settling_to_quarter_lsb(.001, 3.3, 3.3, bits)
        for bad in (0, -1):
            with self.assertRaises(ValueError):
                model.divider_filter(47000, 6800, bad)
            with self.assertRaises(ValueError):
                model.range_headroom(25.2, bad, .1)
        with self.assertRaises(ValueError):
            model.range_headroom(25.2, 3.3, 1.1)
        with self.assertRaises(ValueError):
            model.nominal_shunt(-1, .02, 20)

    def test_collection_is_json_ready_independent_and_keeps_current_rc_unknown(self):
        first, second = model.collect(), model.collect()
        self.assertEqual(first, second)
        self.assertEqual(json.loads(json.dumps(first, allow_nan=False)), first)
        first["unknown_actual_inputs"]["vdda_min_v"] = 3.3
        self.assertIsNone(second["unknown_actual_inputs"]["vdda_min_v"])
        topology = second["captured_topology"]
        self.assertFalse(topology["current_output_series_resistor_present"])
        self.assertIsNone(topology["current_channel_passive_rc_cutoff_hz"])
        self.assertIn("post-D12", topology["voltage_boundary"])
        self.assertIn("converter-input", topology["current_boundary"])


if __name__ == "__main__":
    unittest.main()
