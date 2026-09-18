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
    pages += [ROOT / "firmware_v2/README.md", ROOT / "reviews/codex/imu_interface/README.md"]
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
