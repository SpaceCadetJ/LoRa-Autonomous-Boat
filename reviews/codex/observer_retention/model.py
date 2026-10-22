#!/usr/bin/env python3
"""ACT-09 conditional power deadline and request sequencer; no physical pin proof.

Only explicit event times are evaluated. Between events, supplied inputs are
assumed constant. A tick is required at a desired timer deadline. Unknown input
values fail closed. A timing violation latches request lockout for that trace;
this is conservative analysis behavior, not a claim about hardware priority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from numbers import Real
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
HEALTH = ("guard_ok", "reference_valid", "rail_ok", "local5v_ok",
          "remote_ready", "watchdog_ok", "stop_ok")
INPUTS = HEALTH + ("ack", "arm")
CLAIMS = ("native_accepted", "hardware_accepted", "parts_selected",
          "qualification_ports_implemented", "native_commands_rerun")
DELTAS = ("candidate_electrical_delta", "live_electrical_delta", "live_copper_delta")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value, name, positive=False):
    require(isinstance(value, Real) and not isinstance(value, bool)
            and math.isfinite(value), name + " must be a finite number")
    require(value > 0 if positive else value >= 0, name + " has an invalid sign")
    return float(value)


def integer(value, name, positive=False):
    require(isinstance(value, int) and not isinstance(value, bool), name + " must be an integer")
    require(value > 0 if positive else value >= 0, name + " has an invalid sign")
    return value


def vector(value, name):
    require(isinstance(value, (list, tuple)) and len(value) > 0, name + " must be nonempty")
    return [number(v, name, True) for v in value]


def timing(proposal):
    require(isinstance(proposal, dict), "proposal must be an object")
    keys = ("qualification_ns", "clear_hold_ns", "release_guard_ns", "arm_guard_ns")
    require(all(k in proposal for k in keys), "proposal is missing a timing allocation")
    return {k: integer(proposal[k], k, True) for k in keys}


def calculate(contract):
    require(isinstance(contract, dict), "contract must be an object")
    for key in CLAIMS:
        require(key in contract and contract[key] is False, key + " must explicitly remain false")
    for key in ("physical_disabled_after_hold_up", "native_implemented", "input_ports_qualified",
                "QUAL_OK_implemented", "ACK_implemented", "physical_OE_proven"):
        require(contract.get(key, False) is False, key + " must remain false")
    for key in DELTAS:
        require(key in contract and number(contract[key], key) == 0, key + " must remain zero")
    p = contract.get("proposal")
    t = timing(p)
    scalar_keys = ("same_rail_overdrive_V", "same_rail_valid_floor_V", "total_response_ns",
                   "island_start_source_min_V", "blocking_drop_max_V", "island_valid_floor_V",
                   "island_total_load_A", "reverse_leakage_A", "island_ESR_ohm",
                   "isolation_completion_allocated_s")
    require(all(k in p for k in scalar_keys), "proposal is missing a numeric allocation")
    zero_allowed = ("blocking_drop_max_V", "reverse_leakage_A", "island_ESR_ohm")
    a = {k: number(p[k], k, k not in zero_allowed) for k in scalar_keys}
    require("slew_V_per_us" in p and "effective_capacitance_F" in p,
            "proposal is missing a numeric vector")
    slews = vector(p["slew_V_per_us"], "slew_V_per_us")
    caps = vector(p["effective_capacitance_F"], "effective_capacitance_F")
    headroom = a["same_rail_overdrive_V"] - a["same_rail_valid_floor_V"]
    response_us = a["total_response_ns"] / 1000
    current = a["island_total_load_A"] + a["reverse_leakage_A"]
    esr_drop = current * a["island_ESR_ohm"]
    initial = a["island_start_source_min_V"] - a["blocking_drop_max_V"] - esr_drop
    island_headroom = initial - a["island_valid_floor_V"]
    deadline = a["isolation_completion_allocated_s"]
    cases = []
    for cap in caps:
        charge = cap * max(0, island_headroom)
        duration = charge / current
        cases.append({"effective_capacitance_F": cap, "available_charge_C": charge,
                      "time_to_valid_floor_s": duration, "isolation_margin_s": duration - deadline,
                      "fits_allocated_isolation_deadline_only": duration > deadline,
                      "physical_disabled_after_hold_up": False})
    result = {
        "schema": 1, "revision": "ACT-09", "verdict": "conditional_architecture_and_request_model",
        **{k: False for k in CLAIMS}, **{k: 0 for k in DELTAS},
        "physical_disabled_after_hold_up": False, "physical_OE_proven": False,
        "same_rail": {
            "overdrive_V": a["same_rail_overdrive_V"], "valid_floor_V": a["same_rail_valid_floor_V"],
            "headroom_V": headroom, "response_ns": a["total_response_ns"],
            "maximum_slew_V_per_us": max(0, headroom / response_us),
            "strictly_below_maximum_slew_required": True,
            "cases": [{"slew_V_per_us": s, "additional_excursion_V": s * response_us,
                       "residual_V": headroom - s * response_us,
                       "fits_conditional_deadline_only": headroom - s * response_us > 0}
                      for s in slews]},
        "held_island": {
            "source_min_V": a["island_start_source_min_V"], "blocking_drop_max_V": a["blocking_drop_max_V"],
            "total_discharge_current_A": current, "initial_ESR_drop_V": esr_drop,
            "initial_after_drops_V": initial, "valid_floor_V": a["island_valid_floor_V"],
            "headroom_V": island_headroom, "isolation_deadline_s": deadline,
            "effective_capacitance_at_zero_margin_F": current * deadline / island_headroom
                if island_headroom > 0 else None,
            "cases": cases, "physical_disabled_after_hold_up": False},
        "sequencing_allocations_ns": t,
        "formulas": {
            "same_rail": "headroom = overdrive - valid_floor; residual = headroom - slew*(response_ns/1000)",
            "island": "I = load + reverse_leakage; V0 = source_min - blocking_drop - I*ESR; Q = C*max(0,V0-valid_floor); t = Q/I",
            "isolation_margin": "time_to_valid_floor - allocated_isolation_deadline; positive margin is conditional only"},
        "limitations": [
            "Same-rail detection has a finite deadline and does not retain a valid disabled state through arbitrary brownout.",
            "Hold-up allocations are not chosen components, measured loads, leakage bounds or qualified detection/disable delays.",
            "A finite held island expires at its validity floor; a stalled or prolonged rail fault can exhaust it. Physical disable after that remains unproven.",
            "Reverse blocking does not supply overvoltage protection, reference startup bounds, injection isolation or valid existing U14 behavior.",
            "Sequencer outputs are logical requests, not physical pins; unimplemented input sources default disabled.",
            "Timing conflicts invalidate the complete trace. Request-level ordering cannot establish asynchronous hardware dominance, metastability margins, pulse widths or pin behavior.",
            "Reference validity must be supplied independently; the qualification interval is not a reference startup guarantee."
        ]}
    json.dumps(result, allow_nan=False)
    return result


def simulate(events, proposal):
    """Evaluate requests at event/tick times, with sticky lockout on timing conflict.

    Events are {"t_ns": nonnegative integer, "inputs": {known_name: bool|None}}.
    Times must strictly increase: simultaneous changes belong in one inputs map.
    Health includes both local rails, the independent island guard, reference,
    remote receiver, watchdog and stop. ARM/ACK must remain known and low during
    qualification. After release, a valid ACK rise captures NOT ARM. Unknown
    commands invalidate qualification. A fresh ACK is required after each fault.
    """
    t = timing(proposal)
    require(isinstance(events, (list, tuple)) and len(events) > 0, "events must be nonempty")
    inputs = {k: False for k in INPUTS}
    rows, violations = [], []
    qual = ready = arm_accepted = False
    qualified_at = ready_at = healthy_since = None
    last_invalid = 0
    last_arm_change = last_qualified_ack = last_qualified_arm_rise = None
    previous_time = -1
    for event in events:
        require(isinstance(event, dict) and set(event) <= {"t_ns", "inputs", "note"}, "invalid event keys")
        require("t_ns" in event, "event time is required")
        now = integer(event["t_ns"], "event t_ns")
        require(now > previous_time, "event times must strictly increase; combine simultaneous changes")
        changes = event.get("inputs", {})
        require(isinstance(changes, dict) and set(changes) <= set(INPUTS), "unknown input name")
        require(all(v is None or isinstance(v, bool) for v in changes.values()), "inputs must be bool or None")
        before = inputs.copy()
        inputs.update(changes)
        ack_rise = inputs["ack"] is True and before["ack"] is not True
        arm_change = inputs["arm"] is not before["arm"]
        arm_rise = inputs["arm"] is True and before["arm"] is not True
        health_fall = any(before[k] is True and inputs[k] is not True for k in HEALTH)
        healthy = all(inputs[k] is True for k in HEALTH)
        commands_known = inputs["ack"] is not None and inputs["arm"] is not None
        valid = healthy and commands_known
        validity_fall = health_fall or any(before[k] is not None and inputs[k] is None for k in ("ack", "arm"))
        commands_low = inputs["ack"] is False and inputs["arm"] is False
        was_qual, was_ready = qual, ready
        new_violations = []
        # Timing checks precede logical fault priority: an unsafe race is recorded
        # even though this analysis chooses a low request as its conservative result.
        if was_qual and ack_rise:
            if not valid:
                new_violations.append("ack_coincident_with_invalid_permission")
            if qualified_at is None or now - qualified_at < t["release_guard_ns"]:
                new_violations.append("ack_before_release_guard")
            if arm_change or (last_arm_change is not None and now - last_arm_change < t["arm_guard_ns"]):
                new_violations.append("arm_setup_guard_at_ack")
        if last_qualified_ack is not None:
            if arm_change and now - last_qualified_ack < t["arm_guard_ns"]:
                new_violations.append("arm_hold_guard_after_ack")
            if validity_fall and now - last_qualified_ack < t["release_guard_ns"]:
                new_violations.append("invalid_permission_near_ack")
        if was_qual and arm_rise and not valid:
            new_violations.append("arm_coincident_with_invalid_permission")
        if (last_qualified_arm_rise is not None and validity_fall
                and now - last_qualified_arm_rise < t["arm_guard_ns"]):
            new_violations.append("invalid_permission_near_arm")
        if was_qual and arm_rise and (not was_ready or ready_at is None or now - ready_at < t["arm_guard_ns"]):
            new_violations.append("arm_before_ready_guard")
        if (not was_qual and ack_rise and valid and healthy_since is not None
                and now - healthy_since >= t["qualification_ns"]
                and now - last_invalid >= t["clear_hold_ns"]):
            new_violations.append("ack_at_qualification_release")
        for reason in new_violations:
            violations.append({"t_ns": now, "reason": reason})
        if arm_change:
            last_arm_change = now
        if not valid:
            qual = ready = arm_accepted = False
            qualified_at = ready_at = healthy_since = None
            last_invalid = now
        elif violations:
            qual = ready = arm_accepted = False
            qualified_at = ready_at = healthy_since = None
        elif not qual:
            ready = arm_accepted = False
            if commands_low:
                if healthy_since is None:
                    healthy_since = now
                if now - healthy_since >= t["qualification_ns"] and now - last_invalid >= t["clear_hold_ns"]:
                    qual, qualified_at = True, now
            else:
                healthy_since = None
        else:
            if ack_rise:
                last_qualified_ack = now
                ready = inputs["arm"] is False
                ready_at = now if ready else None
            if arm_rise:
                last_qualified_arm_rise = now
            arm_accepted = bool(qual and ready and inputs["arm"] is True)
        row = {"t_ns": now, "inputs": inputs.copy(),
               "REF_EN_requested": inputs["guard_ok"] is True,
               "QUAL_requested": qual, "READY_requested": ready,
               "ARM_ACCEPTED_requested": arm_accepted,
               "OUTPUT_ENABLE_requested": bool(qual and ready and arm_accepted and not violations),
               "timing_contract_met_so_far": not violations,
               "new_timing_violations": new_violations}
        if "note" in event:
            require(isinstance(event["note"], str), "event note must be text")
            row["note"] = event["note"]
        rows.append(row)
        previous_time = now
    return {"request_model_only": True, "physical_OE_proven": False,
            "hardware_accepted": False, "native_accepted": False,
            "physical_disabled_after_hold_up": False,
            "timing_contract_met": not violations, "timing_violations": violations,
            "trace": rows}


def demonstration_events(proposal):
    """Deterministic diagnostic requests, not a substitute for pin-level testing."""
    t = timing(proposal)
    start = max(t["clear_hold_ns"], 1000)
    release = start + t["qualification_ns"]
    ack = release + t["release_guard_ns"]
    arm = ack + t["arm_guard_ns"]
    all_good = {k: True for k in HEALTH}
    startup = [{"t_ns": 0, "inputs": {"guard_ok": True}, "note": "Reference requested before reference validity."},
               {"t_ns": start, "inputs": all_good}, {"t_ns": release},
               {"t_ns": ack, "inputs": {"ack": True}},
               {"t_ns": arm, "inputs": {"arm": True}}]
    fault = arm + max(t["release_guard_ns"], t["arm_guard_ns"]) + 1
    recover = fault + t["clear_hold_ns"]
    bounce = recover + max(1, t["qualification_ns"] // 2)
    stable = bounce + t["clear_hold_ns"]
    rerelease = stable + max(t["qualification_ns"], t["clear_hold_ns"])
    return {
        "healthy_startup_ack_arm": startup,
        "fault_bounce_fresh_requalification": startup + [
            {"t_ns": fault, "inputs": {"rail_ok": False}},
            {"t_ns": recover, "inputs": {"rail_ok": True, "ack": False, "arm": False}},
            {"t_ns": bounce, "inputs": {"rail_ok": False}},
            {"t_ns": stable, "inputs": {"rail_ok": True}}, {"t_ns": rerelease},
            {"t_ns": rerelease + t["release_guard_ns"], "inputs": {"ack": True}},
            {"t_ns": rerelease + t["release_guard_ns"] + t["arm_guard_ns"], "inputs": {"arm": True}}],
        "held_ack_blocks": startup + [
            {"t_ns": fault, "inputs": {"rail_ok": False}},
            {"t_ns": recover, "inputs": {"rail_ok": True, "arm": False}},
            {"t_ns": recover + t["qualification_ns"] + t["clear_hold_ns"]}],
        "coincident_release_ack_unqualified": startup[:2] + [
            {"t_ns": release, "inputs": {"ack": True}}, {"t_ns": arm, "inputs": {"arm": True}}],
        "unknown_receiver_blocks": [{"t_ns": 0, "inputs": {**all_good, "remote_ready": None}},
                                    {"t_ns": release}],
        "guard_loss_reference_off": startup + [{"t_ns": fault, "inputs": {"guard_ok": False}}]
    }


def collect():
    paths = [HERE / "contract.json", HERE / "model.py",
             HERE.parent / "observation_3v3" / "analysis.json",
             HERE.parent / "observer_power" / "analysis.json"]
    contract = json.loads(paths[0].read_text(encoding="utf-8"))
    result = calculate(contract)
    prior7, prior8 = [json.loads(p.read_text(encoding="utf-8")) for p in paths[2:]]
    prior8_native = prior8.get("native_accepted", prior8.get("conditional_scope", {}).get("native_implemented"))
    require(prior7.get("native_accepted") is False and prior8_native is False,
            "prior conditional packets must explicitly remain unaccepted")
    require(prior8.get("conditional_scope", {}).get("native_implemented", False) is False,
            "ACT-08 must not be relabeled natively implemented")
    p = contract["proposal"]
    alignment = {
        "same_rail_overdrive_V": prior7["overdrive_screen"]["rail_amplitude_V"]["UV"],
        "same_rail_valid_floor_V": prior8["reference_load"]["source_test_min_supply_V"],
        "island_valid_floor_V": prior8["reference_load"]["source_test_min_supply_V"],
        "island_start_source_min_V": prior7["normal_V"][0],
        "total_response_ns": prior7["total_budget_ns"]}
    for key, expected in alignment.items():
        require(math.isclose(p[key], expected, rel_tol=1e-12, abs_tol=0), key + " does not match prior evidence")
    result["prior_allocation_alignment"] = alignment
    result["demonstrations"] = {name: simulate(events, p) for name, events in demonstration_events(p).items()}
    result["source_sha256"] = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in paths}
    json.dumps(result, allow_nan=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--capture", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = collect()
    output = HERE / "analysis.json"
    if args.capture:
        with output.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
        print("Captured ACT-09 conditional deadlines and requests; no physical or native acceptance.")
    else:
        require(json.loads(output.read_text(encoding="utf-8")) == result, "analysis.json is stale or modified")
        print("PASS: ACT-09 conditional calculations, traces and input hashes reproduce.")


if __name__ == "__main__":
    main()
