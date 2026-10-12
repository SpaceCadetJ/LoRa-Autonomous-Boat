"""ACT-04 settled, zero-delay Boolean checks; no analog/timing/hardware proof."""
import argparse
import copy
import hashlib
import itertools
import json
from pathlib import Path
import unittest

P = Path(__file__).resolve().parent
BOOL = (False, True)
N = "/Actuators/ArmInterlock/"
MAP = {
    "U12": {"1": N+"ACK", "2": N+"ARM_LOW", "3": "unconnected-(U12-~{Q}-Pad3)",
            "4": "GND", "5": N+"READY", "6": N+"QUAL_OK", "7": "+3V3", "8": "+3V3"},
    "U13": {"1": "unconnected-(U13-NC-Pad1)", "2": "/ACT_EN_PC4", "3": "GND",
            "4": N+"ARM_LOW", "5": "+3V3"},
    "U14": {"1": N+"READY", "2": "GND", "3": "/ACT_EN_PC4",
            "4": "/Actuators/ACT_OE", "5": "+3V3", "6": N+"QUAL_OK"},
    "R41": {"1": "/ACT_EN_PC4", "2": "GND"},
    "R42": {"1": N+"QUAL_OK", "2": "GND"},
    "R43": {"1": N+"ACK", "2": "GND"},
}
DEVICES = {"U12": "flip_flop", "U13": "inverter", "U14": "and_gate"}


def booleans(*values):
    if any(type(value) is not bool for value in values):
        raise ValueError("Only explicit Boolean logic values are modeled.")


def output(qual, arm, ready):
    booleans(qual, arm, ready)
    return qual and arm and ready


def step(ready, previous_ack, qual, arm, ack):
    """Return READY, ACK history and OE after a settled ideal event."""
    booleans(ready, previous_ack, qual, arm, ack)
    if not qual:
        next_ready = False
    elif ack and not previous_ack:
        next_ready = not arm
    else:
        next_ready = ready
    return next_ready, ack, output(qual, arm, next_ready)


def contract_check(contract, review):
    """Bind the algebra to declared parts/nets; native verification is separate."""
    for ref, pins in MAP.items():
        if contract["candidate_memberships"][ref] != pins:
            raise ValueError("Unexpected logic wiring: " + ref)
    aliases = {"Q_N": "~{Q}", "CLR_N": "~{CLR}", "PRE_N": "~{PRE}"}
    for ref, key in DEVICES.items():
        part, source = contract["candidate_parts"][ref], review["sources"][key]
        if part["mpn"] != source["part"]:
            raise ValueError("Unexpected logic identity: " + ref)
        if {p: v[0] for p, v in part["pins"].items()} != {
                p: aliases.get(name, name) for p, name in source["pins"].items()}:
            raise ValueError("Unexpected logic pin function: " + ref)
    for ref in ("U4.6", "R40.1"):
        if contract["retained_pin_changes"][ref] != {
                "before": "/ACT_EN_PC4", "after": "/Actuators/ACT_OE"}:
            raise ValueError("Missing direct OE split: " + ref)
    for ref in ("R41", "R42", "R43"):
        if contract["candidate_parts"][ref]["value"] != "10k":
            raise ValueError("Unexpected default resistor: " + ref)
    if contract["qualification_ports_implemented"] is not False:
        raise ValueError("Qualification source must remain an unimplemented gate.")
    if review["hardware_accepted"] is not False or review["timing_qualified"] is not False:
        raise ValueError("Boolean checks cannot support qualification claims.")


