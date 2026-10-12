#!/usr/bin/env python3
"""ACT-05 static screening only. --capture writes analysis.json; --check is read-only."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RAILS = {
    "3V3": {"rail": 3.3, "part": "TPS3702CX33DDCR", "short": "CX33",
             "converter": [3.219942244224422, 3.412002431724654], "corridor": [3.0, 3.6],
             "corridor_basis": "ACT-04 LVC 3.3V +/-0.3V timing-analysis interval; not a board-wide safe rail.",
             "rounded": {"high": [3.17, 3.43], "low": [3.00, 3.60]}},
    "5V": {"rail": 5.0, "part": "TPS3702CX50DDCR", "short": "CX50",
            "converter": [4.866303235118693, 5.189909215041985], "corridor": [4.5, 5.5],
            "corridor_basis": "Proposed 5V performance comparison; TXU0102 supply minimum is 1.08V. Not a receiver limit.",
            "rounded": {"high": [4.80, 5.20], "low": [4.55, 5.45]}}}
ACCURACY = 0.009
HYSTERESIS = [0.003, 0.008]
WINDOWS = {"high": 0.04, "low": 0.09}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def interval(value, label):
    require(len(value) == 2 and all(math.isfinite(x) for x in value)
            and value[0] <= value[1], "Invalid interval: " + label)
    return list(value)


def threshold_bounds(rail, fraction, rounded=None, accuracy=ACCURACY,
                     hysteresis=HYSTERESIS, error_basis="nominal_rail"):
    """Union nominal presentations, then apply accuracy and nominal-trip hysteresis.

    Independent extrema deliberately give interval outer bounds. UV recovery is
    assertion PLUS hysteresis; OV recovery is assertion MINUS hysteresis.
    """
    require(math.isfinite(rail) and rail > 0 and 0 < fraction < 1
            and 0 <= accuracy < 1, "Invalid rail/window/error")
    h = interval(hysteresis, "hysteresis")
    require(0 <= h[0] <= h[1] < 1, "Invalid hysteresis")
    percentage = [rail * (1 - fraction), rail * (1 + fraction)]
    table = percentage if rounded is None else interval(rounded, "nominal trips")
    require(table[0] > 0, "Nonpositive nominal trip")
    nominal = {"UV": [min(percentage[0], table[0]), max(percentage[0], table[0])],
               "OV": [min(percentage[1], table[1]), max(percentage[1], table[1])]}
    require(error_basis in ("nominal_rail", "nominal_trip"), "Unknown accuracy basis")
    assertions, releases, hyst = {}, {}, {}
    for comparator in ("UV", "OV"):
        lo, hi = nominal[comparator]
        if error_basis == "nominal_rail":
            assertions[comparator] = [lo - accuracy * rail, hi + accuracy * rail]
        else:
            assertions[comparator] = [lo * (1 - accuracy), hi * (1 + accuracy)]
        hyst[comparator] = [lo * h[0], hi * h[1]]
        a, b = assertions[comparator]
        hmin, hmax = hyst[comparator]
        releases[comparator] = ([a + hmin, b + hmax] if comparator == "UV"
                                else [a - hmax, b - hmin])
    return {"nominal_trip_V": {"percentage_defined": percentage, "rounded_table": rounded, "union": nominal},
            "accuracy_basis": error_basis, "accuracy_fraction": accuracy,
            "hysteresis_fraction_of_nominal_trip": h, "hysteresis_V": hyst,
            "assert_V": assertions, "release_V": releases,
            "guaranteed_no_new_fault_band_V": [assertions["UV"][1], assertions["OV"][0]],
            "guaranteed_recovery_band_V": [releases["UV"][1], releases["OV"][0]],
            "guaranteed_label_scope": "Conditional static-model intervals only, not guaranteed silicon or dynamic bounds."}


def screen(rail_id, SET, fraction=None, error_basis="nominal_rail"):
    c = RAILS[rail_id]
    legacy = fraction is not None
    fraction = fraction if legacy else WINDOWS[SET]
    bounds = threshold_bounds(c["rail"], fraction, None if legacy else c["rounded"][SET],
                              error_basis=error_basis)
    normal, corridor = c["converter"], c["corridor"]
    quiet, recover = bounds["guaranteed_no_new_fault_band_V"], bounds["guaranteed_recovery_band_V"]
    margins = {"no_trip_lower": normal[0] - quiet[0], "no_trip_upper": quiet[1] - normal[1],
               "recovery_lower": normal[0] - recover[0], "recovery_upper": recover[1] - normal[1],
               "late_UV": bounds["assert_V"]["UV"][0] - corridor[0],
               "late_OV": corridor[1] - bounds["assert_V"]["OV"][1]}
    reasons = [key for key, value in margins.items() if value <= 0]
    return {"id": rail_id + "_SET_" + SET, "rail_id": rail_id, "part": None if legacy else c["part"],
            "SET": SET, "nominal_rail_V": c["rail"], "nominal_window_fraction": fraction,
            **bounds, "converter_V": normal, "logic_corridor_V": corridor,
            "corridor_basis": c["corridor_basis"], "margins_V": margins,
            "static_screen_pass": not reasons, "reasons": reasons,
            "dynamic_screen_pass": False, "hardware_accepted": False}


def adjustable_feasibility(rail_id, dynamic_guard_V=0.0, normal_margin_V=0.0):
    """Necessary nominal-trip intervals for hypothetical E/h budgets, not a part."""
    require(all(math.isfinite(v) and v >= 0 for v in [dynamic_guard_V, normal_margin_V]),
            "Margins must be finite and nonnegative")
    c = RAILS[rail_id]
    lo, hi = c["converter"]
    safe_lo, safe_hi = c["corridor"]
    e, h = ACCURACY * c["rail"], HYSTERESIS[1]
    uv = [safe_lo + e + dynamic_guard_V, (lo - e - normal_margin_V) / (1 + h)]
    ov = [(hi + e + normal_margin_V) / (1 - h), safe_hi - e - dynamic_guard_V]
    return {"rail_id": rail_id, "nominal_UV_open_interval_V": uv, "nominal_OV_open_interval_V": ov,
            "threshold_absolute_error_budget_V": e, "hysteresis_fraction_of_nominal_trip_budget": h,
            "dynamic_guard_assumed_V": dynamic_guard_V, "normal_operation_margin_assumed_V": normal_margin_V,
            "nonempty_static_intervals": uv[0] < uv[1] and ov[0] < ov[1],
            "all_dynamic_budget_terms_allocated": False, "part_selected": False,
            "inequalities": ["UVnom > Lsafe + E + dynamic_guard", "UVnom < (Nmin - E - normal_margin)/(1+h)",
                             "OVnom > (Nmax + E + normal_margin)/(1-h)", "OVnom < Usafe - E - dynamic_guard"],
            "limitations": "Zero dynamic guard is optimistic algebra, not acceptable design margin. Envelopes and receiver limits remain incomplete."}


def open_drain_slew(resistance_ohm=10000.0, capacitance_F=10e-12,
                    pullup_V=3.3, low_V=0.8, high_V=2.0, limit_ns_per_V=10.0):
    require(all(math.isfinite(x) for x in [resistance_ohm, capacitance_F, pullup_V, low_V, high_V, limit_ns_per_V]),
            "Nonfinite RC input")
    require(resistance_ohm > 0 and capacitance_F > 0 and 0 <= low_V < high_V < pullup_V
            and limit_ns_per_V > 0, "Invalid RC crossing inputs")
    delta_ns = resistance_ohm * capacitance_F * math.log((pullup_V-low_V)/(pullup_V-high_V)) * 1e9
    average = delta_ns / (high_V-low_V)
    return {"R_ohm_assumed": resistance_ohm, "C_F_assumed_not_measured": capacitance_F,
            "pullup_V": pullup_V, "logic_crossing_V": [low_V, high_V], "crossing_time_ns": delta_ns,
            "average_ns_per_V": average, "receiver_max_ns_per_V": limit_ns_per_V,
            "necessary_slew_screen_pass": average <= limit_ns_per_V,
            "formula": "R*C*ln((VPU-VIL)/(VPU-VIH))",
            "qualification": "Illustrative unloaded RC only. Omits R42 divider, leakage, measured capacitance and partial power. Passing cannot qualify the full transition or a direct LVC connection."}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def validate_inputs(source, buck33, buck5):
    require(source["revision"] == "ACT-05" and source["hardware_accepted"] is False
            and source["parts_selected"] is False and source["expected_electrical_delta"] == 0
            and source["expected_copper_delta"] == 0 and source["native_checks_applicable"] is False,
            "Source review incorrectly releases hardware or changes scope")
    p = source["sources"]["TPS3702"]
    require(p["C_window_fraction_by_SET"] == WINDOWS, "Wrong C-family windows")
    require(p["threshold_accuracy_fraction_magnitude"] == ACCURACY, "Accuracy magnitude changed")
    require(p["hysteresis_fraction_of_nominal_trip"] == {"min": .003, "typ": .0055, "max": .008}, "Wrong hysteresis")
    for c in RAILS.values():
        t = p["rounded_table_10_2_nominal_trips_V"][c["short"]]
        require(t["nominal_rail"] == c["rail"] and all(t["SET_"+s] == c["rounded"][s] for s in WINDOWS),
                "Nominal trips changed")
    require(buck33["hardware_accepted"] is False and buck5["hardware_accepted"] is False, "Converter no longer screening input")
    require([buck33["feedback"]["lower_v"], buck33["feedback"]["upper_v"]] == RAILS["3V3"]["converter"], "3V3 envelope changed")
    require([buck5["feedback"]["initial_pwm_lower_including_leakage_v"], buck5["feedback"]["initial_pwm_upper_including_leakage_v"]]
            == RAILS["5V"]["converter"], "5V envelope changed")


def collect():
    validate_inputs(read_json(HERE / "source_review.json"), read_json(HERE.parent / "buck_3v3/analysis.json"),
                    read_json(HERE.parent / "buck_5v/analysis.json"))
    inputs = [HERE / "source_review.json", HERE.parent / "buck_3v3/analysis.json", HERE.parent / "buck_5v/analysis.json",
              HERE.parent / "actuator_latch/native/netlist.xml", HERE.parent / "actuator_latch/TIMING.md", Path(__file__).resolve()]
    cases = [screen(rail, setting) for rail in RAILS for setting in WINDOWS]
    return {"schema": 1, "revision": "ACT-05", "status": "static_component_screening_only",
            "hardware_accepted": False, "parts_selected": False, "native_checks_applicable": False,
            "expected_electrical_delta": 0, "expected_copper_delta": 0, "QUAL_OK_implemented": False, "ACK_implemented": False,
            "source_sha256": {p.relative_to(ROOT).as_posix(): sha(p) for p in inputs},
            "method": {"main_accuracy_basis": "Section6.3.3 rail-referenced additive percentage-point screen",
                       "nominal_rounding": "Union percentage formula and Table10-2 rounded nominal trip before accuracy",
                       "hysteresis": "Table5.5 footnote2: electrical min/max fractions of nominal trip",
                       "source_presentation_limit": "Table7-1 results3.463/3.139V suggest trip-relative arithmetic; sensitivity is separate. No erratum or manufacturer guarantee is claimed.",
                       "intervals": "Closed numerical intervals; required margins strictly positive. Guaranteed bands are conditional model labels only."},
            "cases": cases,
            "accuracy_basis_sensitivity": {"basis": "nominal_trip", "changes_selection_conclusion": False,
                "cases": [screen(rail, setting, error_basis="nominal_trip") for rail in RAILS for setting in WINDOWS]},
            "incorrect_5_percent_comparison": {"is_released_part": False,
                "description": "Earlier nominal +/-5% assumption, separate from actual C-family +/-4%; arithmetic only.",
                "cases": [screen(rail, "incorrect_nominal_5_percent", .05) for rail in RAILS]},
            "adjustable_feasibility": [adjustable_feasibility(rail) for rail in RAILS], "open_drain_slew": open_drain_slew(),
            "summary": {"tight_windows_static_pass": False, "wide_3V3_static_pass": False,
                        "wide_5V_static_only_pass": cases[3]["static_screen_pass"], "selection_accepted": False,
                        "required_next_task": "Compare adjustable and integrated alternatives with complete accuracy, hysteresis, timing and partial-power budgets."},
            "limitations": [
                "Converter corner records omit complete ripple, load-step, aging, thermal and PFM bounds.",
                "3.0..3.6V is local LVC timing only; captured U6 VDDIO still needs separate IMU2 correction. No whole-board safe rail is established.",
                "4.5..5.5V is a proposed performance interval, not TXU0102's full1.08..5.5V range or remote receiver acceptance.",
                "TPS3702 SENSE-transition delays19/35us and startup300us are NOM-only; no guaranteed dynamic disable budget follows.",
                "Local rails cannot observe remote readiness, stop continuity or fresh commands. QUAL_OK/ACK remain undriven/default-low.",
                "Release delay cannot detect a missed fault or enforce ACK/ARM order. Fault retention and asynchronous timing remain unimplemented.",
                "No CAD, copper, firmware, population or assembly changes. No power, procurement or fabrication acceptance."]}


def check_record(saved, current):
    require(saved == current, "analysis.json stale or modified; review inputs before explicit recapture")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--capture", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    record = collect()
    output = HERE / "analysis.json"
    if args.capture:
        output.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        print("Captured ACT-05 static screen; selection and hardware remain held.")
    else:
        check_record(read_json(output), record)
        print("PASS: ACT-05 inputs and static screening reproduce; no hardware acceptance.")


if __name__ == "__main__":
    main()
