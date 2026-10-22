#!/usr/bin/env python3
"""ACT-10 passive OE decay screen. Allocated inputs are not qualified circuit bounds."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from numbers import Real
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FALSE_CLAIMS = (
    "parts_selected", "hardware_tested", "fabrication_approved", "native_commands_rerun",
    "qualification_ports_implemented", "partial_power_isolation_qualified",
    "source_timing_applicable_to_RC_edge",
)
DELTAS = ("candidate_electrical_delta", "live_electrical_delta", "live_copper_delta")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value, name, positive=True):
    require(isinstance(value, Real) and not isinstance(value, bool)
            and math.isfinite(value), name + " must be a finite number")
    require(value > 0 if positive else value >= 0, name + " has an invalid sign")
    return float(value)


def decay_time_s(resistance_ohm, capacitance_F, initial_V, target_V, feed_A=0):
    """Time to fall to target under a constant positive feed; None if unreachable.

    V(t) = I*R + (V0-I*R)*exp(-t/(R*C)). This omits switch charge injection,
    nonlinear leakage, receiver thresholds, signal bounce and parasitic coupling.
    """
    r = number(resistance_ohm, "resistance_ohm")
    c = number(capacitance_F, "capacitance_F")
    v0 = number(initial_V, "initial_V")
    target = number(target_V, "target_V")
    feed = number(feed_A, "feed_A", False)
    require(target < v0, "target_V must be below initial_V")
    floor = r * feed
    require(math.isfinite(floor), "leakage floor overflow")
    if floor >= target:
        return None
    result = r * c * math.log1p((v0 - target) / (target - floor))
    require(math.isfinite(result) and result > 0, "decay time is not finite and positive")
    return result


def calculate(contract):
    require(isinstance(contract, dict), "contract must be an object")
    require(contract.get("packet") == "ACT-10", "wrong packet")
    require(contract.get("status") == "investigation_only_not_native", "status must remain investigation only")
    for key in FALSE_CLAIMS:
        require(contract.get(key) is False, key + " must explicitly remain false")
    for key in ("native_accepted", "hardware_accepted", "physical_OE_proven"):
        require(contract.get(key, False) is False, key + " must remain false")
    for key in DELTAS:
        require(key in contract and number(contract[key], key, False) == 0, key + " must remain zero")
    a = contract.get("assumptions")
    require(isinstance(a, dict), "assumptions must be an object")
    required = (
        "R40_nominal_ohm", "R40_tolerance_fraction_allocated", "initial_OE_V_allocated",
        "target_OE_V_allocated", "feed_current_A_allocated", "downstream_budget_ns_allocated",
        "control_to_switch_start_ns_screen", "TXU_disable_ns_screen", "other_logic_ns_optimistic",
    )
    require(all(key in a for key in required), "missing numeric assumption")
    zero_allowed = ("R40_tolerance_fraction_allocated", "feed_current_A_allocated", "other_logic_ns_optimistic")
    n = {key: number(a[key], key, key not in zero_allowed) for key in required}
    require(n["R40_tolerance_fraction_allocated"] < 1, "resistance tolerance must be below 100 percent")
    caps = a.get("capacitance_pF_cases")
    require(isinstance(caps, list) and len(caps) > 0, "capacitance cases must be nonempty")
    caps = [number(cap, "capacitance_pF_cases") for cap in caps]
    r = n["R40_nominal_ohm"] * (1 + n["R40_tolerance_fraction_allocated"])
    require(math.isfinite(r), "R_max_ohm overflow")
    v0, target = n["initial_OE_V_allocated"], n["target_OE_V_allocated"]
    feed = n["feed_current_A_allocated"]
    budget = n["downstream_budget_ns_allocated"]
    fixed = n["control_to_switch_start_ns_screen"] + n["TXU_disable_ns_screen"] + n["other_logic_ns_optimistic"]
    require(math.isfinite(fixed), "fixed timing overflow")
    floor = r * feed
    cases = []
    for cap in caps:
        capacitance = cap * 1e-12
        time = decay_time_s(r, capacitance, v0, target, feed)
        decay_ns = None if time is None else time * 1e9
        downstream = None if time is None else fixed + decay_ns
        margin = None if downstream is None else budget - downstream
        cases.append({
            "C_pF": cap, "floor_V": floor, "decay_ns": decay_ns,
            "downstream_screen_ns": downstream, "margin_ns": margin,
            "fits_allocation_only": margin is not None and margin >= 0,
            "slope_at_target_ns_per_V": None if time is None else r * capacitance / (target - floor) * 1e9,
        })
    # One farad gives the time-per-capacitance coefficient without a second formula.
    seconds_per_farad = decay_time_s(r, 1.0, v0, target, feed)
    remaining_ns = budget - fixed
    maximum_cap = (remaining_ns * 1e-9 / seconds_per_farad * 1e12
                   if seconds_per_farad is not None and remaining_ns > 0 else None)
    result = {
        "packet": "ACT-10", "scope": "allocated_constant_feed_RC_screen_only",
        "native_accepted": False, "hardware_accepted": False, "physical_OE_proven": False,
        **{key: False for key in FALSE_CLAIMS}, **{key: 0 for key in DELTAS},
        "R_max_ohm": r, "fixed_screen_ns": fixed, "available_decay_ns": remaining_ns,
        "maximum_C_pF_at_zero_margin": maximum_cap,
        "maximum_feed_A_at_asymptote": target / r,
        "maximum_feed_interpretation": "Strictly less than this value is necessary to reach the target in finite time; it is not a component leakage guarantee.",
        "slope_interpretation": "Magnitude abs(dt/dV) at target, in ns/V. Actual dt/dV is negative. This is a local RC slope, not a valid digital-input edge specification.",
        "timing_applicability": "55 ns and 36 ns are screening inputs from different source tests with fast control edges and different loads. Adding them to an RC decay does not establish an end-to-end bound.",
        "limitations": [
            "Resistance tolerance, capacitance, initial voltage, total constant feed and target are allocations, not a selected and verified component envelope.",
            "No guaranteed arbitrary partial-power isolation, charge injection, slew qualification or propagation through the missing authority logic is modeled.",
            "A positive numeric margin does not authorize native implementation, fabrication, hardware use or a claim of motor stop.",
        ],
        "assumptions": a, "cases": cases,
    }
    json.dumps(result, allow_nan=False)
    return result


def collect(contract_path=None, model_path=None):
    paths = [Path(contract_path) if contract_path is not None else HERE / "contract.json",
             Path(model_path) if model_path is not None else HERE / "model.py"]
    result = calculate(json.loads(paths[0].read_text(encoding="utf-8")))
    result["input_sha256"] = {key: hashlib.sha256(path.read_bytes()).hexdigest()
                              for key, path in zip(("contract.json", "model.py"), paths)}
    return result


def check_record(record, contract_path=None, model_path=None):
    require(record == collect(contract_path, model_path), "analysis.json is stale or modified")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    output = HERE / "analysis.json"
    if args.write:
        with output.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(collect(), indent=2, allow_nan=False) + "\n")
        print("Captured ACT-10 allocated RC screen; no circuit acceptance.")
    else:
        check_record(json.loads(output.read_text(encoding="utf-8")))
        print("PASS: ACT-10 allocated RC screen and input hashes reproduce.")


if __name__ == "__main__":
    main()
