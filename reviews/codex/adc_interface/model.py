"""SENSE-04 proposed ADC-interface contract arithmetic; pure and JSON-safe.

These are necessary conditional calculations, not device selection, qualified
limits, implemented states, or hardware permission. Unknown inputs stay None.
"""
from __future__ import annotations

import math


REQUIRED_QUALIFICATIONS = (
    'source_bound', 'reference_bound', 'power_states', 'isolation',
    'discharge', 'transitions', 'acquisition',
)


def _inputs(values, positive=(), nonnegative=()):
    result = {}
    for name, value in values.items():
        if value is None:
            result[name] = None
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f'{name} must be a finite real number or None')
        try:
            number = float(value)
        except (OverflowError, ValueError) as error:
            raise ValueError(f'{name} must be finite') from error
        if not math.isfinite(number):
            raise ValueError(f'{name} must be finite')
        if name in positive and number <= 0:
            raise ValueError(f'{name} must be positive')
        if name in nonnegative and number < 0:
            raise ValueError(f'{name} must be nonnegative')
        result[name] = number
    return result


def _result(inputs, fields):
    missing = [key for key, value in inputs.items() if value is None]
    return {
        'status': 'unavailable' if missing else 'calculated',
        'available': not missing,
        'inputs': inputs,
        'missing_fields': missing,
        **{key: None for key in fields},
        'necessary_arithmetic_only': True,
        'hardware_accepted': False,
    }


def _set(result, **values):
    if any(not math.isfinite(value) for value in values.values()):
        raise ValueError('Derived arithmetic exceeded the finite model domain')
    result.update(values)
    return result


def shutdown_window(release_floor_v, signal_peak_v, reserve_v,
                    fall_slew_v_per_s, detect_delay_s, open_delay_s):
    """Linear falling-reference illustration: margin must remain strictly > 0.

This uses supplied bounds only. A zero fall slew gives an unbounded time
deadline only when initial headroom is positive; otherwise no positive window
exists. Neither case is represented with Infinity. Delays exclude any effects
not explicitly included by the caller, including a subsequent discharge phase.
"""
    p = _inputs(dict(release_floor_v=release_floor_v, signal_peak_v=signal_peak_v,
                     reserve_v=reserve_v, fall_slew_v_per_s=fall_slew_v_per_s,
                     detect_delay_s=detect_delay_s, open_delay_s=open_delay_s),
                nonnegative=('release_floor_v', 'signal_peak_v', 'reserve_v',
                             'fall_slew_v_per_s', 'detect_delay_s', 'open_delay_s'))
    result = _result(p, ('initial_headroom_v', 'total_delay_s', 'reference_after_delay_v',
                         'headroom_after_delay_v', 'strict_delay_limit_s',
                         'deadline_unbounded', 'positive_initial_window',
                         'strict_positive_arithmetic_margin'))
    if not result['available']:
        return result
    initial = p['release_floor_v'] - p['signal_peak_v'] - p['reserve_v']
    delay = p['detect_delay_s'] + p['open_delay_s']
    fall = p['fall_slew_v_per_s'] * delay
    reference = p['release_floor_v'] - fall
    _set(result, initial_headroom_v=initial, total_delay_s=delay,
         reference_after_delay_v=reference, headroom_after_delay_v=initial - fall)
    result['positive_initial_window'] = initial > 0
    result['strict_positive_arithmetic_margin'] = result['headroom_after_delay_v'] > 0
    result['deadline_unbounded'] = p['fall_slew_v_per_s'] == 0 and initial > 0
    if initial <= 0:
        result['strict_delay_limit_s'] = 0.0
    elif p['fall_slew_v_per_s'] > 0:
        _set(result, strict_delay_limit_s=initial / p['fall_slew_v_per_s'])
    return result


