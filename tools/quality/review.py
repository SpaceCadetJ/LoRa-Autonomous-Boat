#!/usr/bin/env python3
"""Read-only KiCad review runner. Never invokes a CAD generator or writes design inputs.

Requires Python 3.10+ and KiCad CLI 9. Results and temporary project copies stay in
the requested review output directory. See docs/build/REVIEW_WORKFLOW.md.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
PROJECTS = {
    "v1": ("hardware/kicad", "LoRa_Boat_Controller"),
    "v2": ("hardware/kicad_v2", "LoRa_Boat_Controller_V2"),
}
SOURCE_EXTENSIONS = {".kicad_sch", ".kicad_sym", ".kicad_pro", ".kicad_dru", ".kicad_pcb", ".kicad_mod"}
REVIEW_OUTPUT_ROOTS = ("reviews/codex/professionalization", "reviews/codex/publication")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf8")


def canonical_netlist(path):
    """Keep all pins, including isolated pins, without depending on net/UUID names."""
    tree = ET.parse(path).getroot()
    refs = {}
    components = {}
    for c in tree.find("components"):
        properties = {p.get("name"): p.get("value") for p in c.findall("property")}
        ref = properties.get("Allegro_RefDes") or c.get("ref")
        if ref in components:
            raise ValueError(f"Duplicate component identity: {ref}")
        refs[c.get("ref")] = ref
        components[ref] = {"value": c.findtext("value", ""), "footprint": c.findtext("footprint", "")}
    groups, memberships = [], []
    net_names = {}
    for net in tree.find("nets"):
        nodes = sorted([[refs[n.get("ref")], n.get("pin")] for n in net.findall("node")])
        if not nodes:
            raise ValueError("Empty exported net")
        key = json.dumps(nodes, separators=(",", ":"))
        if key in net_names:
            raise ValueError("Duplicate pin group in exported netlist")
        net_names[key] = net.get("name")
        groups.append(nodes)
        memberships.extend(tuple(n) for n in nodes)
    duplicates = [list(p) for p, count in Counter(memberships).items() if count != 1]
    if duplicates:
        raise ValueError(f"Repeated physical pins: {duplicates}")
    return {"components": dict(sorted(components.items())), "pin_groups": sorted(groups),
            "net_names": net_names, "pin_count": len(memberships)}


def compare_netlists(before, after):
    flatten = lambda d: {json.dumps(g, separators=(",", ":")) for g in d["pin_groups"]}
    old, new = flatten(before), flatten(after)
    before_refs, after_refs = before["components"], after["components"]
    changed_components = {r: {"before": before_refs[r], "after": after_refs[r]}
                          for r in before_refs.keys() & after_refs.keys() if before_refs[r] != after_refs[r]}
    result = {"missing_groups": [json.loads(x) for x in sorted(old - new)],
              "added_groups": [json.loads(x) for x in sorted(new - old)],
              "missing_components": sorted(before_refs.keys() - after_refs.keys()),
              "added_components": sorted(after_refs.keys() - before_refs.keys()),
              "changed_components": changed_components,
              "net_name_changes": [{"pins": json.loads(g), "before": before["net_names"][g], "after": after["net_names"][g]}
                                   for g in sorted(old & new) if before["net_names"][g] != after["net_names"][g]],
              "before_pins": before["pin_count"], "after_pins": after["pin_count"]}
    result["passed"] = not any(result[k] for k in ("missing_groups", "added_groups", "missing_components", "added_components", "changed_components"))
    return result


def parse_sexpr(text):
    """Small structural reader for KiCad files; quoted parentheses remain strings."""
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text)
    stack, roots = [], []
    for token in tokens:
        if token == "(":
            node = []
            (stack[-1] if stack else roots).append(node)
            stack.append(node)
        elif token == ")":
            if not stack:
                raise ValueError("Unbalanced closing parenthesis")
            stack.pop()
        else:
            if not stack:
                raise ValueError("Atom outside an expression")
            stack[-1].append(json.loads(token) if token.startswith('"') else token)
    if stack or len(roots) != 1:
        raise ValueError("Incomplete or multiple root expressions")
    return roots[0]


def child(node, name):
    return next((n for n in node if isinstance(n, list) and n and n[0] == name), None)


def coordinate_bounds(path):
    """Check actual primitive anchors/box corners. This is not text/collision QA."""
    tree = parse_sexpr(Path(path).read_text(encoding="utf8"))
    paper = child(tree, "paper")
    sizes = {"A5": (210, 148), "A4": (297, 210), "A3": (420, 297), "A2": (594, 420), "A1": (841, 594), "A0": (1189, 841), "USLetter": (279.4, 215.9), "USLegal": (355.6, 215.9), "USLedger": (431.8, 279.4)}
    if not paper:
        raise ValueError("No paper size found")
    if paper[1] == "User":
        width, height = float(paper[2]), float(paper[3])
    elif paper[1] in sizes:
        width, height = sizes[paper[1]]
    else:
        raise ValueError(f"Unsupported paper size: {paper}")
    if "portrait" in paper:
        width, height = height, width
    points = []
    for node in tree[1:]:
        if not isinstance(node, list) or not node:
            continue
        kind = node[0]
        if kind in {"symbol", "sheet", "text", "text_box", "label", "global_label", "hierarchical_label", "junction", "no_connect"}:
            at = child(node, "at")
            if at:
                x, y = float(at[1]), float(at[2])
                points.append((kind, x, y))
                size = child(node, "size") if kind in {"sheet", "text_box"} else None
                if size:
                    points.append((kind + " corner", x + float(size[1]), y + float(size[2])))
        if kind in {"wire", "polyline", "bus"}:
            pts = child(node, "pts")
            if pts:
                points.extend((kind, float(p[1]), float(p[2])) for p in pts[1:] if isinstance(p, list) and p[0] == "xy")
        if kind in {"rectangle", "arc", "circle"}:
            for name in ("start", "end", "mid", "center"):
                point = child(node, name)
                if point:
                    points.append((kind, float(point[1]), float(point[2])))
    outside = [{"kind": k, "x_mm": x, "y_mm": y} for k, x, y in points if not (0 <= x <= width and 0 <= y <= height)]
    return {"page_mm": [width, height], "checked_anchors_and_corners": len(points), "outside": outside,
            "passed": bool(points) and not outside,
            "limitation": "Does not measure text glyph extents, symbol body extents, overlap, or reading order; visual inspection is required."}


def summarize_erc(data):
    violations = [v for s in data.get("sheets", []) for v in s.get("violations", [])]
    if "sheets" not in data:
        raise ValueError("ERC report missing sheets")
    return {"violations": len(violations), "by_severity": dict(Counter(v.get("severity", "unknown") for v in violations)), "passed": not violations}


def summarize_drc(data):
    required = {"violations", "unconnected_items", "schematic_parity"}
    if not required <= data.keys():
        raise ValueError("DRC report does not include complete connectivity/parity sections")
    violations = data["violations"]
    counts = dict(Counter(v.get("type", "unknown") + ":" + v.get("severity", "unknown") for v in violations))
    # No exclusions/allow-list convert known failures to success. Production is strict.
    return {"errors": sum(v.get("severity") == "error" for v in violations),
            "warnings": sum(v.get("severity") == "warning" for v in violations),
            "total_violations": len(violations), "unconnected": len(data["unconnected_items"]),
            "schematic_parity": len(data["schematic_parity"]), "counts": counts,
            "passed": not (violations or data["unconnected_items"] or data["schematic_parity"])}


def evaluate_gates(checks):
    """Review acceptance is intentionally distinct from manufacturing acceptance."""
    review = bool(checks) and all(c["passed"] for c in checks if c["gate"] in {"review", "both"})
    fabrication = review and all(c["passed"] for c in checks if c["gate"] in {"fabrication", "both"})
    return {"review": review, "fabrication": fabrication}


def find_cli(explicit=None):
    candidates = [explicit, os.environ.get("KICAD_CLI"), shutil.which("kicad-cli"), shutil.which("kicad-cli.exe")]
    if os.environ.get("LOCALAPPDATA"):
        candidates.append(str(Path(os.environ["LOCALAPPDATA"]) / "Programs/KiCad/9.0/bin/kicad-cli.exe"))
    if os.environ.get("ProgramFiles"):
        candidates.append(str(Path(os.environ["ProgramFiles"]) / "KiCad/9.0/bin/kicad-cli.exe"))
    return next((str(Path(c)) for c in candidates if c and Path(c).is_file()), None)


def active_cad_input(relative):
    """Keep active CAD and project libraries, excluding local/session derivatives.

    Use explicit reserved names rather than Git's ignore list: an accidental
    ignore rule must not remove an active schematic or footprint from review.
    """
    for directory in relative.parts[:-1]:
        name = directory.casefold()
        if (name in {"tools", "_build", "backups", "cache", ".cache", "__pycache__", ".git"}
                or name.startswith("_backup_") or name.endswith("-backups")):
            return False
    name = relative.name.casefold()
    if name.startswith(("_autosave-", "~", ".~lock")):
        return False
    return relative.suffix in SOURCE_EXTENSIONS or relative.name in {"fp-lib-table", "sym-lib-table"}


def allowed_review_output(repo, out):
    return any((repo / directory) in out.parents for directory in REVIEW_OUTPUT_ROOTS)


def snapshot_inputs(repo, out):
    manifest, unstable = {}, []
    for folder, _ in PROJECTS.values():
        for source in sorted((repo / folder).rglob("*")):
            if not source.is_file() or not active_cad_input(source.relative_to(repo / folder)):
                continue
            rel = source.relative_to(repo).as_posix()
            raw = source.read_bytes()
            target = out / "inputs" / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            manifest[rel] = hashlib.sha256(raw).hexdigest()
            if sha256(source) != manifest[rel]:
                unstable.append(rel)
    return manifest, unstable


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=ROOT / "reviews/codex/professionalization/quality-runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    parser.add_argument("--profile", choices=["review", "fabrication"], default="review")
    parser.add_argument("--design", choices=["both", "v1", "v2"], default="both")
    parser.add_argument("--kicad-cli")
    parser.add_argument("--baseline-dir", type=Path, default=ROOT / "tools/quality/baselines")
    args = parser.parse_args(argv)
    repo, out = args.repo.resolve(), args.output.resolve()
    # Prevent review output from being pointed at a CAD/source directory by mistake.
    if not allowed_review_output(repo, out):
        parser.error("--output must be a subdirectory of " + " or ".join(REVIEW_OUTPUT_ROOTS))
    if out.exists() and any(out.iterdir()):
        parser.error("--output must be empty; use a fresh directory so old reports cannot be mistaken for this run")
    out.mkdir(parents=True, exist_ok=True)
    result = {"schema": 1, "generated_at": datetime.now(timezone.utc).isoformat(), "profile": args.profile,
              "purpose": "Documentation/layout review is not fabrication approval", "checks": [], "commands": [], "designs": {}}
    checks = result["checks"]

    def check(name, passed, detail, gate="review", evidence=None):
        checks.append({"name": name, "passed": bool(passed), "gate": gate, "detail": detail, "evidence": evidence or []})

    def run(command):
        completed = subprocess.run([str(v) for v in command], cwd=repo, capture_output=True, text=True, errors="replace", timeout=300)
        result["commands"].append({"argv": [str(v) for v in command], "exit_code": completed.returncode,
                                   "stdout": completed.stdout, "stderr": completed.stderr})
        if completed.returncode:
            raise RuntimeError(f"Command failed ({completed.returncode}): {command}\n{completed.stderr}")
        return completed.stdout.strip()

    try:
        result["head"] = run(["git", "rev-parse", "HEAD"])
        result["working_tree"] = run(["git", "status", "--short"])
        manifest, unstable = snapshot_inputs(repo, out)
        result["input_manifest"] = manifest
        check("Stable input capture", not unstable, {"changed_during_copy": unstable}, "both")
        cli = find_cli(args.kicad_cli)
        if not cli:
            raise RuntimeError("KiCad CLI not found; set KICAD_CLI or --kicad-cli. Checks were not silently skipped.")
        version = run([cli, "version"])
        result["kicad_version"] = version
        check("KiCad major version", version.startswith("9."), version, "both")
        if not version.startswith("9."):
            raise RuntimeError("This acceptance baseline requires KiCad 9.")
        selected = PROJECTS if args.design == "both" else {args.design: PROJECTS[args.design]}
        for design, (folder, stem) in selected.items():
            design_out = out / design
            design_out.mkdir(exist_ok=True)
            source = out / "inputs" / folder / stem
            evidence = lambda name: (design_out / name).relative_to(repo).as_posix()
            netlist = design_out / "netlist.xml"
            run([cli, "sch", "export", "netlist", "--format", "kicadxml", "--output", netlist, str(source) + ".kicad_sch"])
            current = canonical_netlist(netlist)
            baseline_path = args.baseline_dir / (design + ".json")
            baseline = read_json(baseline_path)
            comparison = compare_netlists(baseline["netlist"], current)
            write_json(design_out / "connectivity.json", comparison)
            check(design + " source connectivity/component preservation", comparison["passed"],
                  {"parts": len(current["components"]), "pins": current["pin_count"], "baseline_sha256": sha256(baseline_path),
                   "net_name_changes": len(comparison["net_name_changes"])}, "both", [evidence("connectivity.json")])
            protected = baseline.get("protected_files", {})
            changed = [p for p, h in protected.items() if manifest.get(p) != h]
            check(design + " PCB/project preservation", not changed, {"changed": changed}, "review")
            erc_path, drc_path = design_out / "erc.json", design_out / "drc.json"
            run([cli, "sch", "erc", "--severity-all", "--format", "json", "--output", erc_path, str(source) + ".kicad_sch"])
            erc = summarize_erc(read_json(erc_path))
            check(design + " ERC", erc["passed"], erc, "both", [evidence("erc.json")])
            bounds = {p.name: coordinate_bounds(p) for p in sorted(source.parent.glob("*.kicad_sch"))}
            write_json(design_out / "coordinate_bounds.json", bounds)
            check(design + " page-coordinate bounds", all(b["passed"] for b in bounds.values()), bounds,
                  "both", [evidence("coordinate_bounds.json")])
            svg_dir = design_out / "svg"
            svg_dir.mkdir(exist_ok=True)
            run([cli, "sch", "export", "svg", "--output", str(svg_dir) + os.sep, str(source) + ".kicad_sch"])
            svg_files = sorted(svg_dir.glob("*.svg"))
            check(design + " rendered sheet coverage", len(svg_files) == len(bounds),
                  {"expected_sheets": len(bounds), "svg_files": [p.name for p in svg_files]}, "both")
            run([cli, "pcb", "drc", "--severity-all", "--schematic-parity", "--format", "json", "--output", drc_path, str(source) + ".kicad_pcb"])
            drc = summarize_drc(read_json(drc_path))
            check(design + " complete PCB DRC/connectivity/parity", drc["passed"], drc,
                  "fabrication", [evidence("drc.json")])
            # These gates need an actual engineering/visual review record. A passing
            # renderer or coordinate check is deliberately insufficient evidence.
            check(design + " visual and manufacturing acceptance", False,
                  "Pending explicit review of text extents/overlap, pin labeling, assembly data, drill provenance and fabrication package at these hashes. This runner does not issue that approval.",
                  "fabrication")
            result["designs"][design] = {"erc": erc, "drc": drc, "parts": len(current["components"]), "pins": current["pin_count"]}
        changed_during_run = [p for p, h in manifest.items() if not (repo / p).is_file() or sha256(repo / p) != h]
        check("Working inputs unchanged during review", not changed_during_run, {"changed": changed_during_run}, "both")
        copy_changes = [p for p, h in manifest.items() if sha256(out / "inputs" / p) != h]
        check("KiCad did not modify captured design inputs", not copy_changes, {"changed": copy_changes}, "both")
    except Exception as error:
        check("Runner completed all requested checks", False, str(error), "both")
        result["error"] = str(error)
    result["gates"] = evaluate_gates(checks)
    result["verdict"] = "PASS" if result["gates"][args.profile] else "FAIL"
    result["output_manifest"] = {p.relative_to(out).as_posix(): sha256(p) for p in sorted(out.rglob("*"))
                                 if p.is_file() and "inputs" not in p.relative_to(out).parts and p.name not in {"review.json", "REVIEW.md"}}
    write_json(out / "review.json", result)
    lines = ["# Quality review", "", f"Generated: {result['generated_at']}", "",
             f"Requested gate: **{args.profile} — {result['verdict']}**. Fabrication: **{'PASS' if result['gates']['fabrication'] else 'NOT APPROVED'}**.", "",
             "| Check | Gate | Result |", "| --- | --- | --- |"]
    lines += [f"| {c['name']} | {c['gate']} | {'PASS' if c['passed'] else 'FAIL / OPEN'} |" for c in checks]
    lines += ["", "Full commands, counts, input/output hashes and limitations: [review.json](review.json).",
              "", "No generator was run and all CLI operations used isolated copies. Coordinate bounds do not prove legible text, absence of overlap, correct part selection or safe operation."]
    (out / "REVIEW.md").write_text("\n".join(lines) + "\n", encoding="utf8")
    print(json.dumps({"verdict": result["verdict"], "gates": result["gates"], "designs": result["designs"], "report": str(out / "review.json")}, indent=2))
    return 0 if result["gates"][args.profile] else 1


if __name__ == "__main__":
    raise SystemExit(main())
