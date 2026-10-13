#!/usr/bin/env python3
"""ACT-06 conditional supervisor screens. No circuit or hardware release.

--capture writes only analysis.json; --check reproduces it without writes.
"""
from __future__ import annotations
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RAILS = {
    "3V3": {"nominal": 3.3, "converter": [3.219942244224422, 3.412002431724654], "corridor": [3., 3.6]},
    "5V": {"nominal": 5., "converter": [4.866303235118693, 5.189909215041985], "corridor": [4.5, 5.5]}}
INTEGRATED = [("3V3", .04, "TPS3703A4330DSER"), ("3V3", .05, "TPS3703A5330DSER"),
              ("3V3", .06, "TPS3703A6330DSER"), ("3V3", .07, "TPS3703A7330DSER"),
              ("5V", .05, "TPS3703A5500DSER")]
ACCURACY = .007
HYSTERESIS = [.003, .008]
DIVIDERS = {"3V3": {"UV": [6900.], "OV": [7870.]}, "5V": {"UV": [10900.], "OV": [12400., 100.]}}
BOTTOM_OHM = 1000.
BIAS_A = {"UV": 25e-9, "OV": 15e-9}
THRESHOLDS_V = {"fall": [.387, .400], "rise": [.396, .404]}
BUDGETS = {"initial_0p1": .001, "temperature_sensitivity_0p35": .0035}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def finite(*values):
    require(all(math.isfinite(v) for v in values), "Nonfinite numerical input")


def assess(rail_id, assertions, releases):
    normal, safe = RAILS[rail_id]["converter"], RAILS[rail_id]["corridor"]
    quiet, recovery = [assertions["UV"][1], assertions["OV"][0]], [releases["UV"][1], releases["OV"][0]]
    margins = {"no_trip_lower": normal[0]-quiet[0], "no_trip_upper": quiet[1]-normal[1],
               "recovery_lower": normal[0]-recovery[0], "recovery_upper": recovery[1]-normal[1],
               "late_UV": assertions["UV"][0]-safe[0], "late_OV": safe[1]-assertions["OV"][1]}
    reasons = [name for name, value in margins.items() if value <= 0]
    return {"assert_V": assertions, "release_V": releases, "converter_V": normal, "logic_corridor_V": safe,
            "screened_no_new_fault_band_V": quiet, "screened_recovery_band_V": recovery,
            "margins_V": margins, "static_screen_pass": not reasons, "reasons": reasons,
            "dynamic_screen_pass": False, "hardware_accepted": False}


def integrated_case(rail_id, window, part):
    finite(window)
    require(0 < window < 1, "Invalid window")
    rail = RAILS[rail_id]["nominal"]
    uv, ov, e = rail*(1-window), rail*(1+window), rail*ACCURACY
    assertions = {"UV": [uv-e, uv+e], "OV": [ov-e, ov+e]}
    releases = {"UV": [uv-e+HYSTERESIS[0]*uv, uv+e+HYSTERESIS[1]*uv],
                "OV": [ov-e-HYSTERESIS[1]*ov, ov+e-HYSTERESIS[0]*ov]}
    actual_trip_releases = {"UV": [(uv-e)*(1+HYSTERESIS[0]), (uv+e)*(1+HYSTERESIS[1])],
                            "OV": [(ov-e)*(1-HYSTERESIS[1]), (ov+e)*(1-HYSTERESIS[0])]}
    safe = RAILS[rail_id]["corridor"]
    # Eq7 denominator is nominal trip, not actual threshold or nominal rail.
    uv_step, ov_step = assertions["UV"][0]-.05*uv, assertions["OV"][1]+.05*ov
    return {"id": part, "part": part, "rail_id": rail_id, "nominal_rail_V": rail,
            "window_fraction": window, "nominal_trip_V": {"UV": uv, "OV": ov},
            "accuracy_fraction_of_rail": ACCURACY, "hysteresis_fraction": HYSTERESIS,
            "hysteresis_basis": "Nominal comparator trip scaling assumption; sensitivity uses actual trip.",
            **assess(rail_id, assertions, releases),
            "actual_trip_hysteresis_sensitivity": assess(rail_id, assertions, actual_trip_releases),
            "timing_step_screen": {
                "overdrive_fraction": .05, "denominator_basis": "Eq7 nominal comparator trip",
                "propagation_max_us_at_stated_test": 30, "UV_test_rail_V": uv_step, "OV_test_rail_V": ov_step,
                "UV_corridor_margin_V": uv_step-safe[0], "OV_corridor_margin_V": safe[1]-ov_step,
                "test_amplitudes_inside_corridor": uv_step > safe[0] and ov_step < safe[1],
                "guarantee_established": False,
                "interpretation": "Insufficient evidence for in-corridor shutdown; not a prediction of actual failure.",
                "other_test_conditions": "VDD1.7..5.5V, -40..125C, RESET10k/10pF; exact table7.6 step/overdrive conditions apply.",
                "earlier_actual_trip_denominator_sensitivity_V": {
                    "UV": assertions["UV"][0]*.95, "OV": assertions["OV"][1]*1.05}}}


