#!/usr/bin/env python3
"""Check ACT-01 exact native delta and held, exclusive population contract.

collect()/validate_netlists(), validate_population() and --check are read-only.
Normal CLI writes evidence only after real native/source inputs pass.
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
BASELINE = ROOT / "reviews/codex/buck_5v/native"
CONTRACT_PATH = PACKET / "expected_contract.json"
POPULATION_PATH = PACKET / "population_contract.json"
PARSER_PATH = ROOT / "reviews/codex/imu_interface/verify_candidate.py"
spec = importlib.util.spec_from_file_location("actuator_supply_base_parser", PARSER_PATH)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
require = base.require
ValidationError = base.ValidationError
parse_netlist = base.parse_netlist
BOUNDARY = set("U4 U5 C13 C14 D4 D9".split())
IDENTITY_CHANGES = {"D4", "D9"}
EXPECTED_DELTA = {(ref, pin): ("VSERVO", "/Power/+5V_BUCK")
                  for ref, pin in [("C13", "1"), ("C14", "1"), ("U4", "5"), ("U5", "5")]}
PRESERVED_SHEETS = ["Buck3V3.kicad_sch", "Buck5V.kicad_sch"]


def load_contract(path=CONTRACT_PATH):
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    require(data.get("schema") == 1 and data.get("revision") == "ACT-01", "Unexpected expected-contract schema/revision")
    require(data.get("baseline_native") == "reviews/codex/buck_5v/native/netlist.xml", "Wrong contract baseline")
    require(set(data.get("boundary", [])) == BOUNDARY, "Unexpected contract boundary")
    require(data.get("removed_parts") == [] and data.get("added_parts") == [], "Contract must not add/remove parts")
    require(set(data.get("candidate_parts", {})) == BOUNDARY, "Incomplete contract part set")
    require(set(data.get("candidate_memberships", {})) == BOUNDARY, "Incomplete contract membership set")
    require(data.get("expected_counts") == {
        "baseline_components": 119, "candidate_components": 119,
        "baseline_pins": 398, "candidate_pins": 398, "outside_boundary_pins": 380}, "Unexpected contract counts")
    expected_rows = [{"reference": ref, "pin": pin, "before": old, "after": new}
                     for (ref, pin), (old, new) in sorted(EXPECTED_DELTA.items())]
    require(data.get("expected_pin_deltas") == expected_rows, "Contract differs from four authorized supply moves")
    require(set(data.get("expected_identity_changes", [])) == IDENTITY_CHANGES, "Unexpected identity-change contract")
    require(data.get("source_sheets_preserved") == PRESERVED_SHEETS, "Missing converter source preservation contract")
    require(data.get("live_electrical_delta") == 0 and data.get("pcb_updated") is False
            and data.get("qualified_for_power") is False, "Contract attempts to approve live hardware")
    for ref, part in data["candidate_parts"].items():
        require(set(part) == {"value", "mpn", "manufacturer", "library", "footprint", "pins"}, f"Incomplete part identity: {ref}")
        require(isinstance(part["library"], list) and len(part["library"]) == 2, f"Invalid library identity: {ref}")
        require(set(part["pins"]) == set(data["candidate_memberships"][ref]), f"Missing contract physical pin: {ref}")
        require(all(isinstance(v, list) and len(v) == 2 for v in part["pins"].values()), f"Invalid physical-pin identity: {ref}")
    for ref in IDENTITY_CHANGES:
        part = data["candidate_parts"][ref]
        require(part["mpn"] == "SS34-E3/57T" and part["manufacturer"] == "Vishay"
                and part["footprint"] == "LoRa_Boat_Controller_V2:D_SMC", f"Unexpected diode identity contract: {ref}")
    return data


def normalized_part(part):
    result = copy.deepcopy(part)
    result["library"] = tuple(result["library"])
    result["pins"] = {pin: tuple(definition) for pin, definition in result["pins"].items()}
    return result


def tree_root(tree):
    return tree.getroot() if isinstance(tree, ET.ElementTree) else tree


def sheets(tree):
    return {comp.get("ref"): comp.find("sheetpath").get("names")
            if comp.find("sheetpath") is not None else None
            for comp in tree_root(tree).findall("./components/comp")}


def dnp_refs(tree):
    result = set()
    for comp in tree_root(tree).findall("./components/comp"):
        flags = comp.findall("./property[@name='dnp']")
        require(len(flags) <= 1, f"Duplicate native DNP property: {comp.get('ref')}")
        if flags:
            require(flags[0].attrib == {"name": "dnp"}, f"Unexpected native DNP property shape: {comp.get('ref')}")
            result.add(comp.get("ref"))
    return result


def validate_netlists(baseline_tree, candidate_tree, contract=None):
    contract = load_contract() if contract is None else contract
    before, old = parse_netlist(baseline_tree)
    after, new = parse_netlist(candidate_tree)
    require(len(before) == 119 and len(old) == 398, "Unexpected baseline component/pin count")
    require(BOUNDARY <= before.keys(), "Unexpected baseline actuator boundary")
    require(after.keys() == before.keys(), "Unexpected candidate component set")
    require(new.keys() == old.keys(), "Unexpected candidate physical pin set")
    require(len(after) == 119 and len(new) == 398, "Unexpected candidate component/pin count")
    require(sheets(candidate_tree) == sheets(baseline_tree), "Existing component sheet path changed")
    old_dnp, new_dnp = dnp_refs(baseline_tree), dnp_refs(candidate_tree)
    require(not (old_dnp & IDENTITY_CHANGES), "Unexpected baseline diode DNP state")
    require(new_dnp == old_dnp | IDENTITY_CHANGES, "Master DNP state must add exactly D4 and D9; all others preserved")
    for ref, original in before.items():
        if ref not in BOUNDARY:
            require(after[ref] == original, f"Outside-boundary identity or physical pin definition changed: {ref}")
    for ref, expected in contract["candidate_parts"].items():
        require(after[ref] == normalized_part(expected), f"Contract part identity or physical pin definition differs: {ref}")
    changed_parts = {ref for ref in before if before[ref] != after[ref]}
    require(changed_parts == IDENTITY_CHANGES, "Unexpected component identity changes")
    for ref in IDENTITY_CHANGES:
        old_identity = dict(before[ref]); new_identity = dict(after[ref])
        for field in ["footprint", "mpn"]:
            old_identity.pop(field); new_identity.pop(field)
        require(old_identity == new_identity, f"Diode change exceeds MPN and footprint: {ref}")
    outside = {key: net for key, net in old.items() if key[0] not in BOUNDARY}
    require(len(outside) == 380, "Unexpected outside-boundary physical pin count")
    require(all(new.get(key) == net for key, net in outside.items()), "Outside-boundary pin memberships changed")
    expected = dict(old)
    for key, (old_net, new_net) in EXPECTED_DELTA.items():
        require(old[key] == old_net, f"Unexpected baseline buffer supply: {key}")
        expected[key] = new_net
    require(new == expected, "Candidate pin memberships differ from exactly four authorized supply moves")
    for ref, pins in contract["candidate_memberships"].items():
        require({pin: new[(ref, pin)] for pin in pins} == pins, f"Candidate boundary memberships differ from contract: {ref}")
    require(set(new.values()) == set(old.values()), "Candidate introduced or removed a named net")
    old_nodes = {(node.get("ref"), node.get("pin")): node for node in tree_root(baseline_tree).findall("./nets/net/node")}
    new_nodes = {(node.get("ref"), node.get("pin")): node for node in tree_root(candidate_tree).findall("./nets/net/node")}
    for key in old:
        require((old_nodes[key].get("pinfunction"), old_nodes[key].get("pintype")) ==
                (new_nodes[key].get("pinfunction"), new_nodes[key].get("pintype")),
                f"Existing native pin definition/NC marker changed: {key}")
    delta = {key: (old[key], new[key]) for key in old if old[key] != new[key]}
    require(delta == EXPECTED_DELTA, "Unexpected retained-pin delta")
    return {
        "baseline_components": 119, "candidate_components": 119,
        "baseline_physical_pins": 398, "candidate_physical_pins": 398,
        "removed_components": [], "added_components": [],
        "updated_component_identities": sorted(changed_parts),
        "master_schematic_added_dnp_refs": sorted(new_dnp - old_dnp),
        "removed_physical_pins": 0, "added_physical_pins": 0,
        "preserved_existing_pin_memberships": 394,
        "preserved_outside_boundary_pin_memberships": 380,
        "existing_pin_deltas": [{"reference": ref, "pin": pin, "before": a, "after": b}
                                for (ref, pin), (a, b) in sorted(delta.items())],
        "added_net_names": [], "removed_net_names": [],
        "candidate_part_identity_contract": "pass",
        "physical_pin_completeness_and_uniqueness": "pass",
        "all_existing_sheet_paths_and_native_pin_metadata_preserved": True,
    }


def validate_population(data):
    require(data.get("schema") == 1 and data.get("revision") == "ACT-01", "Unexpected population schema/revision")
    require(data.get("status") == "proposed_assembly_variants_not_released", "Population proposal marked released")
    require(set(data.get("variants", {})) == {"BEC_ONLY", "ONBOARD"}, "Only two exclusive population proposals are defined")
    expected = {"BEC_ONLY": {"D4": "DNP", "D9": "POPULATE"},
                "ONBOARD": {"D4": "POPULATE", "D9": "DNP"}}
    for name, parts in expected.items():
        variant = data["variants"][name]
        require(set(variant) == {"D4", "D9", "actuator_source", "logic_supply"}, f"Unexpected variant fields: {name}")
        require({ref: variant[ref] for ref in parts} == parts, f"Variant must have exactly the declared single source: {name}")
        require(all(isinstance(variant.get(field), str) and variant[field].strip()
                    for field in ["actuator_source", "logic_supply"]), f"Missing variant explanation: {name}")
    require(data.get("base_schematic_dnp_refs") == ["D4", "D9"], "Master schematic must hold both diode positions DNP")
    require(data.get("dual_population_allowed") is False, "Dual source population must remain prohibited")
    require(data.get("base_schematic_role") == "superset_for_connectivity_review_not_a_default_assembly", "Review superset cannot become a default assembly")
    require("default_released_variant" in data and data["default_released_variant"] is None, "No variant is released")
    require(data.get("all_parts_held") is True, "Candidate parts must remain held")
    require(data.get("procurement_approved") is False and data.get("hardware_tested") is False, "Population contract cannot approve procurement or claim hardware testing")
    require(data.get("unchanged_connectors") == {"J2": ["ESC_SIG", "BEC_IN", "GND"], "J3": ["SERVO_SIG", "VSERVO", "GND"]}, "Unexpected connector map")
    require(isinstance(data.get("constraints"), list) and data["constraints"]
            and all(isinstance(x, str) and x.strip() for x in data["constraints"]), "Missing population constraints")
    return {"status": "pass_proposed_variants_only", "variants": expected,
            "dual_population_allowed": False, "default_released_variant": None,
            "base_schematic_dnp_refs": ["D4", "D9"],
            "all_parts_held": True, "procurement_approved": False, "hardware_tested": False}


def validate_erc(baseline, candidate):
    old, new = base.erc_summary(baseline), base.erc_summary(candidate)
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
    baseline_dir, candidate_dir = Path(baseline_dir), Path(candidate_dir)
    paths = {"baseline_netlist": baseline_dir / "netlist.xml", "baseline_erc": baseline_dir / "erc.json",
             "candidate_netlist": candidate_dir / "netlist.xml", "candidate_erc": candidate_dir / "erc.json",
             "expected_contract": CONTRACT_PATH, "population_contract": POPULATION_PATH,
             "parser": PARSER_PATH, "verifier": Path(__file__).resolve()}
    for sheet in PRESERVED_SHEETS:
        paths["baseline_source_" + sheet] = baseline_dir.parent / "source/hardware/kicad_v2" / sheet
        paths["candidate_source_" + sheet] = candidate_dir.parent / "source/hardware/kicad_v2" / sheet
    for path in paths.values():
        require(path.is_file(), f"Native, source or contract input missing: {path}")
    captured = {key: record(path) for key, path in paths.items()}
    contract = load_contract()
    delta = validate_netlists(ET.parse(paths["baseline_netlist"]), ET.parse(paths["candidate_netlist"]), contract)
    erc = validate_erc(json.loads(paths["baseline_erc"].read_text(encoding="utf-8-sig")),
                       json.loads(paths["candidate_erc"].read_text(encoding="utf-8-sig")))
    population = validate_population(json.loads(POPULATION_PATH.read_text(encoding="utf-8-sig")))
    preserved = {}
    for sheet in PRESERVED_SHEETS:
        original, candidate = paths["baseline_source_" + sheet], paths["candidate_source_" + sheet]
        require(original.read_bytes() == candidate.read_bytes(), f"Converter source changed: {sheet}")
        preserved[sheet] = captured["baseline_source_" + sheet]["sha256"]
    require(captured == {key: record(path) for key, path in paths.items()}, "Input changed during verification")
    return {"schema_version": 1, "revision": contract["revision"], "status": "pass_isolated_schematic_only",
            "inputs": captured, "electrical_delta": delta, "native_erc": erc,
            "population_contract": population, "preserved_converter_source_sha256": preserved,
            "scope": "isolated native part/pin comparison and proposed exclusive population checks",
            "pcb_updated": False, "live_circuit_updated": False, "hardware_tested": False,
            "qualified_for_power": False, "fabrication_approved": False, "procurement_approved": False,
            "limitations": ["Rechecks captured native files; does not run KiCad or independently establish whole-project source/export freshness.",
                            "Population contract is a proposal, not a released assembly or proof of the physically fitted configuration.",
                            "ERC and contract agreement do not qualify transient, leakage, thermal, backdrive, load or startup behavior.",
                            "Both converters and all other input-stage, ADC and separate IMU2 integration gates remain outside this amendment."]}


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
