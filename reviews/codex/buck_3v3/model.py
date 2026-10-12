#!/usr/bin/env python3
"""BUCK33-A1 analytical screens only; no native or hardware qualification."""
import argparse
import json
import math
from pathlib import Path

TI = "https://www.ti.com/lit/ds/symlink/lmr36520.pdf"
COILCRAFT = "https://www.coilcraft.com/en-us/products/power/shielded-inductors/molded-inductor/xal/xal60xx/xal6060-103/"

def number(value, name, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(name + " must be finite")
    if value < 0 or (positive and value == 0):
        raise ValueError(name + " is outside the supported range")
    return value

def feedback_corners(top_ohm=100000, bottom_ohm=43200, resistor_tolerance=.01,
                     vref_min_v=.985, vref_nom_v=1, vref_max_v=1.015):
    """Independent initial resistor tolerances and VFB limits only, no TCR/aging."""
    for name, value in (("top", top_ohm), ("bottom", bottom_ohm),
                        ("VFB min", vref_min_v), ("VFB nom", vref_nom_v), ("VFB max", vref_max_v)):
        number(value, name, True)
    number(resistor_tolerance, "resistor tolerance")
    if resistor_tolerance >= 1 or not vref_min_v <= vref_nom_v <= vref_max_v:
        raise ValueError("Invalid tolerance or reference ordering")
    ratio, t = top_ohm / bottom_ohm, resistor_tolerance
    values = {"nominal_v": vref_nom_v * (1 + ratio),
              "lower_v": vref_min_v * (1 + ratio * (1-t)/(1+t)),
              "upper_v": vref_max_v * (1 + ratio * (1+t)/(1-t))}
    for key, value in values.items(): number(value, key, True)
    return {"top_ohm": top_ohm, "bottom_ohm": bottom_ohm, "initial_tolerance_fraction": t,
            "vref_min_v": vref_min_v, "vref_nom_v": vref_nom_v, "vref_max_v": vref_max_v,
            **values, "tcr_aging_leakage_and_dynamic_regulation_included": False}

def buck_screen(vin_v, vout_v=3.3, output_current_a=1.2, inductance_h=10e-6,
                frequency_hz=400000, dcr_ohm=.02982):
    """Ideal CCM triangular current; invalid CCM returns no current-limit comparison."""
    for name, value in (("VIN", vin_v), ("VOUT", vout_v), ("L", inductance_h), ("frequency", frequency_hz)):
        number(value, name, True)
    number(output_current_a, "load")
    number(dcr_ohm, "DCR")
    if vin_v < vout_v:
        raise ValueError("This buck-only screen requires VIN >= VOUT")
    product = inductance_h * frequency_hz
    number(product, "L times frequency", True)
    duty = vout_v / vin_v
    ripple = (vout_v / product) * (1-duty)
    valley, peak = output_current_a-ripple/2, output_current_a+ripple/2
    rms = math.hypot(output_current_a, ripple / math.sqrt(12))
    on, off = duty/frequency_hz, (1-duty)/frequency_hz
    loss = rms*rms*dcr_ohm
    for key, value in (("ripple", ripple), ("peak", peak), ("RMS", rms), ("loss", loss), ("on time", on), ("off time", off)):
        number(value, key)
    ccm = output_current_a > 0 and valley >= 0
    return {"vin_v": vin_v, "vout_v": vout_v, "output_current_a": output_current_a,
            "inductance_h_assumed": inductance_h, "frequency_hz_assumed": frequency_hz,
            "ideal_duty": duty, "ideal_on_time_s": on, "ideal_off_time_s": off,
            "ripple_pp_a": ripple, "valley_a": valley, "peak_a": peak, "rms_a": rms,
            "dcr_ohm_25c_screen": dcr_ohm, "dcr_loss_w_25c": loss,
            "ideal_ccm_condition_met": ccm,
            "valley_below_ilimit_min_1p8a_screen": valley < 1.8 if ccm else None,
            "peak_below_isc_min_2p4a_screen": peak < 2.4 if ccm else None,
            "peak_below_isc_max_3p6a_comparison": peak < 3.6 if ccm else None,
            "valley_limit_margin_to_min_a": 1.8-valley if ccm else None,
            "peak_limit_margin_to_min_a": 2.4-peak if ccm else None,
            "on_time_exceeds_92ns_nominal_comparison": on > 92e-9,
            "off_time_exceeds_102ns_maximum_comparison": off > 102e-9,
            "fixed_frequency_proven": False, "hardware_accepted": False}

def study():
    fb = feedback_corners()
    cases = []
    for vin in (7, 25.2, 44):
        for name, l, f in (("nominal_L_and_frequency", 10e-6, 400000),
                           ("initial_L_minus20pct_and_frequency_min", 8e-6, 340000)):
            cases.append({"case": name, **buck_screen(vin, inductance_h=l, frequency_hz=f)})
    lmin = .42 * 3.3 / 340000
    lmin_high_fb = .42 * fb["upper_v"] / 340000
    return {"schema_version": 1, "revision": "BUCK33-A1", "status": "ideal_analytical_screen_only",
            "hardware_accepted": False, "native_proofs_from_this_model": False,
            "feedback": fb,
            "inductor": {"mpn": "XAL6060-103MEC", "nominal_h": 10e-6,
                         "initial_tolerance_min_h": 8e-6, "dc_bias_and_temperature_inductance_bound_verified": False,
                         "eq5_min_h_at_3p3v_340khz": lmin,
                         "eq5_min_h_at_feedback_upper_340khz": lmin_high_fb,
                         "initial_min_above_eq5_screen": 8e-6 > lmin_high_fb,
                         "dcr_max_25c_primary_rounded_ohm": .0298, "dcr_25c_declared_screen_ohm": .02982,
                         "isat_30pct_drop_typical_25c_a": 7.6, "isc_high_side_max_a": 3.6,
                         "typical_isat_minus_isc_max_a": 7.6-3.6, "hot_saturation_bound_verified": False},
            "operating_cases": cases,
            "timing_corner": {"minimum_on_time_nominal_s": 92e-9, "minimum_on_time_maximum_s": None,
                              "minimum_off_time_maximum_s": 102e-9,
                              "shortest_on_time_screen": buck_screen(44, vout_v=fb["lower_v"], frequency_hz=460000),
                              "floor_input_off_time_screen": buck_screen(4.2, vout_v=fb["upper_v"], frequency_hz=460000),
                              "fixed_frequency_proven": False},
            "capacitance": {"output_mpn": "C3225X7R1E226M250AB", "output_count": 3,
                            "output_each_rated_uf": 22, "output_rated_sum_uf": 66,
                            "output_effective_lower_bound_uf": None,
                            "local_input_rated_sum_uf": 20, "local_input_required_effective_uf": 4.7,
                            "local_input_effective_lower_bound_uf": None,
                            "effective_capacitance_verified": False},
            "headroom": {"battery_min_v": 7, "converter_operating_min_v": 4.2,
                         "gross_voltage_budget_before_feed_losses_v": 7-4.2,
                         "en_connection": "VIN_BUCK", "pack_uvlo_implemented": False,
                         "positive_target_v": 44, "clamp_voltage_verified": False, "regulation_proven": False},
            "acceptance_gates": {key: False for key in ("hardware", "effective_capacitance", "loop_stability",
                "load_transient", "thermal", "inductor_hot_current", "input_damping", "negative_rail", "adc_sequencing")},
            "limitations": ["VFB min/max are TI table limits; feedback corners include initial resistor tolerance only.",
                "No guessed TCR, aging, leakage or line/load/dynamic regulation term; those remain open.",
                "Current limits are open-loop table values and may differ in closed-loop use; ISC varies with duty.",
                "ILIMIT is the low-side VALLEY limit; ISC is a separate high-side PEAK limit.",
                "10uH/8uH are nominal/initial tolerance values, not guaranteed inductance under current and heat.",
                "7.6A Isat uses a typical 30% inductance loss at 25C, not a hot minimum or non-saturation proof.",
                "DCR loss includes triangular ripple but excludes hot DCR, AC winding loss and core loss.",
                "CCM equations do not predict PFM/DCM, startup, saturation, switching loss or actual efficiency.",
                "92ns on-time is nominal only; timing comparisons do not guarantee fixed switching frequency.",
                "66uF output is rated/nameplate capacitance; no effective lower bound or stability proof follows.",
                "Only the first 3.3V/1.2A cell is screened; optional 5V/servo supply is separate."],
            "sources": [{"url": TI, "revision": "SNVSBF0C November 2025", "sections": "6.5-6.7, 7.3.3, 8.2.1.2"},
                        {"url": COILCRAFT, "basis": "25C table and footnotes; 29.8mOhm rounded primary maximum"}]}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path, result = Path(__file__).with_name("analysis.json"), study()
    if args.check:
        if json.loads(path.read_text(encoding="utf-8-sig")) != result:
            raise ValueError("Captured buck analysis is stale")
    else:
        path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
    print("PASS: buck analytical screen " + ("checked" if args.check else "captured") + "; hardware unaccepted")

if __name__ == "__main__":
    main()
