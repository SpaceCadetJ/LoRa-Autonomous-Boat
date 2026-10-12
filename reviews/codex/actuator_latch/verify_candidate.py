#!/usr/bin/env python3
"""Independent ACT-04 exact pin/identity and captured-evidence verifier.

Use --capture only after native export; --check and collect() never write.
A pass is isolated schematic evidence, never hardware or fabrication approval.
"""
from __future__ import annotations
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
PACKET = Path(__file__).resolve().parent
BASELINE = ROOT / "reviews/codex/actuator_enable/native"
CONTRACT_PATH = PACKET / "expected_contract.json"
POPULATION_PATH = PACKET / "population_contract.json"
PRIOR_PATH = ROOT / "reviews/codex/actuator_enable/verify_candidate.py"
spec = importlib.util.spec_from_file_location("act04_prior_verifier", PRIOR_PATH)
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
require, ValidationError = prior.require, prior.ValidationError
parse_netlist = prior.parse_netlist
normalized_part, sheets, dnp_refs = prior.normalized_part, prior.sheets, prior.dnp_refs
validate_erc, validate_population = prior.validate_erc, prior.validate_population
record, path_label, read_json = prior.record, prior.path_label, prior.read_json
ARM = "/ACT_EN_PC4"
CHILD = "/Actuators/ArmInterlock/"
ACK, ARM_LOW, READY, QUAL = [CHILD + name for name in ["ACK", "ARM_LOW", "READY", "QUAL_OK"]]
OE = "/Actuators/ACT_OE"
QBAR_NC = "unconnected-(U12-~{Q}-Pad3)"
INVERTER_NC = "unconnected-(U13-NC-Pad1)"
PRESERVED_SHEETS = ["Power.kicad_sch", "Buck3V3.kicad_sch", "Buck5V.kicad_sch", "MCU.kicad_sch"]
ADDED_ORDER = ["U12", "U13", "U14", "R41", "R42", "R43", "C56", "C57", "C58"]
EXPECTED_DELTA = {("U4", "6"): (ARM, OE), ("R40", "1"): (ARM, OE)}
PARTS = {
    "U12": {"value": "SN74LVC1G74", "mpn": "SN74LVC1G74DCUR", "manufacturer": "Texas Instruments",
            "footprint": "LoRa_Boat_Controller_V2:TI_DCU0008A_LVC1G74",
            "library": ["LoRa_Boat_Controller_V2", "SN74LVC1G74"],
            "pins": {"1": ["CLK", "input"], "2": ["D", "input"], "3": ["~{Q}", "output"],
                     "4": ["GND", "power_in"], "5": ["Q", "output"], "6": ["~{CLR}", "input"],
                     "7": ["~{PRE}", "input"], "8": ["VCC", "power_in"]}},
    "U13": {"value": "SN74LVC1G04", "mpn": "SN74LVC1G04DBVR", "manufacturer": "Texas Instruments",
            "footprint": "LoRa_Boat_Controller_V2:TI_DBV0005A_LVC1G04",
            "library": ["LoRa_Boat_Controller_V2", "SN74LVC1G04"],
            "pins": {"1": ["NC", "no_connect"], "2": ["A", "input"], "3": ["GND", "power_in"],
                     "4": ["Y", "output"], "5": ["VCC", "power_in"]}},
    "U14": {"value": "SN74LVC1G11", "mpn": "SN74LVC1G11DBVR", "manufacturer": "Texas Instruments",
            "footprint": "LoRa_Boat_Controller_V2:TI_DBV0006A_LVC1G11",
            "library": ["LoRa_Boat_Controller_V2", "SN74LVC1G11"],
            "pins": {"1": ["A", "input"], "2": ["GND", "power_in"], "3": ["B", "input"],
                     "4": ["Y", "output"], "5": ["VCC", "power_in"], "6": ["C", "input"]}},
}
for ref in ["R41", "R42", "R43"]:
    PARTS[ref] = {"value": "10k", "footprint": "Resistor_SMD:R_0603_1608Metric", "mpn": "RC0603FR-0710KL",
                  "manufacturer": "Yageo", "library": ["Device", "R"],
                  "pins": {"1": ["", "passive"], "2": ["", "passive"]}}
