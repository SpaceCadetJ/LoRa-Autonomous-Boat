"""Corner and rejection tests; never create analysis or native evidence."""
import importlib.util
from pathlib import Path
import sys
import unittest
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("reverse_leakage_model", Path(__file__).with_name("model.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class ModelTests(unittest.TestCase):
    def test_additive_service_bounds(self):
        r = m.resistor_bounds()
        self.assertAlmostEqual(r["additive_fraction"], .043)
        self.assertAlmostEqual(r["minimum_ohm"], 3158.1)
        self.assertAlmostEqual(r["maximum_ohm"], 3441.9)

    def test_80ua_fails_target_without_crossing_absolute(self):
        r = m.bleeder(80e-6, 3441.9)
        self.assertFalse(r["arithmetic_target_met"])
        self.assertTrue(r["arithmetic_above_absolute_min"])
        self.assertAlmostEqual(r["negative_output_v"], -.275352)

    def test_assumed_current_never_becomes_verified(self):
        s = m.study()
        c = next(c for c in s["dc_cases"] if c["name"] == "hypothetical_total_25uA")
        self.assertTrue(c["arithmetic_target_met"])
        self.assertEqual(c["basis"], "assumed_total")
        self.assertFalse(c["full_circuit_current_bound_verified"])
        self.assertFalse(c["hardware_accepted"])
        self.assertFalse(s["capacitor_reverse_accepted"])
        self.assertFalse(s["hardware_accepted"])

    def test_resistor_derating_and_voltage_corner(self):
        r = m.resistor_power(44, 3158.1)
        self.assertAlmostEqual(r["allowed_w_assumed_curve"], 70/85)
        self.assertAlmostEqual(r["loss_w"], 1936/3158.1)
        self.assertEqual(m.resistor_power(44, 3158.1, ambient_c=155)["allowed_w_assumed_curve"], 0)

    def test_ideal_rc_initial_and_asymptotic_limits(self):
        self.assertAlmostEqual(m.rc_voltage(0, 25.2, 25e-6, 3441.9, 47e-6), 25.2)
        self.assertAlmostEqual(m.rc_voltage(100, 0, 25e-6, 3441.9, 47e-6), -.0860475)

    def test_divider_fault_and_poweroff_are_separate(self):
        n = m.divider(-.1)
        self.assertLess(n["minimum_output_v"], n["maximum_output_v"])
        self.assertFalse(n["adc_range_arithmetic_met"])
        self.assertTrue(n["ft_absolute_voltage_arithmetic_met"])
        self.assertAlmostEqual(n["nominal_tau_s"], .0005940520446096654)
        self.assertFalse(m.divider(44)["adc_range_arithmetic_met"])
        self.assertFalse(m.divider(44, vdd=0)["ft_absolute_voltage_arithmetic_met"])
        self.assertFalse(m.divider(25.2, vdda=0)["adc_range_arithmetic_met"])

    def test_invalid_parameters_rejected(self):
        for bad in (float("nan"), float("inf"), -1):
            for call in (lambda: m.resistor_bounds(nominal=bad), lambda: m.resistor_bounds(service=bad),
                         lambda: m.bleeder(bad, 3300), lambda: m.rc_voltage(bad, 0, 0, 3300, 47e-6),
                         lambda: m.resistor_power(44, bad), lambda: m.divider(25.2, top=bad)):
                with self.subTest(value=bad), self.assertRaises(ValueError): call()
        for call in (lambda: m.resistor_bounds(tolerance=1), lambda: m.bleeder(1e-6, 3300, target_v=.3),
                     lambda: m.rc_voltage(0, 0, 0, 3300, 0), lambda: m.divider(0, tolerance=1),
                     lambda: m.divider(float("nan")), lambda: m.resistor_power(1, 1, zero_power_c=70)):
            with self.assertRaises(ValueError): call()

if __name__ == "__main__":
    unittest.main(verbosity=2)
