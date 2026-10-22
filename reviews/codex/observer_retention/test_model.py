#!/usr/bin/env python3
"""Independent fixtures and fault/edge tests for the conditional ACT-09 model."""
import copy
import unittest

import model


def fixture():
    return {**{k: False for k in model.CLAIMS}, **{k: 0 for k in model.DELTAS},
            "proposal": {"same_rail_overdrive_V": 3.0719380026289804,
                         "same_rail_valid_floor_V": 3.005, "total_response_ns": 400,
                         "slew_V_per_us": [0.01, 0.1, 1.0],
                         "island_start_source_min_V": 3.219942244224422,
                         "blocking_drop_max_V": 0.1, "island_valid_floor_V": 3.005,
                         "island_total_load_A": 0.005, "reverse_leakage_A": 0.0001,
                         "island_ESR_ohm": 0.1, "effective_capacitance_F": [1e-6, 4.7e-6, 1e-5],
                         "isolation_completion_allocated_s": 0.0001,
                         "qualification_ns": 1000000, "clear_hold_ns": 1000,
                         "release_guard_ns": 100, "arm_guard_ns": 100}}


class RetentionModelTests(unittest.TestCase):
    def setUp(self):
        self.c = fixture()
        self.p = self.c["proposal"]
        self.events = model.demonstration_events(self.p)

    def test_numeric_fixtures_and_strict_margins(self):
        result = model.calculate(self.c)
        same, held = result["same_rail"], result["held_island"]
        self.assertAlmostEqual(same["headroom_V"], 0.0669380026289804, places=12)
        self.assertAlmostEqual(same["maximum_slew_V_per_us"], 0.167345006572451, places=12)
        self.assertAlmostEqual(same["cases"][1]["residual_V"], 0.0269380026289804, places=12)
        self.assertEqual([r["fits_conditional_deadline_only"] for r in same["cases"]], [True, True, False])
        self.assertAlmostEqual(held["initial_after_drops_V"], 3.119432244224422, places=12)
        self.assertAlmostEqual(held["cases"][0]["time_to_valid_floor_s"] * 1e6, 22.437694945965, places=9)
        self.assertAlmostEqual(held["cases"][1]["time_to_valid_floor_s"] * 1e6, 105.4571662460, places=8)
        self.assertEqual([r["fits_allocated_isolation_deadline_only"] for r in held["cases"]], [False, True, True])
        self.assertFalse(result["physical_disabled_after_hold_up"])

    def test_charge_scaling_and_nonpositive_headroom(self):
        baseline = model.calculate(self.c)["held_island"]["cases"][0]["time_to_valid_floor_s"]
        self.p["effective_capacitance_F"] = [2e-6]
        self.assertAlmostEqual(model.calculate(self.c)["held_island"]["cases"][0]["time_to_valid_floor_s"], 2 * baseline)
        self.p["blocking_drop_max_V"] = 0.3
        held = model.calculate(self.c)["held_island"]
        self.assertIsNone(held["effective_capacitance_at_zero_margin_F"])
        self.assertEqual(held["cases"][0]["time_to_valid_floor_s"], 0)
        self.assertFalse(held["cases"][0]["fits_allocated_isolation_deadline_only"])

    def test_claim_mutations_and_bad_numeric_input_rejected(self):
        for key in model.CLAIMS + ("physical_disabled_after_hold_up", "physical_OE_proven"):
            changed = copy.deepcopy(self.c)
            changed[key] = True
            with self.subTest(key=key), self.assertRaises(ValueError):
                model.calculate(changed)
        for key in model.DELTAS:
            changed = copy.deepcopy(self.c)
            changed[key] = 1
            with self.subTest(key=key), self.assertRaises(ValueError):
                model.calculate(changed)
        for value in (float("nan"), float("inf"), -1, True, "0.1"):
            changed = copy.deepcopy(self.c)
            changed["proposal"]["reverse_leakage_A"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                model.calculate(changed)
        changed = copy.deepcopy(self.c)
        changed["proposal"]["effective_capacitance_F"] = []
        with self.assertRaises(ValueError):
            model.calculate(changed)
        changed["proposal"]["effective_capacitance_F"] = [1e308]
        with self.assertRaises(ValueError):
            model.calculate(changed)

    def test_startup_bootstrap_and_deliberate_ack_arm(self):
        result = model.simulate(self.events["healthy_startup_ack_arm"], self.p)
        rows = result["trace"]
        self.assertTrue(rows[0]["REF_EN_requested"])
        self.assertFalse(rows[0]["inputs"]["reference_valid"])
        self.assertFalse(rows[0]["QUAL_requested"])
        self.assertTrue(rows[2]["QUAL_requested"])
        self.assertFalse(rows[2]["READY_requested"])
        self.assertTrue(rows[3]["READY_requested"])
        self.assertFalse(rows[3]["OUTPUT_ENABLE_requested"])
        self.assertTrue(rows[-1]["OUTPUT_ENABLE_requested"])
        self.assertTrue(result["timing_contract_met"])
        self.assertFalse(result["physical_OE_proven"])

    def test_bounce_restarts_interval_and_requires_fresh_ack(self):
        result = model.simulate(self.events["fault_bounce_fresh_requalification"], self.p)
        rows = result["trace"]
        self.assertTrue(result["timing_contract_met"])
        self.assertFalse(rows[5]["READY_requested"])
        self.assertFalse(rows[7]["QUAL_requested"])
        self.assertTrue(rows[9]["QUAL_requested"])
        self.assertFalse(rows[9]["READY_requested"])
        self.assertTrue(rows[-1]["OUTPUT_ENABLE_requested"])
        # A tick just short of the new healthy interval cannot reuse old credit.
        ev = copy.deepcopy(self.events["fault_bounce_fresh_requalification"][:9])
        ev.append({"t_ns": ev[-1]["t_ns"] + self.p["qualification_ns"] - 1})
        self.assertFalse(model.simulate(ev, self.p)["trace"][-1]["QUAL_requested"])

    def test_held_ack_blocks_rearming_after_fault(self):
        result = model.simulate(self.events["held_ack_blocks"], self.p)
        self.assertTrue(result["timing_contract_met"])
        self.assertTrue(result["trace"][-1]["inputs"]["ack"])
        self.assertFalse(result["trace"][-1]["QUAL_requested"])
        self.assertFalse(result["trace"][-1]["READY_requested"])
        self.assertFalse(result["trace"][-1]["OUTPUT_ENABLE_requested"])

    def test_ack_with_stable_arm_high_captures_not_arm(self):
        ev = copy.deepcopy(self.events["healthy_startup_ack_arm"])
        last = ev[-1]["t_ns"]
        ev.extend([{"t_ns": last + 100, "inputs": {"ack": False}},
                   {"t_ns": last + 200, "inputs": {"ack": True}}])
        result = model.simulate(ev, self.p)
        self.assertTrue(result["timing_contract_met"])
        self.assertTrue(result["trace"][-1]["QUAL_requested"])
        self.assertFalse(result["trace"][-1]["READY_requested"])
        self.assertFalse(result["trace"][-1]["OUTPUT_ENABLE_requested"])

    def test_each_missing_or_unknown_permission_blocks(self):
        good = {k: True for k in model.HEALTH}
        for key in model.HEALTH:
            for value in (False, None):
                events = [{"t_ns": 0, "inputs": {**good, key: value}}, {"t_ns": 2000000}]
                with self.subTest(key=key, value=value):
                    last = model.simulate(events, self.p)["trace"][-1]
                    self.assertFalse(last["QUAL_requested"])
                    self.assertFalse(last["OUTPUT_ENABLE_requested"])
        for key in ("ack", "arm"):
            events = [{"t_ns": 0, "inputs": {**good, key: None}}, {"t_ns": 2000000}]
            self.assertFalse(model.simulate(events, self.p)["trace"][-1]["QUAL_requested"])
        self.assertFalse(model.simulate([{"t_ns": 0}, {"t_ns": 2000000}], self.p)["trace"][-1]["QUAL_requested"])

    def test_guard_loss_removes_reference_request(self):
        result = model.simulate(self.events["guard_loss_reference_off"], self.p)
        self.assertTrue(result["timing_contract_met"])
        last = result["trace"][-1]
        self.assertFalse(last["REF_EN_requested"])
        self.assertFalse(last["QUAL_requested"])
        self.assertFalse(last["READY_requested"])
        self.assertFalse(last["OUTPUT_ENABLE_requested"])

    def test_timing_races_are_flagged_and_latch_request_lockout(self):
        cases = [self.events["coincident_release_ack_unqualified"]]
        early_ack = copy.deepcopy(self.events["healthy_startup_ack_arm"][:4])
        early_ack[-1]["t_ns"] -= 1
        cases.append(early_ack)
        setup = copy.deepcopy(self.events["healthy_startup_ack_arm"][:4])
        setup[-1]["inputs"]["arm"] = True
        cases.append(setup)
        hold = copy.deepcopy(self.events["healthy_startup_ack_arm"])
        hold[-1]["t_ns"] -= 1
        cases.append(hold)
        reset = copy.deepcopy(self.events["healthy_startup_ack_arm"][:4])
        reset.append({"t_ns": reset[-1]["t_ns"] + 1, "inputs": {"rail_ok": False}})
        cases.append(reset)
        arm_fault = copy.deepcopy(self.events["healthy_startup_ack_arm"])
        arm_fault[-1]["inputs"]["rail_ok"] = False
        cases.append(arm_fault)
        near_arm = copy.deepcopy(self.events["healthy_startup_ack_arm"])
        near_arm.append({"t_ns": near_arm[-1]["t_ns"] + 99, "inputs": {"rail_ok": False}})
        cases.append(near_arm)
        for events in cases:
            with self.subTest(events=events):
                result = model.simulate(events, self.p)
                self.assertFalse(result["timing_contract_met"])
                self.assertTrue(result["timing_violations"])
                self.assertFalse(result["trace"][-1]["OUTPUT_ENABLE_requested"])
                self.assertFalse(result["trace"][-1]["QUAL_requested"])
        # Recovery does not erase a previous timing failure from the trace.
        ev = copy.deepcopy(cases[0])
        ev.extend([{"t_ns": 2000000, "inputs": {"ack": False, "arm": False}}, {"t_ns": 4000000}])
        self.assertFalse(model.simulate(ev, self.p)["trace"][-1]["QUAL_requested"])

    def test_minimum_clear_hold_is_separate_from_qualification(self):
        self.p["qualification_ns"] = 100
        self.p["clear_hold_ns"] = 1000
        ev = [{"t_ns": 0, "inputs": {k: True for k in model.HEALTH}},
              {"t_ns": 100}, {"t_ns": 999}, {"t_ns": 1000}]
        rows = model.simulate(ev, self.p)["trace"]
        self.assertEqual([r["QUAL_requested"] for r in rows], [False, False, False, True])

    def test_malformed_events_and_timing_are_rejected(self):
        cases = ([], [{"t_ns": -1}], [{"t_ns": True}], [{"t_ns": 1.0}],
                 [{"t_ns": 0}, {"t_ns": 0}], [{"t_ns": 1}, {"t_ns": 0}],
                 [{"t_ns": 0, "inputs": {"rail_ok": 1}}],
                 [{"t_ns": 0, "inputs": {"unknown": True}}])
        for events in cases:
            with self.subTest(events=events), self.assertRaises(ValueError):
                model.simulate(events, self.p)
        self.p["arm_guard_ns"] = 0
        with self.assertRaises(ValueError):
            model.simulate([{"t_ns": 0}], self.p)


if __name__ == "__main__":
    unittest.main()