def divider_voltage(threshold_V, top_ohm, bottom_ohm, bias_A):
    """Positive bias flows into sense input; KCL gives a PLUS bias*Rt term."""
    finite(threshold_V, top_ohm, bottom_ohm, bias_A)
    require(threshold_V > 0 and top_ohm > 0 and bottom_ohm > 0, "Invalid divider")
    return threshold_V*(1+top_ohm/bottom_ohm)+bias_A*top_ohm


def resistor_endpoints(elements_ohm, tolerance):
    finite(tolerance, *elements_ohm)
    require(0 <= tolerance < 1 and elements_ohm and all(r > 0 for r in elements_ohm), "Invalid resistor budget")
    # Series elements are independently enumerated; coherent signs give the
    # full worst-case tolerance, never an RSS reduction.
    return [sum(r*(1+s*tolerance) for r, s in zip(elements_ohm, signs))
            for signs in itertools.product((-1, 1), repeat=len(elements_ohm))]


def divider_bounds(top_elements, bottom, tolerance, thresholds, bias_bound):
    finite(bottom, bias_bound, *thresholds)
    require(bottom > 0 and bias_bound >= 0 and 0 < thresholds[0] <= thresholds[1], "Invalid divider bounds")
    values = [divider_voltage(v, top, bot, bias)
              for v, top, bot, bias in itertools.product(thresholds,
                  resistor_endpoints(top_elements, tolerance), resistor_endpoints([bottom], tolerance),
                  (-bias_bound, bias_bound))]
    return [min(values), max(values)]


def divider_currents(rail_range, top_elements, bottom, tolerance, bias_bound):
    """Exact resistor currents under the explicitly assumed input-bias envelope."""
    rail_top, ground_bottom = [], []
    for v, rt, rb, ib in itertools.product(rail_range, resistor_endpoints(top_elements, tolerance),
                                         resistor_endpoints([bottom], tolerance), (-bias_bound, bias_bound)):
        rail_top.append((v+ib*rb)/(rt+rb))
        ground_bottom.append((v-ib*rt)/(rt+rb))
    return {"rail_top_current_A": [min(rail_top), max(rail_top)],
            "ground_bottom_current_A": [min(ground_bottom), max(ground_bottom)],
            "bias_applied_as_assumption": True}


def divider_case(rail_id, budget_id, tolerance=None):
    tolerance = BUDGETS[budget_id] if tolerance is None else tolerance
    assertions, releases, currents = {}, {}, {}
    for comparator in ("UV", "OV"):
        top = DIVIDERS[rail_id][comparator]
        a_dir, r_dir = ("fall", "rise") if comparator == "UV" else ("rise", "fall")
        assertions[comparator] = divider_bounds(top, BOTTOM_OHM, tolerance, THRESHOLDS_V[a_dir], BIAS_A[comparator])
        releases[comparator] = divider_bounds(top, BOTTOM_OHM, tolerance, THRESHOLDS_V[r_dir], BIAS_A[comparator])
        currents[comparator] = divider_currents(RAILS[rail_id]["converter"], top, BOTTOM_OHM, tolerance, BIAS_A[comparator])
        currents[comparator]["nominal_no_bias_current_A"] = RAILS[rail_id]["nominal"]/(sum(top)+BOTTOM_OHM)
    currents["total_rail_current_A"] = [sum(currents[c]["rail_top_current_A"][i] for c in ("UV", "OV")) for i in (0, 1)]
    return {"id": rail_id+"_"+budget_id, "family": "TPS3700", "part_selected": False,
            "rail_id": rail_id, "budget_id": budget_id, "resistor_tolerance_fraction": tolerance,
            "top_elements_ohm": DIVIDERS[rail_id], "bottom_ohm": BOTTOM_OHM, "bias_bound_A_assumed": BIAS_A,
            "bias_applicability_at_threshold_qualified": False, "divider_currents": currents,
            **assess(rail_id, assertions, releases)}


