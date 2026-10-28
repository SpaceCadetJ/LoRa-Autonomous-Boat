"""Independent physical-domain and conservation checks for VSERVO-01."""
import math
import unittest

import model


class ReservoirModelTests(unittest.TestCase):
    def test_charge_balance_and_esr_step(self):
        C, I, duration, resistance, initial = 120e-6, 0.7, 80e-6, 0.15, 5.2
        result = model.load_step(C, I, duration, resistance, initial)
        self.assertTrue(result["model_valid"])
        recovered_charge = C * (initial - I * resistance - result["voltage_V"])
        self.assertAlmostEqual(recovered_charge, I * duration, delta=1e-18)
        self.assertAlmostEqual(result["esr_drop_V"], I * resistance)

    def test_energy_conservation(self):
        for C in (56e-6, 80e-6, 100e-6):
            for energy in (0, 0.1e-3, 1e-3):
                result = model.returned_energy(C, energy, 5)
                recovered = 0.5 * C * (result["voltage_V"] ** 2 - 25)
                self.assertAlmostEqual(recovered, energy, delta=1e-18)

    def test_zero_deficit_and_energy_preserve_voltage(self):
        self.assertEqual(model.load_step(1e-4, 0, 1, 10, 5)["voltage_V"], 5)
        self.assertEqual(model.returned_energy(1e-4, 0, 5)["voltage_V"], 5)
        self.assertEqual(model.required_C_step(0, 1, 0, 5, 4)["required_capacitance_F"], 0)
        self.assertEqual(model.required_C_energy(0, 5, 6)["required_capacitance_F"], 0)

    def test_depletion_has_no_voltage_prediction(self):
        for current in (1, 2):
            result = model.load_step(1, current, 1, 0, 1)
            self.assertFalse(result["model_valid"])
            self.assertIsNone(result["voltage_V"])
            self.assertEqual(result["status"], "depleted_model_invalid")

    def test_invalid_inputs_and_nonfinite_values_rejected(self):
        for invalid in (-1, math.inf, -math.inf, math.nan, True, "1"):
            with self.subTest(invalid=invalid):
                for call in (
                    lambda: model.load_step(1, invalid, 1, 0, 5),
                    lambda: model.returned_energy(1, invalid, 5),
                    lambda: model.required_C_step(1, invalid, 0, 5, 4),
                    lambda: model.required_C_energy(invalid, 5, 6),
                ):
                    with self.assertRaises(ValueError):
                        call()
        for call in (
            lambda: model.load_step(0, 1, 1, 0, 5),
            lambda: model.returned_energy(0, 1, 5),
            lambda: model.required_C_step(1, 1, 0, 0, 1),
            lambda: model.required_C_energy(1, 1, 0),
            lambda: model.returned_energy(1e-300, 1e300, 5),
        ):
            with self.assertRaises(ValueError):
                call()

    def test_no_finite_capacitor_when_esr_consumes_margin(self):
        for resistance in (1, 2):
            result = model.required_C_step(1, 0.001, resistance, 5, 4)
            self.assertIsNone(result["required_capacitance_F"])
            self.assertFalse(result["finite_solution_for_positive_margin"])
        self.assertFalse(model.required_C_step(0, 0, 0, 5, 5)["finite_solution_for_positive_margin"])

    def test_no_finite_capacitor_for_nonpositive_energy_window(self):
        for ceiling in (4, 5):
            for energy in (0, 1):
                result = model.required_C_energy(energy, 5, ceiling)
                self.assertIsNone(result["required_capacitance_F"])
                self.assertFalse(result["finite_solution_for_positive_margin"])

    def test_required_step_capacitance_is_equality_not_positive_margin(self):
        requirement = model.required_C_step(1, 0.001, 0, 2, 1)
        C = requirement["required_capacitance_F"]
        self.assertEqual(model.load_step(C, 1, 0.001, 0, 2)["voltage_V"], 1)
        self.assertGreater(model.load_step(2 * C, 1, 0.001, 0, 2)["voltage_V"], 1)
        self.assertLess(model.load_step(0.75 * C, 1, 0.001, 0, 2)["voltage_V"], 1)

    def test_required_energy_capacitance_is_equality_not_positive_margin(self):
        requirement = model.required_C_energy(1.5, 1, 2)
        C = requirement["required_capacitance_F"]
        self.assertEqual(model.returned_energy(C, 1.5, 1)["voltage_V"], 2)
        self.assertLess(model.returned_energy(2 * C, 1.5, 1)["voltage_V"], 2)
        self.assertGreater(model.returned_energy(C / 2, 1.5, 1)["voltage_V"], 2)

    def test_more_capacitance_reduces_droop_and_energy_rise(self):
        steps = [model.load_step(C, 0.5, 100e-6, 0.2, 5)["voltage_V"] for C in (56e-6, 80e-6, 100e-6)]
        peaks = [model.returned_energy(C, 0.001, 5)["voltage_V"] for C in (56e-6, 80e-6, 100e-6)]
        self.assertTrue(all(a < b for a, b in zip(steps, steps[1:])))
        self.assertTrue(all(a > b for a, b in zip(peaks, peaks[1:])))
        for I, t, R in ((1, 100e-6, 0.2), (0.5, 200e-6, 0.2), (0.5, 100e-6, 0.4)):
            self.assertLess(model.load_step(100e-6, I, t, R, 5)["voltage_V"], steps[-1])

    def test_post_endurance_label_keeps_measurement_conditions(self):
        data = model.collect()
        condition = data["parameters"]["source_conditions"]
        for required in ("120 Hz", "20 C", "from the initial value", "after the specified test", "not an all-temperature"):
            self.assertIn(required, condition)
        self.assertEqual(data["cases"][0]["condition"], "stacked_post_endurance_20C_only")
        self.assertIn("restored condition", data["cases"][0]["label"])
        self.assertEqual(data["parameters"]["C12_credited_capacitance_F"], 0)

    def test_arithmetic_margin_never_promotes_release(self):
        data = model.collect()
        self.assertTrue(any(case["strict_positive_allocated_headroom"] for entry in data["cases"] for case in entry["energy_cases"]))
        for field in ("hardware_accepted", "component_selected_for_release", "voltage_envelope_qualified", "actual_load_known", "effective_capacitance_bound_qualified", "reservoir_qualified"):
            self.assertIs(data[field], False)
        for entry in data["cases"]:
            for case in entry["energy_cases"]:
                self.assertEqual(case["strict_positive_allocated_headroom"], case["headroom_J"] > 0)


if __name__ == "__main__":
    unittest.main()
