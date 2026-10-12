"""Limiting-case and invalid-input tests; no artifacts or native proof emitted."""
import importlib.util
import math
from pathlib import Path
import sys
import unittest
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("input_capacitor_model", Path(__file__).with_name("model.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class ModelTests(unittest.TestCase):
    def test_thresholds_are_not_guessed_effective_values(self):
        for n in (1, 2, 3, 4):
            x = m.bank_threshold(n)
            self.assertAlmostEqual(x["required_effective_per_cap_uf_equal_share"], 4.7/n)
            self.assertIsNone(x["hypothetical_total_effective_uf"])
            self.assertIsNone(x["hypothetical_arithmetic_requirement_met"])
            self.assertFalse(x["effective_capacitance_verified"])

    def test_hypothetical_pass_never_becomes_qualification(self):
        x = m.bank_threshold(2, hypothetical_factors={"dc_bias_temperature": .5, "tolerance": .9, "aging": .95})
        self.assertAlmostEqual(x["hypothetical_total_effective_uf"], 8.55)
        self.assertTrue(x["hypothetical_arithmetic_requirement_met"])
        self.assertFalse(x["effective_capacitance_verified"])
        self.assertFalse(x["hardware_accepted"])
        y = m.bank_threshold(1, hypothetical_factors={"dc_bias_temperature": .5, "tolerance": .9, "aging": .95})
        self.assertFalse(y["hypothetical_arithmetic_requirement_met"])

    def test_lossless_limit_and_storage_energy(self):
        x = m.rlc_step(resistance_ohm=0)
        self.assertEqual(x["peak_voltage_v"], 50.4)
        self.assertEqual(x["damping_case"], "undamped")
        self.assertAlmostEqual(x["first_peak_time_s"], math.pi*math.sqrt(20e-6*1e-6))
        self.assertAlmostEqual(x["energy_at_input_voltage_j"], .0063504)
        self.assertAlmostEqual(x["peak_energy_j"], 4*x["energy_at_input_voltage_j"])

    def test_critical_and_overdamped_do_not_overshoot(self):
        critical = m.rlc_step()["critical_resistance_ohm"]
        for r, case in ((critical, "critical"), (critical*2, "overdamped")):
            x = m.rlc_step(resistance_ohm=r)
            self.assertEqual(x["damping_case"], case)
            self.assertEqual(x["peak_voltage_v"], 25.2)
            self.assertIsNone(x["first_peak_time_s"])

    def test_greater_series_resistance_reduces_overshoot(self):
        peaks = [m.rlc_step(resistance_ohm=r)["peak_voltage_v"] for r in (0, .05, .1, .2, .5)]
        self.assertEqual(peaks, sorted(peaks, reverse=True))
        self.assertTrue(all(25.2 <= p <= 50.4 for p in peaks))

    def test_sweep_remains_explicitly_illustrative(self):
        s = m.study()
        self.assertEqual(len(s["rlc_sweep"]), 9)
        self.assertAlmostEqual(s["headroom"]["gross_budget_before_losses_and_sag_v"], 2.8)
        self.assertFalse(s["hardware_accepted"])
        self.assertFalse(s["native_proofs_applicable"])
        self.assertTrue(all(not x["prediction_of_actual_board"] for x in s["rlc_sweep"]))

    def test_invalid_counts_factors_and_parameters_rejected(self):
        for n in (0, -1, 1.5, True):
            with self.assertRaises(ValueError): m.bank_threshold(n)
        for f in ({"dc_bias_temperature": .5}, {"dc_bias_temperature": 1.1, "tolerance": 1, "aging": 1}):
            with self.assertRaises(ValueError): m.bank_threshold(1, hypothetical_factors=f)
        for bad in (float("nan"), float("inf"), -1):
            for key in ("vin_v", "capacitance_f", "inductance_h", "resistance_ohm"):
                with self.subTest(key=key, value=bad), self.assertRaises(ValueError): m.rlc_step(**{key: bad})
            with self.assertRaises(ValueError): m.bank_threshold(1, nominal_per_cap_uf=bad)
            with self.assertRaises(ValueError): m.bank_threshold(1, hypothetical_factors={"dc_bias_temperature": bad, "tolerance": 1, "aging": 1})
        for key in ("capacitance_f", "inductance_h"):
            with self.assertRaises(ValueError): m.rlc_step(**{key: 0})

if __name__ == "__main__":
    unittest.main(verbosity=2)
