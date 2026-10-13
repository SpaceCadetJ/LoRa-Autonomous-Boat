#!/usr/bin/env python3
"""ACT-07 conditional 3V3 observation allocation; not component qualification.

Python stdlib only. --capture writes analysis.json; --check is read-only.
"""
from __future__ import annotations
import argparse
import hashlib
import itertools
import json
import math
from numbers import Real
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value, name, positive=False):
    require(isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value),
            name+" must be a finite number")
    require(value > 0 if positive else value >= 0, name+" has an invalid sign")
    return value


def pair(value, name, strict=False, positive=False):
    require(isinstance(value, (list, tuple)) and len(value) == 2, name+" must have two endpoints")
    a, b = [number(v, name, positive) for v in value]
    require(a < b if strict else a <= b, name+" is reversed or empty")
    return [a, b]


def validate(contract):
    require(isinstance(contract, dict) and isinstance(contract.get("proposal"), dict), "Missing proposal")
    required_state = {"native_accepted", "hardware_accepted", "parts_selected", "qualification_ports_implemented", "native_commands_rerun", "candidate_electrical_delta", "live_electrical_delta", "live_copper_delta"}
    require(required_state <= contract.keys(), "Missing qualification or zero-delta declaration")
    p = contract["proposal"]
    required = {"reference_V", "reference_fraction", "comparator_offset_abs_V", "hysteresis_V", "bias_abs_A", "resistor_fraction", "bottom_ohm", "UV_top_ohm", "OV_top_ohm", "overdrive_V", "detector_budget_ns", "downstream_budget_ns", "sense_settling_budget_ns", "normal_V", "corridor_V", "slew_cases_V_per_us"}
    require(required <= p.keys(), "Missing numerical allocation")
    require(contract.get("revision", "ACT-07") == "ACT-07", "Wrong allocation revision")
    for key in ("reference_V", "bottom_ohm", "UV_top_ohm", "OV_top_ohm", "overdrive_V",
                "detector_budget_ns", "downstream_budget_ns", "sense_settling_budget_ns"):
        number(p[key], key, positive=True)
    for key in ("reference_fraction", "resistor_fraction"):
        require(number(p[key], key) < 1, key+" must be below one")
    number(p["comparator_offset_abs_V"], "comparator_offset_abs_V")
    number(p["bias_abs_A"], "bias_abs_A")
    pair(p["hysteresis_V"], "hysteresis_V")
    normal = pair(p["normal_V"], "normal_V", strict=True, positive=True)
    safe = pair(p["corridor_V"], "corridor_V", strict=True, positive=True)
    require(safe[0] < normal[0] < normal[1] < safe[1], "Normal interval must lie inside corridor")
    require(isinstance(p["slew_cases_V_per_us"], list) and p["slew_cases_V_per_us"], "Missing slew cases")
    for slew in p["slew_cases_V_per_us"]:
        number(slew, "slew case", positive=True)
    require(p["reference_V"]*(1-p["reference_fraction"])-p["comparator_offset_abs_V"]-p["hysteresis_V"][1]/2 > 0,
            "Allocated threshold can become nonpositive")
    for key in ("native_accepted", "hardware_accepted", "parts_selected", "QUAL_OK_implemented", "ACK_implemented", "qualification_ports_implemented", "native_commands_rerun"):
        require(contract.get(key, False) is False, "Unsupported qualification claim: "+key)
    for key in ("candidate_electrical_delta", "live_electrical_delta", "live_copper_delta"):
        require(contract.get(key, 0) == 0, "Nonzero circuit scope: "+key)
    return p


def threshold_bounds(p, top_ohm, hysteresis_sign):
    """Positive sense bias flows into comparator input. Full-width hys is +/-h/2."""
    require(hysteresis_sign in (-1, 1), "Invalid hysteresis sign")
    values = []
    for ref_sign, offset_sign, hys, top_sign, bottom_sign, bias_sign in itertools.product(
            (-1, 1), (-1, 1), p["hysteresis_V"], (-1, 1), (-1, 1), (-1, 1)):
        ref = p["reference_V"]*(1+ref_sign*p["reference_fraction"])
        offset = offset_sign*p["comparator_offset_abs_V"]
        rt = top_ohm*(1+top_sign*p["resistor_fraction"])
        rb = p["bottom_ohm"]*(1+bottom_sign*p["resistor_fraction"])
        threshold = (ref+offset+hysteresis_sign*hys/2)*(1+rt/rb)+bias_sign*p["bias_abs_A"]*rt
        values.append(threshold)
    return [min(values), max(values)]


