#!/usr/bin/env python3
"""Independent numeric fixtures and rejection tests for the ACT-06 screen."""
import copy
import math
import unittest
import model


class ArithmeticTests(unittest.TestCase):
    def pair(self, actual, expected, places=10):
        self.assertEqual(len(actual), len(expected))
        for a, b in zip(actual, expected):
            self.assertAlmostEqual(a, b, places=places)

    def test_five_integrated_fixtures(self):
        fixtures = [
            ([3.1449,3.1911],[3.4089,3.4551],[3.154404,3.216444],[3.381444,3.444804]),
            ([3.1119,3.1581],[3.4419,3.4881],[3.121305,3.18318],[3.41418,3.477705]),
            ([3.0789,3.1251],[3.4749,3.5211],[3.088206,3.149916],[3.446916,3.510606]),
            ([3.0459,3.0921],[3.5079,3.5541],[3.055107,3.116652],[3.479652,3.543507]),
            ([4.715,4.785],[5.215,5.285],[4.72925,4.823],[5.173,5.26925])]
        for args, fixture in zip(model.INTEGRATED, fixtures):
            with self.subTest(part=args[2]):
                c = model.integrated_case(*args)
                for actual, expected in zip([c["assert_V"]["UV"],c["assert_V"]["OV"],c["release_V"]["UV"],c["release_V"]["OV"]], fixture):
                    self.pair(actual, expected)

    def test_integrated_no_trip_is_not_recovery(self):
        c = model.integrated_case(*model.INTEGRATED[-1])
        self.assertGreater(c["margins_V"]["no_trip_upper"], 0)
        self.assertLess(c["margins_V"]["recovery_upper"], 0)
        self.assertFalse(c["static_screen_pass"])
        c = model.integrated_case(*model.INTEGRATED[1])
        self.assertAlmostEqual(c["margins_V"]["recovery_upper"], .002177568275346, places=12)

    def test_hysteresis_sensitivity_is_separate(self):
        for args in model.INTEGRATED:
            c = model.integrated_case(*args)
            alt = c["actual_trip_hysteresis_sensitivity"]
            self.assertNotEqual(c["release_V"], alt["release_V"])
            self.assertEqual(c["static_screen_pass"], alt["static_screen_pass"])
        c = model.integrated_case(*model.INTEGRATED[1])
        self.assertAlmostEqual(c["actual_trip_hysteresis_sensitivity"]["release_V"]["OV"][0], 3.4143648)

    def test_overdrive_uses_nominal_denominator_and_no_failure_prediction(self):
        fixtures = [(2.9865,3.6267),(2.95515,3.66135),(2.9238,3.696),(2.89245,3.73065),(4.4775,5.5475)]
        for args, expected in zip(model.INTEGRATED, fixtures):
            t = model.integrated_case(*args)["timing_step_screen"]
            self.pair([t["UV_test_rail_V"],t["OV_test_rail_V"]], expected)
            self.assertLess(t["UV_corridor_margin_V"], 0)
            self.assertLess(t["OV_corridor_margin_V"], 0)
            self.assertFalse(t["guarantee_established"])
            self.assertNotEqual(t["UV_test_rail_V"], t["earlier_actual_trip_denominator_sensitivity_V"]["UV"])

    def test_signed_bias_KCL(self):
        self.assertAlmostEqual(model.divider_voltage(.4,9000,1000,25e-9), 4.000225)
        self.assertAlmostEqual(model.divider_voltage(.4,9000,1000,-25e-9), 3.999775)
        c = model.divider_currents([4,4],[9000],1000,0,25e-9)
        self.pair(c["rail_top_current_A"], [.0003999975,.0004000025], places=13)
        self.pair(c["ground_bottom_current_A"], [.0003999775,.0004000225], places=13)

    def test_initial_divider_fixtures(self):
        fixtures = {
            "3V3": ([3.0517924077647356,3.165698198025526],[3.5061752548631873,3.589963493375325],
                    [3.1227683318406596,3.197353453280781],[3.4264867733447053,3.5544204703523024]),
            "5V": ([4.596599600671829,4.769001501228728],[5.335922577609891,5.464297797610111],
                   [4.703503596675826,4.816688788516016],[5.214647352834666,5.41019769751001])}
        for rail, fixture in fixtures.items():
            c = model.divider_case(rail,"initial_0p1")
            for actual, expected in zip([c["assert_V"]["UV"],c["assert_V"]["OV"],c["release_V"]["UV"],c["release_V"]["OV"]], fixture):
                self.pair(actual, expected)
            self.assertTrue(c["static_screen_pass"])
            self.assertFalse(c["bias_applicability_at_threshold_qualified"])

    def test_temperature_divider_fixtures(self):
        fixtures = {
            "3V3": ([3.0385011979204037,3.1795609612512545],[3.4906628116054934,3.6059329940330036],
                    [3.1091680140639015,3.2113548398262672],[3.411326892322982,3.5702318600641125]),
            "5V": ([4.575603341642377,4.790900648933142],[5.311284008267937,5.489662315808455],
                   [4.682019036709642,4.8388069208849736],[5.190568761631165,5.435311086505896])}
        for rail, fixture in fixtures.items():
            c = model.divider_case(rail,"temperature_sensitivity_0p35")
            for actual, expected in zip([c["assert_V"]["UV"],c["assert_V"]["OV"],c["release_V"]["UV"],c["release_V"]["OV"]], fixture):
                self.pair(actual, expected)
        c = model.divider_case("3V3","temperature_sensitivity_0p35")
        self.assertLess(c["margins_V"]["late_OV"],0)
        self.assertLess(c["margins_V"]["recovery_upper"],0)
        self.assertFalse(c["static_screen_pass"])

    def test_series_top_tolerance_never_RSS(self):
        points = model.resistor_endpoints([12400,100],.0035)
        self.assertEqual(len(points),4)
        self.pair([min(points),max(points)],[12456.25,12543.75])
        for threshold in model.THRESHOLDS_V.values():
            self.pair(model.divider_bounds([12400,100],1000,.0035,threshold,15e-9),
                      model.divider_bounds([12500],1000,.0035,threshold,15e-9))

    def test_continuous_ratio_empty_and_budget_suprema(self):
        f = model.resistor_feasibility()
        c = model.ov_ratio_interval(.0035)
        self.pair([c["required_ratio_lower_exclusive"],c["allowed_ratio_upper_exclusive"]],
                  [7.871757910199671,7.855417351603938])
        self.assertFalse(c["has_feasible_ratio"])
        self.assertAlmostEqual(f["any_3V3_OV_ratio_budget_supremum_fraction"],.002980504744227841,places=13)
        self.assertAlmostEqual(f["fixed_proposal_budget_suprema_fraction"]["3V3_OV"],.0025726613182573965,places=13)
        self.assertTrue(model.ov_ratio_interval(.0029)["has_feasible_ratio"])
        self.assertFalse(model.ov_ratio_interval(.0030)["has_feasible_ratio"])

    def test_invalid_numeric_inputs_rejected(self):
        calls = [lambda:model.divider_voltage(.4,-1,1000,0),lambda:model.divider_voltage(.4,1000,0,0),
                 lambda:model.divider_voltage(.4,1000,1000,math.nan),
                 lambda:model.resistor_endpoints([1000],-.001),lambda:model.resistor_endpoints([1000],1),
                 lambda:model.divider_bounds([1000],1000,.001,[.404,.396],15e-9),
                 lambda:model.ov_ratio_interval(-.001),lambda:model.integrated_case("3V3",math.nan,"invalid")]
        for call in calls:
            with self.assertRaises(ValueError):
                call()


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = model.read_json(model.HERE/"contract.json")
        cls.prior = model.read_json(model.HERE.parent/"rail_qualification/analysis.json")

    def reject(self, mutate):
        c = copy.deepcopy(self.contract)
        mutate(c)
        with self.assertRaises(ValueError):
            model.validate_contract(c,self.prior)

    def test_actual_contract(self):
        model.validate_contract(self.contract,self.prior)

    def test_unverified_identity_rejected(self):
        self.reject(lambda c:c["integrated"]["cases"][-1].update(part="TPS3703A6500DSER",window_fraction=.06))

    def test_wrong_overdrive_or_accuracy_rejected(self):
        self.reject(lambda c:c["integrated"].update(detect_overdrive_fraction=.025))
        self.reject(lambda c:c["integrated"].update(accuracy_fraction_of_nominal_rail=.005))

    def test_divider_polarity_and_bias_qualification_rejected(self):
        self.reject(lambda c:c["adjustable"].update(falling_threshold_V=[.396,.404]))
        self.reject(lambda c:c["adjustable"].update(bias_applicability_at_threshold_verified=True))

    def test_unreviewed_resistor_values_or_budgets_rejected(self):
        self.reject(lambda c:c["adjustable"]["dividers"]["3V3"].update(UV_top_ohm=6810))
        self.reject(lambda c:c["adjustable"]["resistor_budgets"][1].update(fraction=.001))

    def test_acceptance_and_nonzero_delta_rejected(self):
        for key in ("hardware_accepted","parts_selected","QUAL_OK_implemented","ACK_implemented","hardware_failure_predicted"):
            self.reject(lambda c,k=key:c.update({k:True}))
        self.reject(lambda c:c.update(candidate_electrical_delta=1))
        self.reject(lambda c:c["interface"].update(direct_fault_bus_to_QUAL_OK_accepted=True))

    def test_prior_converter_change_rejected(self):
        p = copy.deepcopy(self.prior)
        p["cases"][0]["converter_V"][1] = 3.3
        with self.assertRaises(ValueError):
            model.validate_contract(self.contract,p)

    def test_portable_inputs_and_output_holds(self):
        r = model.collect()
        self.assertEqual(len(r["integrated_cases"]),5)
        self.assertEqual(len(r["divider_cases"]),4)
        self.assertEqual(len(r["source_sha256"]),5)
        for path,digest in r["source_sha256"].items():
            self.assertFalse(path.startswith(("/","C:")))
            self.assertEqual(digest,model.sha(model.ROOT/path))
        self.assertFalse(r["hardware_accepted"])
        self.assertFalse(r["hardware_failure_predicted"])
        self.assertFalse(r["summary"]["selection_accepted"])
        for c in r["integrated_cases"]+r["divider_cases"]:
            self.assertFalse(c["hardware_accepted"])
            self.assertFalse(c["dynamic_screen_pass"])

    def test_stale_or_forged_record_rejected(self):
        current = model.collect()
        mutations = [lambda r:r.update(hardware_accepted=True),
                     lambda r:r["integrated_cases"][0]["timing_step_screen"].update(guarantee_established=True),
                     lambda r:r["divider_cases"][1]["release_V"]["OV"].__setitem__(0,3.5),
                     lambda r:r["source_sha256"].update({next(iter(r["source_sha256"])):"0"*64})]
        for mutate in mutations:
            saved = copy.deepcopy(current)
            mutate(saved)
            with self.assertRaises(ValueError):
                model.check_record(saved,current)
        model.check_record(copy.deepcopy(current),current)


if __name__ == "__main__":
    unittest.main()
