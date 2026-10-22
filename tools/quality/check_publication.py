#!/usr/bin/env python3
"""Check committed evidence/portfolio portability; no CAD generation or hardware."""
import hashlib
import importlib.util
import xml.etree.ElementTree as ET
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]

def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8-sig"))

def check_hashes(entries, label):
    for name, expected in entries.items():
        source = ROOT / name
        if not source.is_file():
            raise AssertionError(f"{label}: missing {name}")
        actual = hashlib.sha256(source.read_bytes()).hexdigest()
        if actual != expected:
            raise AssertionError(f"{label}: byte mismatch {name}")
    print(f"PASS {label}: {len(entries)} hashes")

def main():
    historical_path = "reviews/codex/publication/native-review"
    historical = read_json(historical_path + "/review.json")
    check_hashes({historical_path + "/inputs/" + p: h for p, h in historical["input_manifest"].items()},
                 "preserved publication native inputs")
    current_path = "reviews/codex/design_completion/native-review/review.json"
    quality = read_json(current_path) if (ROOT / current_path).is_file() else historical
    check_hashes(quality["input_manifest"], "current native review inputs")
    assert quality["gates"]["fabrication"] is False, "This edition is not a fabrication release"
    exports = read_json("docs/img/schematic_export_manifest.json")
    # Board copper is a historical context input for a schematic-only export.
    # Preserve that evidence while independently checking the current board above.
    export_inputs = {historical_path + "/inputs/" + p if p.endswith(".kicad_pcb") else p: h
                     for p, h in exports["input_sha256"].items()}
    check_hashes(export_inputs, "schematic export inputs (PCB context preserved)")
    check_hashes(exports["output_sha256"], "schematic PDF/SVG outputs")
    pcb_renders = read_json("reviews/codex/design_completion/pcb_render_manifest.json")
    check_hashes(pcb_renders["input_sha256"], "V2 PCB render input")
    check_hashes(pcb_renders["output_sha256"], "V2 PCB preview outputs")
    firmware = read_json("docs/build/evidence/v1-build-manifest.json")
    check_hashes(firmware["input_sha256"], "recorded V1 build inputs")
    assert firmware["status"] == "build_pass_unqualified" and firmware["hardware_access"] is False
    diagnostic = read_json("firmware_v2/evidence/stage_a_build.json")
    check_hashes(diagnostic["input_sha256"], "V2 diagnostic build inputs")
    assert diagnostic["hardware_access"] is False and diagnostic["operational_release"] is False
    imu_root = "reviews/codex/imu_interface/"
    captured = read_json(imu_root + "input_manifest.json")
    check_hashes({imu_root + "inputs/" + p: h for p, h in captured["sha256"].items()}, "IMU captured generator/library inputs")
    imu_build = read_json(imu_root + "candidate_manifest.json")
    check_hashes({imu_root + p: h for p, h in imu_build["output_sha256"].items()}, "IMU generated candidate sources")
    check_hashes({imu_root + p: h for p, h in imu_build["source_script_sha256"].items()}, "IMU isolated generation scripts")
    check_hashes({imu_root + "build_candidate.py": imu_build["generator_sha256"]}, "IMU candidate builder")
    imu_native = read_json(imu_root + "native_manifest.json")
    check_hashes(imu_native["input_sha256"], "IMU native export inputs")
    check_hashes(imu_native["output_sha256"], "IMU native export outputs")
    check_hashes({imu_root + "export_candidate.py": imu_native["exporter_sha256"]}, "IMU native exporter")
    imu_result = read_json(imu_root + "validation.json")
    check_hashes({record["path"]: record["sha256"] for record in imu_result["inputs"].values()}, "IMU electrical comparison inputs")
    spec = importlib.util.spec_from_file_location("imu_candidate_check", ROOT / imu_root / "verify_candidate.py")
    imu = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(imu)
    before = ROOT / imu_result["inputs"]["baseline_netlist"]["path"]
    after = ROOT / imu_result["inputs"]["candidate_netlist"]["path"]
    assert imu.validate_netlists(ET.parse(before), ET.parse(after)) == imu_result["electrical_delta"]
    old_erc = imu.erc_summary(read_json(imu_result["inputs"]["baseline_erc"]["path"]))
    new_erc = imu.erc_summary(read_json(imu_result["inputs"]["candidate_erc"]["path"]))
    assert new_erc["errors"] == 0 and new_erc["violations"] == old_erc["violations"]
    assert imu_result["status"] == "pass_candidate_only" and imu_result["pcb_updated"] is False and imu_result["hardware_tested"] is False
    print("PASS IMU captured-evidence comparison; live PCB unchanged and hardware unqualified")
    placement_root = "reviews/codex/imu_placement/"
    placement = read_json(placement_root + "packet_manifest.json")
    check_hashes(placement["input_sha256"], "placement live baseline inputs")
    check_hashes(placement["artifact_sha256"], "placement captured evidence and artifacts")
    placement_native = read_json(placement_root + "native_manifest.json")
    check_hashes(placement_native["input_sha256"], "placement native inputs")
    check_hashes(placement_native["output_sha256"], "placement native reports")
    check_hashes({placement_root + "native_check.py": placement_native["runner_sha256"]}, "placement native runner")
    assert placement["electrically_integrated"] is False and placement["fabrication_approved"] is False
    assert placement["hardware_tested"] is False and placement["whole_board_6s_fit_verified"] is False
    assert placement["courtyard_collisions"] == [] and placement["new_outside_outline"] == []
    spec = importlib.util.spec_from_file_location("placement_compare", ROOT / placement_root / "compare_study.py")
    geometry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(geometry)
    preserved = geometry.compare((ROOT / placement_root / "inputs/normalized_baseline.kicad_pcb").read_text(),
                                 (ROOT / placement_root / "study/IMU_PLACEMENT_STUDY.kicad_pcb").read_text())
    assert preserved == placement["preservation"]
    for name, key in [("drc_baseline.json", "baseline_drc"), ("drc_study.json", "study_drc")]:
        report = read_json(placement_root + name)
        assert sum(v["severity"] == "error" for v in report["violations"]) == placement[key]["errors"]
        assert sum(v["severity"] == "warning" for v in report["violations"]) == placement[key]["warnings"]
    assert placement["baseline_drc"]["errors"] == 0 and placement["study_drc"]["errors"] == 136
    print("PASS placement preservation and recorded FAILED native gate; no electrical integration")
    bias_root = "reviews/codex/imu_bias_filter/"
    bias_build = read_json(bias_root + "build_manifest.json")
    bias_native = read_json(bias_root + "native_manifest.json")
    bias_result = read_json(bias_root + "validation.json")
    check_hashes(bias_build["input_sha256"], "IMU2 previous candidate inputs")
    check_hashes(bias_build["output_sha256"], "IMU2 amended CAD inputs")
    # These two pre-existing workstation edits are intentionally not published or consumed.
    local_only = {"hardware/kicad/tools/v1_design.py", "hardware/kicad_v2/tools/route_v2.py"}
    check_hashes({p: h for p, h in bias_build["protected_sha256"].items() if p not in local_only},
                 "IMU2 preserved prior evidence and live CAD")
    check_hashes(bias_native["input_sha256"], "IMU2 native inputs")
    check_hashes(bias_native["output_sha256"], "IMU2 native exports")
    check_hashes(bias_result["comparison_input_sha256"], "IMU2 comparison inputs")
    check_hashes({bias_root + "build_amendment.py": bias_build["builder_sha256"],
                  bias_root + "export_native.py": bias_native["exporter_sha256"],
                  bias_root + "verify_amendment.py": bias_result["verifier_sha256"]}, "IMU2 evidence tools")
    spec = importlib.util.spec_from_file_location("bias_verify", ROOT / bias_root / "verify_amendment.py")
    bias = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bias)
    updated = ET.parse(ROOT / bias_root / "native/netlist.xml")
    assert bias.validate(ET.parse(ROOT / imu_root / "native/netlist.xml"), updated) == bias_result["amendment_delta"]
    assert bias.cumulative(updated) == bias_result["cumulative_delta"]
    bias_erc = bias.base.erc_summary(read_json(bias_root + "native/erc.json"))
    prior_erc = bias.base.erc_summary(read_json(imu_root + "native/erc.json"))
    assert bias_erc["errors"] == 0 and bias_erc["violations"] == prior_erc["violations"]
    assert bias_result["status"] == "pass_isolated_schematic_only"
    assert not any(bias_result[k] for k in ["pcb_updated", "hardware_tested", "fabrication_approved"])
    visual = read_json(bias_root + "review_notes.json")["visual_review"]
    check_hashes({visual["svg"]: visual["svg_sha256"], visual["png"]: visual["png_sha256"]}, "IMU2 reviewed drawing")
    print("PASS isolated IMU2 two-pin amendment and cumulative contract; no PCB/hardware acceptance")
    power_root = "reviews/codex/power_envelope/"
    power = read_json(power_root + "packet_manifest.json")
    check_hashes(power["artifact_sha256"], "6S power review artifacts")
    spec = importlib.util.spec_from_file_location("power_capture", ROOT / power_root / "capture.py")
    power_capture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(power_capture)
    assert power_capture.collect() == read_json(power_root + "evidence.json")
    holds = read_json("hardware/manufacturing/procurement_policy.json")["v2"]["holds"]
    assert {"C1", "C2", "C10", "F1", "D2", "R1"} <= holds.keys()
    assert power["electrical_delta"] == 0 and power["hardware_tested"] is False
    print("PASS power boundary capture, identity holds and unchanged CAD; no hardware qualification")
    topology_root = "reviews/codex/power_topology/"
    topology = read_json(topology_root + "packet_manifest.json")
    check_hashes(topology["input_sha256"], "power topology unchanged evidence inputs")
    check_hashes(topology["artifact_sha256"], "power topology artifacts")
    spec = importlib.util.spec_from_file_location("topology_model", ROOT / topology_root / "model.py")
    model = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(model)
    assert model.study() == read_json(topology_root + "comparison.json")
    assert topology["electrical_delta"] == 0 and topology["hardware_tested"] is False
    assert topology["fabrication_approved"] is False
    print("PASS proposed power arithmetic and unchanged evidence; no circuit or hardware acceptance")
    input_root = "reviews/codex/input_stage/"
    input_packet = read_json(input_root + "packet_manifest.json")
    check_hashes(input_packet["input_sha256"], "input-stage preserved baseline evidence")
    check_hashes(input_packet["artifact_sha256"], "input-stage captured sources and artifacts")
    input_build = read_json(input_root + "build_manifest.json")
    input_native = read_json(input_root + "native_manifest.json")
    check_hashes(input_build["output_sha256"], "input-stage candidate sources")
    check_hashes(input_native["input_sha256"], "input-stage native inputs")
    check_hashes(input_native["output_sha256"], "input-stage native outputs")
    check_hashes({input_root + "build_candidate.py": input_build["builder_sha256"],
                  input_root + "export_native.py": input_native["runner_sha256"]}, "input-stage evidence tools")
    spec = importlib.util.spec_from_file_location("input_stage_verify", ROOT / input_root / "verify_candidate.py")
    input_verify = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(input_verify)
    assert input_verify.collect() == read_json(input_root + "validation.json")
    assert input_packet["live_electrical_delta"] == 0 and input_packet["live_copper_delta"] == 0
    assert not any(input_packet[k] for k in ["pcb_updated", "hardware_tested", "fabrication_approved"])
    parts = read_json(input_root + "candidate_parts.json")
    assert parts["all_parts_held"] is True and len(parts["parts"]) == 6
    net_parts = {c.get("ref"): c for c in ET.parse(ROOT / input_root / "native/netlist.xml").findall("./components/comp")}
    assert {p["ref"] for p in parts["parts"]} == {"J1", "F1", "D1", "D12", "C1", "C2"}
    for part in parts["parts"]:
        comp = net_parts[part["ref"]]
        fields = {f.get("name"): f.text for f in comp.findall("./fields/field")}
        assert part["value"] == comp.findtext("value") and part["footprint"] == comp.findtext("footprint")
        assert part["mpn"] == fields["MPN"] and part["manufacturer"] == fields["Manufacturer"]
        assert part["quantity"] == 1 and part["status"] == "held_candidate_only_not_order_approved"
    assert all(item["passed"] for item in read_json(input_root + "coordinate_bounds.json").values())
    print("PASS input-stage native delta, held identities and preserved live CAD; no hardware acceptance")
    leakage_root = "reviews/codex/reverse_leakage/"
    leakage = read_json(leakage_root + "packet_manifest.json")
    check_hashes(leakage["input_sha256"], "reverse-leakage unchanged evidence inputs")
    check_hashes(leakage["artifact_sha256"], "reverse-leakage analytical review artifacts")
    for module_name, filename, function, record in [
            ("leakage_capture", "capture.py", "collect", "capture.json"),
            ("leakage_model", "model.py", "study", "analysis.json")]:
        spec = importlib.util.spec_from_file_location(module_name, ROOT / leakage_root / filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert getattr(module, function)() == read_json(leakage_root + record)
    analysis = read_json(leakage_root + "analysis.json")
    assert analysis["hardware_accepted"] is False and analysis["capacitor_reverse_accepted"] is False
    assert analysis["native_proofs_applicable"] is False
    assert leakage["live_electrical_delta"] == 0 and leakage["candidate_electrical_delta"] == 0
    assert leakage["hardware_tested"] is False and leakage["fabrication_approved"] is False
    assert all(c["full_circuit_current_bound_verified"] is False for c in analysis["dc_cases"])
    print("PASS reverse-leakage capture and analytical cases; capacitor and hardware acceptance remain blocked")
    capacitor_root = "reviews/codex/input_capacitors/"
    capacitor = read_json(capacitor_root + "packet_manifest.json")
    check_hashes(capacitor["input_sha256"], "input-capacitor preserved evidence inputs")
    check_hashes(capacitor["artifact_sha256"], "input-capacitor specification and geometry artifacts")
    for module_name, filename, function in [("capacitor_model", "model.py", "study"), ("capacitor_geometry", "check_geometry.py", "check")]:
        spec = importlib.util.spec_from_file_location(module_name, ROOT / capacitor_root / filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = getattr(module, function)()
        if function == "study":
            assert result == read_json(capacitor_root + "analysis.json")
            assert result["hardware_accepted"] is False and result["native_proofs_applicable"] is False
            assert all(x["hypothetical_total_effective_uf"] is None for x in result["local_bank_thresholds"])
        else:
            assert result is True
    assert capacitor["live_electrical_delta"] == 0 and capacitor["candidate_electrical_delta"] == 0
    assert not any(capacitor[k] for k in ["hardware_tested", "fabrication_approved", "effective_capacitance_verified"])
    print("PASS input-capacitor screening and native/portable land dimensions; integration gates remain open")
    buck_roots = ["reviews/codex/buck_3v3/", "reviews/codex/buck_5v/"]
    for buck_root in buck_roots:
        buck = read_json(buck_root + "packet_manifest.json")
        check_hashes(buck["input_sha256"], "converter preserved inputs")
        check_hashes(buck["artifact_sha256"], "converter captured artifacts")
        build = read_json(buck_root + "build_manifest.json")
        native = read_json(buck_root + "native_manifest.json")
        assert native["input_sha256"] == build["output_sha256"]
        check_hashes(build["output_sha256"], "converter source")
        check_hashes(native["output_sha256"], "converter native exports")
        check_hashes({buck_root + "build_candidate.py": build["builder_sha256"],
                      buck_root + "expected_contract.json": build["expected_contract_sha256"],
                      buck_root + "export_native.py": native["runner_sha256"]}, "converter provenance")
        for module_name, filename, function, record in [
                ("buck_verify", "verify_candidate.py", "collect", "validation.json"),
                ("buck_model", "model.py", "study", "analysis.json"),
                ("buck_packages", "inspect_packages.py", "check", None)]:
            spec = importlib.util.spec_from_file_location(module_name, ROOT / buck_root / filename)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            result = getattr(module, function)()
            if record:
                assert result == read_json(buck_root + record)
        assert buck["live_electrical_delta"] == 0 and buck["live_copper_delta"] == 0
        assert not any(buck[k] for k in ["pcb_updated", "hardware_tested", "fabrication_approved", "effective_capacitance_verified"])
        assert all(not v for v in read_json(buck_root + "analysis.json")["acceptance_gates"].values())
        print("PASS converter native delta, package evidence and analytical capture; hardware held")
    actuator_root = "reviews/codex/actuator_supply/"
    actuator = read_json(actuator_root + "packet_manifest.json")
    check_hashes(actuator["input_sha256"], "actuator preserved inputs")
    check_hashes(actuator["artifact_sha256"], "actuator captured artifacts")
    build = read_json(actuator_root + "build_manifest.json")
    native = read_json(actuator_root + "native_manifest.json")
    assert native["input_sha256"] == build["output_sha256"]
    check_hashes(build["output_sha256"], "actuator source")
    check_hashes(native["output_sha256"], "actuator native exports")
    check_hashes({actuator_root + "build_candidate.py": build["builder_sha256"],
                  actuator_root + "expected_contract.json": build["expected_contract_sha256"],
                  actuator_root + "population_contract.json": build["population_contract_sha256"],
                  actuator_root + "export_native.py": native["runner_sha256"]}, "actuator provenance")
    for module_name, filename, function, record in [
            ("actuator_verify", "verify_candidate.py", "collect", "validation.json"),
            ("actuator_packages", "inspect_packages.py", "check", None)]:
        spec = importlib.util.spec_from_file_location(module_name, ROOT / actuator_root / filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = getattr(module, function)()
        if record:
            assert result == read_json(actuator_root + record)
    assert actuator["live_electrical_delta"] == 0 and actuator["live_copper_delta"] == 0
    assert not any(actuator[k] for k in ["pcb_updated", "hardware_tested", "fabrication_approved", "assembly_variant_released"])
    check_hashes(read_json(actuator_root + "v1_procurement_preservation.json"), "ACT-01 preserved V1 procurement")
    assert "C11" in read_json("hardware/manufacturing/procurement_policy.json")["v2"]["holds"]
    print("PASS actuator pin/identity delta, exclusive population and package evidence; assembly/hardware held")
    enable_root = "reviews/codex/actuator_enable/"
    enable = read_json(enable_root + "packet_manifest.json")
    check_hashes(enable["input_sha256"], "enable preserved inputs")
    check_hashes(enable["artifact_sha256"], "enable captured artifacts")
    build = read_json(enable_root + "build_manifest.json")
    native = read_json(enable_root + "native_manifest.json")
    assert native["input_sha256"] == build["output_sha256"]
    check_hashes(build["output_sha256"], "enable source")
    check_hashes(native["output_sha256"], "enable native exports")
    check_hashes({enable_root + "build_candidate.py": build["builder_sha256"],
                  enable_root + "expected_contract.json": build["expected_contract_sha256"],
                  enable_root + "population_contract.json": build["population_contract_sha256"],
                  enable_root + "export_native.py": native["runner_sha256"]}, "enable provenance")
    for module_name, filename, function, record in [
            ("enable_verify", "verify_candidate.py", "collect", "validation.json"),
            ("enable_packages", "inspect_packages.py", "check", None)]:
        spec = importlib.util.spec_from_file_location(module_name, ROOT / enable_root / filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = getattr(module, function)()
        if record:
            assert result == read_json(enable_root + record)
    assert enable["live_electrical_delta"] == 0 and enable["live_copper_delta"] == 0
    assert not any(enable[k] for k in ["pcb_updated", "hardware_tested", "fabrication_approved", "assembly_variant_released"])
    print("PASS ACT-02 native delta and default-enable contract; interlock/hardware held")
    interlock_root = "reviews/codex/actuator_interlock/"
    interlock = read_json(interlock_root + "packet_manifest.json")
    check_hashes(interlock["input_sha256"], "interlock preserved circuit/software inputs")
    check_hashes(interlock["artifact_sha256"], "interlock prototype and observation artifacts")
    for name, expected in interlock["normalized_text_input_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest() == expected, name
    spec = importlib.util.spec_from_file_location("interlock_observation", ROOT / interlock_root / "verify_observability.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.collect() == read_json(interlock_root + "observability.json")
    tests = read_json(interlock_root + "test_results.json")
    check_hashes({interlock_root + "model.js": tests["model_sha256"],
                  interlock_root + "contract.json": tests["contract_sha256"],
                  interlock_root + "test_model.cjs": tests["test_runner_sha256"]}, "interlock test provenance")
    assert tests["failed"] == 0 and tests["passed"] == tests["tests"] and tests["tests"] >= 59
    assert not tests["hardware_tested"] and not tests["firmware_tested"]
    assert interlock["electrical_delta"] == 0 and interlock["copper_delta"] == 0
    assert not any(interlock[k] for k in ["parts_selected", "hardware_tested", "fabrication_approved", "native_commands_rerun"])
    print("PASS ACT-03 captured observability and behavioral test record; no circuit or hardware acceptance")
    latch_root = "reviews/codex/actuator_latch/"
    latch = read_json(latch_root + "packet_manifest.json")
    check_hashes(latch["input_sha256"], "latch preserved inputs")
    check_hashes(latch["artifact_sha256"], "latch candidate and checks")
    for module_name, filename, function, record in [
            ("latch_verify", "verify_candidate.py", "collect", "validation.json"),
            ("latch_packages", "inspect_packages.py", "check", None)]:
        spec = importlib.util.spec_from_file_location(module_name, ROOT / latch_root / filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = getattr(module, function)()
        if record:
            assert result == read_json(latch_root + record)
    assert latch["live_electrical_delta"] == 0 and latch["live_copper_delta"] == 0
    assert not any(latch[k] for k in ["hardware_tested", "pcb_updated", "fabrication_approved", "qualification_ports_implemented"])
    print("PASS ACT-04 isolated native latch and package evidence; timing and qualifications remain held")
    rail_root = "reviews/codex/rail_qualification/"
    rail = read_json(rail_root + "packet_manifest.json")
    check_hashes(rail["input_sha256"], "ACT-05 preserved candidate inputs")
    check_hashes(rail["artifact_sha256"], "ACT-05 screen, viewer and check artifacts")
    assert all(rail[k] == 0 for k in ["candidate_electrical_delta", "live_electrical_delta", "live_copper_delta"])
    assert not any(rail[k] for k in ["parts_selected", "hardware_tested", "fabrication_approved", "native_commands_rerun", "qualification_ports_implemented"])
    print("PASS ACT-05 portable screening evidence; circuit and qualification sources unchanged")
    supervisor_root = "reviews/codex/supervisor_comparison/"
    supervisor = read_json(supervisor_root + "packet_manifest.json")
    check_hashes(supervisor["input_sha256"], "ACT-06 preserved review/native inputs")
    check_hashes(supervisor["artifact_sha256"], "ACT-06 source, calculation and viewer artifacts")
    assert all(supervisor[k] == 0 for k in ["candidate_electrical_delta", "live_electrical_delta", "live_copper_delta"])
    assert not any(supervisor[k] for k in ["parts_selected", "hardware_tested", "fabrication_approved", "native_commands_rerun", "qualification_ports_implemented"])
    print("PASS ACT-06 portable comparison; no new circuit or permission driver")
    observation_root = "reviews/codex/observation_3v3/"
    observation = read_json(observation_root + "packet_manifest.json")
    check_hashes(observation["input_sha256"], "ACT-07 preserved inputs")
    check_hashes(observation["artifact_sha256"], "ACT-07 allocation and viewer artifacts")
    assert all(observation[k] == 0 for k in ["candidate_electrical_delta", "live_electrical_delta", "live_copper_delta"])
    assert not any(observation[k] for k in ["parts_selected", "hardware_tested", "fabrication_approved", "native_commands_rerun", "qualification_ports_implemented"])
    observer_power_root = "reviews/codex/observer_power/"
    observer_power = read_json(observer_power_root + "packet_manifest.json")
    check_hashes(observer_power["input_sha256"], "ACT-08 preserved circuit and review inputs")
    check_hashes(observer_power["artifact_sha256"], "ACT-08 calculation and viewer artifacts")
    assert all(observer_power[k] == 0 for k in ["candidate_electrical_delta", "live_electrical_delta", "live_copper_delta"])
    assert all(observer_power[k] is False for k in ["parts_selected", "hardware_tested", "fabrication_approved", "native_commands_rerun", "qualification_ports_implemented"])
    retention_root = "reviews/codex/observer_retention/"
    retention = read_json(retention_root + "packet_manifest.json")
    check_hashes(retention["input_sha256"], "ACT-09 preserved inputs")
    check_hashes(retention["artifact_sha256"], "ACT-09 architecture, request model and viewer")
    assert all(retention[k] == 0 for k in ["candidate_electrical_delta", "live_electrical_delta", "live_copper_delta"])
    assert all(retention[k] is False for k in ["parts_selected", "hardware_tested", "fabrication_approved", "native_commands_rerun", "qualification_ports_implemented"])
    isolation_root = "reviews/codex/oe_isolation/"
    isolation = read_json(isolation_root + "packet_manifest.json")
    check_hashes(isolation["input_sha256"], "ACT-10 preserved inputs")
    check_hashes(isolation["artifact_sha256"], "ACT-10 circuit proposal and OE screen")
    assert all(isolation[k] == 0 for k in ["candidate_electrical_delta", "live_electrical_delta", "live_copper_delta"])
    assert all(isolation[k] is False for k in ["parts_selected", "hardware_tested", "fabrication_approved", "native_commands_rerun", "qualification_ports_implemented", "partial_power_isolation_qualified", "source_timing_applicable_to_RC_edge"])
    portfolio = read_json("docs/portfolio/portfolio.json")
    assert portfolio["status"]["manufacturing_approved"] is False
    paths = list(portfolio["entrypoints"].values())
    paths += [asset["path"] for asset in portfolio["assets"]]
    paths += [p for result in portfolio["validated_results"] for p in result["evidence"]]
    for path in paths:
        assert (ROOT / path).is_file(), f"Missing portfolio artifact: {path}"
    pages = [ROOT / "README.md", ROOT / "docs/portfolio/README.md"]
    pages += list((ROOT / "docs/build").glob("*.md"))
    pages += list((ROOT / "docs/applications").glob("*.md"))
    pages += [ROOT / "firmware_v2/README.md", ROOT / "reviews/codex/imu_interface/README.md", ROOT / "reviews/codex/imu_placement/README.md", ROOT / "reviews/codex/imu_bias_filter/README.md"]
    pages += [ROOT / power_root / "README.md", ROOT / topology_root / "README.md", ROOT / input_root / "README.md", ROOT / leakage_root / "README.md", ROOT / capacitor_root / "README.md", *[ROOT / folder / "README.md" for folder in buck_roots], ROOT / actuator_root / "README.md", ROOT / enable_root / "README.md", ROOT / interlock_root / "README.md", ROOT / interlock_root / "RECEIVER_ACCEPTANCE.md"]
    pages += [ROOT / latch_root / "README.md", ROOT / latch_root / "TIMING.md"]
    pages += [ROOT / rail_root / "README.md", ROOT / rail_root / "QUALIFICATION.md"]
    pages += [ROOT / supervisor_root / "README.md", ROOT / supervisor_root / "RESULTS.md"]
    pages += [ROOT / observation_root / name for name in ["README.md", "RESULTS.md", "ACCEPTANCE.md"]]
    pages += [ROOT / observer_power_root / name for name in ["README.md", "RESULTS.md"]]
    pages += [ROOT / retention_root / name for name in ["README.md", "RESULTS.md"]]
    pages += [ROOT / isolation_root / name for name in ["README.md", "RESULTS.md"]]
    for page in pages:
        for target in re.findall(r"\]\(([^)]+)\)", page.read_text(encoding="utf-8-sig")):
            target = target.strip("<>").split("#", 1)[0]
            if not target or "://" in target:
                continue
            assert (page.parent / target).is_file(), f"Broken document link: {page.name}: {target}"
    print(f"PASS portfolio artifacts and {len(pages)} linked guide pages")
    print("Scope: portable evidence and software packaging only; fabrication/hardware gates remain open.")

if __name__ == "__main__":
    main()
