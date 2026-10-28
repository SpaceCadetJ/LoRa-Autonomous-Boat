"""ACT-12 connector topology and inherited timing checks; no hardware approval."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

MEASUREMENT_FIELDS = (
    "receiver_identity", "receiver_supply_range", "signal_voltage_limits",
    "input_thresholds", "input_feed_and_capacitance", "pulse_acceptance",
    "signal_loss_response", "readiness_observation", "stop_deadline",
    "harness_definition",
)
_UNRESOLVED = frozenset({"unresolved", "unknown", "pending", "tbd", "unavailable",
                         "not measured", "not selected", "not specified"})
EXPECTED_VALUES = {
    "U4": "TXU0102", "C14": "100nF", "R10": "100R", "R12": "100R",
    "R11": "10k", "R13": "10k", "D10": "PESD5V0S1BA", "D11": "PESD5V0S1BA",
    "J2": "ESC", "J3": "SERVO",
}
EXPECTED_SIGNAL_NETS = {
    "/Actuators/ESC_SIG_5V": {"U4.8", "R10.1"},
    "/Actuators/ESC_SIG": {"R10.2", "R11.1", "D10.1", "J2.1"},
    "/Actuators/SERVO_SIG_5V": {"U4.1", "R12.1"},
    "/Actuators/SERVO_SIG": {"R12.2", "R13.1", "D11.1", "J3.1"},
}
EXPECTED_PIN_NETS = {
    "U1.37": "/PWM_ESC_PC6", "U1.41": "/PWM_SERVO_PA8",
    "U4.1": "/Actuators/SERVO_SIG_5V", "U4.2": "GND", "U4.3": "+3V3",
    "U4.4": "/PWM_SERVO_PA8", "U4.5": "/PWM_ESC_PC6",
    "U4.6": "/Actuators/ACT_OE", "U4.7": "/Power/+5V_BUCK",
    "U4.8": "/Actuators/ESC_SIG_5V", "C14.1": "/Power/+5V_BUCK", "C14.2": "GND",
    "R10.1": "/Actuators/ESC_SIG_5V", "R10.2": "/Actuators/ESC_SIG",
    "R11.1": "/Actuators/ESC_SIG", "R11.2": "GND",
    "R12.1": "/Actuators/SERVO_SIG_5V", "R12.2": "/Actuators/SERVO_SIG",
    "R13.1": "/Actuators/SERVO_SIG", "R13.2": "GND",
    "D10.1": "/Actuators/ESC_SIG", "D10.2": "GND",
    "D11.1": "/Actuators/SERVO_SIG", "D11.2": "GND",
    "J2.1": "/Actuators/ESC_SIG", "J2.2": "/BEC_IN", "J2.3": "GND",
    "J3.1": "/Actuators/SERVO_SIG", "J3.2": "VSERVO", "J3.3": "GND",
}
SOURCE_PATHS = (
    "reviews/codex/actuator_latch/native/netlist.xml",
    "reviews/codex/observation_3v3/contract.json",
    "reviews/codex/observation_3v3/analysis.json",
    "reviews/codex/observer_retention/contract.json",
    "reviews/codex/observer_retention/analysis.json",
)


def _unresolved(value):
    """Completeness only: a populated record still requires substantive review."""
    if value is None or isinstance(value, bool):
        return True
    if isinstance(value, (int, float)) and not math.isfinite(value):
        return True
    if isinstance(value, str):
        return not value.strip() or value.strip().casefold() in _UNRESOLVED
    if isinstance(value, dict):
        return not value or any(_unresolved(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return not value or any(_unresolved(v) for v in value)
    return False


def missing_evidence(profile):
    """Return every required absent/unresolved field; never grants acceptance."""
    if not isinstance(profile, dict):
        raise TypeError("An evidence record must be a dictionary")
    return [name for name in MEASUREMENT_FIELDS if _unresolved(profile.get(name))]


def timing_case(headroom_V, response_ns, slew_V_per_us):
    """Conditional monotone-ramp allocation, after the inherited overdrive point."""
    for name, value in (("headroom_V", headroom_V), ("response_ns", response_ns),
                        ("slew_V_per_us", slew_V_per_us)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{name} must be a finite number")
    if headroom_V <= 0 or response_ns <= 0 or slew_V_per_us < 0:
        raise ValueError("Positive headroom and response, nonnegative slew required")
    duration_us = response_ns / 1000
    ceiling = headroom_V / duration_us
    excursion = slew_V_per_us * duration_us
    residual = headroom_V - excursion
    return {
        "slew_V_per_us": slew_V_per_us,
        "additional_excursion_V": excursion,
        "residual_V": residual,
        # Compare to the ceiling too: roundoff must not turn exact equality into a pass.
        "conditional_margin_positive": bool(residual > 0 and slew_V_per_us < ceiling),
        "hardware_accepted": False,
        "waveform_qualified": False,
    }


def verify_topology(xml_root):
    """Check captured ACT-04 node memberships and values, not physical behavior."""
    components = xml_root.findall("./components/comp")
    values = {c.attrib["ref"]: c.findtext("value") for c in components}
    if len(values) != len(components):
        raise ValueError("Duplicate component reference")
    for ref, value in EXPECTED_VALUES.items():
        if values.get(ref) != value:
            raise ValueError(f"Component value drift: {ref}")
    pins, nets = {}, {}
    for net in xml_root.findall("./nets/net"):
        name = net.attrib["name"]
        if name in nets:
            raise ValueError(f"Duplicate net name: {name}")
        members = set()
        for node in net.findall("node"):
            pin = node.attrib["ref"] + "." + node.attrib["pin"]
            if pin in pins:
                raise ValueError(f"Duplicate pin membership: {pin}")
            pins[pin] = name
            members.add(pin)
        nets[name] = members
    for pin, name in EXPECTED_PIN_NETS.items():
        if pins.get(pin) != name:
            raise ValueError(f"Pin net drift: {pin}")
    for name, expected in EXPECTED_SIGNAL_NETS.items():
        if nets.get(name) != expected:
            raise ValueError(f"Signal net membership drift: {name}")
    for ref in EXPECTED_VALUES:
        actual = {p for p in pins if p.split(".")[0] == ref}
        expected = {p for p in EXPECTED_PIN_NETS if p.split(".")[0] == ref}
        if actual != expected:
            raise ValueError(f"Unexpected pin on scoped component: {ref}")
    return {
        "classification": "independently_checked_captured_native_topology",
        "native_revision": "ACT-04",
        "channels": [
            {"role": "ESC", "port": "J2", "driver_pin": "U4.8",
             "series_component": "R10", "series_value": values["R10"],
             "signal_pin": "J2.1", "signal_net": "/Actuators/ESC_SIG",
             "pulldown_component": "R11", "pulldown_value": values["R11"],
             "protection_component": "D10", "protection_value": values["D10"],
             "supply_pin": "J2.2", "supply_net": pins["J2.2"], "ground_pin": "J2.3"},
            {"role": "servo", "port": "J3", "driver_pin": "U4.1",
             "series_component": "R12", "series_value": values["R12"],
             "signal_pin": "J3.1", "signal_net": "/Actuators/SERVO_SIG",
             "pulldown_component": "R13", "pulldown_value": values["R13"],
             "protection_component": "D11", "protection_value": values["D11"],
             "supply_pin": "J3.2", "supply_net": pins["J3.2"], "ground_pin": "J3.3"},
        ],
        "driver_VCCB": {"pin": "U4.7", "net": pins["U4.7"],
                         "bypass": "C14", "bypass_value": values["C14"]},
        "signal_net_memberships": {n: sorted(m) for n, m in EXPECTED_SIGNAL_NETS.items()},
        "checked_pin_nets": dict(EXPECTED_PIN_NETS),
        "checked_values": {ref: values[ref] for ref in EXPECTED_VALUES},
        "receiver_input_low_proven": False,
        "pulse_rejection_proven": False,
        "actuator_stop_time_known": False,
    }


def _require_equal(actual, expected, label):
    if actual != expected:
        raise ValueError(f"Inherited allocation drift: {label}")


def collect(root: Path) -> dict:
    root = Path(root)
    c7, a7, c9, a9 = [json.loads((root / path).read_text(encoding="utf-8"))
                      for path in SOURCE_PATHS[1:]]
    _require_equal(c7["revision"], "ACT-07", "ACT-07 revision")
    _require_equal(c9["revision"], "ACT-09", "ACT-09 revision")
    budgets = {"sense_settling_budget_ns": 100, "detector_budget_ns": 55,
               "downstream_budget_ns": 245}
    for name, value in budgets.items():
        _require_equal(c7["proposal"][name], value, name)
        _require_equal(a7["budget_components_ns"][name], value, name)
    total = sum(budgets.values())
    for actual in (a7["total_budget_ns"], c9["proposal"]["total_response_ns"],
                   a9["same_rail"]["response_ns"]):
        _require_equal(actual, total, "total response")
    uv_start, uv_end = 3.0719380026289804, 3.005
    ov_start, ov_end = 3.56404020970936, 3.6
    for actual in (a7["overdrive_screen"]["rail_amplitude_V"]["UV"],
                   c9["proposal"]["same_rail_overdrive_V"], a9["same_rail"]["overdrive_V"]):
        _require_equal(actual, uv_start, "UV overdrive")
    for actual in (c9["proposal"]["same_rail_valid_floor_V"], a9["same_rail"]["valid_floor_V"]):
        _require_equal(actual, uv_end, "UV reference boundary")
    _require_equal(a7["overdrive_screen"]["rail_amplitude_V"]["OV"], ov_start, "OV overdrive")
    for actual in (c7["proposal"]["corridor_V"][1], a7["corridor_V"][1]):
        _require_equal(actual, ov_end, "OV corridor boundary")
    slews = [0.01, 0.1, 1.0]
    _require_equal(c7["proposal"]["slew_cases_V_per_us"], slews, "ACT-07 slew cases")
    _require_equal(c9["proposal"]["slew_V_per_us"], slews, "ACT-09 slew cases")
    timing = {"budget_components_ns": budgets, "total_budget_ns": total,
              "allocation_is_measured_delay": False, "allocation_is_system_stop_deadline": False,
              "waveform_qualified": False}
    for label, start, boundary, headroom in (
            ("UV", uv_start, uv_end, uv_start - uv_end),
            ("OV", ov_start, ov_end, ov_end - ov_start)):
        timing[label] = {
            "overdrive_V": start, "valid_boundary_V": boundary, "headroom_V": headroom,
            "maximum_slew_V_per_us": headroom / (total / 1000),
            "strictly_below_maximum_slew_required": True,
            "cases": [timing_case(headroom, total, slew) for slew in slews],
        }
    return {
        "schema": 1, "revision": "ACT-12",
        "classification": "connector_fault_requirements_not_implementation",
        "candidate_electrical_delta": 0, "live_electrical_delta": 0, "live_copper_delta": 0,
        "hardware_accepted": False, "native_accepted": False, "native_commands_rerun": False,
        "timing_qualified": False, "receiver_contract_closed": False,
        "topology": verify_topology(ET.parse(root / SOURCE_PATHS[0]).getroot()),
        "timing": timing,
        "evidence_gate": {"required_fields": list(MEASUREMENT_FIELDS),
                          "missing_fields": missing_evidence({}), "record_complete": False,
                          "hardware_accepted": False,
                          "meaning": "Record completeness only; populated entries still require review and physical verification."},
        "limitations": [
            "The 400 ns allocation is inherited, conditional and unqualified; it is not an actuator stop deadline.",
            "Only continuous monotone ramps after sufficient differential overdrive are screened; steps, noise, bouncing rails and pulses remain unqualified.",
            "The ACT-09 UV boundary is 3.005 V; the ACT-07 OV boundary remains 3.6 V. Neither is an observed hardware failure threshold.",
            "HiZ, pulldown and TVS topology do not establish receiver input-low voltage, pulse rejection or actuator stop response.",
            "Receiver identity, thresholds, feed/capacitance, pulse policy, missing-signal response, readiness, stop deadline and harness evidence remain required.",
            "Missing qualifications default disabled. Local VSERVO does not establish remote receiver readiness.",
            "Timing arithmetic and record completeness cannot approve hardware, fabrication or use.",
        ],
        "source_sha256": {path: hashlib.sha256((root / path).read_bytes()).hexdigest()
                          for path in (*SOURCE_PATHS, "reviews/codex/connector_fault_contract/model.py")},
    }
