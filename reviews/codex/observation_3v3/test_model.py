#!/usr/bin/env python3
"""Ten independent numeric, dimensional and rejection tests for ACT-07."""
import copy
import math
import unittest
import model


def fixture():
    return {"revision":"ACT-07", "native_accepted":False, "hardware_accepted":False,
            "parts_selected":False, "qualification_ports_implemented":False, "native_commands_rerun":False,
            "candidate_electrical_delta":0, "live_electrical_delta":0, "live_copper_delta":0,
            "proposal":{"reference_V":2.5,"reference_fraction":.002,"comparator_offset_abs_V":.010,
                "hysteresis_V":[0,.004],"bias_abs_A":5e-9,"resistor_fraction":.0035,"bottom_ohm":1000,
                "UV_top_ohm":249,"OV_top_ohm":402,"overdrive_V":.020,"detector_budget_ns":55,
                "downstream_budget_ns":245,"sense_settling_budget_ns":100,
                "normal_V":[3.219942244224422,3.412002431724654],"corridor_V":[3.,3.6],
                "slew_cases_V_per_us":[.01,.1,1.]}}


class AllocationTests(unittest.TestCase):
    def pair(self, actual, expected):
        self.assertEqual(len(actual),len(expected))
        for a,b in zip(actual,expected):
            self.assertAlmostEqual(a,b,places=11)

    def test_independent_threshold_fixture(self):
        r = model.analyze(fixture())
        self.pair(r["thresholds_V"]["UV"]["assert"],[3.0969529850675155,3.14563529100326])
        self.pair(r["thresholds_V"]["UV"]["recover"],[3.0994475112259607,3.1481367892471135])
        self.pair(r["thresholds_V"]["OV"]["assert"],[3.476999596437093,3.5359437320375084])
        self.pair(r["thresholds_V"]["OV"]["recover"],[3.4742012048077964,3.5331340842703236])
        self.assertAlmostEqual(r["margins_V"]["normal_UV_recovery"],.07180545497730861,places=11)
        self.assertAlmostEqual(r["margins_V"]["normal_OV_recovery"],.06219877308314237,places=11)

    def test_hysteresis_is_full_width_and_correct_polarity(self):
        c = fixture()
        c["proposal"].update(reference_fraction=0,comparator_offset_abs_V=0,bias_abs_A=0,resistor_fraction=0,hysteresis_V=[.004,.004])
        t = model.analyze(c)["thresholds_V"]
        self.assertAlmostEqual(t["UV"]["recover"][0]-t["UV"]["assert"][0],.004996,places=12)
        self.assertAlmostEqual(t["OV"]["assert"][0]-t["OV"]["recover"][0],.005608,places=12)
        self.assertAlmostEqual(t["UV"]["assert"][0],2.498*1.249,places=12)
        self.assertAlmostEqual(t["OV"]["assert"][0],2.502*1.402,places=12)

    def test_error_increase_cannot_improve_headroom(self):
        base = model.analyze(fixture())
        for key in ("reference_fraction","comparator_offset_abs_V","bias_abs_A","resistor_fraction"):
            c = fixture()
            c["proposal"][key] *= 2
            r = model.analyze(c)
            for side in ("UV","OV"):
                self.assertLess(r["overdrive_screen"]["headroom_to_corridor_V"][side],base["overdrive_screen"]["headroom_to_corridor_V"][side])

    def test_overdrive_cross_corner_bound(self):
        r = model.analyze(fixture())
        o = r["overdrive_screen"]
        self.assertAlmostEqual(o["maximum_divider_multiplier"]["UV"],1.2507491219267437,places=12)
        self.assertAlmostEqual(o["maximum_divider_multiplier"]["OV"],1.4048238835925742,places=12)
        self.assertAlmostEqual(o["rail_amplitude_V"]["UV"],3.0719380026289804,places=11)
        self.assertAlmostEqual(o["rail_amplitude_V"]["OV"],3.56404020970936,places=11)
        c = fixture()
        c["proposal"]["overdrive_V"] *= 2
        double = model.analyze(c)["overdrive_screen"]
        self.assertAlmostEqual(o["headroom_to_corridor_V"]["UV"]-double["headroom_to_corridor_V"]["UV"],.02*o["maximum_divider_multiplier"]["UV"],places=12)

    def test_time_and_slew_dimensions(self):
        r = model.analyze(fixture())
        self.assertEqual(r["total_budget_ns"],400)
        self.assertAlmostEqual(r["maximum_slew_V_per_us"]["UV"],.17984500657245106,places=11)
        self.assertAlmostEqual(r["maximum_slew_V_per_us"]["OV"],.08989947572660029,places=11)
        self.assertEqual(r["ramp_cases"][1]["additional_excursion_V"],.04000000000000001)
        c = fixture()
        for key in ("detector_budget_ns","downstream_budget_ns","sense_settling_budget_ns"):
            c["proposal"][key] *= 2
        slower = model.analyze(c)
        self.assertAlmostEqual(slower["maximum_slew_V_per_us"]["OV"],r["maximum_slew_V_per_us"]["OV"]/2,places=12)

    def test_declared_ramps_and_budget_exhaustion(self):
        r = model.analyze(fixture())
        self.assertEqual([p["conditional_allocation_pass"] for p in r["ramp_cases"]],[True,False,False])
        self.assertEqual(r["ramp_cases"][1]["positive_headroom"],{"UV":True,"OV":False})
        self.assertFalse(r["all_declared_cases_fit_allocation"])
        c = fixture()
        c["proposal"]["overdrive_V"] = .2
        exhausted = model.analyze(c)
        self.assertEqual(exhausted["maximum_slew_V_per_us"],{"UV":0.,"OV":0.})
        self.assertTrue(all(not x["conditional_allocation_pass"] for x in exhausted["ramp_cases"]))

    def test_invalid_or_nonfinite_allocations_rejected(self):
        invalid = [("reference_V",math.nan),("reference_V",True),("reference_fraction",1),
            ("resistor_fraction",-.1),("comparator_offset_abs_V",math.inf),("bias_abs_A",-1),
            ("bottom_ohm",0),("overdrive_V",0),("detector_budget_ns",0),
            ("hysteresis_V",[.004,0]),("hysteresis_V",[-.001,.004]),
            ("normal_V",[3.5,3.2]),("corridor_V",[3.2,3.3]),("slew_cases_V_per_us",[]),
            ("slew_cases_V_per_us",[0]),("slew_cases_V_per_us",[math.inf]),("reference_V","NaN")]
        for key,value in invalid:
            c = fixture()
            c["proposal"][key] = value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                model.analyze(c)
        c = fixture()
        del c["proposal"]["bias_abs_A"]
        with self.assertRaises(ValueError):
            model.analyze(c)

    def test_missing_or_promoted_qualifications_rejected(self):
        for key in ("native_accepted","hardware_accepted","parts_selected","qualification_ports_implemented","native_commands_rerun"):
            c = fixture()
            c[key] = True
            with self.subTest(promoted=key),self.assertRaises(ValueError):
                model.analyze(c)
            del c[key]
            with self.subTest(missing=key),self.assertRaises(ValueError):
                model.analyze(c)
        for key in ("candidate_electrical_delta","live_electrical_delta","live_copper_delta"):
            c = fixture()
            c[key] = 1
            with self.subTest(delta=key),self.assertRaises(ValueError):
                model.analyze(c)

    def test_conditional_fit_cannot_create_hardware_acceptance(self):
        c = fixture()
        c["proposal"]["slew_cases_V_per_us"] = [.001]
        r = model.analyze(c)
        self.assertTrue(r["all_declared_cases_fit_allocation"])
        for key in ("native_accepted","hardware_accepted","parts_selected","ramp_detection_qualified",
                    "parameters_are_sourced_guarantees","QUAL_OK_implemented","ACK_implemented","qualification_ports_implemented"):
            self.assertIs(r[key],False)
        self.assertEqual(r["verdict"],"conditional_allocation_only")

    def test_actual_contract_and_portable_hashes(self):
        r = model.collect()
        expected = model.analyze(fixture())
        for key in ("thresholds_V","margins_V","overdrive_screen","total_budget_ns","maximum_slew_V_per_us","ramp_cases"):
            self.assertEqual(r[key],expected[key])
        self.assertEqual(len(r["source_sha256"]),2)
        for path,digest in r["source_sha256"].items():
            self.assertFalse(path.startswith(("C:","/")))
            self.assertEqual(len(digest),64)


if __name__ == "__main__":
    unittest.main()
