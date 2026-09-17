#!/usr/bin/env python3
"""Explicitly create baseline JSON from the pre-edit, independently exported netlists.

Never called by review.py or CI. Refuses to overwrite baselines: electrical baseline
changes require a separately reviewed change, not automatic acceptance of current CAD.
"""
from pathlib import Path
import sys
from review import ROOT, PROJECTS, canonical_netlist, read_json, sha256, write_json


def main():
    source = ROOT / "reviews/codex/professionalization/quality-baseline"
    manifest = read_json(source / "manifest.json")
    hashes = {f["path"]: f["sha256"] for f in manifest["files"]}
    for entry in manifest["files"]:
        if not entry["unchanged"] or sha256(source / entry["path"]) != entry["sha256"]:
            raise RuntimeError("Pre-edit input changed: " + entry["path"])
    destinations = [ROOT / "tools/quality/baselines" / (design + ".json") for design in PROJECTS]
    if any(p.exists() for p in destinations):
        raise RuntimeError("Baseline already exists. Do not automatically replace an electrical acceptance baseline.")
    for (design, (folder, stem)), target in zip(PROJECTS.items(), destinations):
        xml = source / (design + ".netlist.xml")
        protected = {p: h for p, h in hashes.items() if p.startswith(folder + "/") and Path(p).suffix in {".kicad_pcb", ".kicad_pro", ".kicad_dru"}}
        data = {"schema": 1, "captured_at": manifest["captured_at"], "head_at_capture": manifest["revision"],
                "scope": "Pre-professionalization working files, preserved before layout edits; HEAD alone is not the full input identity.",
                "exported_netlist": {"path": xml.relative_to(ROOT).as_posix(), "sha256": sha256(xml)},
                "input_hashes": {p: h for p, h in hashes.items() if p.startswith(folder + "/")},
                "protected_files": protected, "netlist": canonical_netlist(xml)}
        write_json(target, data)
        print(design, len(data["netlist"]["components"]), "parts", data["netlist"]["pin_count"], "pins", target)


if __name__ == "__main__":
    main()