for ref in ["C56", "C57", "C58"]:
    PARTS[ref] = {"value": "100nF", "footprint": "Capacitor_SMD:C_0603_1608Metric", "mpn": "KGM15ACG1H104KT",
                  "manufacturer": "Kyocera AVX", "library": ["Device", "C"],
                  "pins": {"1": ["", "passive"], "2": ["", "passive"]}}
MEMBERSHIPS = {
    "U12": {"1": ACK, "2": ARM_LOW, "3": QBAR_NC, "4": "GND", "5": READY, "6": QUAL, "7": "+3V3", "8": "+3V3"},
    "U13": {"1": INVERTER_NC, "2": ARM, "3": "GND", "4": ARM_LOW, "5": "+3V3"},
    "U14": {"1": READY, "2": "GND", "3": ARM, "4": OE, "5": "+3V3", "6": QUAL},
    "R41": {"1": ARM, "2": "GND"}, "R42": {"1": QUAL, "2": "GND"}, "R43": {"1": ACK, "2": "GND"},
    "C56": {"1": "+3V3", "2": "GND"}, "C57": {"1": "+3V3", "2": "GND"}, "C58": {"1": "+3V3", "2": "GND"},
}
EXPECTED_CONTRACT = {
    "schema": 1, "revision": "ACT-04", "baseline_native": "reviews/codex/actuator_enable/native/netlist.xml",
    "added_parts": ADDED_ORDER, "removed_parts": [], "candidate_parts": PARTS, "candidate_memberships": MEMBERSHIPS,
    "retained_pin_changes": {ref + "." + pin: {"before": old, "after": new} for (ref, pin), (old, new) in EXPECTED_DELTA.items()},
    "expected_counts": {"baseline_components": 119, "candidate_components": 128,
                        "baseline_pins": 398, "candidate_pins": 429, "retained_unchanged_pins": 396},
    "preserved_sheets": PRESERVED_SHEETS, "population_contract_preserved": True,
    "live_electrical_delta": 0, "pcb_updated": False, "qualified_for_power": False, "qualification_ports_implemented": False,
}


def validate_contract(data):
    require(data == EXPECTED_CONTRACT, "Expected contract differs from independent ACT-04 specification")
    return data


def load_contract(path=CONTRACT_PATH):
    return validate_contract(read_json(path))


def node_attributes(ref, pin):
    name, kind = PARTS[ref]["pins"][pin]
    if (ref, pin) == ("U12", "3"):
        kind += "+no_connect"
    attributes = {"ref": ref, "pin": pin, "pintype": kind}
    if name:
        attributes["pinfunction"] = name
    return attributes


