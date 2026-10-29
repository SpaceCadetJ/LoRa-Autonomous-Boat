"""VSERVO-02 symbolic transient boundaries; no component or hardware acceptance.

All arguments are required. None means unavailable evidence, never a default.
The illustrations are allocations, not actual actuator/source specifications.
"""
from __future__ import annotations

from decimal import Decimal
import math


def _inputs(values, positive=(), nonnegative=()):
    result = {}
    for name, value in values.items():
        if value is None:
            result[name] = None
            continue
        if isinstance(value, bool) or not isinstance(value, (float, int)):
            raise ValueError(f"{name} must be a finite real number or None")
        value = float(value)
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
        if name in positive and value <= 0:
            raise ValueError(f"{name} must be positive")
        if name in nonnegative and value < 0:
            raise ValueError(f"{name} must be nonnegative")
        result[name] = value
    return result


def _result(inputs, fields):
    missing = [name for name, value in inputs.items() if value is None]
    return {
        "status": "unavailable" if missing else "calculated",
        "missing_fields": missing,
        "inputs": inputs,
        **{field: None for field in fields},
        "hardware_accepted": False,
    }


def _finite(*values):
    if any(not math.isfinite(value) for value in values):
        raise ValueError("derived arithmetic exceeded the finite model domain")


def _difference(value, *subtractions):
    # Decimal input spellings keep a written boundary such as 5.5-5.3-0.2
    # exactly zero, rather than promoting a binary round-off residue to margin.
    result = Decimal(str(value))
    for term in subtractions:
        result -= Decimal(str(term))
    value = float(result)
    _finite(value)
    return value


def clamp_window(normal_max_V, turnon_min_V, turnon_max_V, overshoot_V, allowed_max_V):
    """Necessary scalar window only; both margins must be strictly positive.

    overshoot_V is the combined remaining rise above turnon_max_V: it must
    include threshold-to-full-current clamp regulation/I-V, response delay,
    ESR/inductance and local path effects. A turn-on/breakdown threshold alone
    is not the full-current clamp voltage. Remote harness behavior is separate.
    """
    p = _inputs(dict(normal_max_V=normal_max_V, turnon_min_V=turnon_min_V,
                     turnon_max_V=turnon_max_V, overshoot_V=overshoot_V,
                     allowed_max_V=allowed_max_V),
                positive=("normal_max_V", "turnon_min_V", "turnon_max_V", "allowed_max_V"),
                nonnegative=("overshoot_V",))
    if p["turnon_min_V"] is not None and p["turnon_max_V"] is not None and p["turnon_min_V"] > p["turnon_max_V"]:
        raise ValueError("turnon_min_V cannot exceed turnon_max_V")
    out = _result(p, ("off_margin_V", "protection_margin_V", "strict_positive_arithmetic_margin"))
    out.update(
        overshoot_definition="Combined rise above turnon_max_V including full-current clamp I-V/regulation, delay, ESR/inductance and local path effects; not delay alone.",
        full_current_response_qualified=False,
        remote_harness_qualified=False,
        window_is_necessary_not_sufficient=True,
    )
    if out["missing_fields"]:
        return out
    off = _difference(p["turnon_min_V"], p["normal_max_V"])
    protection = _difference(p["allowed_max_V"], p["turnon_max_V"], p["overshoot_V"])
    out.update(off_margin_V=off, protection_margin_V=protection,
               strict_positive_arithmetic_margin=off > 0 and protection > 0)
    return out


def delay_rise(C_F, return_current_A, delay_s):
    """Ideal capacitive rise before response under constant net return current.

    This omits ESR/inductive peaks and assumes the stated net current continues
    during the entire delay. It is not a clamp response-time qualification.
    """
    p = _inputs(dict(C_F=C_F, return_current_A=return_current_A, delay_s=delay_s),
                positive=("C_F",), nonnegative=("return_current_A", "delay_s"))
    out = _result(p, ("returned_charge_C", "rise_V"))
    if out["missing_fields"]:
        return out
    charge = p["return_current_A"] * p["delay_s"]
    rise = charge / p["C_F"]
    _finite(charge, rise)
    out.update(returned_charge_C=charge, rise_V=rise)
    return out


