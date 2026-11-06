"""SENSE-03 conditional static divider/reference arithmetic.

Pure functions return JSON-safe records; collect() does not read or write files.
The converter calculation is a reference/resistor corner cross-check, not a
guaranteed VDDA envelope. None means unavailable, never an assumed safe value.
"""
from __future__ import annotations

import math


def _inputs(values, positive=(), nonnegative=(), tolerances=()):
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
        if name in tolerances and not 0 <= number < 1:
            raise ValueError(f'{name} must be in [0, 1)')
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
        'conditional_static_only': True,
        'hardware_accepted': False,
    }


def _set(result, **values):
    if any(not math.isfinite(value) for value in values.values()):
        raise ValueError('Derived arithmetic exceeded the finite model domain')
    result.update(values)
    return result


def feedback_bounds(vfb_min_v, vfb_max_v, rtop_ohm, rbottom_ohm,
                    rtop_tol=0.01, rbottom_tol=0.01):
    """Independent corners of VOUT = VFB * (1 + Rtop/Rbottom).

Only supplied VFB limits and resistor tolerances enter this calculation.
Conditions under which VFB limits apply must be carried separately by callers.
"""
    p = _inputs(dict(vfb_min_v=vfb_min_v, vfb_max_v=vfb_max_v,
                     rtop_ohm=rtop_ohm, rbottom_ohm=rbottom_ohm,
                     rtop_tol=rtop_tol, rbottom_tol=rbottom_tol),
                positive=('vfb_min_v', 'vfb_max_v', 'rtop_ohm', 'rbottom_ohm'),
                tolerances=('rtop_tol', 'rbottom_tol'))
    if p['vfb_min_v'] is not None and p['vfb_max_v'] is not None and p['vfb_min_v'] > p['vfb_max_v']:
        raise ValueError('vfb_min_v cannot exceed vfb_max_v')
    result = _result(p, ('gain_min', 'gain_max', 'output_min_v', 'output_max_v'))
    if not result['available']:
        return result
    top_min = p['rtop_ohm'] * (1 - p['rtop_tol'])
    top_max = p['rtop_ohm'] * (1 + p['rtop_tol'])
    bottom_min = p['rbottom_ohm'] * (1 - p['rbottom_tol'])
    bottom_max = p['rbottom_ohm'] * (1 + p['rbottom_tol'])
    if any(not math.isfinite(value) or value <= 0
           for value in (top_min, top_max, bottom_min, bottom_max)):
        raise ValueError('Derived arithmetic exceeded the finite model domain')
    low = 1 + top_min / bottom_max
    high = 1 + top_max / bottom_min
    return _set(result, gain_min=low, gain_max=high,
                output_min_v=p['vfb_min_v'] * low,
                output_max_v=p['vfb_max_v'] * high)


def divider_bounds(rtop_ohm, rbottom_ohm, rtop_tol=0.01, rbottom_tol=0.01):
    """Independent corners of unloaded divider ratio Rbottom/(Rtop+Rbottom)."""
    p = _inputs(dict(rtop_ohm=rtop_ohm, rbottom_ohm=rbottom_ohm,
                     rtop_tol=rtop_tol, rbottom_tol=rbottom_tol),
                positive=('rtop_ohm', 'rbottom_ohm'), tolerances=('rtop_tol', 'rbottom_tol'))
    result = _result(p, ('ratio_min', 'ratio_nominal', 'ratio_max'))
    if not result['available']:
        return result
    top_min = p['rtop_ohm'] * (1 - p['rtop_tol'])
    top_max = p['rtop_ohm'] * (1 + p['rtop_tol'])
    bottom_min = p['rbottom_ohm'] * (1 - p['rbottom_tol'])
    bottom_max = p['rbottom_ohm'] * (1 + p['rbottom_tol'])
    # Explicit intermediate checks prevent overflow from silently becoming ratio zero.
    intermediates = (top_min, top_max, bottom_min, bottom_max,
                     top_max + bottom_min, top_min + bottom_max,
                     p['rtop_ohm'] + p['rbottom_ohm'])
    if any(not math.isfinite(value) or value <= 0 for value in intermediates):
        raise ValueError('Derived arithmetic exceeded the finite model domain')
    low = bottom_min / (top_max + bottom_min)
    nominal = p['rbottom_ohm'] / (p['rtop_ohm'] + p['rbottom_ohm'])
    high = bottom_max / (top_min + bottom_max)
    if not 0 < low <= nominal <= high < 1:
        raise ValueError('Derived ratio exceeded the finite model domain')
    return _set(result, ratio_min=low, ratio_nominal=nominal, ratio_max=high)


