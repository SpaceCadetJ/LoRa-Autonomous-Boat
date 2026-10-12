#!/usr/bin/env python3
"""Read-only analytical study; CLI capture is optional and never qualifies hardware."""
import argparse
import json
import math
from pathlib import Path

def number(value, name, minimum=0, strict=False):
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(name + " must be finite")
    if minimum is not None and (value < minimum or (strict and value == minimum)):
        raise ValueError(name + " is outside its permitted range")
    return value

def resistor_bounds(nominal=3300, tolerance=.01, tempco_ppm=100, delta_k=130, service=.02):
    number(nominal, "resistance", strict=True)
    for name, value in (("tolerance", tolerance), ("tempco", tempco_ppm), ("temperature span", delta_k), ("service budget", service)):
        number(value, name)
    fraction = tolerance + tempco_ppm * 1e-6 * delta_k + service
    if fraction >= 1:
        raise ValueError("Total additive resistance uncertainty must be below one")
    return {"nominal_ohm": nominal, "additive_fraction": fraction,
            "minimum_ohm": nominal * (1 - fraction), "maximum_ohm": nominal * (1 + fraction)}

def bleeder(current_a, rmax_ohm, target_v=.1, absolute_v=.3):
    for name, value in (("current", current_a), ("resistance", rmax_ohm), ("target", target_v), ("absolute magnitude", absolute_v)):
        number(value, name, strict=name != "current")
    if target_v >= absolute_v:
        raise ValueError("Target must retain margin to the absolute limit")
    magnitude = current_a * rmax_ohm
    return {"assumed_total_sink_a": current_a, "negative_output_v": -magnitude,
            "target_margin_v": target_v - magnitude, "absolute_margin_v": absolute_v - magnitude,
            "arithmetic_target_met": magnitude <= target_v,
            "arithmetic_above_absolute_min": magnitude < absolute_v,
            "full_circuit_current_bound_verified": False, "hardware_accepted": False}

def resistor_power(voltage_v, rmin_ohm, rated_w=1, ambient_c=85, full_power_c=70, zero_power_c=155):
    for name, value in (("voltage", voltage_v), ("resistance", rmin_ohm), ("rated power", rated_w),
                        ("ambient", ambient_c), ("full-power temperature", full_power_c), ("zero-power temperature", zero_power_c)):
        number(value, name, strict=name in {"resistance", "rated power"})
    if zero_power_c <= full_power_c:
        raise ValueError("Invalid linear derating range")
    allowed = rated_w * min(1, max(0, (zero_power_c - ambient_c) / (zero_power_c - full_power_c)))
    loss = voltage_v ** 2 / rmin_ohm
    return {"voltage_v": voltage_v, "loss_w": loss, "allowed_w_assumed_curve": allowed,
            "arithmetic_power_margin_w": allowed - loss, "thermal_qualified": False}

def rc_voltage(time_s, initial_v, current_a, resistance_ohm, capacitance_f):
    for name, value in (("time", time_s), ("initial voltage", initial_v), ("current", current_a),
                        ("resistance", resistance_ohm), ("capacitance", capacitance_f)):
        number(value, name, strict=name in {"resistance", "capacitance"})
    ir = current_a * resistance_ohm
    return -ir + (initial_v + ir) * math.exp(-time_s / (resistance_ohm * capacitance_f))

def divider(vin, vdda=3.3, vdd=3.3, top=47000, bottom=6800, tolerance=.01, capacitance_f=100e-9):
    number(vin, "input voltage", minimum=None)
    for name, value in (("VDDA", vdda), ("VDD", vdd), ("top", top), ("bottom", bottom),
                        ("tolerance", tolerance), ("capacitance", capacitance_f)):
        number(value, name, strict=name in {"top", "bottom", "capacitance"})
    if tolerance >= 1:
        raise ValueError("Divider tolerance must be below one")
    ratio = bottom / (top + bottom)
    lo = bottom * (1 - tolerance) / (top * (1 + tolerance) + bottom * (1 - tolerance))
    hi = bottom * (1 + tolerance) / (top * (1 - tolerance) + bottom * (1 + tolerance))
    low, high = sorted((vin * lo, vin * hi))
    return {"vin_v": vin, "vdda_v": vdda, "vdd_v": vdd, "nominal_output_v": vin * ratio,
            "minimum_output_v": low, "maximum_output_v": high,
            "nominal_tau_s": top * bottom / (top + bottom) * capacitance_f,
            "adc_range_arithmetic_met": low >= 0 and high <= vdda,
            "ft_absolute_voltage_arithmetic_met": low >= -.3 and high <= vdd + 4,
            "startup_or_injection_qualified": False}

def study():
    r = resistor_bounds()
    definitions = [("original_STPS_1mA_point", .001, "component_test_point"),
                   ("proposed_STTH_20uA_point", 20e-6, "component_test_point"),
                   ("hypothetical_total_25uA", 25e-6, "assumed_total"),
                   ("illustrative_total_80uA", 80e-6, "assumed_total_not_guaranteed_INA_off_state")]
    cases = [{"name": name, "basis": basis, **bleeder(i, r["maximum_ohm"])} for name, i, basis in definitions]
    return {"schema_version": 1, "status": "analytical_disposition_only", "hardware_accepted": False,
            "capacitor_reverse_accepted": False, "native_proofs_applicable": False, "electrical_delta": 0,
            "resistor": r, "dc_cases": cases,
            "power_cases": [resistor_power(v, r["minimum_ohm"]) for v in (25.2, 44)],
            "ideal_rc": {"capacitance_f_nominal_only": 47e-6, "resistance_ohm": r["maximum_ohm"],
                         "current_a_assumed": 25e-6, "initial_v": 0,
                         "points": [{"time_s": t, "voltage_v": rc_voltage(t, 0, 25e-6, r["maximum_ohm"], 47e-6)} for t in (0, .1, 1)],
                         "fast_dynamics_modelled": False},
            "divider_cases": [divider(v, vdda=rail, vdd=rail) for v in (-.1, 25.2, 44) for rail in (3.3, 0)],
            "limitations": ["Component test points are not a proven full-circuit leakage budget.",
                            "The 2% service term and 25uA/80uA totals are declared assumptions, not measurements.",
                            "Polarized C1 is not accepted for reverse voltage; meeting the buck target does not clear it.",
                            "Ideal RC omits diode capacitance, reverse recovery, wiring inductance and converter behavior.",
                            "ADC voltage comparisons do not prove power sequencing, injection or unpowered acceptance."]}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("analysis.json"))
    args = parser.parse_args()
    result = study()
    if args.check:
        if json.loads(args.output.read_text(encoding="utf-8-sig")) != result:
            raise ValueError("Captured analysis is stale")
    else:
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("PASS: analytical study " + ("checked" if args.check else "captured") + "; hardware/capacitor acceptance remains false")

if __name__ == "__main__":
    main()