def validate_netlists(baseline_tree, candidate_tree, contract=None):
    validate_contract(load_contract() if contract is None else contract)
    before, old = parse_netlist(baseline_tree)
    after, new = parse_netlist(candidate_tree)
    require(len(before) == 119 and len(old) == 398, "Unexpected baseline component/pin count")
    require(not (set(before) & set(PARTS)), "New reference already exists in baseline")
    require({key for key, net in old.items() if net == ARM} == {("U1", "24"), ("U4", "6"), ("R40", "1")}, "Unexpected baseline PC4/OE connection")
    require(set(after) == set(before) | set(PARTS), "Unexpected candidate component set")
    expected = dict(old)
    for key, (old_net, new_net) in EXPECTED_DELTA.items():
        require(old[key] == old_net, f"Unexpected baseline retained pin: {key}")
        expected[key] = new_net
    for ref, pins in MEMBERSHIPS.items():
        expected.update({(ref, pin): net for pin, net in pins.items()})
    require(new.keys() == expected.keys(), "Unexpected candidate physical pin set")
    require(len(after) == 128 and len(new) == 429, "Unexpected candidate component/pin count")
    expected_sheets = dict(sheets(baseline_tree))
    expected_sheets.update({ref: CHILD for ref in PARTS})
    require(sheets(candidate_tree) == expected_sheets, "Existing sheet path changed or new part outside ArmInterlock child")
    old_dnp = dnp_refs(baseline_tree)
    require({"D4", "D9"} <= old_dnp, "Unexpected baseline master DNP state")
    require(dnp_refs(candidate_tree) == old_dnp, "Master DNP state changed")
    for ref, identity in before.items():
        require(after[ref] == identity, f"Existing identity or physical pin definition changed: {ref}")
    for ref, identity in PARTS.items():
        require(after[ref] == normalized_part(identity), f"Contract part identity or physical pin definition differs: {ref}")
    unchanged = {key: net for key, net in old.items() if key not in EXPECTED_DELTA}
    require(len(unchanged) == 396, "Unexpected preserved existing pin count")
    require(all(new.get(key) == net for key, net in unchanged.items()), "Unrelated existing pin memberships changed")
    require(new == expected, "Candidate pin memberships differ from exact ACT-04 contract")
    require(set(new.values()) == set(expected.values()), "Unexpected named nets")
    old_nodes, new_nodes = prior.nodes(baseline_tree), prior.nodes(candidate_tree)
    for key, node in old_nodes.items():
        require(new_nodes[key].attrib == node.attrib, f"Existing native pin metadata/NC marker changed: {key}")
    for ref, pins in MEMBERSHIPS.items():
        for pin in pins:
            require(new_nodes[(ref, pin)].attrib == node_attributes(ref, pin), f"New native pin metadata differs: {ref}.{pin}")
    for ref, pin, net in [("U12", "3", QBAR_NC), ("U13", "1", INVERTER_NC)]:
        require({key for key, name in new.items() if name == net} == {(ref, pin)}, f"New NC must be a singleton: {ref}.{pin}")
    delta = {key: (net, new[key]) for key, net in old.items() if new[key] != net}
    require(delta == EXPECTED_DELTA, "Unexpected retained-pin delta")
    return {"baseline_components": 119, "candidate_components": 128,
            "baseline_physical_pins": 398, "candidate_physical_pins": 429,
            "added_components": sorted(PARTS), "removed_components": [], "updated_component_identities": [],
            "added_physical_pins": 31, "removed_physical_pins": 0, "preserved_existing_pin_memberships": 396,
            "existing_pin_deltas": [{"reference": ref, "pin": pin, "before": a, "after": b}
                                     for (ref, pin), (a, b) in sorted(delta.items())],
            "preserved_master_dnp_refs": sorted(old_dnp),
            "added_net_names": sorted(set(new.values()) - set(old.values())), "removed_net_names": [],
            "all_existing_identities_sheet_paths_and_native_pin_metadata_preserved": True,
            "candidate_part_identity_contract": "pass", "physical_pin_completeness_and_uniqueness": "pass",
            "qualification_ports": "default-low proposed interfaces; no supervisor, receiver-ready or command watchdog implemented"}


def validate_preservation(baseline_sources, candidate_sources, baseline_population, candidate_population):
    """Bytes-only check usable by mutation tests without producing source files."""
    require(set(baseline_sources) == set(PRESERVED_SHEETS) and set(candidate_sources) == set(PRESERVED_SHEETS), "Incomplete preserved-source set")
    for name in PRESERVED_SHEETS:
        require(baseline_sources[name] == candidate_sources[name], f"Preserved source changed: {name}")
    require(baseline_population == candidate_population, "ACT-01 population contract changed")
    return validate_population(json.loads(candidate_population.decode("utf-8-sig")))