def discharge(initial_v, leakage_a, rdis_ohm, cap_max_f, target_v):
    """Isolated-node RC with worst constant nonnegative leakage into the node.

V(t) = I*R + (Vinitial-I*R)*exp(-t/(R*C)). The returned time is the
first time to <= target in this ideal model. Initial <= target returns zero,
including when subsequent leakage would raise it; the floor flags distinguish
that case. Immediate attainment does not imply sustained parking. The sustained
flag requires finite attainment and an equilibrium at/below target, solely in
this constant-leakage model. A target at/below the floor cannot be reached from
above in finite time. Actual switch leakage, tolerances, capacitance and target
remain external.
"""
    p = _inputs(dict(initial_v=initial_v, leakage_a=leakage_a, rdis_ohm=rdis_ohm,
                     cap_max_f=cap_max_f, target_v=target_v),
                positive=('rdis_ohm', 'cap_max_f'),
                nonnegative=('initial_v', 'leakage_a', 'target_v'))
    result = _result(p, ('leakage_floor_v', 'tau_s', 'initial_already_at_or_below_target',
                         'target_above_leakage_floor', 'leakage_floor_exceeds_target',
                         'equilibrium_at_or_below_target', 'sustained_target_possible_in_model',
                         'finite_time_to_target', 'time_to_target_s',
                         'voltage_at_target_time_v'))
    if not result['available']:
        return result
    floor = p['leakage_a'] * p['rdis_ohm']
    tau = p['rdis_ohm'] * p['cap_max_f']
    _set(result, leakage_floor_v=floor, tau_s=tau)
    if tau <= 0 or (p['leakage_a'] > 0 and floor <= 0):
        raise ValueError('Derived arithmetic exceeded the finite model domain')
    result['initial_already_at_or_below_target'] = p['initial_v'] <= p['target_v']
    result['target_above_leakage_floor'] = p['target_v'] > floor
    result['leakage_floor_exceeds_target'] = floor > p['target_v']
    result['equilibrium_at_or_below_target'] = floor <= p['target_v']
    if result['initial_already_at_or_below_target']:
        result['finite_time_to_target'] = True
        result['sustained_target_possible_in_model'] = result['equilibrium_at_or_below_target']
        return _set(result, time_to_target_s=0.0, voltage_at_target_time_v=p['initial_v'])
    if not result['target_above_leakage_floor']:
        result.update(status='no_finite_time_to_target', finite_time_to_target=False,
                      sustained_target_possible_in_model=False)
        return result
    interval = math.log1p((p['initial_v'] - p['target_v']) / (p['target_v'] - floor))
    time = tau * interval
    endpoint = floor + (p['initial_v'] - floor) * math.exp(-interval)
    _set(result, time_to_target_s=time, voltage_at_target_time_v=endpoint)
    if time <= 0:
        raise ValueError('Derived arithmetic exceeded the finite model domain')
    result['finite_time_to_target'] = True
    result['sustained_target_possible_in_model'] = True
    return result


def injection_step(charge_c, cap_min_f):
    """Magnitude |Q|/Cmin for a supplied injected charge; no clamp/settling model."""
    p = _inputs(dict(charge_c=charge_c, cap_min_f=cap_min_f), positive=('cap_min_f',))
    result = _result(p, ('glitch_magnitude_v',))
    result['conditional_glitch_only'] = True
    if not result['available']:
        return result
    return _set(result, glitch_magnitude_v=abs(p['charge_c']) / p['cap_min_f'])


def bleed_interval(rth_ohm, ron_max_ohm, loading_error_fraction, park_max_v, leak_max_a):
    """Necessary permanent pull-down interval for static loading versus leakage.

Rp >= (Rth+Ron)*(1-eps)/eps, and Rp <= Vpark/Ileak for Ileak > 0.
Equality is included in this static interval. Zero leakage leaves the upper
bound unbounded (None with an explicit flag), not Infinity. This omits dynamic
acquisition, tolerances unless supplied, noise, operating states and protection.
"""
    p = _inputs(dict(rth_ohm=rth_ohm, ron_max_ohm=ron_max_ohm,
                     loading_error_fraction=loading_error_fraction,
                     park_max_v=park_max_v, leak_max_a=leak_max_a),
                positive=('rth_ohm',), nonnegative=('ron_max_ohm', 'park_max_v', 'leak_max_a'))
    if p['loading_error_fraction'] is not None and not 0 < p['loading_error_fraction'] < 1:
        raise ValueError('loading_error_fraction must be in (0, 1)')
    result = _result(p, ('rp_min_ohm', 'rp_max_ohm', 'upper_bound_unbounded',
                         'necessary_interval_exists'))
    result.update(interval_inclusive=True, resistor_selected=False)
    if not result['available']:
        return result
    eps = p['loading_error_fraction']
    low = (p['rth_ohm'] + p['ron_max_ohm']) * (1 - eps) / eps
    _set(result, rp_min_ohm=low)
    if low <= 0:
        raise ValueError('Derived arithmetic exceeded the finite model domain')
    result['upper_bound_unbounded'] = p['leak_max_a'] == 0
    if result['upper_bound_unbounded']:
        result['necessary_interval_exists'] = True
    else:
        high = p['park_max_v'] / p['leak_max_a']
        _set(result, rp_max_ohm=high)
        result['necessary_interval_exists'] = low <= high
    return result


def permission(qualifications, request):
    """Default-disabled contract decision; never a command or implemented state."""
    if qualifications is None:
        qualifications = {}
    if not isinstance(qualifications, dict):
        raise ValueError('qualifications must be a dictionary or None')
    if set(qualifications) - set(REQUIRED_QUALIFICATIONS):
        raise ValueError('Unknown qualification key')
    if request is not None and type(request) is not bool:
        raise ValueError('request must be an exact boolean or None')
    normalized = {key: qualifications.get(key) for key in REQUIRED_QUALIFICATIONS}
    for key, value in normalized.items():
        if value is not None and type(value) is not bool:
            raise ValueError(f'{key} must be an exact boolean or None')
    unqualified = [key for key, value in normalized.items() if value is not True]
    return {
        'qualifications': normalized, 'request': request,
        'unqualified': unqualified, 'enabled': request is True and not unqualified,
        'permission_is_contract_model_only': True,
        'state_control_implemented': False, 'hardware_accepted': False,
    }


