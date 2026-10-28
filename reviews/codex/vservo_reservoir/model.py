"""VSERVO-01 idealized reservoir arithmetic; no load or hardware qualification.

Current is the net capacitor discharge deficit after source contribution. Energy
is the net energy retained by the capacitor after other dissipation/return paths.
Constant ESR is an independent allocation, not the candidate's AC impedance.
These functions omit source dynamics, inductance, ripple, temperature, aging in
operation, thermal behavior and transient overshoot. SI inputs and outputs.
"""
from __future__ import annotations

import math

SOURCE_CONDITIONS = (
    "The candidate's nominal 100 uF has initial +/-20% capacitance tolerance "
    "at 120 Hz and 20 C. The separate endurance criterion allows +/-30% "
    "change from the initial value after the specified test and restoration "
    "to 20 C. Stacking those limits gives 56 uF only for that post-test "
    "condition; it is not an all-temperature, in-operation lifetime or "
    "effective-capacitance lower bound."
)


def _number(name, value, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite real number")
    value = float(value)
    if not math.isfinite(value) or value < 0 or (positive and value == 0):
        kind = "positive" if positive else "nonnegative"
        raise ValueError(f"{name} must be finite and {kind}")
    return value


def _finite(*values):
    if any(not math.isfinite(value) for value in values):
        raise ValueError("derived arithmetic exceeded the finite model domain")


def load_step(C_F, I_A, t_s, R_ohm, Vstart):
    """Constant net discharge and ESR; nonpositive endpoints are invalid.

    A nonpositive algebraic endpoint marks depletion/model invalidity. It is
    retained only as an equation diagnostic, never returned as voltage_V.
    """
    C = _number("C_F", C_F, positive=True)
    I = _number("I_A", I_A)
    t = _number("t_s", t_s)
    R = _number("R_ohm", R_ohm)
    start = _number("Vstart", Vstart, positive=True)
    charge = I * t
    esr_drop = I * R
    capacitive_drop = charge / C
    endpoint = start - esr_drop - capacitive_drop
    _finite(charge, esr_drop, capacitive_drop, endpoint)
    valid = endpoint > 0
    return {
        "charge_removed_C": charge,
        "esr_drop_V": esr_drop,
        "capacitive_drop_V": capacitive_drop,
        "algebraic_endpoint_V": endpoint,
        "voltage_V": endpoint if valid else None,
        "model_valid": valid,
        "status": "idealized_endpoint" if valid else "depleted_model_invalid",
    }


def returned_energy(C_F, E_J, Vstart):
    """Ideal final capacitor voltage after net retained energy; no peak model."""
    C = _number("C_F", C_F, positive=True)
    energy = _number("E_J", E_J)
    start = _number("Vstart", Vstart, positive=True)
    squared = start * start + 2 * energy / C
    _finite(squared)
    return {
        "net_retained_energy_J": energy,
        "voltage_V": math.sqrt(squared),
        "model_valid": True,
        "status": "idealized_energy_endpoint_not_peak_voltage",
    }


def required_C_step(I, t, R, Vstart, Vfloor):
    """Equality capacitance threshold; strictly greater C gives positive margin.

    When ESR consumes the voltage window, no finite C provides positive margin.
    A zero threshold means any positive C, under these allocations only.
    """
    current = _number("I", I)
    duration = _number("t", t)
    resistance = _number("R", R)
    start = _number("Vstart", Vstart, positive=True)
    floor = _number("Vfloor", Vfloor, positive=True)
    charge = current * duration
    esr_drop = current * resistance
    headroom = start - floor - esr_drop
    _finite(charge, esr_drop, headroom)
    required = charge / headroom if headroom > 0 else None
    if required is not None:
        _finite(required)
    return {
        "headroom_V": headroom,
        "required_capacitance_F": required,
        "finite_solution_for_positive_margin": headroom > 0,
        "comparison": "C > required_capacitance_F; C must also be positive",
        "status": "equality_threshold" if headroom > 0 else "no_finite_C_for_positive_margin",
    }


def required_C_energy(E, Vstart, Vceiling):
    """Equality capacitance threshold for retained energy, not transient peaks."""
    energy = _number("E", E)
    start = _number("Vstart", Vstart, positive=True)
    ceiling = _number("Vceiling", Vceiling, positive=True)
    window = ceiling * ceiling - start * start
    _finite(window)
    required = 2 * energy / window if window > 0 else None
    if required is not None:
        _finite(required)
    return {
        "headroom_V": ceiling - start,
        "voltage_squared_window_V2": window,
        "required_capacitance_F": required,
        "finite_solution_for_positive_margin": window > 0,
        "comparison": "C > required_capacitance_F; C must also be positive",
        "status": "equality_threshold" if window > 0 else "no_finite_C_for_positive_margin",
    }


def collect():
    """Fixed, explicitly allocated cases for the review viewer and report."""
    nominal = 100e-6
    initial_min = nominal * (1 - 0.20)
    post_endurance_min = initial_min * (1 - 0.30)
    p = {
        "classification": "illustrative_allocations_not_measured_load_or_limits",
        "initial_voltage_V": 5.0,
        "allocated_floor_V": 4.5,
        "allocated_ceiling_V": 5.5,
        "current_deficit_A": 0.5,
        "duration_s": 100e-6,
        "allocated_constant_esr_ohm": 0.2,
        "net_retained_energies_J": [0.1e-3, 0.25e-3, 1e-3],
        "C12_credited_capacitance_F": 0.0,
        "C12_credit_condition": "No credit until DC-bias and temperature behavior are established.",
        "voltage_envelope_note": "4.5/5.5 V are allocations, not receiver limits or capacitor ratings.",
        "esr_note": "0.2 ohm is a free allocation, not inferred from 360 mOhm AC impedance.",
        "source_conditions": SOURCE_CONDITIONS,
        "nominal_capacitance_F": nominal,
        "initial_tolerance_fraction": 0.20,
        "post_endurance_change_fraction_of_initial": 0.30,
    }
    cases = []
    labels = [
        (post_endurance_min, "stacked_post_endurance_20C_only", "56 uF: stacked initial and post-endurance limits at the specified restored condition"),
        (initial_min, "initial_120Hz_20C_minimum_only", "80 uF: initial tolerance minimum at 120 Hz and 20 C"),
        (nominal, "nominal_reference_only", "100 uF: nominal reference, not a guaranteed effective value"),
    ]
    for C, condition, label in labels:
        step = load_step(C, p["current_deficit_A"], p["duration_s"], p["allocated_constant_esr_ohm"], p["initial_voltage_V"])
        headroom = step["voltage_V"] - p["allocated_floor_V"] if step["model_valid"] else None
        step.update({"headroom_V": headroom, "strict_positive_allocated_headroom": headroom is not None and headroom > 0})
        energy_budget = 0.5 * C * (p["allocated_ceiling_V"] ** 2 - p["initial_voltage_V"] ** 2)
        energy_cases = []
        for energy in p["net_retained_energies_J"]:
            result = returned_energy(C, energy, p["initial_voltage_V"])
            result.update({
                "allocated_energy_budget_J": energy_budget,
                "headroom_J": energy_budget - energy,
                "headroom_V": p["allocated_ceiling_V"] - result["voltage_V"],
                "strict_positive_allocated_headroom": energy < energy_budget,
            })
            energy_cases.append(result)
        cases.append({"capacitance_F": C, "condition": condition, "label": label, "load_step": step, "energy_cases": energy_cases})
    return {
        "revision": "VSERVO-01",
        "classification": "source_conditioned_idealized_arithmetic",
        "parameters": p,
        "cases": cases,
        "required_C_step": required_C_step(p["current_deficit_A"], p["duration_s"], p["allocated_constant_esr_ohm"], p["initial_voltage_V"], p["allocated_floor_V"]),
        "required_C_energy": [dict(net_retained_energy_J=E, **required_C_energy(E, p["initial_voltage_V"], p["allocated_ceiling_V"])) for E in p["net_retained_energies_J"]],
        "limitations": [
            "Current is the capacitor deficit after source contribution; no actual actuator load is known.",
            "Returned energy is NET retained after other paths; no regenerative event has been measured.",
            "The returned-energy calculation omits ESR and inductive voltage peaks. Neither calculation includes source response, converter stability or thermal behavior.",
            "Constant ESR and capacitance are allocations; small-signal AC data do not establish pulse behavior.",
            "Equality at the floor or ceiling has zero margin and does not pass strict positive headroom.",
            "A nonpositive algebraic load-step endpoint means model invalid/depleted, not predicted negative voltage.",
            "Positive arithmetic margin establishes neither a component selection nor hardware acceptance.",
        ],
        "hardware_accepted": False,
        "component_selected_for_release": False,
        "voltage_envelope_qualified": False,
        "actual_load_known": False,
        "effective_capacitance_bound_qualified": False,
        "reservoir_qualified": False,
    }
