#!/usr/bin/env python3
"""Build V2 Stage A only: checked pins, inactive actuators, no hardware access."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
V2 = ROOT / "firmware_v2"
IMAGE = "v2_stage_a_unqualified"
SOURCES = ["firmware_v2/src/main.c", "firmware/Core/Src/system_stm32f4xx.c",
           "firmware/Core/Startup/startup_stm32f446retx.s"]
LINKER = "firmware/STM32F446RETX_FLASH.ld"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pin_contract(root=ROOT):
    contract = json.loads((root / "firmware_v2/board_contract.json").read_text())
    if contract.get("schema") != 1 or contract.get("target") != "STM32F446RET6":
        raise ValueError("Stage A requires schema 1 and STM32F446RET6")
    evidence = json.loads((root / contract["schematic_evidence"]).read_text())
    schematic_inputs = {p: h for p, h in evidence["input_manifest"].items()
                        if p.startswith("hardware/kicad_v2/") and p.endswith((".kicad_sch", ".kicad_sym"))}
    if len(schematic_inputs) < 8:
        raise ValueError("Incomplete schematic input evidence")
    for path, expected in schematic_inputs.items():
        if digest(root / path) != expected:
            raise ValueError("Schematic changed; review the diagnostic pin contract: " + path)
    xml_path = root / contract["netlist"]
    relative = xml_path.relative_to((root / contract["schematic_evidence"]).parent).as_posix()
    if digest(xml_path) != evidence["output_manifest"][relative]:
        raise ValueError("Pin netlist differs from its native export record")
    netlist = ET.parse(xml_path)
    for name, pin in contract["pins"].items():
        matches = [(net, node) for net in netlist.findall(".//nets/net")
                   for node in net.findall("node")
                   if node.get("ref") == "U1" and node.get("pin") == pin["pad"]]
        if len(matches) != 1:
            raise ValueError("Missing or ambiguous MCU pad: " + name)
        net, node = matches[0]
        members = [(n.get("ref"), n.get("pin")) for n in net.findall("node")]
        if (node.get("pinfunction") != pin["gpio"] or net.get("name") != pin["net"]
                or tuple(pin["peer"]) not in members):
            raise ValueError("Diagnostic pin does not match schematic: " + name)
    # Stage A supports only the reviewed output set; SWD must remain untouched.
    expected = {"ESC": "PC6", "SERVO": "PA8", "HEARTBEAT": "PC1", "FIX": "PC2",
                "MARKER": "PC3", "SWDIO": "PA13", "SWCLK": "PA14"}
    if {k: v["gpio"] for k, v in contract["pins"].items()} != expected:
        raise ValueError("Stage A GPIO set changed; review implementation before building")
    modes = {"ESC": "output_low", "SERVO": "output_low", "FIX": "output_low",
             "HEARTBEAT": "diagnostic_led", "MARKER": "diagnostic_led",
             "SWDIO": "reset_state", "SWCLK": "reset_state"}
    if {k: v["mode"] for k, v in contract["pins"].items()} != modes:
        raise ValueError("Stage A pin modes changed; SWD must remain untouched")
    return contract, schematic_inputs


def inputs(contract, schematic_inputs):
    paths = set(SOURCES + [LINKER, "firmware/tools/build_v1.py", "firmware_v2/tools/build.py",
                          "firmware_v2/board_contract.json", contract["netlist"], contract["schematic_evidence"]])
    paths.update(schematic_inputs)
    paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT / "firmware/Drivers/CMSIS").rglob("*") if p.is_file())
    return {p: digest(ROOT / p) for p in sorted(paths)}


def tools(explicit):
    spec = importlib.util.spec_from_file_location("preserved_builder", ROOT / "firmware/tools/build_v1.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper.find_tools(explicit), helper.CPU


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["check", "build"])
    parser.add_argument("--toolchain")
    parser.add_argument("--out", type=Path, default=V2 / "build/stage_a")
    args = parser.parse_args()
    contract, schematic_inputs = pin_contract()
    if args.action == "check":
        print("PASS Stage A contract: 7 MCU pins and preserved schematic/export hashes; hardware unqualified")
        return
    out = args.out.resolve()
    allowed = (V2 / "build").resolve()
    if out == allowed or allowed not in out.parents:
        raise ValueError("--out must be a subdirectory of firmware_v2/build")
    if out.exists() and any(out.iterdir()):
        raise ValueError("Use an empty output directory to avoid stale firmware artifacts")
    found, cpu = tools(args.toolchain)
    before = inputs(contract, schematic_inputs)
    out.mkdir(parents=True, exist_ok=True)
    report = {"schema": 1, "stage": "A", "status": "building", "target": contract["target"],
              "created_utc": datetime.now(timezone.utc).isoformat(), "input_sha256": before,
              "hardware_access": False, "actuator_control": False, "operational_release": False,
              "load_address": "0x08000000", "commands": [], "artifact_sha256": {}}
    report["compiler"] = subprocess.check_output([str(found["gcc"]), "--version"], text=True).splitlines()[0]
    try:
        header = ["/* Generated from the validated Stage A contract. */"]
        for name, pin in contract["pins"].items():
            if pin["mode"] != "reset_state":
                header += [f"#define {name}_PORT GPIO{pin['gpio'][1]}", f"#define {name}_PIN {pin['gpio'][2:]}u"]
        (out / "board_pins.h").write_text("\n".join(header) + "\n")
        def run(argv):
            argv = [str(x) for x in argv]
            result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, errors="replace")
            report["commands"].append({"argv": argv, "exit_code": result.returncode,
                                       "stdout": result.stdout, "stderr": result.stderr})
            if result.returncode:
                raise RuntimeError(result.stdout + result.stderr)
            return result.stdout
        flags = cpu + ["-std=c11", "-Og", "-g3", "-Wall", "-Wextra", "-Werror", "-DSTM32F446xx",
                       "-ffunction-sections", "-fdata-sections", "-ffile-prefix-map=" + str(ROOT) + "=repo",
                       "-ffile-prefix-map=" + str(out) + "=build", "-I" + str(out),
                       "-Ifirmware/Drivers/CMSIS/Device/ST/STM32F4xx/Include", "-Ifirmware/Drivers/CMSIS/Include"]
        objects = []
        for i, source in enumerate(SOURCES):
            obj = out / f"source_{i}.o"
            run([found["gcc"], *flags, *(["-x", "assembler-with-cpp"] if source.endswith(".s") else []),
                 "-c", source, "-o", obj])
            objects.append(obj)
        elf = out / (IMAGE + ".elf")
        run([found["gcc"], *cpu, "-T" + LINKER, "--specs=nano.specs", "--specs=nosys.specs",
             "-Wl,--gc-sections", "-Wl,--print-memory-usage", "-Wl,-Map=" + str(out / (IMAGE + ".map")),
             *objects, "-Wl,--start-group", "-lc", "-lm", "-Wl,--end-group", "-o", elf])
        for extension, fmt in [("bin", "binary"), ("hex", "ihex")]:
            run([found["objcopy"], "-O", fmt, elf, out / (IMAGE + "." + extension)])
        report["size"] = run([found["size"], elf])
        raw = (out / (IMAGE + ".bin")).read_bytes()
        stack, reset = struct.unpack_from("<II", raw)
        if not (8 <= len(raw) <= 512 * 1024 and 0x20000000 < stack <= 0x20020000 and stack % 8 == 0
                and reset & 1 and 0x08000000 <= (reset & ~1) < 0x08000000 + len(raw)):
            raise ValueError("Image/vector memory checks failed")
        if before != inputs(contract, schematic_inputs):
            raise ValueError("Sources changed during build")
        report.update(status="build_pass_unqualified", binary_bytes=len(raw), initial_stack=hex(stack), reset_vector=hex(reset),
                      artifact_sha256={p.name: digest(p) for p in out.glob(IMAGE + ".*")})
    except Exception as error:
        report.update(status="build_failed", error=str(error), artifact_sha256={})
        raise
    finally:
        (out / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ["status", "binary_bytes", "hardware_access", "actuator_control"]}))
    print("Artifacts: " + str(out))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError, KeyError) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        sys.exit(1)
