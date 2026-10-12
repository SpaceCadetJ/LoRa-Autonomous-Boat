#!/usr/bin/env python3
"""Ideal input-network sensitivity: no measured capacitance or hardware acceptance."""
import argparse
import json
import math
from pathlib import Path

def number(value, name, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(name + " must be a finite number")
    if value < 0 or (positive and value == 0):
        raise ValueError(name + " is outside its permitted range")
    return value

def bank_threshold(count, nominal_per_cap_uf=10, minimum_total_uf=4.7, hypothetical_factors=None):
    """Report a requirement; never invent DC-bias, temperature or aging retention."""
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise ValueError("Capacitor count must be a positive integer")
    number(nominal_per_cap_uf, "nominal capacitance", True)
    number(minimum_total_uf, "minimum total effective capacitance", True)
    nominal_total = count * nominal_per_cap_uf
    if not math.isfinite(nominal_total):
        raise ValueError("Nominal capacitance overflow")
    factors = None
    effective = None
    if hypothetical_factors is not None:
        if not isinstance(hypothetical_factors, dict) or set(hypothetical_factors) != {"dc_bias_temperature", "tolerance", "aging"}:
            raise ValueError("Factors must explicitly include dc_bias_temperature, tolerance and aging")
        factors = dict(hypothetical_factors)
        for key, value in factors.items():
            number(value, key)
            if value > 1:
                raise ValueError("Retention factors must be between zero and one")
        effective = nominal_total * math.prod(factors.values())
    return {"count": count, "nominal_per_cap_uf": nominal_per_cap_uf,
            "minimum_total_effective_uf": minimum_total_uf,
            "required_effective_per_cap_uf_equal_share": minimum_total_uf / count,
            "required_combined_retention_fraction": minimum_total_uf / nominal_total,
            "hypothetical_factors": factors, "hypothetical_total_effective_uf": effective,
            "hypothetical_arithmetic_requirement_met": None if effective is None else effective >= minimum_total_uf,
            "effective_capacitance_verified": False, "hardware_accepted": False}

def rlc_step(vin_v=25.2, capacitance_f=20e-6, inductance_h=1e-6, resistance_ohm=.05):
    """Series RLC, ideal positive source step, zero initial capacitor voltage/current."""
    for name, value in (("voltage", vin_v), ("capacitance", capacitance_f),
                        ("inductance", inductance_h), ("resistance", resistance_ohm)):
        number(value, name, name in {"capacitance", "inductance"})
    product = inductance_h * capacitance_f
    ratio = inductance_h / capacitance_f
    if product <= 0 or not math.isfinite(product) or ratio <= 0 or not math.isfinite(ratio):
        raise ValueError("RLC numerical scale is unsupported")
    omega0 = 1 / math.sqrt(product)
    critical_r = 2 * math.sqrt(ratio)
    zeta = resistance_ohm / critical_r
    if not math.isfinite(zeta):
        raise ValueError("Damping ratio overflow")
    if zeta < 1:
        root = math.sqrt((1 - zeta) * (1 + zeta))
        overshoot = math.exp(-math.pi * zeta / root)
        peak_time = math.pi / (omega0 * root)
        damped_hz = omega0 * root / (2 * math.pi)
        case = "undamped" if zeta == 0 else "underdamped"
    else:
        overshoot, peak_time, damped_hz = 0, None, None
        case = "critical" if zeta == 1 else "overdamped"
    peak = vin_v * (1 + overshoot)
    energy = .5 * capacitance_f * vin_v ** 2
    peak_energy = .5 * capacitance_f * peak ** 2
    if not all(math.isfinite(x) for x in (peak, energy, peak_energy, 2 * vin_v)):
        raise ValueError("Voltage or energy overflow")
    return {"vin_v": vin_v, "effective_capacitance_f_assumed": capacitance_f,
            "source_inductance_h_assumed": inductance_h, "source_resistance_ohm_assumed": resistance_ohm,
            "resonance_hz": omega0 / (2 * math.pi), "critical_resistance_ohm": critical_r,
            "damping_ratio": zeta, "damping_case": case, "ringing_hz": damped_hz,
            "overshoot_fraction": overshoot, "first_peak_time_s": peak_time,
            "peak_voltage_v": peak, "ideal_zero_loss_ceiling_v": 2 * vin_v,
            "energy_at_input_voltage_j": energy, "peak_energy_j": peak_energy,
            "prediction_of_actual_board": False, "hardware_accepted": False}

def study():
    return {"schema_version": 1, "status": "illustrative_analytical_sensitivity_only",
            "hardware_accepted": False, "native_proofs_applicable": False, "electrical_delta": 0,
            "local_bank_thresholds": [bank_threshold(n) for n in (1, 2, 3, 4)],
            "rlc_default": rlc_step(),
            "rlc_sweep": [rlc_step(inductance_h=l, resistance_ohm=r) for l in (1e-6, 10e-6, 100e-6) for r in (.05, .5, 2)],
            "ripple_screening": [{"rail": "first_3v3", "output_current_a": 1.2, "approx_input_cap_rms_a": .6},
                                 {"rail": "future_5v_separate", "output_current_a": 2, "approx_input_cap_rms_a": 1}],
            "headroom": {"battery_min_v": 7, "converter_operating_min_v": 4.2,
                         "gross_budget_before_losses_and_sag_v": 7 - 4.2, "regulation_proven": False},
            "assumptions": ["20uF in the RLC cases is assumed EFFECTIVE capacitance, not a nominal BOM sum.",
                            "Zero initial capacitor voltage and inductor current; ideal constant source step.",
                            "Linear lumped R, L and C; positive-step capacitor peak is bounded by2Vin only within this model."],
            "limitations": ["No DC-bias curve or measured capacitance is supplied by this study.",
                            "No diode, TVS, buck, nonlinear capacitance, distributed wiring or repeated-pulse model.",
                            "RMS figures are IOUT/2 screening, not measured ripple ratings or a combined feed budget.",
                            "No component, layout, thermal, surge or hardware qualification follows from these calculations."]}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = Path(__file__).with_name("analysis.json")
    result = study()
    if args.check:
        if json.loads(path.read_text(encoding="utf-8-sig")) != result:
            raise ValueError("Captured analytical study is stale")
    else:
        path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("PASS: analytical sensitivity " + ("checked" if args.check else "captured") + "; hardware remains unaccepted")

if __name__ == "__main__":
    main()
