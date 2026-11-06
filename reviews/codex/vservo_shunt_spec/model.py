"""VSERVO-03 necessary shunt arithmetic; no device or hardware release.

All inputs are explicit. None records missing evidence, never a default.
The switched-resistor branch excludes switching transitions and FET linear SOA.
"""
from __future__ import annotations

from decimal import Decimal, localcontext
import math


def _inputs(values, positive=(), nonnegative=()):
    out = {}
    for name, value in values.items():
        if value is None:
            out[name] = None
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
        out[name] = value
    return out


def _ordered(p, low, high):
    if p[low] is not None and p[high] is not None and p[low] > p[high]:
        raise ValueError(f"{low} cannot exceed {high}")


def _tolerance(p):
    value = p["tolerance"]
    if value is not None and not 0 <= value < 1:
        raise ValueError("tolerance must be in [0, 1)")


def _result(inputs, fields):
    missing = [name for name, value in inputs.items() if value is None]
    return {
        "status": "unavailable" if missing else "calculated",
        "inputs": inputs,
        "missing_fields": missing,
        **{field: None for field in fields},
        "necessary_arithmetic_only": True,
        "hardware_accepted": False,
        "device_release_approved": False,
    }


def _d(value):
    return Decimal(str(value))


def _float(value):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("derived arithmetic exceeded the finite model domain")
    return value


def _difference(value, *terms):
    # Written decimal equality remains zero: no positive binary round-off margin.
    with localcontext() as ctx:
        ctx.prec = 50
        result = _d(value)
        for term in terms:
            result -= _d(term)
        return _float(result)


def window(normal_max, off_min, off_max, on_min, on_max, noise_pp,
           remaining_rise, allowed_max):
    """Necessary release, hysteresis and protection margins in volts.

    remaining_rise covers all rise above worst turn-on, including loaded clamp
    response, delay, capacitor ESR and local inductance. noise_pp is the complete
    allocated peak-to-peak disturbance at the threshold sensing boundary.
    normal_max includes the worst sensed normal source, ripple and signed sense
    disturbance. noise_pp protects the rising/falling gap. A release threshold
    does not bound turn-OFF-delay discharge below that threshold. This does not
    simulate dynamics, self-powered startup or remote voltage.
    """
    p = _inputs(dict(normal_max=normal_max, off_min=off_min, off_max=off_max,
                     on_min=on_min, on_max=on_max, noise_pp=noise_pp,
                     remaining_rise=remaining_rise, allowed_max=allowed_max),
                positive=("normal_max", "off_min", "off_max", "on_min", "on_max", "allowed_max"),
                nonnegative=("noise_pp", "remaining_rise"))
    _ordered(p, "off_min", "off_max")
    _ordered(p, "on_min", "on_max")
    out = _result(p, ("release_margin_V", "hysteresis_margin_V", "protection_margin_V",
                      "strict_positive_arithmetic_margin"))
    if out["missing_fields"]:
        return out
    release = _difference(p["off_min"], p["normal_max"])
    hysteresis = _difference(p["on_min"], p["off_max"], p["noise_pp"])
    protection = _difference(p["allowed_max"], p["on_max"], p["remaining_rise"])
    out.update(release_margin_V=release, hysteresis_margin_V=hysteresis,
               protection_margin_V=protection,
               strict_positive_arithmetic_margin=min(release, hysteresis, protection) > 0)
    return out


def resistance_window(off_min, excess_current_max, rail_max,
                      path_current_allocation, ron_min, ron_max, tolerance):
    """Strict nominal resistance interval for a fully ON series resistor/FET.

    A lower bound limits worst current; an upper bound permits recovery at the
    lowest release threshold against the declared positive excess-current bound.
    Excess current includes every simultaneously contributing source after
    credited loads, and the path-current allocation is an independent constraint.
    Threshold, dynamics, temperature, pulse ratings and failures remain open.
    """
    p = _inputs(dict(off_min=off_min, excess_current_max=excess_current_max,
                     rail_max=rail_max, path_current_allocation=path_current_allocation,
                     ron_min=ron_min, ron_max=ron_max, tolerance=tolerance),
                positive=("off_min", "excess_current_max", "rail_max", "path_current_allocation"),
                nonnegative=("ron_min", "ron_max"))
    _ordered(p, "ron_min", "ron_max")
    _ordered(p, "off_min", "rail_max")
    _tolerance(p)
    out = _result(p, ("nominal_lower_exclusive_ohm", "nominal_upper_exclusive_ohm",
                      "nominal_interval_width_ohm", "strict_positive_nominal_interval"))
    if out["missing_fields"]:
        return out
    with localcontext() as ctx:
        ctx.prec = 50
        d = {key: _d(value) for key, value in p.items()}
        lower = max(Decimal(0), (d["rail_max"] / d["path_current_allocation"] - d["ron_min"]) / (1 - d["tolerance"]))
        upper = (d["off_min"] / d["excess_current_max"] - d["ron_max"]) / (1 + d["tolerance"])
        width = upper - lower
        out.update(nominal_lower_exclusive_ohm=_float(lower),
                   nominal_upper_exclusive_ohm=_float(upper),
                   nominal_interval_width_ohm=_float(width),
                   strict_positive_nominal_interval=width > 0)
    return out


