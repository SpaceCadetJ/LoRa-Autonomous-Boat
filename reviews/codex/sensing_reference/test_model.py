"""Independent rational, monotonicity, inverse and rejection tests for SENSE-03."""
from fractions import Fraction as F
import itertools
import json
import math
import unittest

import model


class ReferenceModelTests(unittest.TestCase):
    @staticmethod
    def reference_corners():
        return [vfb * (1 + rt / rb)
                for vfb, rt, rb in itertools.product(
                    (F(985, 1000), F(1015, 1000)),
                    (F(100000) * F(99, 100), F(100000) * F(101, 100)),
                    (F(43200) * F(99, 100), F(43200) * F(101, 100)))]

    @staticmethod
    def divider_corners():
        return [rb / (rt + rb)
                for rt, rb in itertools.product(
                    (F(47000) * F(99, 100), F(47000) * F(101, 100)),
                    (F(6800) * F(99, 100), F(6800) * F(101, 100)))]

    def test_01_feedback_bounds_match_all_independent_fraction_corners(self):
        exact = self.reference_corners()
        result = model.feedback_bounds(.985, 1.015, 100000, 43200)
        self.assertAlmostEqual(result['output_min_v'], float(min(exact)), places=14)
        self.assertAlmostEqual(result['output_max_v'], float(max(exact)), places=14)
        self.assertLess(result['output_min_v'], 3.3)
        self.assertGreater(result['output_max_v'], 3.3)

    def test_02_divider_bounds_match_independent_fraction_corners(self):
        exact = self.divider_corners()
        result = model.divider_bounds(47000, 6800)
        self.assertAlmostEqual(result['ratio_min'], float(min(exact)), places=15)
        self.assertAlmostEqual(result['ratio_max'], float(max(exact)), places=15)
        self.assertAlmostEqual(result['ratio_nominal'], float(F(6800, 53800)), places=15)

    def test_03_25v2_margin_and_ceiling_match_exact_rational_reference(self):
        floor, ratio = min(self.reference_corners()), max(self.divider_corners())
        result = model.headroom(25.2, float(floor), float(ratio), 0)
        self.assertAlmostEqual(result['adc_max_v'], float(F(126, 5) * ratio), places=14)
        self.assertAlmostEqual(result['headroom_v'], float(floor - F(126, 5) * ratio), places=14)
        self.assertAlmostEqual(result['vin_ceiling_v'], float(floor / ratio), places=13)
        self.assertFalse(result['strict_positive_arithmetic_margin'])

    def test_04_headroom_monotonicity_for_each_independent_input(self):
        base = model.headroom(24, 3.2, .12, .05)['headroom_v']
        self.assertLess(model.headroom(25, 3.2, .12, .05)['headroom_v'], base)
        self.assertGreater(model.headroom(24, 3.3, .12, .05)['headroom_v'], base)
        self.assertLess(model.headroom(24, 3.2, .13, .05)['headroom_v'], base)
        self.assertLess(model.headroom(24, 3.2, .12, .1)['headroom_v'], base)
        self.assertGreater(model.headroom(24, 3.2, .12, 0)['vin_ceiling_v'],
                           model.headroom(24, 3.2, .12, .05)['vin_ceiling_v'])

    def test_05_larger_tolerances_widen_both_independent_envelopes(self):
        for function, args, lower, upper in [
                (model.feedback_bounds, (.985, 1.015, 100000, 43200), 'output_min_v', 'output_max_v'),
                (model.divider_bounds, (47000, 6800), 'ratio_min', 'ratio_max')]:
            with self.subTest(function=function.__name__):
                nominal = function(*args, 0, 0)
                top = function(*args, .01, 0)
                both = function(*args, .01, .01)
                self.assertLess(top[lower], nominal[lower])
                self.assertLess(both[lower], top[lower])
                self.assertGreater(top[upper], nominal[upper])
                self.assertGreater(both[upper], top[upper])

    def test_06_exact_equality_is_not_strict_positive_margin(self):
        threshold = model.threshold_rtop(2, 1, (0, 0), 1, 0)
        self.assertEqual(threshold['rtop_threshold_ohm'], 1)
        self.assertEqual(threshold['comparator'], '>')
        ratio = model.divider_bounds(1, 1, 0, 0)['ratio_max']
        result = model.headroom(2, 1, ratio, 0)
        self.assertEqual(result['headroom_v'], 0)
        self.assertFalse(result['strict_positive_arithmetic_margin'])
        self.assertFalse(result['hardware_accepted'])

    def test_07_inverse_threshold_matches_fraction_and_straddles_margin(self):
        floor = min(self.reference_corners())
        for vin, reserve in itertools.product((F(24), F(126, 5), F(26), F(44)), (F(0), F(1, 20))):
            with self.subTest(vin=str(vin), reserve=str(reserve)):
                # Rearrange the exact corner inequality without using model functions.
                rb_high = F(6800) * F(101, 100)
                exact = (vin * rb_high / (floor - reserve) - rb_high) / F(99, 100)
                threshold = model.threshold_rtop(float(vin), 6800, (.01, .01), float(floor), float(reserve))
                actual = threshold['rtop_threshold_ohm']
                self.assertTrue(math.isclose(actual, float(exact), rel_tol=1e-14))
                for factor, positive in ((1 - 1e-8, False), (1 + 1e-8, True)):
                    ratio = model.divider_bounds(actual * factor, 6800)['ratio_max']
                    result = model.headroom(float(vin), float(floor), ratio, float(reserve))
                    self.assertEqual(result['strict_positive_arithmetic_margin'], positive)
                self.assertFalse(threshold['resistor_selected'])

    def test_08_each_missing_numeric_input_leaves_result_unavailable(self):
        calls = [
            (model.feedback_bounds, [.985, 1.015, 100000, 43200, .01, .01]),
            (model.divider_bounds, [47000, 6800, .01, .01]),
            (model.headroom, [25.2, 3.2, .13, 0]),
            (model.threshold_rtop, [25.2, 6800, (.01, .01), 3.2, 0]),
        ]
        for function, args in calls:
            for index in range(len(args)):
                with self.subTest(function=function.__name__, missing=index):
                    unknown = list(args)
                    unknown[index] = None
                    result = function(*unknown)
                    self.assertEqual(result['status'], 'unavailable')
                    self.assertFalse(result['available'])
                    self.assertTrue(result['missing_fields'])
                    self.assertFalse(result['hardware_accepted'])
                    for key in ['headroom_v', 'strict_positive_arithmetic_margin', 'rtop_threshold_ohm']:
                        if key in result:
                            self.assertIsNone(result[key])
        self.assertEqual(model.threshold_rtop(25.2, 6800, (None, .01), 3.2, 0)['status'], 'unavailable')

    def test_09_nonfinite_boolean_and_nonnumeric_inputs_are_rejected(self):
        bad_values = [float('nan'), float('inf'), -float('inf'), True, False, '3.3', [], {}, complex(3, 0)]
        for bad in bad_values:
            for function, args, position in [
                    (model.feedback_bounds, [.985, 1.015, 100000, 43200], 0),
                    (model.divider_bounds, [47000, 6800], 0),
                    (model.headroom, [25.2, 3.2, .13, 0], 3),
                    (model.threshold_rtop, [25.2, 6800, (.01, .01), 3.2, 0], 0)]:
                with self.subTest(function=function.__name__, bad=repr(bad)):
                    args[position] = bad
                    with self.assertRaises(ValueError):
                        function(*args)
        with self.assertRaises(ValueError):
            model.headroom(None, True, .13, None)

    def test_10_invalid_physical_domains_and_tolerance_shapes_are_rejected(self):
        invalid_calls = [
            (model.feedback_bounds, (1.1, 1.0, 100000, 43200)),
            (model.feedback_bounds, (.985, 1.015, 0, 43200)),
            (model.feedback_bounds, (.985, 1.015, 100000, 43200, 1, .01)),
            (model.divider_bounds, (-47000, 6800)),
            (model.divider_bounds, (47000, 0)),
            (model.divider_bounds, (47000, 6800, -.01, .01)),
            (model.headroom, (-1, 3.2, .13, 0)),
            (model.headroom, (25.2, -1, .13, 0)),
            (model.headroom, (25.2, 3.2, 0, 0)),
            (model.headroom, (25.2, 3.2, 1, 0)),
            (model.headroom, (25.2, 3.2, .13, -.1)),
            (model.threshold_rtop, (25.2, 0, (.01, .01), 3.2, 0)),
            (model.threshold_rtop, (25.2, 6800, (True, .01), 3.2, 0)),
            (model.threshold_rtop, (25.2, 6800, (1, .01), 3.2, 0)),
        ]
        for function, args in invalid_calls:
            with self.subTest(function=function.__name__, args=args):
                with self.assertRaises(ValueError):
                    function(*args)
        for tols in (.01, '.01,.01', (), (.01,), (.01, .01, .01), {'top': .01, 'bottom': .01}):
            with self.assertRaises(ValueError):
                model.threshold_rtop(25.2, 6800, tols, 3.2, 0)

    def test_11_finite_inputs_cannot_silently_overflow_or_collapse_divider(self):
        invalid_calls = [
            (model.feedback_bounds, (1, 1, 1e308, 1e-308)),
            (model.feedback_bounds, (1, 1, 1e308, 1e308, .99, .99)),
            (model.divider_bounds, (1e308, 1e308)),
            (model.divider_bounds, (1e308, 1e-308)),
            (model.headroom, (1, 1e308, 1e-308, 0)),
            (model.threshold_rtop, (1e308, 6800, (.01, .01), 1e-308, 0)),
            (model.divider_bounds, (10 ** 1000, 6800)),
        ]
        for function, args in invalid_calls:
            with self.subTest(function=function.__name__):
                with self.assertRaises(ValueError):
                    function(*args)

    def test_12_nonpositive_usable_reference_is_only_an_active_range_result(self):
        for floor, reserve in [(0, 0), (.05, .05), (.04, .05)]:
            result = model.threshold_rtop(25.2, 6800, (.01, .01), floor, reserve)
            self.assertTrue(result['available'])
            self.assertFalse(result['finite_positive_rtop_can_meet_arithmetic_margin'])
            self.assertIsNone(result['rtop_threshold_ohm'])
            self.assertFalse(result['hardware_accepted'])
        # If VIN is below the usable reference, all positive Rtop meet this arithmetic condition.
        result = model.threshold_rtop(0, 6800, (.01, .01), 3.2, 0)
        self.assertLess(result['rtop_threshold_ohm'], 0)
        self.assertTrue(result['rtop_must_also_be_positive'])

    def test_13_collect_is_json_finite_conditional_and_never_accepts_hardware(self):
        result = model.collect()
        self.assertEqual(json.loads(json.dumps(result, allow_nan=False)), result)
        self.assertEqual([case['inputs']['vin'] for case in result['static_cases']], [24, 25.2, 26, 44])
        self.assertTrue(all(value is None for value in result['unknown_actual_inputs'].values()))
        self.assertEqual(result['actual']['headroom']['status'], 'unavailable')
        self.assertEqual(result['actual']['threshold']['status'], 'unavailable')
        self.assertFalse(result['feedback_reference_cross_check']['guaranteed_vdda_envelope'])
        self.assertEqual(result['feedback_reference_cross_check']['reference_limit_conditions'],
                         {'vin_v': 24.0, 'temperature_min_c': -40.0, 'temperature_max_c': 125.0})
        for case in result['static_cases']:
            self.assertFalse(case['vin_is_qualified_bound'])
            self.assertFalse(case['hardware_accepted'])
        self.assertIn('not an actual bound', result['static_cases'][-1]['description'])
        reserve = result['allocated_reserve_case']
        self.assertEqual(reserve['reserve_allocation_v'], .05)
        self.assertFalse(reserve['allocation_is_verified'])
        self.assertGreater(reserve['threshold']['rtop_threshold_ohm'],
                           result['static_cases'][1]['threshold']['rtop_threshold_ohm'])
        for key in ['hardware_accepted', 'fabrication_approved', 'procurement_approved',
                    'protection_qualified', 'full_6s_accepted', 'divider_selected', 'pcb_integrated']:
            self.assertFalse(result[key])

    def test_14_collect_has_no_shared_mutable_state(self):
        first = model.collect()
        second = model.collect()
        self.assertEqual(first, second)
        first['unknown_actual_inputs']['vdda_min_v'] = 3.3
        first['static_cases'][0]['inputs']['reference_floor'] = 3.3
        self.assertEqual(model.collect(), second)


if __name__ == '__main__':
    unittest.main(verbosity=2)
