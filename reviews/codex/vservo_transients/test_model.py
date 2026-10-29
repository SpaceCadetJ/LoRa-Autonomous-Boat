"""VSERVO-02 boundary, conservation and unavailable-input checks."""
import math
import unittest

import model


class TransientBoundaryTests(unittest.TestCase):
    def test_all_unknowns_remain_unavailable_without_numeric_defaults(self):
        cases = [
            (model.clamp_window(None, None, None, None, None), 5, "off_margin_V"),
            (model.delay_rise(None, None, None), 3, "rise_V"),
            (model.sink_budget(None, None, None, None, None), 5, "minimum_event_sink_J"),
            (model.negative_boundary(None, None, None), 3, "capacitor_margin_V"),
        ]
        for result, count, metric in cases:
            self.assertEqual(result["status"], "unavailable")
            self.assertEqual(len(result["missing_fields"]), count)
            self.assertIsNone(result[metric])
            self.assertTrue(all(v is None for v in result["inputs"].values()))
            self.assertIs(result["hardware_accepted"], False)

    def test_partial_unknown_reports_exact_field_and_no_promoted_result(self):
        result = model.clamp_window(5.1, 5.2, 5.3, None, 5.5)
        self.assertEqual(result["missing_fields"], ["overshoot_V"])
        self.assertIsNone(result["strict_positive_arithmetic_margin"])
        with self.assertRaises(ValueError):
            model.delay_rise(None, -1, 1)
        with self.assertRaises(ValueError):
            model.clamp_window(None, 6, 5, None, None)

    def test_nonfinite_and_nonreal_inputs_rejected(self):
        for bad in (math.nan, math.inf, -math.inf, True, "unknown"):
            for call in (
                lambda: model.clamp_window(5, 5.1, 5.2, bad, 5.5),
                lambda: model.delay_rise(1, bad, 1),
                lambda: model.sink_budget(1, 5, 6, bad, 1),
                lambda: model.negative_boundary(bad, 0, 0),
            ):
                with self.subTest(bad=bad), self.assertRaises(ValueError):
                    call()

    def test_physical_domains_reject_invalid_inputs(self):
        for call in (
            lambda: model.delay_rise(0, 1, 1),
            lambda: model.delay_rise(1, 1, -1),
            lambda: model.sink_budget(1, 5, 4, 1, 1),
            lambda: model.sink_budget(1, 0, 1, 1, 1),
            lambda: model.sink_budget(1, 5, 6, 1, -1),
            lambda: model.clamp_window(5, 5.3, 5.2, 0, 6),
            lambda: model.clamp_window(5, 5.1, 5.2, -0.1, 6),
            lambda: model.delay_rise(1e-300, 1e300, 1),
        ):
            with self.assertRaises(ValueError):
                call()

    def test_clamp_window_requires_both_positive_margins(self):
        fit = model.clamp_window(5.1, 5.2, 5.3, 0.1, 5.5)
        self.assertTrue(fit["strict_positive_arithmetic_margin"])
        self.assertGreater(fit["off_margin_V"], 0)
        self.assertGreater(fit["protection_margin_V"], 0)
        self.assertIn("full-current clamp", fit["overshoot_definition"])
        self.assertFalse(fit["full_current_response_qualified"])
        off_bad = model.clamp_window(5.3, 5.2, 5.3, 0.1, 5.5)
        protection_bad = model.clamp_window(5.1, 5.2, 5.3, 0.3, 5.5)
        self.assertFalse(off_bad["strict_positive_arithmetic_margin"])
        self.assertFalse(protection_bad["strict_positive_arithmetic_margin"])

    def test_written_decimal_zero_is_not_positive_roundoff_margin(self):
        off_equal = model.clamp_window(5.2, 5.2, 5.3, 0.1, 5.5)
        protection_equal = model.clamp_window(5.1, 5.2, 5.3, 0.2, 5.5)
        self.assertEqual(off_equal["off_margin_V"], 0)
        self.assertEqual(protection_equal["protection_margin_V"], 0)
        self.assertFalse(off_equal["strict_positive_arithmetic_margin"])
        self.assertFalse(protection_equal["strict_positive_arithmetic_margin"])

    def test_delay_rise_obeys_charge_conservation(self):
        C, I, delay = 73e-6, 0.43, 17e-6
        result = model.delay_rise(C, I, delay)
        self.assertAlmostEqual(C * result["rise_V"], I * delay, delta=1e-18)
        self.assertEqual(model.delay_rise(C, 0, delay)["rise_V"], 0)
        self.assertEqual(model.delay_rise(C, I, 0)["rise_V"], 0)

    def test_delay_rise_is_monotone_in_charge_and_inverse_capacitance(self):
        base = model.delay_rise(80e-6, 0.5, 10e-6)["rise_V"]
        self.assertAlmostEqual(model.delay_rise(160e-6, 0.5, 10e-6)["rise_V"], base / 2)
        self.assertAlmostEqual(model.delay_rise(80e-6, 1, 10e-6)["rise_V"], 2 * base)
        self.assertAlmostEqual(model.delay_rise(80e-6, 0.5, 20e-6)["rise_V"], 2 * base)

    def test_single_event_budget_obeys_energy_balance(self):
        C, start, ceiling = 80e-6, 5, 5.5
        for energy in (0, 0.1e-3, 1e-3):
            result = model.sink_budget(C, start, ceiling, energy, 10)
            retained = energy - result["minimum_event_sink_J"]
            self.assertGreaterEqual(retained, 0)
            self.assertLessEqual(retained, result["capacitor_energy_window_J"] + 1e-18)
            endpoint = math.sqrt(start * start + 2 * retained / C)
            self.assertLessEqual(endpoint, ceiling + 1e-12)
            self.assertAlmostEqual(0.5 * C * (endpoint * endpoint - start * start), retained, delta=1e-18)

    def test_repeated_reset_cannot_reuse_event_storage_credit(self):
        for energy in (0.1e-3, 1e-3):
            result = model.sink_budget(80e-6, 5, 5.5, energy, 10)
            self.assertEqual(result["repeated_events_same_start_require_local_sink_J"], energy)
            self.assertAlmostEqual(result["mean_local_sink_W"] / 10, energy)
        low = model.sink_budget(80e-6, 5, 5.5, 0.1e-3, 10)
        self.assertEqual(low["minimum_event_sink_J"], 0)
        self.assertGreater(low["mean_local_sink_W"], 0)
        self.assertTrue(low["minimum_event_sink_is_lower_bound"])
        self.assertFalse(low["endpoint_model_bounds_peak"])
        self.assertFalse(low["credits_later_absorption"])
        self.assertFalse(low["automatically_adds_harness_inductive_energy"])
        self.assertIn("same starting rail", low["repeated_average_scope"])

    def test_zero_storage_window_and_zero_event_rate(self):
        result = model.sink_budget(80e-6, 5, 5, 1e-3, 0)
        self.assertEqual(result["capacitor_energy_window_J"], 0)
        self.assertEqual(result["minimum_event_sink_J"], 1e-3)
        self.assertEqual(result["mean_local_sink_W"], 0)
        self.assertEqual(result["repeated_events_same_start_require_local_sink_J"], 1e-3)

    def test_negative_boundary_keeps_terminal_constraints_separate(self):
        equal = model.negative_boundary(0, 0, 0)
        self.assertTrue(equal["capacitor_nonnegative_boundary_met"])
        self.assertTrue(equal["receiver_boundary_met"])
        self.assertFalse(equal["strict_positive_arithmetic_margin"])
        cap_bad = model.negative_boundary(-0.1, 0.1, 0)
        receiver_bad = model.negative_boundary(0.1, -0.1, 0)
        self.assertFalse(cap_bad["capacitor_nonnegative_boundary_met"])
        self.assertTrue(cap_bad["receiver_boundary_met"])
        self.assertTrue(receiver_bad["capacitor_nonnegative_boundary_met"])
        self.assertFalse(receiver_bad["receiver_boundary_met"])
        self.assertTrue(model.negative_boundary(0.1, 0.1, -0.1)["strict_positive_arithmetic_margin"])

    def test_more_storage_does_not_lower_repeated_sink_average(self):
        low = model.sink_budget(56e-6, 5, 5.5, 1e-3, 10)
        high = model.sink_budget(100e-6, 5, 5.5, 1e-3, 10)
        self.assertGreater(high["capacitor_energy_window_J"], low["capacitor_energy_window_J"])
        self.assertLess(high["minimum_event_sink_J"], low["minimum_event_sink_J"])
        self.assertEqual(high["mean_local_sink_W"], low["mean_local_sink_W"])
        self.assertAlmostEqual(model.sink_budget(100e-6, 5, 5.5, 1e-3, 20)["mean_local_sink_W"], 2 * high["mean_local_sink_W"])

    def test_collect_separates_unknown_actuals_and_unqualified_illustrations(self):
        data = model.collect()
        for actual in data["actual"].values():
            self.assertEqual(actual["status"], "unavailable")
            self.assertTrue(all(value is None for value in actual["inputs"].values()))
        self.assertTrue(data["window_cases"][0]["result"]["strict_positive_arithmetic_margin"])
        self.assertFalse(data["window_cases"][1]["result"]["strict_positive_arithmetic_margin"])
        for field in ("hardware_accepted", "component_selected_for_release", "voltage_envelope_qualified", "actual_load_known", "sink_qualified", "reverse_voltage_qualified", "fabrication_approved"):
            self.assertIs(data[field], False)
        for field in ("candidate_electrical_delta", "live_electrical_delta", "live_copper_delta"):
            self.assertEqual(data[field], 0)


if __name__ == "__main__":
    unittest.main()