def collect(baseline_dir=BASELINE, candidate_dir=PACKET / "native"):
    baseline_dir, candidate_dir = Path(baseline_dir), Path(candidate_dir)
    paths = {"baseline_netlist": baseline_dir / "netlist.xml", "baseline_erc": baseline_dir / "erc.json",
             "candidate_netlist": candidate_dir / "netlist.xml", "candidate_erc": candidate_dir / "erc.json",
             "expected_contract": CONTRACT_PATH, "population_contract": POPULATION_PATH,
             "baseline_population_contract": baseline_dir.parent / "population_contract.json",
             "act02_verifier": PRIOR_PATH, "act01_verifier": prior.PRIOR_PATH,
             "parser": prior.PARSER_PATH, "verifier": Path(__file__).resolve()}
    for sheet in PRESERVED_SHEETS:
        paths["baseline_source_" + sheet] = baseline_dir.parent / "source/hardware/kicad_v2" / sheet
        paths["candidate_source_" + sheet] = candidate_dir.parent / "source/hardware/kicad_v2" / sheet
    for path in paths.values():
        require(path.is_file(), f"Native, source or contract input missing: {path}")
    captured = {key: record(path) for key, path in paths.items()}
    tracked = {}
    manifests = prior.validate_manifest_chain(candidate_dir.parent, tracked)
    delta = validate_netlists(ET.parse(paths["baseline_netlist"]), ET.parse(paths["candidate_netlist"]), load_contract())
    erc = validate_erc(read_json(paths["baseline_erc"]), read_json(paths["candidate_erc"]))
    population = validate_preservation(
        {name: paths["baseline_source_" + name].read_bytes() for name in PRESERVED_SHEETS},
        {name: paths["candidate_source_" + name].read_bytes() for name in PRESERVED_SHEETS},
        paths["baseline_population_contract"].read_bytes(), paths["population_contract"].read_bytes())
    require(captured == {key: record(path) for key, path in paths.items()}, "Input changed during verification")
    require(all(record(ROOT / path) == item for path, item in tracked.items()), "Manifest input changed during verification")
    return {"schema_version": 1, "revision": "ACT-04", "status": "pass_isolated_schematic_only",
            "inputs": captured, "manifest_inputs": tracked, "manifest_chain": manifests,
            "electrical_delta": delta, "native_erc": erc, "population_contract": population,
            "preserved_source_sha256": {name: captured["baseline_source_" + name]["sha256"] for name in PRESERVED_SHEETS},
            "population_contract_byte_preserved": True,
            "scope": "isolated native connectivity, exact part identities and captured source/provenance checks",
            "pcb_updated": False, "live_circuit_updated": False, "firmware_updated": False,
            "qualification_ports_implemented": False, "hardware_tested": False,
            "qualified_for_power": False, "fabrication_approved": False, "procurement_approved": False,
            "limitations": ["Checks recorded native evidence and manifest hashes; does not rerun KiCad or prove execution of recorded commands.",
                            "QUAL_OK and ACK are unimplemented default-low interfaces. This is not a receiver observer or command watchdog.",
                            "No timing, metastability, fault-pulse capture, partial-power, startup or actual actuator behavior is accepted by a connectivity check.",
                            "ACK while armed clears READY in this one-DFF proposal; ACT-03 ignores that ACK, so the behavioral difference remains explicit.",
                            "D4/D9 remain DNP in the master; assembly variants and all new parts remain held.",
                            "Installed libraries and unrelated live/local edits are outside this captured hash check."]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-dir", type=Path, default=BASELINE)
    parser.add_argument("--candidate-dir", type=Path, default=PACKET / "native")
    parser.add_argument("--output", type=Path, default=PACKET / "validation.json")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--capture", action="store_true", help="Write validation only after actual native inputs pass")
    mode.add_argument("--check", action="store_true", help="Compare recorded validation without writing")
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
