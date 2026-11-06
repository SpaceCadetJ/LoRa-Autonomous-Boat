"""Independent analytical and rejection checks for the proposed shunt bounds."""
import math
import unittest

import model


class ShuntModelTests(unittest.TestCase):
    def test_actual_values_remain_missing_and_no_release(self):
        data = model.collect()
        for result in data["actual"].values():
            self.assertEqual(result["status"], "unavailable")
            self.assertTrue(result["missing_fields"])
            self.assertTrue(all(value is None for value in result["inputs"].values()))
            self.assertFalse(result["hardware_accepted"])
            self.assertFalse(result["device_release_approved"])
            self.assertTrue(result["necessary_arithmetic_only"])
        for key in ("hardware_accepted", "device_release_approved", "parts_selected",
                    "native_commands_rerun", "protection_qualified", "fabrication_approved"):
            self.assertIs(data[key], False)
        for key in ("candidate_electrical_delta", "live_electrical_delta", "live_copper_delta"):
            self.assertEqual(data[key], 0)

    def test_partial_unknown_does_not_hide_bad_input(self):
        self.assertEqual(model.window(None, 5.1, 5.15, 5.25, 5.3, .04, .1, 5.5)["status"], "unavailable")
        with self.assertRaises(ValueError):
            model.window(None, 5.1, 5.15, 5.25, 5.3, -.04, .1, 5.5)
        with self.assertRaises(ValueError):
            model.resistance_window(None, .5, 5.5, 1, .2, .1, .05)
        with self.assertRaises(ValueError):
            model.branch_bound(None, 1, 0, .1, 5.1, 5.5, .5)

    def test_nonfinite_nonnumeric_and_bool_rejected(self):
        for bad in (math.nan, math.inf, -math.inf, True, "5", 10**1000):
            with self.subTest(bad=type(bad).__name__):
                with self.assertRaises(ValueError):
                    model.window(bad, 5.1, 5.15, 5.25, 5.3, .04, .1, 5.5)
                with self.assertRaises(ValueError):
                    model.branch_bound(8.2, .05, 0, .1, 5.1, bad, .5)

    def test_threshold_domains_and_order_rejected(self):
        base = [5, 5.1, 5.15, 5.25, 5.3, .04, .1, 5.5]
        for index in (0, 1, 2, 3, 4, 7):
            bad = base.copy()
            bad[index] = 0
            with self.assertRaises(ValueError):
                model.window(*bad)
        with self.assertRaises(ValueError):
            model.window(5, 5.2, 5.1, 5.25, 5.3, .04, .1, 5.5)
        with self.assertRaises(ValueError):
            model.window(5, 5.1, 5.15, 5.4, 5.3, .04, .1, 5.5)

    def test_tolerance_ron_and_branch_domains_rejected(self):
        for tolerance in (-.01, 1, 1.01):
            with self.assertRaises(ValueError):
                model.resistance_window(5.1, .5, 5.5, 1, 0, .1, tolerance)
        for rnom, i, rmin, rmax in ((0, .5, 0, .1), (-1, .5, 0, .1), (8.2, 0, 0, .1), (8.2, .5, -.1, .1), (8.2, .5, .2, .1)):
            with self.assertRaises(ValueError):
                model.branch_bound(rnom, .05, rmin, rmax, 5.1, 5.5, i)
        with self.assertRaises(ValueError):
            model.resistance_window(5.6, .5, 5.5, 1, 0, .1, .05)
        with self.assertRaises(ValueError):
            model.resistance_window(5.1, .5, 5.5, 0, 0, .1, .05)

    def test_illustrative_margins_match_independent_decimal_values(self):
        result = model.window(5, 5.1, 5.15, 5.25, 5.3, .04, .1, 5.5)
        self.assertEqual(result["release_margin_V"], .1)
        self.assertEqual(result["hysteresis_margin_V"], .06)
        self.assertEqual(result["protection_margin_V"], .1)
        self.assertTrue(result["strict_positive_arithmetic_margin"])

    def test_written_equality_never_becomes_positive_margin(self):
        cases = ((5.1, 5.1, 5.15, 5.25, 5.3, .04, .1, 5.5),
                 (5, 5.1, 5.15, 5.25, 5.3, .1, .1, 5.5),
                 (5, 5.1, 5.15, 5.25, 5.3, .04, .2, 5.5))
        for args, field in zip(cases, ("release_margin_V", "hysteresis_margin_V", "protection_margin_V")):
            result = model.window(*args)
            self.assertEqual(result[field], 0)
            self.assertFalse(result["strict_positive_arithmetic_margin"])

    def test_margin_monotonicity(self):
        base = model.window(5, 5.1, 5.15, 5.25, 5.3, .04, .1, 5.5)
        worse = model.window(5.05, 5.1, 5.15, 5.25, 5.3, .05, .15, 5.5)
        for field in ("release_margin_V", "hysteresis_margin_V", "protection_margin_V"):
            self.assertLess(worse[field], base[field])

    def test_resistance_interval_matches_rational_bounds(self):
        result = model.resistance_window(5.1, .5, 5.5, 1, 0, .1, .05)
        self.assertAlmostEqual(result["nominal_lower_exclusive_ohm"], 110 / 19)
        self.assertAlmostEqual(result["nominal_upper_exclusive_ohm"], 202 / 21)
        self.assertTrue(result["strict_positive_nominal_interval"])
        self.assertGreater(8.2, result["nominal_lower_exclusive_ohm"])
        self.assertLess(8.2, result["nominal_upper_exclusive_ohm"])

    def test_stressed_and_equal_intervals_fail_strict_test(self):
        stressed = model.resistance_window(5.1, 1, 5.5, 1, 0, .1, .05)
        self.assertLess(stressed["nominal_interval_width_ohm"], 0)
        self.assertFalse(stressed["strict_positive_nominal_interval"])
        equal = model.resistance_window(5, 1, 5, 1, 0, 0, 0)
        self.assertEqual(equal["nominal_interval_width_ohm"], 0)
        self.assertFalse(equal["strict_positive_nominal_interval"])

    def test_lower_bound_clamped_to_zero_and_negative_upper_retained(self):
        clamped = model.resistance_window(5, .1, 5.5, 1, 6, 7, 0)
        self.assertEqual(clamped["nominal_lower_exclusive_ohm"], 0)
        self.assertTrue(clamped["strict_positive_nominal_interval"])
        negative = model.resistance_window(5, 1, 5.5, 1, 0, 6, 0)
        self.assertLess(negative["nominal_upper_exclusive_ohm"], 0)
        self.assertFalse(negative["strict_positive_nominal_interval"])

    def test_tolerance_narrows_interval(self):
        exact = model.resistance_window(5.1, .5, 5.5, 1, 0, .1, 0)
        loose = model.resistance_window(5.1, .5, 5.5, 1, 0, .1, .1)
        self.assertGreater(loose["nominal_lower_exclusive_ohm"], exact["nominal_lower_exclusive_ohm"])
        self.assertLess(loose["nominal_upper_exclusive_ohm"], exact["nominal_upper_exclusive_ohm"])

    def test_branch_values_and_exact_current_equality(self):
        result = model.branch_bound(8.2, .05, 0, .1, 5.1, 5.5, .5)
        self.assertAlmostEqual(result["sink_current_min_A"], 510 / 871)
        self.assertAlmostEqual(result["branch_current_max_A"], 550 / 779)
        self.assertTrue(result["strict_positive_sink_current_margin"])
        equal = model.branch_bound(10, 0, 0, .2, 5.1, 5.5, .5)
        self.assertEqual(equal["sink_current_margin_A"], 0)
        self.assertFalse(equal["strict_positive_sink_current_margin"])
        low_sink = model.branch_bound(20, .05, 0, .1, 5.1, 5.5, .5)
        self.assertLess(low_sink["sink_current_min_A"], result["sink_current_min_A"])
        self.assertFalse(low_sink["strict_positive_sink_current_margin"])

    def test_conservative_powers_enclose_independent_corner_sweep(self):
        result = model.branch_bound(8.2, .05, 0, .1, 5.1, 5.5, .5)
        for resistor in (7.79, 8.2, 8.61):
            for ron in (0, .025, .05, .075, .1):
                for voltage in (5.1, 5.3, 5.5):
                    current = voltage / (resistor + ron)
                    self.assertLessEqual(current * current * resistor, result["resistor_instantaneous_upper_W"] + 1e-12)
                    self.assertLessEqual(current * current * ron, result["fet_on_state_conduction_upper_W"] + 1e-12)
        self.assertFalse(result["switching_loss_included"])
        self.assertFalse(result["linear_soa_qualified"])
        self.assertFalse(result["thermal_qualified"])

    def test_zero_ron_zero_tolerance_supported(self):
        result = model.branch_bound(10, 0, 0, 0, 5, 5.5, .4)
        self.assertEqual(result["sink_current_min_A"], .5)
        self.assertEqual(result["branch_current_max_A"], .55)
        self.assertEqual(result["resistor_instantaneous_upper_W"], 3.025)
        self.assertEqual(result["fet_on_state_conduction_upper_W"], 0)

    def test_derived_nonfinite_power_is_rejected(self):
        with self.assertRaises(ValueError):
            model.branch_bound(1, 0, 0, 0, 5, 1e308, .5)


if __name__ == "__main__":
    unittest.main()