def headroom(vin, reference_floor, ratio_max, reserve_v):
    """Conditional active-ADC range margin; equality is not positive margin.

The supplied reference floor and reserve must be explicit. A zero reference is
allowed as an arithmetic power-state illustration. This function does not
model the PA2 FT absolute maximum, injection, or power-off protection.
"""
    p = _inputs(dict(vin=vin, reference_floor=reference_floor, ratio_max=ratio_max,
                     reserve_v=reserve_v),
                positive=('ratio_max',), nonnegative=('vin', 'reference_floor', 'reserve_v'))
    if p['ratio_max'] is not None and p['ratio_max'] >= 1:
        raise ValueError('ratio_max must be less than one for this two-resistor divider')
    result = _result(p, ('adc_max_v', 'usable_reference_v', 'headroom_v',
                         'vin_ceiling_v', 'strict_positive_arithmetic_margin'))
    if not result['available']:
        return result
    adc_max = p['vin'] * p['ratio_max']
    usable = p['reference_floor'] - p['reserve_v']
    _set(result, adc_max_v=adc_max, usable_reference_v=usable,
         headroom_v=usable - adc_max, vin_ceiling_v=usable / p['ratio_max'])
    result['strict_positive_arithmetic_margin'] = result['headroom_v'] > 0
    return result


def threshold_rtop(vin, rbottom, tols, floor, reserve):
    """Inverse static bound: Rtop_nominal > returned threshold, with Rtop > 0.

tols is (top fractional tolerance, bottom fractional tolerance), or None.
The threshold is not an available/selected resistor, ADC acquisition result,
or hardware permission. If floor <= reserve, no finite positive Rtop yields
strictly positive active-ADC arithmetic margin for the nonnegative VIN domain.
That statement is not a power-off protection theorem.
"""
    if tols is None:
        tols = (None, None)
    if not isinstance(tols, (tuple, list)) or len(tols) != 2:
        raise ValueError('tols must contain (top tolerance, bottom tolerance), or None')
    p = _inputs(dict(vin=vin, rbottom=rbottom, rtop_tol=tols[0], rbottom_tol=tols[1],
                     floor=floor, reserve=reserve),
                positive=('rbottom',), nonnegative=('vin', 'floor', 'reserve'),
                tolerances=('rtop_tol', 'rbottom_tol'))
    result = _result(p, ('usable_reference_v', 'rtop_threshold_ohm',
                         'finite_positive_rtop_can_meet_arithmetic_margin'))
    result.update(comparator='>', rtop_must_also_be_positive=True,
                  resistor_selected=False)
    if not result['available']:
        return result
    usable = p['floor'] - p['reserve']
    _set(result, usable_reference_v=usable)
    if usable <= 0:
        result.update(status='no_feasible_positive_arithmetic_margin',
                      finite_positive_rtop_can_meet_arithmetic_margin=False)
        return result
    threshold = p['rbottom'] * (1 + p['rbottom_tol']) / (1 - p['rtop_tol']) * (p['vin'] / usable - 1)
    _set(result, rtop_threshold_ohm=threshold)
    result['finite_positive_rtop_can_meet_arithmetic_margin'] = True
    return result