def ov_ratio_interval(tolerance, rail_id="3V3"):
    """Necessary strict OV ratio limits, fixed Rb1k, assumed bias and no guard."""
    finite(tolerance)
    require(0 <= tolerance < .1, "Ratio sensitivity restricted to0..10%")
    nmax, upper = RAILS[rail_id]["converter"][1], RAILS[rail_id]["corridor"][1]
    vf, vr, ib = THRESHOLDS_V["fall"][0], THRESHOLDS_V["rise"][1], BIAS_A["OV"]
    den_lo = vf*(1-tolerance)/(1+tolerance)-ib*BOTTOM_OHM*(1-tolerance)
    den_hi = vr*(1+tolerance)/(1-tolerance)+ib*BOTTOM_OHM*(1+tolerance)
    require(den_lo > 0, "Nonpositive ratio denominator")
    lower, upper_ratio = (nmax-vf)/den_lo, (upper-vr)/den_hi
    return {"resistor_tolerance_fraction": tolerance, "required_ratio_lower_exclusive": lower,
            "allowed_ratio_upper_exclusive": upper_ratio, "has_feasible_ratio": lower < upper_ratio,
            "guard_V": 0., "qualification": "Conditional on threshold/bias assumptions and fixed1k bottom; no dynamic/aging budget."}


def supremum_budget(predicate):
    """Monotone feasibility bisection; returned boundary itself is not acceptable."""
    lower, upper = 0., .02
    require(predicate(lower) and not predicate(upper), "Unbracketed resistor budget boundary")
    for _ in range(70):
        middle = (lower+upper)/2
        if predicate(middle):
            lower = middle
        else:
            upper = middle
    return (lower+upper)/2


def resistor_feasibility():
    fixed = {}
    for rail in RAILS:
        for comparator in ("UV", "OV"):
            relevant = ("no_trip_lower", "recovery_lower", "late_UV") if comparator == "UV" else ("no_trip_upper", "recovery_upper", "late_OV")
            def viable(t, r=rail, keys=relevant):
                m = divider_case(r, "custom", t)["margins_V"]
                return all(m[k] > 0 for k in keys)
            fixed[rail+"_"+comparator] = supremum_budget(viable)
    return {"fixed_proposal_budget_suprema_fraction": fixed,
            "any_3V3_OV_ratio_budget_supremum_fraction": supremum_budget(lambda t: ov_ratio_interval(t)["has_feasible_ratio"]),
            "3V3_OV_ratio_cases": [ov_ratio_interval(t) for t in BUDGETS.values()],
            "strictly_less_than_supremum_required": True,
            "all_dynamic_and_aging_guards_allocated": False, "parts_selected": False}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_contract(c, prior):
    require(c["schema"] == 1 and c["revision"] == "ACT-06", "Wrong contract revision")
    for key in ("parts_selected", "native_commands_rerun", "hardware_accepted", "QUAL_OK_implemented", "ACK_implemented", "hardware_failure_predicted"):
        require(c[key] is False, "Unsupported acceptance: "+key)
    for key in ("candidate_electrical_delta", "live_electrical_delta", "live_copper_delta"):
        require(c[key] == 0, "Nonzero scope: "+key)
    for rail, expected in RAILS.items():
        r = c["rails"][rail]
        require([r["nominal_V"], r["converter_V"], r["corridor_V"]] ==
                [expected["nominal"], expected["converter"], expected["corridor"]], "Rail inputs changed")
        prior_cases = [p for p in prior["cases"] if p["rail_id"] == rail]
        require(prior_cases and all(p["converter_V"] == expected["converter"] and p["logic_corridor_V"] == expected["corridor"] for p in prior_cases), "ACT-05 rail inputs changed")
    require(prior["revision"] == "ACT-05" and prior["hardware_accepted"] is False, "Wrong prior evidence")
    i = c["integrated"]
    require([(p["rail_id"], p["window_fraction"], p["part"]) for p in i["cases"]] == INTEGRATED,
            "Unreviewed integrated identity/window")
    require(i["accuracy_fraction_of_nominal_rail"] == ACCURACY and i["hysteresis_fraction"] == HYSTERESIS,
            "Integrated threshold inputs changed")
    require(i["detect_overdrive_fraction"] == .05 and i["detect_max_us"] == 30, "Wrong detection conditions")
    a = c["adjustable"]
    require(a["rising_threshold_V"] == THRESHOLDS_V["rise"] and a["falling_threshold_V"] == THRESHOLDS_V["fall"], "Wrong divider polarity/threshold")
    require(a["input_bias_abs_A"] == BIAS_A and a["bias_applicability_at_threshold_verified"] is False, "Wrong bias bound or qualification")
    require(a["exact_resistor_MPNs_selected"] is False, "Resistors not selected in this packet")
    require({p["id"]: p["fraction"] for p in a["resistor_budgets"]} == BUDGETS, "Resistor budgets changed")
    for rail, dividers in DIVIDERS.items():
        d = a["dividers"][rail]
        require(d["bottom_ohm"] == BOTTOM_OHM and all(d[k+"_top_ohm"] == sum(v) for k, v in dividers.items()), "Divider values changed")
    require(a["dividers"]["5V"]["OV_top_series_ohm"] == [12400, 100], "Series top changed")
    require(c["interface"]["direct_fault_bus_to_QUAL_OK_accepted"] is False, "Direct QUAL bus not accepted")


