#!/usr/bin/env python3
"""Run V2 'sch' only in an isolated copy and prove PCB/BOM/project preservation.

An explicit regression tool, never implicitly called by the read-only review runner.
The working CAD is read for copying/hashing; only the scratch copy is generated.
"""
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import subprocess
import sys
from review import ROOT, sha256, write_json


def main():
    out = ROOT / "reviews/codex/professionalization/generator-guard" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    sandbox = out / "copy"
    for folder in ("hardware/kicad", "hardware/kicad_v2"):
        shutil.copytree(ROOT / folder, sandbox / folder,
                        ignore=shutil.ignore_patterns("_build", "__pycache__", "*-backups", "*.lck", "*.prl"))
    (sandbox / "docs").mkdir(parents=True)
    shutil.copy2(ROOT / "docs/BOM_V2.csv", sandbox / "docs/BOM_V2.csv")
    protected = ["hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_pcb",
                 "hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_pro", "docs/BOM_V2.csv"]
    before = {p: sha256(sandbox / p) for p in protected}
    working_before = {p: sha256(ROOT / p) for p in protected}
    script = sandbox / "hardware/kicad_v2/tools/gen_v2.py"
    command = [sys.executable, str(script), "sch"]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    completed = subprocess.run(command, cwd=sandbox, capture_output=True, text=True, errors="replace", timeout=300, env=env)
    after = {p: sha256(sandbox / p) if (sandbox / p).exists() else None for p in protected}
    working_after = {p: sha256(ROOT / p) for p in protected}
    changed = [p for p in protected if before[p] != after[p]]
    original_changed = [p for p in protected if working_before[p] != working_after[p]]
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "command": command,
              "generator_sha256": sha256(script), "exit_code": completed.returncode,
              "stdout": completed.stdout, "stderr": completed.stderr,
              "protected_before": before, "protected_after": after, "changed_in_copy": changed,
              "working_inputs_changed_during_test": original_changed,
              "passed": completed.returncode == 0 and not changed and not original_changed,
              "scope": "Explicitly tests only gen_v2.py sch; generated schematic correctness is assessed separately by review.py."}
    write_json(out / "dispatch.json", report)
    print(str(out / "dispatch.json"))
    print("PASS" if report["passed"] else "FAIL", "copy changes:", changed, "original changes:", original_changed)
    if completed.returncode:
        print(completed.stderr)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