def collect():
    """Deterministic conditional cross-checks; unknown actual envelopes stay None."""
    feedback = feedback_bounds(0.985, 1.015, 100000, 43200, 0.01, 0.01)
    feedback.update(
        reference='U2 VFB', rtop_ref='R4', rbottom_ref='R5',
        vfb_nominal_v=1.0, output_nominal_v=1.0 * (1 + 100000 / 43200),
        reference_limit_conditions={'vin_v': 24.0, 'temperature_min_c': -40.0,
                                    'temperature_max_c': 125.0},
        guaranteed_vdda_envelope=False,
        excluded_terms=['Other line/load regulation and dynamic terms',
                        'Resistor temperature drift and aging',
                        'Output ripple, startup, shutdown and fault behavior',
                        'VDDA path drop and VREF+ behavior'],
    )
    divider = divider_bounds(47000, 6800, 0.01, 0.01)
    divider.update(rtop_ref='R31', rbottom_ref='R32',
                   voltage_boundary='VIN_RAW; not battery-terminal voltage',
                   resistor_temperature_and_adc_errors_included=False)
    floor = feedback['output_min_v']
    cases = []
    for vin in (24.0, 25.2, 26.0, 44.0):
        case = headroom(vin, floor, divider['ratio_max'], 0.0)
        case.update(
            description=('Existing unqualified protected-rail target; not an actual bound'
                         if vin == 44.0 else 'Illustrative static VIN_RAW case'),
            reference_is_conditional_converter_corner=True,
            vin_is_qualified_bound=False,
            reserve_allocation_v=0.0,
            threshold=threshold_rtop(vin, 6800, (0.01, 0.01), floor, 0.0),
        )
        cases.append(case)
    reserve_case = headroom(25.2, floor, divider['ratio_max'], 0.05)
    reserve_case.update(
        description='Explicitly allocated 50 mV reserve; not a verified error budget',
        reserve_allocation_v=0.05, allocation_is_verified=False,
        threshold=threshold_rtop(25.2, 6800, (0.01, 0.01), floor, 0.05),
    )
    return {
        'schema': 1, 'revision': 'SENSE-03', 'status': 'conditional_static_analysis_only',
        'candidate_electrical_delta': 0, 'live_electrical_delta': 0, 'live_copper_delta': 0,
        'native_commands_rerun': False, 'hardware_accepted': False,
        'fabrication_approved': False, 'procurement_approved': False,
        'protection_qualified': False, 'qualification_ports_implemented': False,
        'full_6s_accepted': False, 'divider_selected': False, 'pcb_integrated': False,
        'feedback_reference_cross_check': feedback,
        'divider': divider, 'static_cases': cases, 'allocated_reserve_case': reserve_case,
        'unknown_actual_inputs': {
            'vin_raw_source_max_v': None, 'vin_raw_transient_max_v': None,
            'vdda_min_v': None, 'vref_plus_min_v': None,
            'power_sequence_envelope': None, 'required_reserve_v': None,
        },
        'actual': {
            'headroom': headroom(None, None, divider['ratio_max'], None),
            'threshold': threshold_rtop(None, 6800, (0.01, 0.01), None, None),
        },
        'limitations': [
            'The U2 reference/resistor corners are conditional static arithmetic, not guaranteed VDDA limits.',
            'The VFB limits are stated at VIN 24 V and -40 to 125 C; extension to a full 6S envelope is unqualified.',
            'Other converter, distribution, reference, source, resistor drift and ADC error terms are absent.',
            'A negative conditional margin identifies an overlap; a positive conditional margin is not acceptance.',
            '44 V is an existing unqualified protected-rail target, not a measured or guaranteed VIN_RAW bound.',
            'The 50 mV reserve is an explicit allocation only; the actual required reserve remains unknown.',
            'Active ADC input range 0 to VREF+ differs from the PA2 FT absolute-voltage rule involving VDD+4 V.',
            'No power-off protection, injection, sequencing, or passive-divider impossibility theorem is established.',
            'Strict Rtop thresholds do not select a resistor or establish source impedance, acquisition, or protection.',
        ],
    }
