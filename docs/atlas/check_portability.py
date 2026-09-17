"""Check V1 atlas reproducibility without ignored build artifacts or KiCad.

Runs a source-only checkout simulation in a temporary directory under docs/atlas.
No original source files are moved, hidden, removed, or modified.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
ATLAS = (ROOT / "docs/atlas").resolve()
REPORT = "pm/data/connectors.json"
GENERATOR = "docs/atlas/generate_atlas.py"


def main():
    report = json.loads((ROOT / REPORT).read_text(encoding="utf-8"))
    paths = {entry["path"] for entry in report["sources"]}
    paths.update(connector["doc"] for connector in report["connectors"])
    paths.update((GENERATOR, REPORT, "docs/atlas/README.md"))
    assert not any("/_build/" in path for path in paths), "Atlas still depends on ignored build output"
    with tempfile.TemporaryDirectory(prefix=".portability-", dir=ATLAS) as temporary:
        checkout = Path(temporary).resolve()
        # Verify the recursive-cleanup target is inside this task-owned directory.
        assert checkout.parent == ATLAS and checkout.name.startswith(".portability-")
        for relative in sorted(paths):
            destination = (checkout / relative).resolve()
            assert checkout in destination.parents, f"Path escapes isolated checkout: {relative}"
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)
        assert not (checkout / "hardware/kicad/_build").exists()
        command = [sys.executable, str(checkout / GENERATOR), "--check"]
        result = subprocess.run(command, cwd=checkout, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        print("PASS: source-only checkout verifies with no _build directory or CAD tools.")
        print(result.stdout.strip())
        snapshot = checkout / "docs/atlas/evidence/v1-netmap.json"
        snapshot.write_bytes(snapshot.read_bytes() + b"\n")
        changed = subprocess.run(command, cwd=checkout, capture_output=True, text=True)
        assert changed.returncode != 0 and "Preserved V1 evidence differs" in changed.stderr, changed.stderr
        print("PASS: a modified snapshot is rejected by its recorded integrity check.")


if __name__ == "__main__":
    main()
