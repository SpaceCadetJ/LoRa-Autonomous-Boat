#!/usr/bin/env python3
"""Export the existing V1/V2 schematics to review PDFs/SVGs; never regenerate CAD."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
DESIGNS = {
    "v1": ("hardware/kicad", "LoRa_Boat_Controller"),
    "v2": ("hardware/kicad_v2", "LoRa_Boat_Controller_V2"),
}

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", default=os.environ.get("KICAD_CLI") or shutil.which("kicad-cli"))
    args = parser.parse_args()
    cli = args.cli or str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/KiCad/9.0/bin/kicad-cli.exe")
    if not Path(cli).is_file():
        parser.error("KiCad CLI not found; supply --cli with its full path")
    inputs = {p.relative_to(ROOT).as_posix(): digest(p) for directory, _ in DESIGNS.values()
              for p in (ROOT / directory).glob("*.kicad_*")
              if p.is_file() and p.suffix in {".kicad_sch", ".kicad_pcb", ".kicad_pro", ".kicad_sym", ".kicad_dru"}}
    output = ROOT / "docs/img"
    output.mkdir(exist_ok=True)
    commands, published = [], []
    with tempfile.TemporaryDirectory(prefix="lora-schematic-export-") as temp:
        staging = Path(temp)
        for version, (directory, stem) in DESIGNS.items():
            source = ROOT / directory / (stem + ".kicad_sch")
            pdf = staging / (version + "_schematic.pdf")
            svg_dir = staging / version
            svg_dir.mkdir()
            for fmt, dest in (("pdf", str(pdf)), ("svg", str(svg_dir) + os.sep)):
                cmd = [cli, "sch", "export", fmt, "--output", dest, str(source)]
                commands.append(cmd)
                subprocess.run(cmd, check=True)
            svgs = sorted(svg_dir.glob("*.svg"))
            expected = len(list((ROOT / directory).glob("*.kicad_sch")))
            if len(svgs) != expected:
                raise RuntimeError(f"{version}: expected {expected} SVG sheets, found {len(svgs)}")
            published.append((pdf, output / pdf.name))
            for svg in svgs:
                sheet = svg.stem.removeprefix(stem + "-")
                if sheet == stem:
                    sheet = "Root" if version == "v1" else "root"
                published.append((svg, output / (version + "_sch_" + sheet + ".svg")))
        changed = [p for p, h in inputs.items() if digest(ROOT / p) != h]
        if changed:
            raise RuntimeError("CAD changed during export: " + ", ".join(changed))
        for source, dest in published:
            # Publish complete files; a browser/OneDrive reader may briefly lock
            # an old export. Never leave a truncated destination after that race.
            temporary = dest.with_name(dest.name + ".pending")
            shutil.copyfile(source, temporary)
            for attempt in range(5):
                try:
                    os.replace(temporary, dest)
                    break
                except OSError:
                    # Some Windows viewers permit writes but deny replacement.
                    # Copy the complete staged bytes and verify below instead.
                    try:
                        shutil.copyfile(temporary, dest)
                        if digest(dest) != digest(temporary):
                            raise RuntimeError("Published hash mismatch: " + str(dest))
                        temporary.unlink()
                        break
                    except OSError:
                        pass
                    if attempt == 4:
                        raise
                    time.sleep(.5)
    result = {"generated_at": datetime.now(timezone.utc).isoformat(),
              "kicad_version": subprocess.check_output([cli, "version"], text=True).strip(),
              "input_sha256": inputs, "commands": commands,
              "output_sha256": {p.relative_to(ROOT).as_posix(): digest(p) for _, p in published},
              "scope": "Rendering only; visual review and electrical acceptance are separate checks."}
    (output / "schematic_export_manifest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf8")
    print(json.dumps({"files_exported": len(published), "CAD_unchanged": True}))

if __name__ == "__main__":
    main()