def sink_budget(C_F, start_V, ceiling_V, net_event_energy_J, events_per_s):
    """Event storage versus residual sink energy, including repeated reset.

    net_event_energy_J is an allocated positive residual burst after other
    paths, with no later offset/recovery absorption credited inside the burst.
    Endpoint-based minimum sink energy is only a lower bound; actual peak
    closure needs the maximum cumulative energy excursion and time waveform.
    Never automatically add harness inductive energy already counted at a port.
    For repeated events restored to the same starting rail, the full residual
    burst energy must leave through the sole local sink with no other later
    absorption credit. No thermal, pulse-power or peak qualification occurs.
    """
    p = _inputs(dict(C_F=C_F, start_V=start_V, ceiling_V=ceiling_V,
                     net_event_energy_J=net_event_energy_J, events_per_s=events_per_s),
                positive=("C_F", "start_V", "ceiling_V"),
                nonnegative=("net_event_energy_J", "events_per_s"))
    if p["start_V"] is not None and p["ceiling_V"] is not None and p["ceiling_V"] < p["start_V"]:
        raise ValueError("ceiling_V cannot be below start_V")
    out = _result(p, ("capacitor_energy_window_J", "minimum_event_sink_J",
                      "repeated_events_same_start_require_local_sink_J", "mean_local_sink_W"))
    out.update(
        event_energy_definition="Allocated positive residual burst energy after other paths; no later offset or recovery absorption is credited within the burst.",
        minimum_event_sink_is_lower_bound=True,
        endpoint_model_bounds_peak=False,
        peak_requires_max_cumulative_energy_excursion=True,
        repeated_average_scope="Conditional on restoration to the same starting rail by the sole residual local sink, with no other later absorption credit.",
        credits_later_absorption=False,
        automatically_adds_harness_inductive_energy=False,
    )
    if out["missing_fields"]:
        return out
    window = 0.5 * p["C_F"] * (p["ceiling_V"] * p["ceiling_V"] - p["start_V"] * p["start_V"])
    minimum = max(0.0, p["net_event_energy_J"] - window)
    mean = p["net_event_energy_J"] * p["events_per_s"]
    _finite(window, minimum, mean)
    out.update(capacitor_energy_window_J=window,
               minimum_event_sink_J=minimum,
               repeated_events_same_start_require_local_sink_J=p["net_event_energy_J"],
               mean_local_sink_W=mean)
    return out


def negative_boundary(cap_terminal_min_V, receiver_terminal_min_V, receiver_allowed_min_V):
    """Separate terminal constraints; zero margin is a boundary, not acceptance."""
    p = _inputs(dict(cap_terminal_min_V=cap_terminal_min_V,
                     receiver_terminal_min_V=receiver_terminal_min_V,
                     receiver_allowed_min_V=receiver_allowed_min_V))
    out = _result(p, ("capacitor_margin_V", "receiver_margin_V",
                      "capacitor_nonnegative_boundary_met", "receiver_boundary_met",
                      "strict_positive_arithmetic_margin"))
    if out["missing_fields"]:
        return out
    cap_margin = p["cap_terminal_min_V"]
    receiver_margin = _difference(p["receiver_terminal_min_V"], p["receiver_allowed_min_V"])
    out.update(capacitor_margin_V=cap_margin, receiver_margin_V=receiver_margin,
               capacitor_nonnegative_boundary_met=cap_margin >= 0,
               receiver_boundary_met=receiver_margin >= 0,
               strict_positive_arithmetic_margin=cap_margin > 0 and receiver_margin > 0)
    return out