def collect():
    """Return explicit allocations and unavailable actual conditions; no IO."""
    signal = 3.241200044945504
    qualifications = {key: None for key in REQUIRED_QUALIFICATIONS}
    shutdown_examples = []
    for slew in (100.0, 10000.0):
        result = shutdown_window(3.35, signal, .05, slew, 150e-6, 50e-6)
        result.update(
            description='Allocated linear-fall illustration; not a qualified sequence',
            release_threshold_selected=False,
            release_floor_availability_on_low_rail_qualified=False,
            allocation_only=True,
        )
        shutdown_examples.append(result)
    discharge_examples = []
    for cap, leakage, description in [
            (100e-9, 1e-6, 'Retained C36 100 nF used as an illustrative capacitance, not a maximum bound'),
            (100e-9, 100e-6, 'Retained C36 illustration with a higher injected-leakage allocation'),
            (1e-9, 1e-6, 'Hypothetical separate downstream 1 nF; not a selected or implemented capacitor')]:
        result = discharge(signal, leakage, 6800, cap, .3)
        result.update(description=description, target_is_allocated_not_pa2_limit=True,
                      allocation_only=True, capacitance_is_qualified_maximum=False)
        discharge_examples.append(result)
    injection = injection_step(1e-12, 1e-9)
    injection.update(description='Allocated 1 pC into hypothetical downstream 1 nF',
                     allocation_only=True, capacitance_is_qualified_minimum=False)
    bleed_examples = []
    rth = 47000 * 6800 / (47000 + 6800)
    for leakage in (1e-6, 1e-9):
        result = bleed_interval(rth, 10, .001, .3, leakage)
        result.update(description='Allocated Ron, loading-error, park voltage and leakage example',
                      allocation_only=True, park_target_is_pa2_limit=False,
                      rth_is_nominal_only=True)
        bleed_examples.append(result)
    return {
        'schema': 1, 'revision': 'SENSE-04', 'status': 'proposed_contract_and_necessary_arithmetic_only',
        'candidate_electrical_delta': 0, 'live_electrical_delta': 0, 'live_copper_delta': 0,
        'native_commands_rerun': False, 'hardware_accepted': False,
        'fabrication_approved': False, 'procurement_approved': False,
        'protection_qualified': False, 'qualification_ports_implemented': False,
        'full_6s_accepted': False, 'interface_selected': False, 'pcb_integrated': False,
        'qualifications': qualifications, 'permission': permission(qualifications, None),
        'unknown_actual_inputs': {
            'release_floor_v': None, 'signal_peak_v': None, 'reserve_v': None,
            'fall_slew_v_per_s': None, 'detect_delay_s': None, 'open_delay_s': None,
            'initial_v': None, 'leakage_a': None, 'rdis_ohm': None,
            'cap_max_f': None, 'target_v': None, 'charge_c': None, 'cap_min_f': None,
            'rth_ohm': None, 'ron_max_ohm': None, 'loading_error_fraction': None,
            'park_max_v': None, 'leak_max_a': None,
        },
        'actual': {
            'shutdown': shutdown_window(None, None, None, None, None, None),
            'discharge': discharge(None, None, None, None, None),
            'injection': injection_step(None, None),
            'bleed': bleed_interval(None, None, None, None, None),
        },
        'shutdown_examples': shutdown_examples,
        'discharge_examples': discharge_examples,
        'injection_example': injection, 'bleed_examples': bleed_examples,
        'limitations': [
            'All examples are allocations; actual source, reference, sequence, leakage and dynamic limits remain unknown.',
            'The allocated 3.35 V release floor is not a selected threshold and may be unavailable on the low rail.',
            'Shutdown-window margin covers the two supplied delays only; subsequent node discharge and sequencing require separate proof.',
            'The allocated 0.3 V park target is not a PA2 absolute, injection, or active-ADC limit.',
            'Retained C36 remains 100 nF nominal; using it in an example does not establish its maximum capacitance.',
            'A separate downstream 1 nF capacitor and 1 pC charge are hypothetical; no component or bound is selected.',
            'Permanent pull-down feasibility is a necessary static interval, not acquisition, transition, or protection qualification.',
            'Active ADC range and PA2 FT stress/power-off behavior are separate constraints; no universal passive-divider impossibility is claimed.',
            'All seven qualifications must be explicit True before the modeled permission can enable; the model implements no hardware state control.',
        ],
    }
