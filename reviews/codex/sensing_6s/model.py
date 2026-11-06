"""SENSE-01 conditional arithmetic for the captured sensing circuit.

Pure functions and JSON-ready collect(); no file writes or import side effects.
Unknown inputs stay None. Arithmetic margins never authorize hardware use.
"""
from __future__ import annotations

import math


def _inputs(values, positive=(), nonnegative=()):
    result = {}
    for name, value in values.items():
        if value is None:
            result[name] = None
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be a finite real number or None")
        try:
            value = float(value)
        except (OverflowError, ValueError) as exc:
            raise ValueError(f"{name} must be finite") from exc
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
        if name in positive and value <= 0:
            raise ValueError(f"{name} must be positive")
        if name in nonnegative and value < 0:
            raise ValueError(f"{name} must be nonnegative")
        result[name] = value
    return result


def _bits(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 32:
        raise ValueError("bits must be an integer from 1 through 32 or None")
    return value


def _result(inputs, fields):
    missing = [key for key, value in inputs.items() if value is None]
    return {
        "status": "unavailable" if missing else "calculated",
        "inputs": inputs,
        "missing_fields": missing,
        **{key: None for key in fields},
        "necessary_arithmetic_only": True,
        "hardware_accepted": False,
    }


def _set(result, **values):
    if any(not math.isfinite(value) for value in values.values()):
        raise ValueError("derived arithmetic exceeded the finite model domain")
    result.update(values)
    return result


def divider(rtop_ohm, rbottom_ohm, top_tolerance, bottom_tolerance):
    """Independent resistor corners; no temperature/leakage/ADC error budget."""
    p = _inputs(dict(rtop_ohm=rtop_ohm, rbottom_ohm=rbottom_ohm,
                     top_tolerance=top_tolerance, bottom_tolerance=bottom_tolerance),
                positive=("rtop_ohm", "rbottom_ohm"))
    for key in ("top_tolerance", "bottom_tolerance"):
        if p[key] is not None and not 0 <= p[key] < 1:
            raise ValueError(f"{key} must be in [0, 1)")
    result = _result(p, ("ratio_nominal", "ratio_min", "ratio_max", "inverse_nominal"))
    if result["missing_fields"]:
        return result
    rt, rb, tt, bt = (p[key] for key in p)
    rlo = rb * (1 - bt) / (rt * (1 + tt) + rb * (1 - bt))
    rhi = rb * (1 + bt) / (rt * (1 - tt) + rb * (1 + bt))
    return _set(result, ratio_nominal=rb / (rt + rb), ratio_min=rlo,
                ratio_max=rhi, inverse_nominal=(rt + rb) / rb)


def range_headroom(vin_raw_max_v, vdda_min_v, ratio_max):
    """Upper ADC voltage and inverse ceiling using explicit VDDA minimum.

A positive margin is only conditional divider arithmetic. It excludes source
transients, reference accuracy, resistor temperature drift and ADC error.
"""
    p = _inputs(dict(vin_raw_max_v=vin_raw_max_v, vdda_min_v=vdda_min_v,
                     ratio_max=ratio_max), positive=("vdda_min_v", "ratio_max"),
                nonnegative=("vin_raw_max_v",))
    if p["ratio_max"] is not None and p["ratio_max"] > 1:
        raise ValueError("ratio_max cannot exceed one for a passive divider")
    result = _result(p, ("adc_max_v", "headroom_v", "input_ceiling_v",
                         "strict_positive_arithmetic_margin"))
    if p["vin_raw_max_v"] is not None and p["ratio_max"] is not None:
        _set(result, adc_max_v=p["vin_raw_max_v"] * p["ratio_max"])
    if p["vdda_min_v"] is not None and p["ratio_max"] is not None:
        _set(result, input_ceiling_v=p["vdda_min_v"] / p["ratio_max"])
    if result["missing_fields"]:
        return result
    _set(result, headroom_v=p["vdda_min_v"] - result["adc_max_v"])
    result["strict_positive_arithmetic_margin"] = result["headroom_v"] > 0
    return result


def divider_filter(rtop_ohm, rbottom_ohm, capacitance_f):
    """Ideal unloaded divider plus capacitor; nominal component values only."""
    p = _inputs(dict(rtop_ohm=rtop_ohm, rbottom_ohm=rbottom_ohm,
                     capacitance_f=capacitance_f),
                positive=("rtop_ohm", "rbottom_ohm", "capacitance_f"))
    result = _result(p, ("rth_ohm", "tau_s", "fc_hz"))
    if result["missing_fields"]:
        return result
    rth = 1 / (1 / p["rtop_ohm"] + 1 / p["rbottom_ohm"])
    tau = rth * p["capacitance_f"]
    return _set(result, rth_ohm=rth, tau_s=tau, fc_hz=1 / (2 * math.pi * tau))


def settling_to_quarter_lsb(tau_s, adc_node_step_v, vref_v, bits):
    """Time for ideal RC step residue <= Vref/(4*2**N).

adc_node_step_v is the final divider-node step, not the battery voltage step.
This is continuous RC settling, not switched-capacitor ADC acquisition.
"""
    p = _inputs(dict(tau_s=tau_s, adc_node_step_v=adc_node_step_v, vref_v=vref_v),
                positive=("tau_s", "vref_v"))
    p["bits"] = _bits(bits)
    result = _result(p, ("quarter_lsb_v", "settling_time_s"))
    if result["missing_fields"]:
        return result
    target = p["vref_v"] / (4 * 2 ** p["bits"])
    step = abs(p["adc_node_step_v"])
    delay = 0 if step <= target else p["tau_s"] * math.log(step / target)
    return _set(result, quarter_lsb_v=target, settling_time_s=delay)


def adc_resistive_acquisition(fadc_hz, rain_ohm, radc_ohm, cadc_f, bits):
    """Illustrative resistive-source expression, not an external-cap model.

k_min = 0.5 + fADC*CADC*(RAIN+RADC)*ln(2**(N+2)).
No claim is made for the captured 100 nF reservoir, amplifier stability,
channel-to-channel kickback, selected ADC mode or actual sample-time setting.
"""
    p = _inputs(dict(fadc_hz=fadc_hz, rain_ohm=rain_ohm, radc_ohm=radc_ohm,
                     cadc_f=cadc_f), positive=("fadc_hz", "cadc_f"),
                nonnegative=("rain_ohm", "radc_ohm"))
    p["bits"] = _bits(bits)
    result = _result(p, ("k_min_cycles", "equivalent_time_s"))
    result.update(illustrative_only=True, external_capacitance_modeled=False,
                  actual_sample_cycles=None, actual_sample_time_s=None,
                  acquisition_qualified=False)
    if result["missing_fields"]:
        return result
    cycles = .5 + p["fadc_hz"] * p["cadc_f"] * (p["rain_ohm"] + p["radc_ohm"]) * ((p["bits"] + 2) * math.log(2))
    return _set(result, k_min_cycles=cycles, equivalent_time_s=cycles / p["fadc_hz"])


def nominal_shunt(current_a, shunt_ohm, gain_v_per_v):
    """Positive-direction ideal transfer and losses, never device/range ratings."""
    p = _inputs(dict(current_a=current_a, shunt_ohm=shunt_ohm,
                     gain_v_per_v=gain_v_per_v),
                positive=("shunt_ohm", "gain_v_per_v"), nonnegative=("current_a",))
    result = _result(p, ("ideal_transfer_v_per_a", "ideal_output_v",
                         "shunt_drop_v", "shunt_loss_w"))
    result.update(validated_current_range_a=None, output_swing_qualified=False,
                  values_are_device_ratings=False)
    if result["missing_fields"]:
        return result
    current, resistance, gain = (p[key] for key in p)
    return _set(result, ideal_transfer_v_per_a=resistance * gain,
                ideal_output_v=current * resistance * gain,
                shunt_drop_v=current * resistance,
                shunt_loss_w=current * current * resistance)


def collect():
    """Return deterministic results; examples are allocations, not measurements."""
    ratio = divider(47000, 6800, .01, .01)
    filt = divider_filter(47000, 6800, 100e-9)
    cases = []
    for vin in (25.2, 26.0):
        for vdda in (3.3, 3.135):
            case = range_headroom(vin, vdda, ratio["ratio_max"])
            case.update(assumed_reference_floor=True,
                        adc_nominal_v=vin * ratio["ratio_nominal"],
                        adc_min_resistor_corner_v=vin * ratio["ratio_min"])
            cases.append(case)
    return {
        "schema": 1,
        "revision": "SENSE-01",
        "status": "conditional_analysis_only",
        "candidate_electrical_delta": 0,
        "live_electrical_delta": 0,
        "live_copper_delta": 0,
        "hardware_accepted": False,
        "device_release_approved": False,
        "protection_qualified": False,
        "native_commands_rerun": False,
        "captured_topology": {
            "voltage_boundary": "VIN_RAW: post-fuse and post-D12 series diode, before R33",
            "current_boundary": "R33: VIN_RAW to shared converter-input VIN_BUCK",
            "rtop_ref": "R31", "rtop_ohm": 47000,
            "rbottom_ref": "R32", "rbottom_ohm": 6800,
            "voltage_cap_ref": "C36", "voltage_cap_nominal_f": 100e-9,
            "shunt_ref": "R33", "shunt_nominal_ohm": .02,
            "amplifier_ref": "U8", "amplifier_gain_nominal": 20,
            "current_cap_ref": "C37", "current_cap_nominal_f": 100e-9,
            "current_output_series_resistor_present": False,
            "current_channel_passive_rc_cutoff_hz": None,
        },
        "unknown_actual_inputs": {
            "vin_raw_source_max_v": None, "vin_raw_transient_max_v": None,
            "vdda_min_v": None, "vdda_max_v": None,
            "effective_filter_capacitance_f": None,
            "adc_sample_cycles": None, "adc_clock_hz": None,
            "adc_error_budget_v": None, "amplifier_error_budget_v": None,
            "current_envelope_a": None, "power_sequence_envelope": None,
        },
        "actual": {
            "voltage_range": range_headroom(None, None, ratio["ratio_max"]),
            "adc_acquisition": adc_resistive_acquisition(None, None, None, None, 12),
            "current_transfer": nominal_shunt(None, .02, 20),
        },
        "divider": ratio,
        "divider_filter_nominal": filt,
        "voltage_cases": cases,
        "divider_settling_cases": [
            {"description": "Full-reference ADC-node step, ideal nominal RC",
             **settling_to_quarter_lsb(filt["tau_s"], 3.3, 3.3, 12)},
            {"description": "Zero to 25.2 V VIN_RAW, nominal divider and RC",
             **settling_to_quarter_lsb(filt["tau_s"], 25.2 * ratio["ratio_nominal"], 3.3, 12)},
        ],
        "adc_illustration": adc_resistive_acquisition(30e6, filt["rth_ohm"], 6000, 7e-12, 12),
        "shunt_examples": [nominal_shunt(current, .02, 20) for current in (0, 1, 3)],
        "limitations": [
            "Recorded part values and arithmetic do not establish qualified supplier identities or ratings.",
            "The 1% resistor examples exclude temperature, leakage, reference variation and ADC errors.",
            "3.3 V and 3.135 V are explicit illustration inputs; neither is a measured VDDA bound.",
            "VIN_RAW sensing excludes upstream diode/fuse/wiring drops and is not battery-terminal measurement.",
            "R33 measures converter input; BEC_ONLY servo current, divider draw and input TVS/capacitor currents bypass it.",
            "Current-channel C37 directly loads U8; no series isolation resistor or valid passive RC cutoff is established.",
            "RC step settling and the resistive-source ADC expression are separate simplified models, not combined acquisition proof.",
            "Shunt ideal output ignores common-mode, output swing, amplifier offset/gain error and unpowered behavior.",
            "Stage A firmware has no ADC driver, calibration, acquisition setting or voltage/current conversion.",
        ],
    }