def check_record(saved, current):
    require(saved == current, "analysis.json stale or modified; review before explicit recapture")


def collect():
    contract_path = HERE / "contract.json"
    prior_path = HERE.parent / "rail_qualification/analysis.json"
    prior_manifest_path = HERE.parent / "rail_qualification/input_manifest.json"
    c, prior = read_json(contract_path), read_json(prior_path)
    validate_contract(c, prior)
    manifest_path = HERE / "input_manifest.json"
    manifest = read_json(manifest_path)
    require(manifest["revision"] == "ACT-06", "Wrong input manifest")
    for path in (prior_path, prior_manifest_path):
        key = path.relative_to(ROOT).as_posix()
        require(manifest["input_sha256"][key] == sha(path), "Captured input changed: "+key)
    # Recheck ACT-05's own listed sources without native-tool execution.
    for key, expected in prior["source_sha256"].items():
        path = (ROOT / key).resolve()
        require(path.is_relative_to(ROOT), "Prior source path escapes repository")
        require(sha(path) == expected, "ACT-05 source hash stale: "+key)
    paths = [contract_path, prior_path, prior_manifest_path, manifest_path, Path(__file__).resolve()]
    integrated = [integrated_case(*p) for p in INTEGRATED]
    dividers = [divider_case(rail, budget) for rail in RAILS for budget in BUDGETS]
    return {"schema": 1, "revision": "ACT-06", "status": "conditional_component_comparison",
            "source_sha256": {p.relative_to(ROOT).as_posix(): sha(p) for p in paths},
            "prior_analysis_input_hashes_rechecked": len(prior["source_sha256"]),
            "candidate_electrical_delta": 0, "live_electrical_delta": 0, "live_copper_delta": 0,
            "parts_selected": False, "native_commands_rerun": False, "hardware_accepted": False,
            "hardware_failure_predicted": False, "QUAL_OK_implemented": False, "ACK_implemented": False,
            "integrated_cases": integrated, "divider_cases": dividers,
            "resistor_feasibility": resistor_feasibility(),
            "summary": {"integrated_cases": len(integrated), "divider_cases": len(dividers),
                        "integrated_static_pass_parts": [p["part"] for p in integrated if p["static_screen_pass"]],
                        "divider_static_pass_cases": [p["id"] for p in dividers if p["static_screen_pass"]],
                        "in_corridor_detection_guarantee_established": False,
                        "selection_accepted": False},
            "method": {"integrated_accuracy": "Rail-additive0.007 per reviewed Eq8/9 numerical example",
                       "hysteresis": "Nominal-trip main assumption; actual-trip sensitivity separate",
                       "timing": "Eq7 nominal-trip denominator,5% step amplitude at latest assertion corner; not arbitrary ramp timing",
                       "divider": "Enumerate independent threshold, each series resistor, bottom resistor and signed bias extrema; no RSS or duplicate hysteresis",
                       "currents": "Top=(Vrail+Ibias*Rb)/(Rt+Rb); bottom=(Vrail-Ibias*Rt)/(Rt+Rb); Ibias positive into pin",
                       "budget": "0.1% initial versus assumed0.1%+25ppm/C*100C=0.35%; no resistor MPN selected"},
            "limitations": [
                "Static arithmetic cannot qualify shutdown latency, overshoot, ramp response, startup or fault capture.",
                "Nominal-trip and actual-trip hysteresis screens are engineering interpretations, not blanket silicon guarantees.",
                "Published TPS3700 input bias is tested away from threshold; applicability of the assumed symmetric envelope remains unqualified.",
                "Unrelated resistor extrema are conservative; correlation/aging/self-heating and total ratio budget remain unqualified.",
                "3V3 corridor is local ACT-04 timing, not whole-board acceptance; IMU2 is still separate. 5V corridor is a proposed performance comparison.",
                "No remote-ready, command-watchdog or ACK source is implemented; actuator permission remains disabled.",
                "No regulator dynamic/PFM/aging completeness, hardware-failure prediction, power, procurement or fabrication approval follows."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--capture", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    record = collect()
    output = HERE / "analysis.json"
    if args.capture:
        with output.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(record, indent=2, allow_nan=False)+"\n")
        print("Captured ACT-06 conditional comparison; no selection or hardware acceptance.")
    else:
        check_record(read_json(output), record)
        print("PASS: ACT-06 conditional arithmetic and source hashes reproduce; all hardware gates held.")


if __name__ == "__main__":
    main()
