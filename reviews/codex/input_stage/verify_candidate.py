#!/usr/bin/env python3
"""Verify the isolated input-stage identity and exact native netlist delta.

collect() and validate_netlists() are read-only; only the CLI without --check
writes validation.json. No result establishes PCB or hardware acceptance.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
PACKET = Path(__file__).resolve().parent
BASELINE = ROOT / "reviews/codex/design_completion/native-review/v2"
PARSER_PATH = ROOT / "reviews/codex/imu_interface/verify_candidate.py"
spec = importlib.util.spec_from_file_location("input_stage_base_parser", PARSER_PATH)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
parse_netlist = base.parse_netlist
ValidationError = base.ValidationError
require = base.require

PROJECT = "LoRa_Boat_Controller_V2:"
OLD_IN = "/Power/VBAT_IN"
OLD_FUSED = "/Power/VBAT_FUSED"
NEW_IN = "/PowerInput/VBAT_IN"
NEW_FUSED = "/PowerInput/VBAT_FUSED"
BOUNDARY = {"J1", "F1", "Q1", "D1", "D2", "R1", "C1", "C2"}
REMOVED = {"Q1", "D2", "R1"}
EXPECTED_DELTA = {
    ("J1", "1"): (OLD_IN, NEW_IN),
    ("F1", "1"): (OLD_IN, NEW_IN),
    ("F1", "2"): (OLD_FUSED, NEW_FUSED),
    ("D1", "1"): ("VIN_RAW", NEW_FUSED),
}
REMOVED_PINS = {
    ("Q1", "1"): "/Power/PGATE", ("Q1", "2"): "VIN_RAW", ("Q1", "3"): OLD_FUSED,
    ("R1", "1"): "/Power/PGATE", ("R1", "2"): "GND",
    ("D2", "1"): "VIN_RAW", ("D2", "2"): "/Power/PGATE",
}
NEW_PINS = {("D12", "1"): "VIN_RAW", ("D12", "2"): NEW_FUSED}

def part(value, mpn, manufacturer, symbol, footprint, names=("", "")):
    return {"value": value, "mpn": mpn, "manufacturer": manufacturer,
            "library": ("Device", symbol), "footprint": PROJECT + footprint,
            "pins": {str(i): (name, "passive") for i, name in enumerate(names, 1)}}

PARTS = {
    "F1": part("2A 125V", "0451002.MRL", "Littelfuse", "Fuse", "Fuse_Littelfuse-NANO2-451_453"),
    "C1": part("47uF 63V", "EEEFK1J470P", "Panasonic", "C_Polarized", "CP_Elec_8x10.5"),
    "C2": part("1uF 100V", "GRM32ER72A105KA01L", "Murata", "C", "C_1210_3225Metric"),
    "D1": part("SMBJ26CA", "SMBJ26CA", "Littelfuse", "D_TVS", "D_SMB", ("A1", "A2")),
    "D12": part("STPS3H100U", "STPS3H100U", "STMicroelectronics", "D_Schottky", "D_SMB", ("K", "A")),
}

def validate_netlists(baseline_tree, candidate_tree):
    before, old = parse_netlist(baseline_tree)
    after, new = parse_netlist(candidate_tree)
    require(len(before) == 114 and len(old) == 361, "Unexpected baseline component/pin count")
    require(BOUNDARY <= set(before) and "D12" not in before, "Unexpected baseline input boundary")
    require(set(after) == (set(before) - REMOVED) | {"D12"}, "Unexpected component set")
    for ref, original in before.items():
        if ref not in REMOVED | set(PARTS):
            require(after[ref] == original, f"Unrelated component identity/pin definition changed: {ref}")
    for ref, expected in PARTS.items():
        require(after[ref] == expected, f"Candidate identity/pin definition differs from contract: {ref}: {after[ref]}")
    removed = {key: old[key] for key in old.keys() - new.keys()}
    added = {key: new[key] for key in new.keys() - old.keys()}
    delta = {key: (old[key], new[key]) for key in old.keys() & new.keys() if old[key] != new[key]}
    require(removed == REMOVED_PINS, f"Unexpected removed pin memberships: {removed}")
    require(added == NEW_PINS, f"Wrong new diode pin memberships: {added}")
    require(delta == EXPECTED_DELTA, f"Unexpected retained-pin delta: {delta}")
    require(set(new.values()) == (set(old.values()) - {OLD_IN, OLD_FUSED, "/Power/PGATE"}) | {NEW_IN, NEW_FUSED},
            "Unexpected added or removed net names")
    outside = {k: v for k, v in old.items() if k[0] not in BOUNDARY}
    require(len(outside) == 344 and all(new.get(k) == v for k, v in outside.items()),
            "Outside-boundary memberships changed")
    return {
        "baseline_components": len(before), "candidate_components": len(after),
        "baseline_physical_pins": len(old), "candidate_physical_pins": len(new),
        "removed_components": sorted(REMOVED), "added_components": ["D12"],
        "updated_component_identities": sorted(set(PARTS) - {"D12"}),
        "removed_physical_pins": len(removed), "added_physical_pins": len(added),
        "preserved_existing_pin_memberships": len(old.keys() & new.keys()) - len(delta),
        "preserved_outside_boundary_pin_memberships": len(outside),
        "existing_pin_deltas": [{"reference": r, "pin": p, "before": a, "after": b}
                                for (r, p), (a, b) in sorted(delta.items())],
        "added_memberships": {f"{r}.{p}": n for (r, p), n in sorted(added.items())},
        "removed_memberships": {f"{r}.{p}": n for (r, p), n in sorted(removed.items())},
        "candidate_part_identity_contract": "pass",
        "unchanged_components_and_pin_definitions_preserved": True,
        "physical_pin_completeness_and_uniqueness": "pass",
    }

def path_label(path):
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())

def record(path):
    return {"path": path_label(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

def collect(baseline_dir=BASELINE, candidate_dir=PACKET / "native"):
    """Return deterministic evidence from existing native files without writing."""
    paths = {"baseline_netlist": Path(baseline_dir) / "netlist.xml",
             "baseline_erc": Path(baseline_dir) / "erc.json",
             "candidate_netlist": Path(candidate_dir) / "netlist.xml",
             "candidate_erc": Path(candidate_dir) / "erc.json",
             "parser": PARSER_PATH, "verifier": Path(__file__).resolve()}
    for path in paths.values():
        require(path.is_file(), f"Native input missing: {path}")
    captured = {key: record(path) for key, path in paths.items()}
    delta = validate_netlists(ET.parse(paths["baseline_netlist"]), ET.parse(paths["candidate_netlist"]))
    old_erc = base.erc_summary(json.loads(paths["baseline_erc"].read_text(encoding="utf-8-sig")))
    new_erc = base.erc_summary(json.loads(paths["candidate_erc"].read_text(encoding="utf-8-sig")))
    require(new_erc["errors"] == 0, "Candidate has native ERC errors")
    require(new_erc["violations"] == old_erc["violations"], "Native ERC findings changed; independent review required")
    require(captured == {key: record(path) for key, path in paths.items()}, "Input changed during verification")
    return {"schema_version": 1, "status": "pass_isolated_schematic_only", "inputs": captured,
            "electrical_delta": delta, "native_erc": {"baseline": old_erc, "candidate": new_erc},
            "scope": "isolated native schematic identity/connectivity comparison",
            "pcb_updated": False, "live_circuit_updated": False, "hardware_tested": False,
            "fabrication_approved": False,
            "limitations": ["ERC and netlist agreement do not qualify voltage, current, thermal, transient or inrush behavior.",
                            "Project-local generic footprints are not manufacturer land-pattern or assembly acceptance.",
                            "Existing downstream power and IMU defects remain outside this input-stage correction."]}

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-dir", type=Path, default=BASELINE)
    parser.add_argument("--candidate-dir", type=Path, default=PACKET / "native")
    parser.add_argument("--output", type=Path, default=PACKET / "validation.json")
    parser.add_argument("--check", action="store_true", help="Compare captured evidence without writing")
    args = parser.parse_args(argv)
    try:
        result = collect(args.baseline_dir, args.candidate_dir)
        if args.check:
            require(json.loads(args.output.read_text(encoding="utf-8-sig")) == result, "Captured validation is stale")
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({"status": result["status"], "mode": "check" if args.check else "capture",
                          "output": path_label(args.output), "delta": result["electrical_delta"]}, indent=2))
        return 0
    except (OSError, ValueError, ET.ParseError) as error:
        print(json.dumps({"status": "fail", "error": str(error)}))
        return 1

if __name__ == "__main__":
    sys.exit(main())
