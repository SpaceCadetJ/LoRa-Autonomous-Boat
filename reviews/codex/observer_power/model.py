#!/usr/bin/env python3
"""ACT-08 conditional observer load/discharge screen; no port or hardware acceptance.

Only the standard library is used. --check is read-only; --capture refreshes
analysis.json from the explicit proposal in contract.json. All text is UTF-8.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from numbers import Real
from pathlib import Path

HERE = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value, name, positive=False):
    require(isinstance(value, Real) and not isinstance(value, bool)
            and math.isfinite(value), name + " must be finite and numeric")
    require(value > 0 if positive else value >= 0, name + " has an invalid sign")
    return float(value)


def pair(value, name, positive=False):
    require(isinstance(value, (list, tuple)) and len(value) == 2,
            name + " must contain two endpoints")
    result = [number(v, name, positive) for v in value]
    require(result[0] <= result[1], name + " endpoints are reversed")
    return result


def vector(value, name, positive=False):
    require(isinstance(value, (list, tuple)) and len(value) > 0,
            name + " must be a nonempty list")
    return [number(v, name, positive) for v in value]


def decay_voltage(initial_V, feed_A, resistance_ohm, capacitance_F, time_s):
    """Ideal constant-feed, constant-capacitance bleeder ODE, not a diode model."""
    v0 = number(initial_V, "initial_V")
    current = number(feed_A, "feed_A")
    resistance = number(resistance_ohm, "resistance_ohm", True)
    capacitance = number(capacitance_F, "capacitance_F", True)
    elapsed = number(time_s, "time_s")
    floor = resistance * current
    return floor + (v0 - floor) * math.exp(-elapsed / (resistance * capacitance))


def discharge_case(initial_V, feed_A, resistance_ohm, capacitance_F, target_V):
    """Return a finite crossing time or null when the target cannot be reached."""
    v0 = number(initial_V, "initial_V", True)
    current = number(feed_A, "feed_A")
    resistance = number(resistance_ohm, "resistance_ohm", True)
    capacitance = number(capacitance_F, "capacitance_F", True)
    target = number(target_V, "target_V", True)
    require(target < v0, "target_V must be below initial_V")
    floor = resistance * current
    reachable = floor < target
    crossing = (resistance * capacitance * math.log((v0 - floor) / (target - floor))
                if reachable else None)
    return {"feed_A": current, "floor_V": floor,
            "target_reachable": reachable, "time_to_target_s": crossing}


def calculate(contract):
    require(isinstance(contract, dict), "contract must be an object")
    required_flags = ("native_accepted", "hardware_accepted", "parts_selected",
                      "qualification_ports_implemented", "native_commands_rerun")
    for key in required_flags:
        require(key in contract and contract[key] is False,
                key + " must explicitly remain false")
    for key in ("native_implemented", "input_ports_qualified", "QUAL_OK_implemented", "ACK_implemented"):
        require(contract.get(key, False) is False, key + " must remain false")
    for key in ("candidate_electrical_delta", "live_electrical_delta", "live_copper_delta"):
        require(key in contract, key + " declaration is required")
        require(number(contract[key], key) == 0, key + " must remain zero")
    p = contract.get("proposal")
    require(isinstance(p, dict), "proposal must be an object")
    ref = pair(p["reference_V"], "reference_V", True)
    rail = pair(p["normal_rail_V"], "normal_rail_V", True)
    resistance = number(p["bleeder_ohm"], "bleeder_ohm", True)
    fraction = number(p["resistor_fraction"], "resistor_fraction")
    require(fraction < 1, "resistor_fraction must be less than one")
    bias = number(p["bias_abs_A"], "bias_abs_A")
    inputs = p["reference_inputs"]
    require(isinstance(inputs, int) and not isinstance(inputs, bool) and inputs > 0,
            "reference_inputs must be a positive integer")
    cap = pair(p["effective_C_F"], "effective_C_F", True)
    feeds = vector(p["feed_cases_A"], "feed_cases_A")
    target = number(p["discharge_target_V"], "discharge_target_V", True)
    require(target < ref[1], "discharge target must be below maximum initial reference voltage")
    series = vector(p["series_ohm"], "series_ohm", True)
    input_cap = number(p["input_C_allocated_F"], "input_C_allocated_F", True)
    settling = number(p["settle_fraction"], "settle_fraction", True)
    require(settling < 1, "settle_fraction must be less than one")
    budget_ns = number(p["sense_budget_ns"], "sense_budget_ns", True)
    spec_supply = number(p["reference_spec_supply_max_V"], "reference_spec_supply_max_V", True)
    line_headroom = number(p["line_test_headroom_V"], "line_test_headroom_V")
    source_headroom = number(p["source_test_headroom_V"], "source_test_headroom_V")
    load_ppm = number(p["load_regulation_ppm_per_mA"], "load_regulation_ppm_per_mA")
    line_ppm = number(p["line_regulation_ppm_per_V"], "line_regulation_ppm_per_V")
    total = number(p["reference_total_fraction"], "reference_total_fraction", True)
    initial = number(p["initial_plus_BOX_fraction"], "initial_plus_BOX_fraction")
    require(total < 1 and initial < 1, "reference error fractions must be less than one")
    line_span = spec_supply - (ref[0] + line_headroom)
    require(line_span >= 0, "line test span must not be negative")

    rmin, rmax = resistance * (1 - fraction), resistance * (1 + fraction)
    load_min = ref[0] / rmax - inputs * bias
    load_max = ref[1] / rmin + inputs * bias
    require(load_min >= 0, "assumed bias exceeds minimum sourcing load")
    load_fraction = load_max * 1000 * load_ppm * 1e-6
    line_fraction = line_span * line_ppm * 1e-6
    combined_fraction = initial + load_fraction + line_fraction
    series_cases = []
    for nominal in series:
        low, high = nominal * (1 - fraction), nominal * (1 + fraction)
        settle_s = high * input_cap * math.log(1 / settling)
        series_cases.append({
            "nominal_ohm": nominal, "minimum_ohm": low, "maximum_ohm": high,
            "ideal_zero_V_node_current_ceiling_A_per_input": ref[1] / low,
            "steady_bias_error_V_per_input": bias * high,
            "allocated_capacitance_F": input_cap, "settling_time_s": settle_s,
            "settling_time_ns": settle_s * 1e9,
            "remaining_sense_budget_ns": budget_ns - settle_s * 1e9,
            "fits_allocated_sense_budget_only": settle_s * 1e9 <= budget_ns,
        })
    result = {
        "packet": "ACT-08", "model": "conditional observer power-state screen",
        "native_accepted": False, "hardware_accepted": False, "parts_selected": False,
        "qualification_ports_implemented": False, "native_commands_rerun": False,
        "candidate_electrical_delta": 0, "live_electrical_delta": 0, "live_copper_delta": 0,
        "conditional_scope": {
            "native_implemented": False, "hardware_accepted": False,
            "input_ports_qualified": False, "bias_applicability_qualified": False,
            "capacitance_bound_qualified": False, "startup_shutdown_qualified": False,
            "linear_regulation_allocation_only": True,
            "ideal_constant_feed_bleeder_ODE_only": True,
            "series_current_is_zero_V_node_ceiling_not_diode_behavior": True,
        },
        "formulas": {
            "resistor_bounds": "Rmin = Rnom*(1-f); Rmax = Rnom*(1+f)",
            "reference_load": "Imin = Vref_min/Rmax - N*Ibias; Imax = Vref_max/Rmin + N*Ibias",
            "bleeder_power": "Pmax = Vref_max**2/Rmin",
            "linear_regulation": "f_load = Imax[A]*1000[mA/A]*load[ppm/mA]*1e-6; f_line = (Vspec_max-(Vref_min+line_headroom))*line[ppm/V]*1e-6",
            "remaining_allocation": "total_fraction - initial_plus_BOX_fraction - f_load - f_line (linear sum, conditional screen)",
            "voltage_decay": "V(t) = R*If + (V0-R*If)*exp(-t/(R*C))",
            "target_time": "t = R*C*ln((V0-R*If)/(Vtarget-R*If)) if R*If < Vtarget < V0; otherwise null",
            "series_current_ceiling": "I_ceiling = Vref_max/Rseries_min per input, ideal receiving node at 0 V",
            "series_bias": "abs(error_V) = abs(Ibias)*Rseries_max per input",
            "series_settling": "t = Rseries_max*C_allocated*ln(1/settle_fraction); ignores source impedance and port parasitics",
        },
        "reference_load": {
            "resistance_min_ohm": rmin, "resistance_max_ohm": rmax,
            "minimum_sourcing_A": load_min, "maximum_sourcing_A": load_max,
            "bleeder_power_max_W": ref[1]**2/rmin,
            "source_test_min_supply_V": ref[1] + source_headroom,
            "minimum_normal_rail_headroom_margin_V": rail[0] - (ref[1] + source_headroom),
        },
        "reference_allocation": {
            "initial_plus_BOX_fraction": initial,
            "specified_line_span_V": line_span,
            "load_regulation_fraction": load_fraction,
            "line_regulation_fraction": line_fraction,
            "linear_sum_fraction": combined_fraction,
            "total_allocated_fraction": total,
            "remaining_fraction": total - combined_fraction,
            "positive_remaining_allocation_only": total > combined_fraction,
        },
        "discharge": {
            "initial_V": ref[1], "resistance_ohm": rmax, "capacitance_F": cap[1],
            "target_V": target, "time_constant_s": rmax*cap[1],
            "cases": [discharge_case(ref[1], feed, rmax, cap[1], target) for feed in feeds],
        },
        "series_input": {"sense_budget_ns": budget_ns, "settle_fraction": settling,
                         "cases": series_cases},
    }
    # Serializing forbids NaN/Infinity even if extreme finite inputs overflow.
    json.dumps(result, allow_nan=False)
    return result


def artifact(contract_path):
    raw = contract_path.read_bytes()
    result = calculate(json.loads(raw.decode("utf-8")))
    result["contract_sha256"] = hashlib.sha256(raw).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--capture", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--contract", type=Path, default=HERE/"contract.json")
    parser.add_argument("--output", type=Path, default=HERE/"analysis.json")
    args = parser.parse_args()
    result = artifact(args.contract)
    if args.capture:
        args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+"\n", encoding="utf-8")
        print("Captured conditional ACT-08 analysis; no native, port or hardware acceptance.")
    else:
        require(json.loads(args.output.read_text(encoding="utf-8")) == result,
                "analysis.json does not match the contract and model")
        print("ACT-08 analysis matches contract and model; acceptance remains held.")


if __name__ == "__main__":
    main()
