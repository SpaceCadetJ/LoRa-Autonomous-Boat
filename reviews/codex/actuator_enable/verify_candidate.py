#!/usr/bin/env python3
"""ACT-02 isolated schematic verifier; captures only actual native evidence.

collect(), validate_netlists() and --check are read-only. Expectations below are
independent of candidate XML and must agree with the pre-export contract.
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
BASELINE = ROOT / "reviews/codex/actuator_supply/native"
CONTRACT_PATH = PACKET / "expected_contract.json"
POPULATION_PATH = PACKET / "population_contract.json"
PARSER_PATH = ROOT / "reviews/codex/imu_interface/verify_candidate.py"
PRIOR_PATH = ROOT / "reviews/codex/actuator_supply/verify_candidate.py"
spec = importlib.util.spec_from_file_location("act02_prior_verifier", PRIOR_PATH)
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
base = prior.base
require, ValidationError = base.require, base.ValidationError
parse_netlist = base.parse_netlist
normalized_part, sheets, dnp_refs = prior.normalized_part, prior.sheets, prior.dnp_refs
validate_population, validate_erc = prior.validate_population, prior.validate_erc
BOUNDARY = {"U4", "U5", "C13", "C14"}
PC4 = ("U1", "24")
PC4_OLD = "unconnected-(U1-PC4-Pad24)"
ENABLE = "/ACT_EN_PC4"
PRESERVED_SHEETS = ["Buck3V3.kicad_sch", "Buck5V.kicad_sch", "Power.kicad_sch"]
CAP = {"value": "100nF", "footprint": "Capacitor_SMD:C_0603_1608Metric",
       "mpn": "KGM15ACG1H104KT", "manufacturer": "Kyocera AVX",
       "library": ["Device", "C"], "pins": {"1": ["", "passive"], "2": ["", "passive"]}}
PARTS = {
    "U4": {"value": "TXU0102", "footprint": "LoRa_Boat_Controller_V2:TI_DCU0008A_TXU0102",
           "mpn": "TXU0102DCUR", "manufacturer": "Texas Instruments",
           "library": ["LoRa_Boat_Controller_V2", "TXU0102DCU"],
           "pins": {"1": ["B2Y", "tri_state"], "2": ["GND", "power_in"],
                    "3": ["VCCA", "power_in"], "4": ["A2", "input"],
                    "5": ["A1", "input"], "6": ["OE", "input"],
                    "7": ["VCCB", "power_in"], "8": ["B1Y", "tri_state"]}},
    "C13": copy.deepcopy(CAP), "C14": copy.deepcopy(CAP),
    "R40": {"value": "10k", "footprint": "Resistor_SMD:R_0603_1608Metric",
            "mpn": "RC0603FR-0710KL", "manufacturer": "Yageo",
            "library": ["Device", "R"], "pins": {"1": ["", "passive"], "2": ["", "passive"]}},
}
MEMBERSHIPS = {
    "U4": {"1": "/Actuators/SERVO_SIG_5V", "2": "GND", "3": "+3V3",
           "4": "/PWM_SERVO_PA8", "5": "/PWM_ESC_PC6", "6": ENABLE,
           "7": "/Power/+5V_BUCK", "8": "/Actuators/ESC_SIG_5V"},
    "C13": {"1": "+3V3", "2": "GND"},
    "C14": {"1": "/Power/+5V_BUCK", "2": "GND"},
    "R40": {"1": ENABLE, "2": "GND"},
}
BASE_MEMBERSHIPS = {
    "U4": {"1": "GND", "2": "/PWM_ESC_PC6", "3": "GND", "4": "/Actuators/ESC_SIG_5V", "5": "/Power/+5V_BUCK"},
    "U5": {"1": "GND", "2": "/PWM_SERVO_PA8", "3": "GND", "4": "/Actuators/SERVO_SIG_5V", "5": "/Power/+5V_BUCK"},
    "C13": {"1": "/Power/+5V_BUCK", "2": "GND"},
    "C14": {"1": "/Power/+5V_BUCK", "2": "GND"},
}
EXPECTED_CONTRACT = {
    "schema": 1, "revision": "ACT-02", "baseline_native": "reviews/codex/actuator_supply/native/netlist.xml",
    "boundary": ["U4", "U5", "C13", "C14"],
    "pin_exceptions": {"U1": {"24": {"before": PC4_OLD, "after": ENABLE, "remove_no_connect": True}}},
    "removed_parts": ["U5"], "added_parts": ["R40"],
    "candidate_parts": PARTS, "candidate_memberships": MEMBERSHIPS,
    "expected_counts": {"baseline_components": 119, "candidate_components": 119,
                        "baseline_pins": 398, "candidate_pins": 398, "outside_boundary_pins": 383},
    "source_sheets_preserved": PRESERVED_SHEETS, "population_contract_preserved": True,
    "live_electrical_delta": 0, "pcb_updated": False, "qualified_for_power": False,
}


def validate_contract(data):
    require(data == EXPECTED_CONTRACT, "Expected contract differs from independent ACT-02 specification")
    return data


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def load_contract(path=CONTRACT_PATH):
    return validate_contract(read_json(path))


def nodes(tree):
    return {(node.get("ref"), node.get("pin")): node
            for node in prior.tree_root(tree).findall("./nets/net/node")}


def validate_netlists(baseline_tree, candidate_tree, contract=None):
    validate_contract(load_contract() if contract is None else contract)
    before, old = parse_netlist(baseline_tree)
    after, new = parse_netlist(candidate_tree)
    require(len(before) == 119 and len(old) == 398, "Unexpected baseline component/pin count")
    require(BOUNDARY <= before.keys() and "R40" not in before, "Unexpected baseline actuator boundary")
    for ref, pins in BASE_MEMBERSHIPS.items():
        require({pin: old.get((ref, pin)) for pin in pins} == pins, f"Unexpected baseline memberships: {ref}")
    require(old.get(PC4) == PC4_OLD and list(old.values()).count(PC4_OLD) == 1, "Baseline PC4 must be an NC singleton")
    require(before["U1"]["pins"]["24"] == ("PC4", "bidirectional"), "Unexpected MCU PC4 physical definition")
    require(set(after) == (set(before) - {"U5"}) | {"R40"}, "Unexpected candidate component set")
    expected = {key: net for key, net in old.items() if key[0] not in {"U4", "U5"}}
    expected[PC4] = ENABLE
    for ref, pins in MEMBERSHIPS.items():
        expected.update({(ref, pin): net for pin, net in pins.items()})
    require(new.keys() == expected.keys(), "Unexpected candidate physical pin set")
    require(len(after) == 119 and len(new) == 398, "Unexpected candidate component/pin count")
    expected_sheets = {ref: path for ref, path in sheets(baseline_tree).items() if ref != "U5"}
    expected_sheets["R40"] = "/Actuators/"
    require(sheets(candidate_tree) == expected_sheets, "Existing component sheet path changed or new resistor misplaced")
    old_dnp = dnp_refs(baseline_tree)
    require({"D4", "D9"} <= old_dnp and not (old_dnp & BOUNDARY), "Unexpected baseline master DNP state")
    require(dnp_refs(candidate_tree) == old_dnp, "Master DNP state changed")
    for ref, identity in before.items():
        if ref not in {"U4", "U5"}:
            require(after[ref] == identity, f"Existing identity or physical pin definition changed: {ref}")
    for ref, identity in PARTS.items():
        require(after[ref] == normalized_part(identity), f"Contract part identity or physical pin definition differs: {ref}")
    outside = {key: net for key, net in old.items() if key[0] not in BOUNDARY and key != PC4}
    require(len(outside) == 383, "Unexpected outside-boundary physical pin count")
    require(all(new.get(key) == net for key, net in outside.items()), "Outside-boundary pin memberships changed")
    require(new == expected, "Candidate pin memberships differ from exact ACT-02 contract")
    require(set(new.values()) == (set(old.values()) - {PC4_OLD}) | {ENABLE}, "Unexpected net names")
    old_nodes, new_nodes = nodes(baseline_tree), nodes(candidate_tree)
    require(old_nodes[PC4].attrib == {"ref": "U1", "pin": "24", "pinfunction": "PC4", "pintype": "bidirectional+no_connect"}, "Unexpected baseline PC4 native NC metadata")
    for key in set(old) & set(new):
        if key[0] == "U4":
            continue
        expected_attributes = dict(old_nodes[key].attrib)
        if key == PC4:
            expected_attributes["pintype"] = "bidirectional"
        require(new_nodes[key].attrib == expected_attributes, f"Existing native pin metadata/NC marker changed: {key}")
    for ref in ["U4", "R40"]:
        for pin, (name, kind) in PARTS[ref]["pins"].items():
            attributes = {"ref": ref, "pin": pin, "pintype": kind}
            if name:
                attributes["pinfunction"] = name
            require(new_nodes[(ref, pin)].attrib == attributes, f"New native pin metadata differs: {ref}.{pin}")
    common = set(old) & set(new)
    delta = {key: (old[key], new[key]) for key in common if old[key] != new[key]}
    expected_delta = {(ref, pin): (BASE_MEMBERSHIPS[ref][pin], net)
                      for ref, pins in MEMBERSHIPS.items() if ref in {"U4", "C13", "C14"}
                      for pin, net in pins.items() if pin in BASE_MEMBERSHIPS[ref] and BASE_MEMBERSHIPS[ref][pin] != net}
    expected_delta[PC4] = (PC4_OLD, ENABLE)
    require(delta == expected_delta, "Unexpected retained-pin delta")
    return {"baseline_components": 119, "candidate_components": 119,
            "baseline_physical_pins": 398, "candidate_physical_pins": 398,
            "removed_components": ["U5"], "added_components": ["R40"],
            "updated_component_identities": ["U4"], "preserved_master_dnp_refs": sorted(old_dnp),
            "removed_physical_pins": len(set(old) - set(new)), "added_physical_pins": len(set(new) - set(old)),
            "preserved_existing_pin_memberships": len(common) - len(delta),
            "preserved_outside_boundary_pin_memberships": 383,
            "existing_pin_deltas": [{"reference": ref, "pin": pin, "before": a, "after": b}
                                     for (ref, pin), (a, b) in sorted(delta.items())],
            "added_net_names": [ENABLE], "removed_net_names": [PC4_OLD],
            "native_pin_metadata_exceptions": [{"reference": "U1", "pin": "24", "before": "bidirectional+no_connect", "after": "bidirectional"}],
            "candidate_part_identity_contract": "pass", "physical_pin_completeness_and_uniqueness": "pass",
            "other_existing_sheet_paths_and_native_pin_metadata_preserved": True}


def path_label(path):
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(Path(path).resolve())


def record(path):
    return {"path": path_label(path), "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}


def validate_manifest_chain(packet, tracked):
    """Rehash captured files, not installed tools or unrelated uncommitted edits.

    This proves recorded linkage and current bytes, not independent execution of
    a recorded KiCad command. All manifests are still provenance claims.
    """
    def track(path):
        path = Path(path).resolve()
        require(path.is_relative_to(ROOT), f"Manifest path escapes repository: {path}")
        require(path.is_file(), f"Manifest input missing: {path}")
        item = record(path)
        tracked[item["path"]] = item
        return item["sha256"]
    def check_map(mapping):
        require(isinstance(mapping, dict) and mapping, "Missing manifest hash mapping")
        for name, digest in mapping.items():
            require(isinstance(name, str) and not Path(name).is_absolute(), "Manifest path must be repository-relative")
            require(track(ROOT / name) == digest, f"Manifest hash differs: {name}")
    input_path, build_path, native_path = [packet / name for name in ["input_manifest.json", "build_manifest.json", "native_manifest.json"]]
    for path in [input_path, build_path, native_path]:
        track(path)
    inputs, build, native = map(read_json, [input_path, build_path, native_path])
    require(build["source_revision"] == inputs["source_revision"], "Build baseline revision differs")
    require(build["baseline_source_sha256"] == inputs["baseline_source_sha256"], "Build baseline source mapping differs")
    check_map(inputs["baseline_source_sha256"])
    check_map(inputs["additional_input_sha256"])
    for field, filename in [("builder_sha256", "build_candidate.py"), ("expected_contract_sha256", "expected_contract.json"), ("population_contract_sha256", "population_contract.json")]:
        require(track(packet / filename) == build[field], f"Build provenance differs: {field}")
    outputs = build["output_sha256"]
    check_map(outputs)
    actual = {path_label(path) for path in (packet / "source").rglob("*") if path.is_file()}
    require(set(outputs) == actual, "Build manifest source-file coverage differs")
    require(native["input_sha256"] == outputs, "Native manifest inputs differ from captured build")
    require(track(packet / "export_native.py") == native["runner_sha256"], "Native runner hash differs")
    commands = native.get("commands", [])
    require(len(commands) == 3 and all(command.get("returncode") == 0 for command in commands), "Native manifest must report three successful commands")
    prefixes = [["sch", "export", "netlist"], ["sch", "erc"], ["sch", "export", "svg"]]
    for command, prefix in zip(commands, prefixes):
        require(command.get("argv", [])[1:1 + len(prefix)] == prefix, "Unexpected native command kind/order")
    check_map(native["output_sha256"])
    require({path_label(packet / "native/netlist.xml"), path_label(packet / "native/erc.json")} <= set(native["output_sha256"]), "Native evidence missing from manifest")
    return {"status": "pass_captured_hash_chain", "source_revision": build["source_revision"],
            "source_file_count": len(outputs), "native_output_file_count": len(native["output_sha256"]),
            "reported_native_commands": 3, "independently_reran_native_commands": False,
            "live_local_preservation_files_rechecked": False}


def collect(baseline_dir=BASELINE, candidate_dir=PACKET / "native"):
    baseline_dir, candidate_dir = Path(baseline_dir), Path(candidate_dir)
    paths = {"baseline_netlist": baseline_dir / "netlist.xml", "baseline_erc": baseline_dir / "erc.json",
             "candidate_netlist": candidate_dir / "netlist.xml", "candidate_erc": candidate_dir / "erc.json",
             "expected_contract": CONTRACT_PATH, "population_contract": POPULATION_PATH,
             "baseline_population_contract": baseline_dir.parent / "population_contract.json",
             "parser": PARSER_PATH, "prior_verifier": PRIOR_PATH, "verifier": Path(__file__).resolve()}
    for sheet in PRESERVED_SHEETS:
        paths["baseline_source_" + sheet] = baseline_dir.parent / "source/hardware/kicad_v2" / sheet
        paths["candidate_source_" + sheet] = candidate_dir.parent / "source/hardware/kicad_v2" / sheet
    for path in paths.values():
        require(path.is_file(), f"Native, source or contract input missing: {path}")
    captured = {key: record(path) for key, path in paths.items()}
    tracked = {}
    manifests = validate_manifest_chain(candidate_dir.parent, tracked)
    delta = validate_netlists(ET.parse(paths["baseline_netlist"]), ET.parse(paths["candidate_netlist"]), load_contract())
    erc = validate_erc(read_json(paths["baseline_erc"]), read_json(paths["candidate_erc"]))
    require(paths["baseline_population_contract"].read_bytes() == POPULATION_PATH.read_bytes(), "ACT-01 population contract changed")
    population = validate_population(read_json(POPULATION_PATH))
    preserved = {}
    for sheet in PRESERVED_SHEETS:
        require(paths["baseline_source_" + sheet].read_bytes() == paths["candidate_source_" + sheet].read_bytes(), f"Preserved source changed: {sheet}")
        preserved[sheet] = captured["baseline_source_" + sheet]["sha256"]
    require(captured == {key: record(path) for key, path in paths.items()}, "Input changed during verification")
    require(all(record(ROOT / path) == item for path, item in tracked.items()), "Manifest input changed during verification")
    return {"schema_version": 1, "revision": "ACT-02", "status": "pass_isolated_schematic_only",
            "inputs": captured, "manifest_inputs": tracked, "manifest_chain": manifests,
            "electrical_delta": delta, "native_erc": erc, "population_contract": population,
            "preserved_source_sha256": preserved, "population_contract_byte_preserved": True,
            "scope": "isolated native part/pin, captured manifest hash and held population checks",
            "pcb_updated": False, "live_circuit_updated": False, "firmware_updated": False,
            "hardware_tested": False, "qualified_for_power": False, "fabrication_approved": False, "procurement_approved": False,
            "limitations": ["Checks captured hashes and recorded successful native commands; does not independently rerun KiCad or prove command execution.",
                            "Source hashes cover the isolated capture; installed library versions and unrelated live/local files are not requalified.",
                            "Only PC4 native NC metadata is removed. Firmware remains unchanged and has not enabled or qualified this actuator path.",
                            "D4/D9 remain held DNP in the master schematic; the exclusive assembly variants are proposals.",
                            "ERC and exact connectivity do not qualify startup, partial-power, pulse integrity, fault, load, thermal or real hardware behavior."]}


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
            require(read_json(args.output) == result, "Captured validation is stale")
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({"status": result["status"], "mode": "check" if args.check else "capture",
                          "output": path_label(args.output), "delta": result["electrical_delta"]}, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, ET.ParseError) as error:
        print(json.dumps({"status": "fail", "error": str(error)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
