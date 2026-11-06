"""Independent equation, endpoint, monotonicity and rejection tests for SENSE-04."""
from fractions import Fraction as F
import json
import math
import unittest

import model


class InterfaceModelTests(unittest.TestCase):
    NUMERIC_CALLS = [
        (model.shutdown_window, [3.35, 3.241200044945504, .05, 100, 150e-6, 50e-6]),
        (model.discharge, [3.241200044945504, 1e-6, 6800, 100e-9, .3]),
        (model.injection_step, [1e-12, 1e-9]),
        (model.bleed_interval, [5940.520446096654, 10, .001, .3, 1e-6]),
    ]

    def test_01_shutdown_examples_match_independent_fraction_arithmetic(self):
        signal = F('3.241200044945504')
        initial = F('3.35') - signal - F('.05')
        delay = F(150, 1000000) + F(50, 1000000)
        for slew, passes in [(100, True), (10000, False)]:
            with self.subTest(slew=slew):
                result = model.shutdown_window(3.35, float(signal), .05, slew, 150e-6, 50e-6)
                self.assertAlmostEqual(result['initial_headroom_v'], float(initial), places=14)
                self.assertAlmostEqual(result['headroom_after_delay_v'], float(initial - slew * delay), places=14)
                self.assertAlmostEqual(result['strict_delay_limit_s'], float(initial / slew), places=16)
                self.assertEqual(result['strict_positive_arithmetic_margin'], passes)
                self.assertFalse(result['hardware_accepted'])

    def test_02_shutdown_equality_is_not_positive_and_zero_slew_is_explicit(self):
        equal = model.shutdown_window(3, 2, 0, 1, .25, .75)
        self.assertEqual(equal['headroom_after_delay_v'], 0)
        self.assertEqual(equal['strict_delay_limit_s'], 1)
        self.assertFalse(equal['strict_positive_arithmetic_margin'])
        zero_slew = model.shutdown_window(3, 2, 0, 0, 1e6, 1e6)
        self.assertTrue(zero_slew['deadline_unbounded'])
        self.assertIsNone(zero_slew['strict_delay_limit_s'])
        self.assertTrue(zero_slew['strict_positive_arithmetic_margin'])
        no_initial_margin = model.shutdown_window(2, 2, 0, 0, 0, 0)
        self.assertFalse(no_initial_margin['deadline_unbounded'])
        self.assertEqual(no_initial_margin['strict_delay_limit_s'], 0)
        self.assertFalse(no_initial_margin['strict_positive_arithmetic_margin'])
        json.dumps(zero_slew, allow_nan=False)

    def test_03_shutdown_margin_monotonicity_for_each_bound(self):
        args = [3.35, 3.2, .05, 100, 150e-6, 50e-6]
        base = model.shutdown_window(*args)['headroom_after_delay_v']
        for index, value in [(0, 3.3), (1, 3.25), (2, .1), (3, 200), (4, 200e-6), (5, 100e-6)]:
            with self.subTest(index=index):
                changed = list(args)
                changed[index] = value
                self.assertLess(model.shutdown_window(*changed)['headroom_after_delay_v'], base)

    def test_04_discharge_time_and_endpoint_match_independent_analytic_solution(self):
        initial, leakage, resistance, capacitance, target = 3.241200044945504, 1e-6, 6800, 100e-9, .3
        result = model.discharge(initial, leakage, resistance, capacitance, target)
        floor = leakage * resistance
        tau = resistance * capacitance
        exact_time = tau * math.log((initial - floor) / (target - floor))
        self.assertAlmostEqual(result['time_to_target_s'], exact_time, places=15)
        endpoint = floor + (initial - floor) * math.exp(-result['time_to_target_s'] / tau)
        self.assertAlmostEqual(endpoint, target, places=14)
        self.assertAlmostEqual(result['voltage_at_target_time_v'], endpoint, places=14)
        before = floor + (initial - floor) * math.exp(-.99 * result['time_to_target_s'] / tau)
        self.assertGreater(before, target)
        self.assertTrue(result['finite_time_to_target'])

    def test_05_discharge_floor_equality_and_initial_endpoint_are_distinct(self):
        for target in (.68, .3):
            with self.subTest(target=target):
                result = model.discharge(3.2, 100e-6, 6800, 100e-9, target)
                self.assertFalse(result['finite_time_to_target'])
                self.assertIsNone(result['time_to_target_s'])
        equality = model.discharge(2, 1, 1, 1, 1)
        self.assertFalse(equality['finite_time_to_target'])
        self.assertFalse(equality['target_above_leakage_floor'])
        for initial in (.2, .3):
            already = model.discharge(initial, 100e-6, 6800, 100e-9, .3)
            self.assertEqual(already['time_to_target_s'], 0)
            self.assertEqual(already['voltage_at_target_time_v'], initial)
            self.assertTrue(already['initial_already_at_or_below_target'])
            self.assertTrue(already['leakage_floor_exceeds_target'])
            self.assertTrue(already['finite_time_to_target'])

    def test_06_discharge_time_monotonicity_and_capacitance_scaling(self):
        base = model.discharge(3.2, 1e-6, 6800, 100e-9, .3)['time_to_target_s']
        self.assertAlmostEqual(model.discharge(3.2, 1e-6, 6800, 200e-9, .3)['time_to_target_s'], 2 * base)
        self.assertGreater(model.discharge(3.2, 2e-6, 6800, 100e-9, .3)['time_to_target_s'], base)
        self.assertGreater(model.discharge(3.2, 1e-6, 7000, 100e-9, .3)['time_to_target_s'], base)
        self.assertGreater(model.discharge(3.3, 1e-6, 6800, 100e-9, .3)['time_to_target_s'], base)
        self.assertGreater(model.discharge(3.2, 1e-6, 6800, 100e-9, .2)['time_to_target_s'], base)
        self.assertAlmostEqual(model.discharge(3.2, 1e-6, 6800, 1e-9, .3)['time_to_target_s'], base / 100)

    def test_07_charge_step_uses_absolute_charge_and_minimum_capacitance(self):
        exact = float(F(1, 10**12) / F(1, 10**9))
        for charge in (1e-12, -1e-12):
            self.assertAlmostEqual(model.injection_step(charge, 1e-9)['glitch_magnitude_v'], exact, places=15)
        self.assertEqual(model.injection_step(0, 1e-9)['glitch_magnitude_v'], 0)
        self.assertAlmostEqual(model.injection_step(2e-12, 1e-9)['glitch_magnitude_v'], 2 * exact)
        self.assertAlmostEqual(model.injection_step(1e-12, 2e-9)['glitch_magnitude_v'], exact / 2)

    def test_08_bleed_interval_matches_independent_fraction_loading_and_leakage(self):
        rth = F(47000 * 6800, 47000 + 6800)
        epsilon = F(1, 1000)
        lower = (rth + 10) * (1 - epsilon) / epsilon
        for leakage, feasible in [(F(1, 10**6), False), (F(1, 10**9), True)]:
            with self.subTest(leakage=str(leakage)):
                result = model.bleed_interval(float(rth), 10, float(epsilon), .3, float(leakage))
                self.assertTrue(math.isclose(result['rp_min_ohm'], float(lower), rel_tol=1e-15))
                self.assertTrue(math.isclose(result['rp_max_ohm'], float(F(3, 10) / leakage), rel_tol=1e-15))
                self.assertEqual(result['necessary_interval_exists'], feasible)
                # Independent loading equation reaches the allocated relative error at Rp_min.
                loss = float(rth + 10) / (result['rp_min_ohm'] + float(rth + 10))
                self.assertAlmostEqual(loss, float(epsilon), places=15)

    def test_09_bleed_equality_is_inclusive_and_zero_leakage_has_no_infinity(self):
        equal = model.bleed_interval(1, 0, .5, 1, 1)
        self.assertEqual(equal['rp_min_ohm'], 1)
        self.assertEqual(equal['rp_max_ohm'], 1)
        self.assertTrue(equal['necessary_interval_exists'])
        zero_leak = model.bleed_interval(1, 0, .5, 0, 0)
        self.assertTrue(zero_leak['upper_bound_unbounded'])
        self.assertIsNone(zero_leak['rp_max_ohm'])
        self.assertTrue(zero_leak['necessary_interval_exists'])
        self.assertFalse(model.bleed_interval(1, 0, .5, 0, 1)['necessary_interval_exists'])
        json.dumps(zero_leak, allow_nan=False)

    def test_10_bleed_bounds_move_monotonically_with_constraints(self):
        base = model.bleed_interval(6000, 10, .001, .3, 1e-6)
        self.assertGreater(model.bleed_interval(7000, 10, .001, .3, 1e-6)['rp_min_ohm'], base['rp_min_ohm'])
        self.assertGreater(model.bleed_interval(6000, 20, .001, .3, 1e-6)['rp_min_ohm'], base['rp_min_ohm'])
        self.assertGreater(model.bleed_interval(6000, 10, .0005, .3, 1e-6)['rp_min_ohm'], base['rp_min_ohm'])
        self.assertLess(model.bleed_interval(6000, 10, .001, .3, 2e-6)['rp_max_ohm'], base['rp_max_ohm'])
        self.assertLess(model.bleed_interval(6000, 10, .001, .2, 1e-6)['rp_max_ohm'], base['rp_max_ohm'])

    def test_11_every_required_unknown_leaves_arithmetic_unavailable(self):
        for function, args in self.NUMERIC_CALLS:
            for index in range(len(args)):
                with self.subTest(function=function.__name__, index=index):
                    values = list(args)
                    values[index] = None
                    result = function(*values)
                    self.assertEqual(result['status'], 'unavailable')
                    self.assertFalse(result['available'])
                    self.assertTrue(result['missing_fields'])
                    for key in ['strict_positive_arithmetic_margin', 'finite_time_to_target',
                                'glitch_magnitude_v', 'necessary_interval_exists']:
                        if key in result:
                            self.assertIsNone(result[key])

    def test_12_bad_types_nonfinite_and_overflow_inputs_never_produce_results(self):
        for function, args in self.NUMERIC_CALLS:
            for index in range(len(args)):
                for invalid in (True, False, float('nan'), float('inf'), -float('inf'), '1', [], 10**1000):
                    with self.subTest(function=function.__name__, index=index, invalid=type(invalid).__name__):
                        values = list(args)
                        values[index] = invalid
                        with self.assertRaises(ValueError):
                            function(*values)
        for function, args in [
                (model.shutdown_window, (3, 2, 0, 1e308, 1e308, 1e308)),
                (model.discharge, (3, 1e308, 1e308, 1, .3)),
                (model.discharge, (3, 0, 1e-308, 1e-308, .3)),
                (model.injection_step, (1e308, 1e-308)),
                (model.bleed_interval, (1e308, 1e308, .001, .3, 1e-6))]:
            with self.assertRaises(ValueError):
                function(*args)

    def test_13_invalid_physical_domains_are_rejected(self):
        for index in range(6):
            args = list(self.NUMERIC_CALLS[0][1])
            args[index] = -1
            with self.assertRaises(ValueError):
                model.shutdown_window(*args)
        for index in range(5):
            args = list(self.NUMERIC_CALLS[1][1])
            args[index] = -1
            with self.assertRaises(ValueError):
                model.discharge(*args)
        for index in (2, 3):
            args = list(self.NUMERIC_CALLS[1][1])
            args[index] = 0
            with self.assertRaises(ValueError):
                model.discharge(*args)
        with self.assertRaises(ValueError):
            model.injection_step(1e-12, 0)
        for index, invalid in [(0, 0), (0, -1), (1, -1), (2, 0), (2, 1), (2, -.1), (3, -1), (4, -1)]:
            args = list(self.NUMERIC_CALLS[3][1])
            args[index] = invalid
            with self.assertRaises(ValueError):
                model.bleed_interval(*args)
        with self.assertRaises(ValueError):
            model.shutdown_window(None, True, None, None, None, None)

    def test_14_each_unqualified_or_missing_permission_flag_disables(self):
        all_true = {key: True for key in model.REQUIRED_QUALIFICATIONS}
        enabled = model.permission(all_true, True)
        self.assertTrue(enabled['enabled'])
        self.assertFalse(enabled['hardware_accepted'])
        self.assertFalse(enabled['state_control_implemented'])
        for key in model.REQUIRED_QUALIFICATIONS:
            for missing in (None, False, 'absent'):
                with self.subTest(key=key, missing=missing):
                    qualifications = dict(all_true)
                    if missing == 'absent':
                        del qualifications[key]
                    else:
                        qualifications[key] = missing
                    result = model.permission(qualifications, True)
                    self.assertFalse(result['enabled'])
                    self.assertIn(key, result['unqualified'])
        for request in (None, False):
            self.assertFalse(model.permission(all_true, request)['enabled'])
        self.assertFalse(model.permission(None, True)['enabled'])

    def test_15_truthy_nonbooleans_and_unknown_qualification_names_are_rejected(self):
        all_true = {key: True for key in model.REQUIRED_QUALIFICATIONS}
        for invalid in (1, 0, 'true', [], float('nan')):
            with self.assertRaises(ValueError):
                model.permission(all_true, invalid)
            for key in model.REQUIRED_QUALIFICATIONS:
                qualifications = dict(all_true)
                qualifications[key] = invalid
                with self.assertRaises(ValueError):
                    model.permission(qualifications, True)
        with self.assertRaises(ValueError):
            model.permission({**all_true, 'acqusition': True}, True)
        with self.assertRaises(ValueError):
            model.permission(list(all_true), True)

    def test_16_collect_has_no_actual_bounds_or_hardware_acceptance(self):
        result = model.collect()
        self.assertEqual(json.loads(json.dumps(result, allow_nan=False)), result)
        self.assertTrue(all(value is None for value in result['unknown_actual_inputs'].values()))
        self.assertTrue(all(value is None for value in result['qualifications'].values()))
        self.assertFalse(result['permission']['enabled'])
        for actual in result['actual'].values():
            self.assertFalse(actual['available'])
            self.assertTrue(all(value is None for value in actual['inputs'].values()))
        for key in ['hardware_accepted', 'fabrication_approved', 'procurement_approved',
                    'protection_qualified', 'qualification_ports_implemented',
                    'full_6s_accepted', 'interface_selected', 'pcb_integrated', 'native_commands_rerun']:
            self.assertFalse(result[key])
        self.assertEqual([x['strict_positive_arithmetic_margin'] for x in result['shutdown_examples']], [True, False])
        self.assertEqual([x['finite_time_to_target'] for x in result['discharge_examples']], [True, False, True])
        self.assertEqual([x['necessary_interval_exists'] for x in result['bleed_examples']], [False, True])
        self.assertAlmostEqual(result['injection_example']['glitch_magnitude_v'], .001)

    def test_17_collect_and_permission_do_not_share_mutable_state(self):
        first, second = model.collect(), model.collect()
        self.assertEqual(first, second)
        first['qualifications']['source_bound'] = True
        first['shutdown_examples'][0]['inputs']['release_floor_v'] = 4
        self.assertEqual(model.collect(), second)
        quals = {key: True for key in model.REQUIRED_QUALIFICATIONS}
        result = model.permission(quals, True)
        result['qualifications']['source_bound'] = False
        self.assertTrue(quals['source_bound'])

    def test_18_immediate_attainment_and_sustained_parking_are_distinct(self):
        rebound = model.discharge(.2, 100e-6, 6800, 100e-9, .3)
        self.assertEqual(rebound['time_to_target_s'], 0)
        self.assertTrue(rebound['finite_time_to_target'])
        self.assertFalse(rebound['equilibrium_at_or_below_target'])
        self.assertFalse(rebound['sustained_target_possible_in_model'])
        later = .68 + (.2 - .68) * math.exp(-5)
        self.assertGreater(later, .3)
        # At an equilibrium exactly equal to target, starting below stays below;
        # starting above approaches the target without attaining it in finite time.
        for initial, sustainable in [(.5, True), (2.0, False)]:
            with self.subTest(initial=initial):
                result = model.discharge(initial, 1, 1, 1, 1)
                self.assertTrue(result['equilibrium_at_or_below_target'])
                self.assertEqual(result['finite_time_to_target'], sustainable)
                self.assertEqual(result['sustained_target_possible_in_model'], sustainable)
                later = 1 + (initial - 1) * math.exp(-5)
                self.assertEqual(later <= 1, sustainable)
                self.assertFalse(result['hardware_accepted'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
