#!/usr/bin/env python3
"""Check the isolated E-01 netlist delta; never edit or approve live hardware.

Run from any directory with Python 3.10+; defaults resolve relative to this file.
Only actual XML/ERC inputs produce validation.json. Synthetic tests do not.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / "reviews/codex/imu_interface"
BASELINE = ROOT / "reviews/codex/design_completion/native-review/v2"
V18 = "/Navigation/+1V8_IMU"
INT18 = "/Navigation/IMU_INT_1V8"
SCL18 = "/Navigation/IMU_SCL_1V8"
SDA18 = "/Navigation/IMU_SDA_1V8"
BIAS = "/Navigation/PCA9306_BIAS"
U10_FOOTPRINT = "LoRa_Boat_Controller_V2:TI_DCT0008A_PCA9306_3x3mm_P0.65mm"
EXPECTED_DELTA = {
    ("U6", "8"): ("+3V3", V18),
    ("U6", "22"): ("+3V3", V18),
    ("U6", "12"): ("/IMU_INT", INT18),
    ("U6", "23"): ("/I2C1_SCL", SCL18),
    ("U6", "24"): ("/I2C1_SDA", SDA18),
}
NEW_PARTS = {
    "U9": ("TLV75518PDBVR", {"1": "+3V3", "2": "GND", "3": "+3V3", "4": "unconnected-(U9-NC-Pad4)", "5": V18}),
    "U10": ("PCA9306DCTR", {"1": "GND", "2": V18, "3": SCL18, "4": SDA18, "5": "/I2C1_SDA", "6": "/I2C1_SCL", "7": BIAS, "8": BIAS}),
    "U11": ("SN74AXC1T45DBVR", {"1": V18, "2": "GND", "3": INT18, "4": "/IMU_INT", "5": V18, "6": "+3V3"}),
    "R36": ("4.7k", {"1": V18, "2": SCL18}),
    "R37": ("4.7k", {"1": V18, "2": SDA18}),
    "R38": ("200k", {"1": "+3V3", "2": BIAS}),
    "R39": ("100k", {"1": V18, "2": "GND"}),
    "C38": ("2.2uF", {"1": "+3V3", "2": "GND"}),
    "C39": ("2.2uF", {"1": V18, "2": "GND"}),
    "C40": ("100nF", {"1": V18, "2": "GND"}),
    "C41": ("100nF", {"1": V18, "2": "GND"}),
    "C42": ("100nF", {"1": "+3V3", "2": "GND"}),
}


class ValidationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def parse_netlist(tree):
    """Check each physical pin appears exactly once, even for explicit NCs."""
    root = tree.getroot() if isinstance(tree, ET.ElementTree) else tree
    libraries = {}
    for part in root.findall("./libparts/libpart"):
        key = (part.get("lib"), part.get("part"))
        require(key not in libraries, f"Duplicate library definition: {key}")
        pins = {}
        for pin in part.findall("./pins/pin"):
            num = pin.get("num")
            require(num and num not in pins, f"Missing or duplicate library pin: {key}.{num}")
            pins[num] = (pin.get("name"), pin.get("type"))
        require(pins, f"No physical pins for library part: {key}")
        libraries[key] = pins
    components = {}
    expected_pins = set()
    for comp in root.findall("./components/comp"):
        ref = comp.get("ref")
        require(ref and ref not in components, f"Missing or duplicate component: {ref}")
        src = comp.find("libsource")
        require(src is not None, f"Missing libsource: {ref}")
        identity = (src.get("lib"), src.get("part"))
        require(identity in libraries, f"Unresolved library part: {ref}: {identity}")
        properties = {p.get("name"): p.get("value") for p in comp.findall("property")}
        fields = {p.get("name"): p.text or "" for p in comp.findall("./fields/field")}
        components[ref] = {
            "value": comp.findtext("value", ""),
            "footprint": comp.findtext("footprint", ""),
            "mpn": properties.get("MPN", fields.get("MPN", "")),
            "manufacturer": properties.get("Manufacturer", fields.get("Manufacturer", "")),
            "library": identity,
            "pins": libraries[identity],
        }
        expected_pins.update((ref, pin) for pin in libraries[identity])
    membership = {}
    net_names = set()
    for net in root.findall("./nets/net"):
        name = net.get("name")
        require(name and name not in net_names, f"Missing or duplicate net name: {name}")
        net_names.add(name)
        nodes = net.findall("node")
        require(nodes, f"Empty net: {name}")
        for node in nodes:
            key = (node.get("ref"), node.get("pin"))
            require(key in expected_pins, f"Unknown physical pin: {key}")
            require(key not in membership, f"Duplicate physical pin membership: {key}")
            membership[key] = name
    missing = expected_pins - membership.keys()
    require(not missing, f"Missing physical pin memberships: {sorted(missing)}")
    require(components, "Empty component list")
    return components, membership


def validate_netlists(baseline_tree, candidate_tree):
    before, old_pins = parse_netlist(baseline_tree)
    after, new_pins = parse_netlist(candidate_tree)
    require(not (before.keys() & NEW_PARTS.keys()), "Added reference already exists in baseline")
    require(set(after) == set(before) | set(NEW_PARTS),
            f"Unexpected component set: missing={sorted(set(before) - set(after))}, "
            f"added={sorted(set(after) - set(before))}")
    for ref, old in before.items():
        require(after[ref] == old, f"Existing component identity or physical pin definition changed: {ref}")
    actual_delta = {}
    for key, net in old_pins.items():
        if new_pins[key] != net:
            actual_delta[key] = (net, new_pins[key])
    require(actual_delta == EXPECTED_DELTA,
            f"Existing electrical delta differs from exactly five intended U6 pins: {actual_delta}")
    for ref, (value, pins) in NEW_PARTS.items():
        actual = after[ref]
        require(actual["value"] == value, f"Wrong added value: {ref}")
        require(actual["footprint"], f"Missing added footprint: {ref}")
        require(set(actual["pins"]) == set(pins), f"Wrong added physical pins: {ref}")
        if ref.startswith("U"):
            require(actual["mpn"] == value, f"Wrong added IC MPN: {ref}")
        for pin, net in pins.items():
            require(new_pins[(ref, pin)] == net, f"Wrong new pin net: {ref}.{pin}: {new_pins[(ref, pin)]} != {net}")
    require(after["U10"]["footprint"] == U10_FOOTPRINT, "PCA9306 must use reviewed project-local DCT footprint")
    return {
        "baseline_components": len(before),
        "candidate_components": len(after),
        "added_components": sorted(NEW_PARTS),
        "baseline_physical_pins": len(old_pins),
        "candidate_physical_pins": len(new_pins),
        "added_physical_pins": len(new_pins) - len(old_pins),
        "preserved_existing_pin_memberships": len(old_pins) - len(EXPECTED_DELTA),
        "existing_pin_deltas": [
            {"reference": ref, "pin": pin, "before": old, "after": new}
            for (ref, pin), (old, new) in sorted(actual_delta.items())
        ],
        "existing_component_values_footprints_mpns_libraries_and_pin_definitions_preserved": True,
        "physical_pin_completeness_and_uniqueness": "pass",
    }


def erc_summary(data):
    require(isinstance(data.get("sheets"), list) and data["sheets"], "ERC JSON has no sheets")
    violations = []
    for sheet in data["sheets"]:
        require(isinstance(sheet.get("violations"), list), "Malformed native ERC sheet")
        for item in sheet["violations"]:
            require(item.get("severity") in {"error", "warning", "exclusion"}, "Unknown native ERC severity")
            violations.append({
                "sheet": sheet["path"], "severity": item["severity"],
                "type": item.get("type"), "description": item.get("description"),
                "items": sorted(i.get("description", "") for i in item.get("items", [])),
            })
    counts = Counter(v["severity"] for v in violations)
    return {"kicad_version": data.get("kicad_version"), "date": data.get("date"),
            "errors": counts["error"], "warnings": counts["warning"], "exclusions": counts["exclusion"],
            "violations": sorted(violations, key=lambda v: json.dumps(v, sort_keys=True))}


def path_label(path):
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def input_record(path):
    return {"path": path_label(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=BASELINE / "netlist.xml")
    parser.add_argument("--candidate", type=Path, default=PACKET / "native/netlist.xml")
    parser.add_argument("--baseline-erc", type=Path, default=BASELINE / "erc.json")
    parser.add_argument("--erc", type=Path, default=PACKET / "native/erc.json")
    parser.add_argument("--output", type=Path, default=PACKET / "validation.json")
    args = parser.parse_args(argv)
    paths = {"baseline_netlist": args.baseline, "candidate_netlist": args.candidate,
             "baseline_erc": args.baseline_erc, "candidate_erc": args.erc}
    # Do not create or update evidence when native inputs are absent.
    for path in paths.values():
        if not path.is_file():
            parser.error(f"Native input missing; no validation record written: {path}")
    records = {key: input_record(path) for key, path in paths.items()}
    report = {"schema_version": 1, "generated_utc": datetime.now(timezone.utc).isoformat(),
              "status": "fail", "inputs": records,
              "scope": "isolated schematic/netlist candidate only",
              "pcb_updated": False, "live_circuit_updated": False, "fabrication_approved": False,
              "hardware_tested": False,
              "limitations": ["Native ERC does not validate voltage limits, timing, effective capacitance, package land patterns or physical behavior.",
                              "Candidate PCB routing, procurement qualification and operational firmware are not implemented by this check."]}
    try:
        report["electrical_delta"] = validate_netlists(ET.parse(args.baseline), ET.parse(args.candidate))
        old_erc = erc_summary(json.loads(args.baseline_erc.read_text(encoding="utf-8")))
        new_erc = erc_summary(json.loads(args.erc.read_text(encoding="utf-8")))
        report["native_erc"] = {"baseline": old_erc, "candidate": new_erc}
        require(new_erc["errors"] == 0, "Candidate has native ERC errors")
        require(new_erc["violations"] == old_erc["violations"], "Native ERC findings differ from captured baseline; review required")
        require(records == {key: input_record(path) for key, path in paths.items()}, "Native input changed during verification")
        report["status"] = "pass_candidate_only"
    except (ValidationError, ET.ParseError, ValueError) as exc:
        report["error"] = str(exc)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": path_label(args.output), "error": report.get("error")}, indent=2))
    return 0 if report["status"] == "pass_candidate_only" else 1


if __name__ == "__main__":
    sys.exit(main())