def branch_bound(Rnom, tolerance, ron_min, ron_max, off_min, rail_max, Iexcess):
    """Fully ON branch bounds; no switching, hot pulse or SOA qualification.

    The resistor upper bound Vmax^2/Rmin deliberately ignores positive Ron.
    Imax^2*Ronmax is conservative fully ON conduction power with independent
    endpoint bounds; it is not switching or linear-region FET dissipation.
    """
    p = _inputs(dict(Rnom=Rnom, tolerance=tolerance, ron_min=ron_min,
                     ron_max=ron_max, off_min=off_min, rail_max=rail_max, Iexcess=Iexcess),
                positive=("Rnom", "off_min", "rail_max", "Iexcess"),
                nonnegative=("ron_min", "ron_max"))
    _ordered(p, "ron_min", "ron_max")
    _ordered(p, "off_min", "rail_max")
    _tolerance(p)
    out = _result(p, ("sink_current_min_A", "branch_current_max_A", "sink_current_margin_A",
                      "strict_positive_sink_current_margin", "resistor_instantaneous_upper_W",
                      "fet_on_state_conduction_upper_W"))
    out.update(switching_loss_included=False, linear_soa_qualified=False,
               thermal_qualified=False)
    if out["missing_fields"]:
        return out
    with localcontext() as ctx:
        ctx.prec = 50
        d = {key: _d(value) for key, value in p.items()}
        rmin = d["Rnom"] * (1 - d["tolerance"])
        rmax = d["Rnom"] * (1 + d["tolerance"])
        worst_r = rmax + d["ron_max"]
        sink_min = d["off_min"] / worst_r
        branch_max = d["rail_max"] / (rmin + d["ron_min"])
        # Compare the exact decimal numerator before non-terminating division.
        margin_numerator = d["off_min"] - d["Iexcess"] * worst_r
        margin = margin_numerator / worst_r
        resistor_power = d["rail_max"] ** 2 / rmin
        fet_power = branch_max ** 2 * d["ron_max"]
        out.update(sink_current_min_A=_float(sink_min), branch_current_max_A=_float(branch_max),
                   sink_current_margin_A=_float(margin),
                   strict_positive_sink_current_margin=margin_numerator > 0,
                   resistor_instantaneous_upper_W=_float(resistor_power),
                   fet_on_state_conduction_upper_W=_float(fet_power))
    return out


def collect():
    """Actual values remain unavailable; fixed values are allocations only."""
    actual = {
        "window": window(*([None] * 8)),
        "resistance_window": resistance_window(*([None] * 7)),
        "branch_bound": branch_bound(*([None] * 7)),
    }
    return {
        "revision": "VSERVO-03",
        "classification": "necessary_shunt_arithmetic_with_unavailable_actual_envelopes",
        "actual": actual,
        "parameters": {
            "classification": "illustrative_allocations_not_actual_limits",
            "normal_max_V": 5.0, "off_min_V": 5.1, "off_max_V": 5.15,
            "on_min_V": 5.25, "on_max_V": 5.3, "noise_pp_V": 0.04,
            "remaining_rise_V": 0.1, "allowed_max_V": 5.5,
            "excess_current_max_A": 0.5, "rail_max_V": 5.5,
            "path_current_allocation_A": 1.0, "ron_min_ohm": 0.0,
            "ron_max_ohm": 0.1, "tolerance": 0.05, "Rnom_ohm": 8.2,
        },
        "window_cases": [
            {"id": "allocated_fit", "label": "Positive allocated margins; physically unqualified",
             "result": window(5, 5.1, 5.15, 5.25, 5.3, 0.04, 0.1, 5.5)},
            {"id": "allocated_exhausted", "label": "Allocated protection margin exhausted",
             "result": window(5, 5.1, 5.15, 5.25, 5.3, 0.04, 0.2, 5.5)},
            {"id": "unknown", "label": "Actual envelope unavailable", "result": actual["window"]},
        ],
        "resistance_cases": [
            {"id": "half_amp", "label": "0.5 A excess-current allocation",
             "result": resistance_window(5.1, 0.5, 5.5, 1, 0, 0.1, 0.05)},
            {"id": "one_amp", "label": "1 A excess allocation exceeds the interval",
             "result": resistance_window(5.1, 1, 5.5, 1, 0, 0.1, 0.05)},
        ],
        "branch_case": branch_bound(8.2, 0.05, 0, 0.1, 5.1, 5.5, 0.5),
        "limitations": [
            "Actual source, receiver and branch values are unavailable; no component has been selected.",
            "All positive windows are necessary arithmetic only. Equality is not positive margin or hardware acceptance.",
            "Threshold allocations include tolerance, drift and sense error. normal_max includes the worst sensed normal source, ripple and signed sense disturbance; noise_pp protects the rising/falling gap.",
            "Remaining rise includes loaded clamp response, delay, ESR and local inductance; remote harness voltage and reverse voltage are separate. The turn-OFF-delay lower-rail excursion needs its own bound; a release threshold alone does not protect the receiver minimum.",
            "Excess current is the positive simultaneous net current from all contributing paths after credited loads, not an assumed servo-only current.",
            "Branch bounds assume a fully ON switch at declared Ron bounds over operating conditions. Gate-drive startup, transitions, SOA and fault behavior are not modeled.",
            "Instantaneous resistor and fully ON FET powers are conservative independent endpoint bounds, not pulse or continuous thermal ratings.",
            "A nominal resistance interval does not choose a resistor, FET, comparator, controller or approved circuit.",
            "Repeated energy requires a real sink and restoration; this packet gives no recurring capacitor-storage credit.",
            "No firmware, native schematic, copper, waveform, physical device or powered-application acceptance is established.",
        ],
        "necessary_arithmetic_only": True,
        "hardware_accepted": False,
        "device_release_approved": False,
        "parts_selected": False,
        "native_commands_rerun": False,
        "protection_qualified": False,
        "fabrication_approved": False,
        "candidate_electrical_delta": 0,
        "live_electrical_delta": 0,
        "live_copper_delta": 0,
    }
