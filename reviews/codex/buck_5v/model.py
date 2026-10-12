#!/usr/bin/env python3
"""BUCK5-A1: ideal converter and source-feed screens, never hardware acceptance."""
import argparse
import itertools
import json
import math
from pathlib import Path

TI = "https://www.ti.com/lit/ds/symlink/lm76003.pdf"
TI20 = "https://www.ti.com/lit/ds/symlink/lmr36520.pdf"
ST = "https://www.st.com/resource/en/datasheet/stps3h100.pdf"

def number(value, name, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(name + " must be finite")
    if value < 0 or (positive and value == 0):
        raise ValueError(name + " is outside the supported range")
    return value

def feedback_corners(top_ohm=100000, bottom_ohm=24900, tolerance=.01, leakage_a=60e-9):
    for key, value in (("top", top_ohm), ("bottom", bottom_ohm)):
        number(value, key, True)
    number(tolerance, "tolerance")
    number(leakage_a, "FB leakage magnitude")
    if tolerance >= 1: raise ValueError("Tolerance must be less than one")
    ratio, t = top_ohm/bottom_ohm, tolerance
    lo = .987*(1 + ratio*(1-t)/(1+t))
    hi = 1.017*(1 + ratio*(1+t)/(1-t))
    leak = leakage_a*top_ohm*(1+t)
    typical = 1.006*(1+ratio)
    for value in (lo, hi, leak, typical): number(value, "feedback result")
    if lo-leak <= 0: raise ValueError("Leakage bound exceeds positive output model")
    return {"top_ohm": top_ohm, "bottom_ohm": bottom_ohm, "initial_tolerance_fraction": t,
            "pwm_vfb_min_typ_max_v": [.987, 1.006, 1.017], "typical_pwm_v": typical,
            "initial_reference_resistor_lower_v": lo, "initial_reference_resistor_upper_v": hi,
            "fb_leakage_bound_a": leakage_a, "conservative_leakage_output_shift_v": leak,
            "initial_pwm_lower_including_leakage_v": lo-leak,
            "initial_pwm_upper_including_leakage_v": hi+leak,
            "pfm_no_load_offset_typical_fraction": .02, "guaranteed_pfm_upper_v": None,
            "tcr_aging_layout_and_dynamic_regulation_included": False}

def converter_screen(vin_v, vout_v=5.046160642570281, output_current_a=2,
                     inductance_h=10e-6, frequency_hz=500000, dcr_ohm=.02982):
    for key, value in (("VIN", vin_v), ("VOUT", vout_v), ("L", inductance_h), ("frequency", frequency_hz)):
        number(value, key, True)
    number(output_current_a, "load")
    number(dcr_ohm, "DCR")
    if vin_v < vout_v: raise ValueError("Buck-only screen requires VIN >= VOUT")
    product = number(inductance_h*frequency_hz, "L times frequency", True)
    duty = vout_v/vin_v
    ripple = vout_v/product*(1-duty)
    valley, peak = output_current_a-ripple/2, output_current_a+ripple/2
    rms = math.hypot(output_current_a, ripple/math.sqrt(12))
    on, off, loss = duty/frequency_hz, (1-duty)/frequency_hz, rms*rms*dcr_ohm
    for value in (ripple, peak, rms, on, off, loss): number(value, "converter result")
    ccm = output_current_a > 0 and valley >= 0
    return {"vin_v": vin_v, "vout_v": vout_v, "output_current_a": output_current_a,
            "inductance_h_assumed": inductance_h, "frequency_hz_assumed": frequency_hz,
            "ideal_duty": duty, "ripple_pp_a": ripple, "valley_a": valley, "peak_a": peak,
            "rms_a": rms, "dcr_loss_w_25c": loss, "ideal_on_time_s": on, "ideal_off_time_s": off,
            "ideal_ccm_condition_met": ccm,
            "valley_margin_to_ils_min_3p4a": 3.4-valley if ccm else None,
            "peak_margin_to_ihs_min_4p35a": 4.35-peak if ccm else None,
            "on_time_exceeds_95ns_maximum_comparison": on > 95e-9,
            "off_time_exceeds_130ns_maximum_comparison": off > 130e-9,
            "fixed_frequency_proven": False, "hardware_accepted": False}

def lmr36520_exclusion():
    """No fixed L passes both open-loop minimum-limit screens for the stated corners."""
    low_factor = 5*(1-5/7)/(1.2*460000)
    high_factor = 5*(1-5/44)/(.8*340000)
    ratio = high_factor/low_factor
    low_needed, high_allowed = 2*(2-1.8), 2*(2.4-2)
    optimum_low_ripple = 2*(2.4-1.8)/(1+ratio)
    return {"load_a": 2, "vout_v": 5, "vin_range_v": [7, 44],
            "frequency_range_hz": [340000, 460000], "initial_l_tolerance_fraction": .2,
            "required_low_input_ripple_at_2a_a": low_needed,
            "allowed_high_input_ripple_at_2a_a": high_allowed,
            "high_to_low_ripple_ratio": ratio,
            "l_nominal_max_from_valley_h": low_factor/low_needed,
            "l_nominal_min_from_peak_h": high_factor/high_allowed,
            "fixed_l_satisfies_both_screens": high_factor/high_allowed <= low_factor/low_needed,
            "best_ideal_fixed_l_h": low_factor/optimum_low_ripple,
            "best_ideal_common_load_ceiling_a": 1.8+optimum_low_ripple/2,
            "every_physical_device_failure_proven": False,
            "limitation": "Open-loop comparator limits; excludes feedback, losses, hot inductance and dynamic behavior."}

def feed_budget(battery_v=7, logic_current_a=1.2, rail5_current_a=2,
                efficiency_3v3=.85, efficiency_5v=.85, diode_v0=.6, diode_r_ohm=.027,
                fuse_r_ohm=.0367, shunt_r_ohm=.02, harness_r_ohm=0, feed_goal_a=1):
    """DC constant-power lower-current root; ST loss fit plus nominal ohmic losses."""
    for key, value in locals().copy().items(): number(value, key, key in {"battery_v", "efficiency_3v3", "efficiency_5v", "feed_goal_a"})
    if efficiency_3v3 > 1 or efficiency_5v > 1: raise ValueError("Efficiency must be in (0,1]")
    power = 3.3*logic_current_a/efficiency_3v3 + 5*rail5_current_a/efficiency_5v
    available = battery_v-diode_v0
    if available <= 0: raise ValueError("Source voltage does not exceed affine diode offset")
    r = diode_r_ohm+fuse_r_ohm+shunt_r_ohm+harness_r_ohm
    discriminant = available*available-4*r*power
    for value in (power, r, available*available, 4*r*power): number(value, "source-feed scale")
    current = 2*power/(available+math.sqrt(discriminant)) if discriminant >= 0 else None
    if current is not None: number(current, "source current")
    bus_v = available-r*current if current is not None else None
    result = {"battery_v": battery_v, "logic_current_a_planned_at_3p3v": logic_current_a,
              "total_5v_rail_current_a_planned": rail5_current_a,
              "efficiencies_assumed": [efficiency_3v3, efficiency_5v],
              "converter_input_power_w_assumed": power, "diode_v0_loss_fit": diode_v0,
              "diode_r_ohm_loss_fit": diode_r_ohm, "fuse_r_ohm_nominal": fuse_r_ohm,
              "shunt_r_ohm_nominal": shunt_r_ohm, "harness_r_ohm_assumed": harness_r_ohm,
              "dc_source_solution_exists": current is not None, "source_current_a": current,
              "converter_input_v_assumed": bus_v, "feed_goal_a": feed_goal_a,
              "within_feed_goal_arithmetic": current <= feed_goal_a if current is not None else False,
              "below_fuse_25c_1p5a_derating_screen": current <= 1.5 if current is not None else False,
              "source_power_w": battery_v*current if current is not None else None,
              "diode_loss_w_fit": diode_v0*current+diode_r_ohm*current*current if current is not None else None,
              "ohmic_loss_w_nominal": (r-diode_r_ohm)*current*current if current is not None else None,
              "hardware_accepted": False, "dynamic_stability_proven": False}
    capacity_current = min(feed_goal_a, available/(2*r)) if r else feed_goal_a
    capacity = (available-r*capacity_current)*capacity_current
    number(capacity, "source capacity")
    result["max_total_5v_current_at_feed_goal_a_assumed"] = max(0, (capacity-3.3*logic_current_a/efficiency_3v3)*efficiency_5v/5)
    return result

def study():
    fb = feedback_corners()
    lo, hi = fb["initial_pwm_lower_including_leakage_v"], fb["initial_pwm_upper_including_leakage_v"]
    corners = [converter_screen(v, vo, inductance_h=l, frequency_hz=f)
               for v, vo, l, f in itertools.product((7, 25.2, 44), (lo, hi), (8e-6, 12e-6), (440000, 560000))]
    cases = [{"case": name, **converter_screen(v, fb["typical_pwm_v"], inductance_h=l, frequency_hz=f)}
             for v in (7, 25.2, 44) for name, l, f in
             (("nominal", 10e-6, 500000), ("initial_L_min_and_frequency_min", 8e-6, 440000))]
    feeds = [{"case": name, **feed_budget(v, rail5_current_a=i)} for v in (7, 25.2)
             for name, i in (("external_BEC_20mA_aux_only", .02), ("2A_total_5V_rail", 2), ("2A_servo_plus_20mA_aux", 2.02))]
    return {"schema_version": 1, "revision": "BUCK5-A1", "status": "ideal_analytical_screen_only",
            "hardware_accepted": False, "native_proofs_from_this_model": False,
            "selected": {"regulator": "LM76003RNPR", "rt": "open", "frequency_min_typ_max_hz": [440000, 500000, 560000],
                "inductor": "XAL6060-103MEC", "inductance_h": 10e-6, "initial_l_tolerance_fraction": .2,
                "ti_5v_500khz_typical_l_h": 6.8e-6, "inductor_value_deviation_requires_loop_review": True,
                "isat_30pct_drop_typical_25c_a": 7.6, "ihs_min_typ_max_a": [4.35, 5.5, 6.8],
                "ils_valley_min_typ_max_a": [3.4, 4.2, 5.3], "hot_saturation_bound_verified": False,
                "minimum_on_time_typ_max_s": [65e-9, 95e-9], "minimum_off_time_typ_max_s": [95e-9, 130e-9]},
            "feedback": fb, "operating_cases": cases,
            "initial_corner_envelope": {"corner_count": len(corners), "includes_hot_inductance": False,
                "largest_peak_case": max(corners, key=lambda x: x["peak_a"]),
                "smallest_valley_margin_case": min(corners, key=lambda x: x["valley_margin_to_ils_min_3p4a"]),
                "shortest_on_time_case": min(corners, key=lambda x: x["ideal_on_time_s"]),
                "shortest_off_time_case": min(corners, key=lambda x: x["ideal_off_time_s"])},
            "lmr36520_comparison": lmr36520_exclusion(),
            "capacitance": {"output_mpn": "C3225X7R1E226M250AB", "output_count": 5,
                "output_each_rated_uf": 22, "output_rated_sum_uf": 110,
                "output_initial_tolerance_only_lower_uf": 88, "output_effective_lower_bound_uf": None,
                "ti_typical_output_reference_uf": 100, "guaranteed_100uf_effective_claim": False,
                "output_effective_requirement_from_transient_loop_review_uf": None,
                "local_input_rated_sum_uf": 20, "ti_typical_input_guidance_uf": [10, 22],
                "local_input_effective_requirement_uf": None, "effective_capacitance_verified": False,
                "bootstrap_mpn": "C1608X7R1E474K080AB", "bootstrap_rated_uf": .47,
                "vcc_mpn": "C2012X7R1E225K125AB", "vcc_rated_uf": 2.2,
                "bias_mpn": "C1608X7R1E105K080AB", "bias_rated_uf": 1},
            "source_feed_cases": feeds,
            "lossless_7v_full_rail_capacity_current_a": (3.3*1.2+5*2)/7,
            "acceptance_gates": {k: False for k in ("hardware", "source_feed", "thermal", "magnetics_hot",
                "effective_capacitance", "loop_stability", "load_transient", "input_damping", "negative_rail", "backfeed")},
            "limitations": ["Converter VIN cases are terminal voltages, not battery voltages before feed drops; source budgets use 3.3 V and 5 V planning loads.",
                "Source-feed maximum 5 V current is a power-budget calculation, not permission to exceed the 2 A rail design goal.",
                "PWM bounds omit TCR, aging and dynamics; 2% PFM no-load offset is typical, not a guaranteed bound.",
                "Inductance corners cover initial tolerance only. Current-limit comparator delays change closed-loop thresholds.",
                "Timing comparisons are ideal only; PFM, losses, ringing, startup and control dynamics are not modeled.",
                "DCR loss at 25 C excludes hot DCR, AC winding and core losses; 7.6 A Isat is typical 30% drop, not a hot bound.",
                "110 uF output rated and 88 uF initial minimum do not prove 100 uF effective or loop/transient acceptance.",
                "Local CIN differs from TI example; the first converter's 4.7 uF criterion is not automatically portable.",
                "Source fit uses DC current for diode RMS; 85% efficiencies and harness resistance are assumptions.",
                "Fuse/shunt resistance is nominal; no cold-drop, hot-resistance, ripple, inrush or fuse-opening guarantee.",
                "A 2 A fuse with 25% room-temperature derating screens at 1.5 A; additional temperature/pulse checks remain.",
                "Source quadratic uses its lower-current root and does not establish dynamic stability or startup.",
                "BIAS tied to own 5 V must obey VIN + 0.3 V; external BEC and falling-input/backfeed sequencing remain held.",
                "44 V is a positive target, not a verified clamp. External-BEC servo energy is outside board-feed budget."],
            "sources": [{"url": TI, "revision": "SNVSAK0A October 2019", "sections": "5,6.5-6.7,8.2.2"},
                {"url": TI20, "revision": "SNVSBF0C November 2025", "sections": "6.5-6.7,7.3.3"},
                {"url": ST, "revision": "DS6597 Rev 3 January 2020", "page": 2},
                {"url": "https://www.coilcraft.com/en-us/products/power/shielded-inductors/molded-inductor/xal/xal60xx/xal6060-103/", "basis": "25 C table; 29.82 mOhm declared screen versus 29.8 rounded primary value"},
                {"url": "https://www.littelfuse.com/assetdocs/fuse-451-and-453-datasheet?assetguid=533cd5cc-956c-4243-867f-6ab5a62f6ba1", "basis": "0451002.MRL nominal 36.7 mOhm, 25% continuous derating; no hot bound"}]}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path, result = Path(__file__).with_name("analysis.json"), study()
    if args.check:
        if json.loads(path.read_text(encoding="utf-8-sig")) != result: raise ValueError("Captured buck analysis is stale")
    else:
        path.write_text(json.dumps(result, indent=2, allow_nan=False)+"\n", encoding="utf-8", newline="\n")
    print("PASS: buck/source analytical screen " + ("checked" if args.check else "captured") + "; hardware unaccepted")

if __name__ == "__main__":
    main()