def analyze(contract):
    p = validate(contract)
    thresholds = {
        "UV": {"assert": threshold_bounds(p,p["UV_top_ohm"],-1), "recover": threshold_bounds(p,p["UV_top_ohm"],1)},
        "OV": {"assert": threshold_bounds(p,p["OV_top_ohm"],1), "recover": threshold_bounds(p,p["OV_top_ohm"],-1)}}
    uv, ov = thresholds["UV"], thresholds["OV"]
    normal, safe = p["normal_V"], p["corridor_V"]
    margins = {"normal_UV_assert": normal[0]-uv["assert"][1], "normal_OV_assert": ov["assert"][0]-normal[1],
               "normal_UV_recovery": normal[0]-uv["recover"][1], "normal_OV_recovery": ov["recover"][0]-normal[1],
               "latest_UV_assert_to_corridor": uv["assert"][0]-safe[0],
               "latest_OV_assert_to_corridor": safe[1]-ov["assert"][1]}
    multipliers = {k: 1+p[k+"_top_ohm"]*(1+p["resistor_fraction"])/(p["bottom_ohm"]*(1-p["resistor_fraction"]))
                   for k in ("UV", "OV")}
    amplitudes = {"UV": uv["assert"][0]-p["overdrive_V"]*multipliers["UV"],
                  "OV": ov["assert"][1]+p["overdrive_V"]*multipliers["OV"]}
    headroom = {"UV": amplitudes["UV"]-safe[0], "OV": safe[1]-amplitudes["OV"]}
    total_ns = sum(p[k] for k in ("detector_budget_ns", "downstream_budget_ns", "sense_settling_budget_ns"))
    total_us = total_ns/1000
    maximum_slew = {k: max(0., headroom[k])/total_us for k in ("UV", "OV")}
    cases = []
    static_pass = all(value > 0 for value in margins.values())
    for slew in p["slew_cases_V_per_us"]:
        consumed = slew*total_us
        residual = {k: headroom[k]-consumed for k in ("UV", "OV")}
        cases.append({"slew_V_per_us": slew, "additional_excursion_V": consumed,
                      "residual_V": residual, "positive_headroom": {k: residual[k] > 0 for k in ("UV", "OV")},
                      "conditional_allocation_pass": static_pass and all(v > 0 for v in residual.values()),
                      "hardware_accepted": False, "ramp_detection_qualified": False})
    return {"schema": 1, "revision": "ACT-07", "verdict": "conditional_allocation_only",
            "native_accepted": False, "hardware_accepted": False, "parts_selected": False,
            "candidate_electrical_delta": 0, "live_electrical_delta": 0, "live_copper_delta": 0,
            "native_commands_rerun": False, "qualification_ports_implemented": False,
            "QUAL_OK_implemented": False, "ACK_implemented": False, "ramp_detection_qualified": False,
            "parameters_are_sourced_guarantees": False,
            "thresholds_V": thresholds, "margins_V": margins,
            "normal_V": normal, "corridor_V": safe, "static_allocation_pass": static_pass,
            "overdrive_screen": {"sense_overdrive_V": p["overdrive_V"], "maximum_divider_multiplier": multipliers,
                "rail_amplitude_V": amplitudes, "headroom_to_corridor_V": headroom,
                "method": "Use latest assertion and maximum divider multiplier independently: conservative cross-corner bound, not a single physical corner."},
            "total_budget_ns": total_ns,
            "budget_components_ns": {k: p[k] for k in ("detector_budget_ns", "downstream_budget_ns", "sense_settling_budget_ns")},
            "maximum_slew_V_per_us": maximum_slew,
            "strictly_below_maximum_slew_required": True,
            "ramp_cases": cases, "all_declared_cases_fit_allocation": all(c["conditional_allocation_pass"] for c in cases),
            "method": {"threshold": "(Vref+offset+/-hys/2)*(1+Rt/Rb)+Ibias*Rt",
                       "corners_per_threshold": 64,
                       "UV": "assert lower, recover upper threshold", "OV": "assert upper, recover lower threshold",
                       "ramp": "residual=headroom-slew*(total_ns/1000); slew is V/us. Clamped zero maximum means no positive slew allocation."},
            "limitations": [
                "Error, hysteresis, bias and timing values are allocations, not a qualified component implementation.",
                "The full-width hysteresis allocation is split about a modeled center threshold; that transfer function needs component confirmation.",
                "The voltage beyond threshold needed to reach allocated overdrive is counted before the full downstream time budget.",
                "Comparator step delay does not establish arbitrary-ramp response. No sourced ramp, full-temperature timing or settling guarantee follows.",
                "Budget exhaustion means this conditional allocation fails, not a prediction of actual hardware failure.",
                "Reference startup, invalid/missing supply, independence, reset retention, conditioning and remote qualification remain open.",
                "No native circuit, copper, firmware, QUAL_OK, ACK or hardware acceptance is created."]}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def collect():
    path = HERE/"contract.json"
    result = analyze(read_json(path))
    result["source_sha256"] = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (path,Path(__file__).resolve())}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--capture", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = collect()
    output = HERE/"analysis.json"
    if args.capture:
        with output.open("w",encoding="utf-8",newline="\n") as stream:
            stream.write(json.dumps(result,indent=2,allow_nan=False)+"\n")
        print("Captured ACT-07 conditional allocation only; hardware and native acceptance false.")
    else:
        require(read_json(output) == result, "analysis.json is stale or modified")
        print("PASS: ACT-07 conditional allocation and input hashes reproduce; no hardware acceptance.")


if __name__ == "__main__":
    main()