class LatchTests(unittest.TestCase):
    def test_and_all_eight_combinations(self):
        for values in itertools.product(BOOL, repeat=3):
            with self.subTest(values=values):
                self.assertEqual(output(*values), values == (True, True, True))

    def test_all_32_state_input_combinations(self):
        for ready, previous, qual, arm, ack in itertools.product(BOOL, repeat=5):
            with self.subTest(state=(ready, previous), inputs=(qual, arm, ack)):
                new, history, oe = step(ready, previous, qual, arm, ack)
                if not qual:
                    self.assertFalse(new)
                    self.assertFalse(oe)
                elif (previous, ack) == (False, True):
                    self.assertEqual(new, not arm)
                    self.assertFalse(oe)
                else:
                    self.assertEqual(new, ready)
                    self.assertEqual(oe, arm and ready)
                self.assertEqual(history, ack)

    def test_valid_reset_covers_unknown_initial_q_and_held_inputs(self):
        for initial, held_ack, held_arm in itertools.product(BOOL, repeat=3):
            ready, previous, oe = step(initial, held_ack, False, held_arm, held_ack)
            self.assertEqual((ready, oe), (False, False))
            for _ in range(3):
                ready, previous, oe = step(ready, previous, True, held_arm, held_ack)
                self.assertEqual((ready, oe), (False, False))

    def test_fault_recovery_requires_new_ack_then_arm(self):
        ready, previous, oe = True, False, True
        events = [
            # qual, arm, ack, expected READY, expected OE
            (False, True, True, False, False),
            (True, True, True, False, False),
            (True, False, True, False, False),  # held ACK does not acknowledge
            (True, True, True, False, False),
            (True, False, False, False, False),
            (True, False, True, True, False),
            (True, False, False, True, False),
            (True, True, False, True, True),
        ]
        for qual, arm, ack, wanted, enabled in events:
            ready, previous, oe = step(ready, previous, qual, arm, ack)
            self.assertEqual((ready, oe), (wanted, enabled))

    def test_normal_disarm_retains_readiness(self):
        ready, previous, oe = step(True, False, True, False, False)
        self.assertEqual((ready, oe), (True, False))
        self.assertEqual(step(ready, previous, True, True, False), (True, False, True))

    def test_ack_while_armed_clears_readiness(self):
        state = step(True, False, True, True, True)
        self.assertEqual(state, (False, True, False))
        self.assertFalse(step(state[0], state[1], True, False, True)[0])
        self.assertFalse(step(state[0], state[1], True, True, True)[2])

    def test_no_reset_means_no_safe_startup_inference(self):
        self.assertTrue(step(True, True, True, True, True)[2])
        self.assertFalse(step(False, True, True, True, True)[2])

    def test_every_five_event_trace_from_valid_reset(self):
        for events in itertools.product(tuple(itertools.product(BOOL, repeat=3)), repeat=5):
            ready, previous, acknowledged = False, False, False
            for qual, arm, ack in events:
                if not qual:
                    acknowledged = False
                elif ack and not previous:
                    acknowledged = not arm
                ready, previous, oe = step(ready, previous, qual, arm, ack)
                self.assertEqual(ready, acknowledged)
                if oe:
                    self.assertTrue(qual and arm and acknowledged)

    def test_rejects_non_boolean_values(self):
        for bad in (None, 0, 1, -1, "", "false", float("nan"), float("inf"), [], {}):
            for index in range(5):
                values = [False] * 5
                values[index] = bad
                with self.assertRaises(ValueError):
                    step(*values)
            for index in range(3):
                values = [False] * 3
                values[index] = bad
                with self.assertRaises(ValueError):
                    output(*values)

    def test_declared_contract_matches_sources(self):
        contract_check(read_json("expected_contract.json"), read_json("source_review.json"))

    def test_rejects_changed_topology_identity_and_claims(self):
        contract, review = read_json("expected_contract.json"), read_json("source_review.json")
        mutations = [
            lambda c, r: c["candidate_memberships"]["U12"].update({"6": "+3V3"}),
            lambda c, r: c["candidate_memberships"]["U14"].update({"6": "+3V3"}),
            lambda c, r: c["candidate_memberships"]["U12"].update({"2": "/ACT_EN_PC4"}),
            lambda c, r: c["candidate_parts"]["U12"].update({"mpn": "SN74LVC2G74DCUR"}),
            lambda c, r: c["candidate_parts"]["U12"]["pins"].update({"5": ["~{Q}", "output"]}),
            lambda c, r: c["retained_pin_changes"]["R40.1"].update({"after": "/ACT_EN_PC4"}),
            lambda c, r: c["candidate_parts"]["R42"].update({"value": "1M"}),
            lambda c, r: c.update({"qualification_ports_implemented": True}),
            lambda c, r: r.update({"timing_qualified": True}),
            lambda c, r: r.update({"hardware_accepted": True}),
        ]
        for mutation in mutations:
            c, r = copy.deepcopy(contract), copy.deepcopy(review)
            mutation(c, r)
            with self.assertRaises(ValueError):
                contract_check(c, r)


def read_json(name):
    return json.loads((P/name).read_text(encoding="utf-8-sig"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--capture", action="store_true", help="Write logic_results.json after passing checks.")
    modes.add_argument("--check", action="store_true", help="Read-only comparison with captured input hashes/results.")
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(LatchTests)
    names = [test.id().split(".")[-1] for test in suite]
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        return 1
    record = {
        "schema": 1, "revision": "ACT-04",
        "classification": "settled_zero_delay_boolean_model_only",
        "passed": True, "test_count": result.testsRun, "tests": names,
        "enumerated_cases": {"and_combinations": 8, "state_input_combinations": 32,
                             "valid_reset_initial_cases": 8, "five_event_traces": 32768,
                             "contract_mutations": 10},
        "input_sha256": {name: hashlib.sha256((P/name).read_bytes()).hexdigest()
                         for name in ("test_latch.py", "expected_contract.json", "source_review.json")},
        "assumptions": ["Valid rails and valid reset already established.",
                        "Every event represents settled Boolean values after propagation.",
                        "Edges satisfy the separately documented timing/power contract."],
        "exclusions": ["No pulse width, setup, hold, recovery/removal or propagation model.",
                       "No analog startup, brownout, bounce, metastability or concurrent-edge proof.",
                       "No independent qualification, watchdog or receiver-ready source.",
                       "No native connectivity result; use the separate native verifier."],
        "hardware_accepted": False, "timing_qualified": False, "act03_fully_implemented": False,
    }
    path = P/"logic_results.json"
    if args.capture:
        path.write_text(json.dumps(record, indent=2)+"\n", encoding="utf-8")
        print("Captured logic_results.json; Boolean scope only.")
    elif args.check:
        if not path.exists() or read_json(path.name) != record:
            print("FAIL: logic_results.json is absent or stale; review changes before capture.")
            return 1
        print("Captured Boolean result and input hashes match; no files written.")
    else:
        print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