def collect():
    """Unknown actual boundaries and separate allocation-only illustrations."""
    actual = {
        "clamp_window": clamp_window(None, None, None, None, None),
        "delay_rise": delay_rise(None, None, None),
        "sink_budget": sink_budget(None, None, None, None, None),
        "negative_boundary": negative_boundary(None, None, None),
    }
    return {
        "revision": "VSERVO-02",
        "classification": "analytical_boundaries_with_unavailable_actual_envelopes",
        "actual": actual,
        "parameters": {
            "classification": "illustrative_allocations_not_actual_limits",
            "start_V": 5.0, "normal_max_V": 5.1,
            "turnon_min_V": 5.2, "turnon_max_V": 5.3,
            "overshoot_V": 0.1, "allowed_max_V": 5.5,
            "C_F": 80e-6, "return_current_A": 0.5, "delay_s": 10e-6,
            "net_event_energies_J": [1e-3, 0.1e-3], "events_per_s": 10.0,
            "capacitance_condition": "80 uF is the earlier initial 120 Hz/20 C tolerance illustration, not an all-condition effective-capacitance bound.",
        },
        "window_cases": [
            {"id": "allocated_fit", "label": "Allocated positive window; physically unqualified", "result": clamp_window(5.1, 5.2, 5.3, 0.1, 5.5)},
            {"id": "allocated_exhausted", "label": "Allocated overshoot consumes the protection window", "result": clamp_window(5.1, 5.2, 5.3, 0.2, 5.5)},
            {"id": "unknown", "label": "Actual envelope unavailable", "result": actual["clamp_window"]},
        ],
        "delay_case": delay_rise(80e-6, 0.5, 10e-6),
        "sink_cases": [
            {"id": "one_mJ", "label": "1 mJ per event, 10 events/s; allocation only", "result": sink_budget(80e-6, 5, 5.5, 1e-3, 10)},
            {"id": "tenth_mJ", "label": "0.1 mJ per event, 10 events/s; allocation only", "result": sink_budget(80e-6, 5, 5.5, 0.1e-3, 10)},
        ],
        "negative_case": negative_boundary(0, 0, 0),
        "limitations": [
            "Actual source, receiver, clamp, current and energy envelopes are unavailable; no component is selected.",
            "The normal-voltage and protection margins must both be strictly positive; equality is not margin.",
            "The overshoot allocation includes all rise above turn-on maximum: full-current clamp I-V/regulation, delay, ESR/inductance and local path effects. It is not derived from the delay example alone.",
            "A necessary scalar window does not establish dynamic clamp behavior, tolerance, temperature, shutdown applicability or remote harness voltage.",
            "Delay rise assumes constant net capacitor return current; ESR and inductive peaks are omitted.",
            "Energy means an allocated positive residual burst after other paths, without later offset/recovery absorption inside the burst. Harness inductive energy already counted at the port is not added again.",
            "The event-sink result is an endpoint-based lower bound only. Actual peak closure needs maximum cumulative energy excursion and the time waveform.",
            "A capacitor's one-event storage window cannot be credited repeatedly while also assuming restoration to the same starting voltage.",
            "Full residual burst energy must leave through the sole local sink for each event restored to the same starting rail, with no other later absorption credit. Average watts alone do not qualify pulse power or thermals.",
            "C11 nonnegative terminal voltage and receiver minimum voltage are separate constraints. Zero is a boundary with no positive margin.",
            "No actual waveform, load, clamp, reverse-voltage, thermal or hardware acceptance is established.",
        ],
        "hardware_accepted": False,
        "component_selected_for_release": False,
        "voltage_envelope_qualified": False,
        "actual_load_known": False,
        "sink_qualified": False,
        "reverse_voltage_qualified": False,
        "fabrication_approved": False,
        "candidate_electrical_delta": 0,
        "live_electrical_delta": 0,
        "live_copper_delta": 0,
    }
