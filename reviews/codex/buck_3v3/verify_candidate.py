#!/usr/bin/env python3
"""Independently verify the predeclared BUCK33-A1 part/pin contract.

collect()/validate_netlists() and --check are read-only. The normal CLI writes
validation.json only after actual native inputs pass. No hardware approval.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
PACKET = Path(__file__).resolve().parent
BASELINE = ROOT / "reviews/codex/input_stage/native"
CONTRACT_PATH = PACKET / "expected_contract.json"
PARSER_PATH = ROOT / "reviews/codex/imu_interface/verify_candidate.py"
spec = importlib.util.spec_from_file_location("buck_3v3_base_parser", PARSER_PATH)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
require = base.require
ValidationError = base.ValidationError
parse_netlist = base.parse_netlist
BOUNDARY = set("U2 L1 C3 C4 C5 C6 R2 R3 R4 R5 D3".split())
REMOVED = set("R2 R3 C4 D3".split())
ADDED = set("C44 C45 C46 C47 C48".split())
CHILD_PATH = "/Power/Buck3V3/"


def load_contract(path=CONTRACT_PATH):
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    require(data.get("schema") == 1 and data.get("revision") == "BUCK33-A1", "Unexpected expected-contract schema/revision")
    require(data.get("baseline_native") == "reviews/codex/input_stage/native/netlist.xml", "Wrong baseline in contract")
    require(set(data.get("boundary", [])) == BOUNDARY, "Unexpected contract boundary")
    require(set(data.get("removed_parts", [])) == REMOVED, "Unexpected contract removed parts")
    require(set(data.get("added_parts", [])) == ADDED, "Unexpected contract added parts")
    require(set(data.get("candidate_parts", {})) == (BOUNDARY - REMOVED) | ADDED, "Incomplete contract part set")
    require(set(data.get("candidate_memberships", {})) == set(data["candidate_parts"]), "Incomplete contract membership set")
    require(data.get("expected_counts") == {
        "baseline_components": 112, "candidate_components": 113,
        "baseline_pins": 356, "candidate_pins": 361, "outside_boundary_pins": 330}, "Unexpected contract counts")
    require(data.get("live_electrical_delta") == 0 and data.get("pcb_updated") is False
            and data.get("qualified_for_power") is False, "Contract attempts to approve live hardware")
    for ref, part in data["candidate_parts"].items():
        require(set(part) == {"value", "mpn", "manufacturer", "library", "footprint", "pins"}, f"Incomplete part identity: {ref}")
        require(isinstance(part["library"], list) and len(part["library"]) == 2, f"Invalid library identity: {ref}")
        require(set(part["pins"]) == set(data["candidate_memberships"][ref]), f"Missing contract physical pin: {ref}")
        require(all(isinstance(v, list) and len(v) == 2 for v in part["pins"].values()), f"Invalid physical-pin identity: {ref}")
    return data


def normalized_part(part):
    result = copy.deepcopy(part)
    result["library"] = tuple(result["library"])
    result["pins"] = {pin: tuple(definition) for pin, definition in result["pins"].items()}
    return result


def sheets(tree):
    root = tree.getroot() if isinstance(tree, ET.ElementTree) else tree
    return {comp.get("ref"): comp.find("sheetpath").get("names")
            if comp.find("sheetpath") is not None else None
            for comp in root.findall("./components/comp")}


def validate_netlists(baseline_tree, candidate_tree, contract=None):
    """Compare all physical pins against baseline plus the pre-export contract."""
    contract = load_contract() if contract is None else contract
    before, old = parse_netlist(baseline_tree)
    after, new = parse_netlist(candidate_tree)
    require(len(before) == 112 and len(old) == 356, "Unexpected baseline component/pin count")
    require(BOUNDARY <= before.keys() and not (ADDED & before.keys()), "Unexpected baseline converter boundary")
    expected_refs = (before.keys() - REMOVED) | ADDED
    require(after.keys() == expected_refs, "Unexpected candidate component set")
    require(len(after) == 113 and len(new) == 361, "Unexpected candidate component/pin count")
    old_sheets, new_sheets = sheets(baseline_tree), sheets(candidate_tree)
    for ref, original in before.items():
        if ref not in BOUNDARY:
            require(after[ref] == original, f"Outside-boundary part identity or pin definition changed: {ref}")
            require(new_sheets[ref] == old_sheets[ref], f"Outside-boundary sheet changed: {ref}")
    for ref, expected in contract["candidate_parts"].items():
        require(after[ref] == normalized_part(expected), f"Contract part identity or physical pin definition differs: {ref}")
        require(new_sheets[ref] == CHILD_PATH, f"Converter component is not on expected child sheet: {ref}")
    outside = {key: net for key, net in old.items() if key[0] not in BOUNDARY}
    require(len(outside) == 330, "Unexpected outside-boundary physical pin count")
    require(all(new.get(key) == net for key, net in outside.items()), "Outside-boundary pin memberships changed")
    expected = dict(outside)
    for ref, pins in contract["candidate_memberships"].items():
        expected.update({(ref, pin): net for pin, net in pins.items()})
    require(new == expected, "Candidate pin memberships differ from pre-export contract")
    require(set(new.values()) == set(expected.values()), "Unexpected net-name set")
    root = candidate_tree.getroot() if isinstance(candidate_tree, ET.ElementTree) else candidate_tree
    pg_nodes = [node for node in root.findall("./nets/net/node") if node.get("ref") == "U2" and node.get("pin") == "4"]
    require(len(pg_nodes) == 1 and pg_nodes[0].get("pintype") == "open_collector+no_connect", "PG pin 4 needs an explicit no-connect marker")
    removed = {key: old[key] for key in old.keys() - new.keys()}
    added = {key: new[key] for key in new.keys() - old.keys()}
    delta = {key: (old[key], new[key]) for key in old.keys() & new.keys() if old[key] != new[key]}
    retained = old.keys() & new.keys()
    return {
        "baseline_components": len(before), "candidate_components": len(after),
        "baseline_physical_pins": len(old), "candidate_physical_pins": len(new),
        "removed_components": sorted(REMOVED), "added_components": sorted(ADDED),
        "updated_component_identities": sorted(BOUNDARY - REMOVED),
        "removed_physical_pins": len(removed), "added_physical_pins": len(added),
        "preserved_existing_pin_memberships": len(retained) - len(delta),
        "preserved_outside_boundary_pin_memberships": len(outside),
        "existing_pin_deltas": [{"reference": ref, "pin": pin, "before": a, "after": b}
                                for (ref, pin), (a, b) in sorted(delta.items())],
        "added_memberships": {f"{ref}.{pin}": net for (ref, pin), net in sorted(added.items())},
        "removed_memberships": {f"{ref}.{pin}": net for (ref, pin), net in sorted(removed.items())},
        "added_net_names": sorted(set(new.values()) - set(old.values())),
        "removed_net_names": sorted(set(old.values()) - set(new.values())),
        "candidate_part_identity_contract": "pass",
        "physical_pin_completeness_and_uniqueness": "pass",
        "pg_explicit_no_connect": True,
        "converter_child_sheet": CHILD_PATH,
    }


def validate_erc(baseline, candidate):
    old = base.erc_summary(baseline)
    new = base.erc_summary(candidate)
    require(old["errors"] == 0 and old["warnings"] == 1, "Unexpected baseline native ERC summary")
    require(new["errors"] == 0, "Candidate has native ERC errors")
    require(new["violations"] == old["violations"], "Native ERC findings changed; independent review required")
    return {"baseline": old, "candidate": new}


def path_label(path):
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def record(path):
    return {"path": path_label(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def collect(baseline_dir=BASELINE, candidate_dir=PACKET / "native"):
    paths = {"baseline_netlist": Path(baseline_dir) / "netlist.xml",
             "baseline_erc": Path(baseline_dir) / "erc.json",
             "candidate_netlist": Path(candidate_dir) / "netlist.xml",
             "candidate_erc": Path(candidate_dir) / "erc.json",
             "expected_contract": CONTRACT_PATH, "parser": PARSER_PATH,
             "verifier": Path(__file__).resolve()}
    for path in paths.values():
        require(path.is_file(), f"Native or contract input missing: {path}")
    captured = {key: record(path) for key, path in paths.items()}
    contract = load_contract()
    delta = validate_netlists(ET.parse(paths["baseline_netlist"]), ET.parse(paths["candidate_netlist"]), contract)
    erc = validate_erc(json.loads(paths["baseline_erc"].read_text(encoding="utf-8-sig")),
                       json.loads(paths["candidate_erc"].read_text(encoding="utf-8-sig")))
    require(captured == {key: record(path) for key, path in paths.items()}, "Input changed during verification")
    return {"schema_version": 1, "revision": contract["revision"], "status": "pass_isolated_schematic_only",
            "inputs": captured, "electrical_delta": delta, "native_erc": erc,
            "scope": "isolated native schematic identity/connectivity comparison to pre-export contract",
            "pcb_updated": False, "live_circuit_updated": False, "hardware_tested": False,
            "qualified_for_power": False, "fabrication_approved": False,
            "limitations": ["Rechecks captured native files; does not run KiCad or independently prove source-to-export freshness.",
                            "ERC and contract agreement do not qualify capacitance, inrush, thermal, transient, leakage, damping, stability or startup behavior.",
                            "PCB layout and footprint qualification are outside this comparison.",
                            "INPUT-A1 downstream defects and separate IMU2 work remain outside this converter amendment."]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-dir", type=Path, default=BASELINE)
    parser.add_argument("--candidate-dir", type=Path, default=PACKET / "native")
    parser.add_argument("--output", type=Path, default=PACKET / "validation.json")
    parser.add_argument("--check", action="store_true", help="Compare recorded evidence without writing")
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
