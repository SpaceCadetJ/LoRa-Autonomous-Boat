#!/usr/bin/env python3
"""Build the preserved V1 sources without CubeMX, downloads, or hardware access.

Python 3.9+; standard library only. This is an engineering reconstruction of the
missing build recipe, not proof of equivalence to an original deployed image.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
from datetime import datetime, timezone

FW = Path(__file__).resolve().parents[1]
ROOT = FW.parent
DEFAULT_OUT = FW / "Debug" / "reproducible_v1"
IMAGE = "boat_v1_unqualified"
LINKER = "STM32F446RETX_FLASH.ld"
INCLUDES = ["Core/Inc", "Drivers/STM32F4xx_HAL_Driver/Inc",
            "Drivers/STM32F4xx_HAL_Driver/Inc/Legacy",
            "Drivers/CMSIS/Device/ST/STM32F4xx/Include", "Drivers/CMSIS/Include"]
CPU = ["-mcpu=cortex-m4", "-mthumb", "-mfpu=fpv4-sp-d16", "-mfloat-abi=hard"]
WARNINGS = [
    "UNQUALIFIED V1 reconstruction; no device has been programmed or bench-tested.",
    "V1 has no link-loss failsafe or explicit arming; keep actuators disconnected.",
    "V1 PCB header labels and firmware motor/rudder names are reversed.",
    "CubeMX TIM3 initial pulse is 1500; current C initializes it to 1000.",
    "This build is not approved for V2 hardware or deployment.",
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs():
    paths = []
    for folder in (FW / "Core", FW / "Drivers"):
        paths.extend(p for p in folder.rglob("*") if p.is_file())
    paths.extend([FW / LINKER, FW / "BoatTHISTIMEITSDIFFERENT.ioc", Path(__file__)])
    return {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(paths)}


def sources():
    paths = sorted((FW / "Core" / "Src").glob("*.c"))
    paths += sorted((FW / "Drivers" / "STM32F4xx_HAL_Driver" / "Src").glob("*.c"))
    paths += [FW / "Core" / "Startup" / "startup_stm32f446retx.s"]
    return [p.relative_to(FW).as_posix() for p in paths]


def find_tools(explicit):
    suffix = ".exe" if os.name == "nt" else ""
    candidates = []
    if explicit:
        candidates = [Path(explicit)]
    elif os.environ.get("ARM_GCC_BIN"):
        candidates = [Path(os.environ["ARM_GCC_BIN"])]
    else:
        located = shutil.which("arm-none-eabi-gcc")
        if located:
            candidates.append(Path(located).parent)
        if os.name == "nt":
            candidates += sorted(Path("C:/ST").glob(
                "STM32CubeIDE*/STM32CubeIDE/plugins/"
                "com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32*/tools/bin"),
                reverse=True)
    for folder in candidates:
        found = {name: folder / ("arm-none-eabi-" + name + suffix)
                 for name in ("gcc", "objcopy", "size")}
        if all(p.is_file() for p in found.values()):
            return found
    raise RuntimeError("GNU Arm tools missing. Set ARM_GCC_BIN or --toolchain to the bin directory.")


def preflight(toolchain):
    required = [FW / LINKER, FW / "BoatTHISTIMEITSDIFFERENT.ioc",
                FW / "Core/Src/main.c", FW / "Core/Inc/main.h",
                FW / "Core/Startup/startup_stm32f446retx.s",
                FW / "Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal.c"]
    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        raise RuntimeError("Missing build inputs: " + ", ".join(missing))
    found = find_tools(toolchain)
    version = subprocess.check_output([str(found["gcc"]), "--version"], text=True).splitlines()[0]
    report = {"status": "software_preflight_pass", "target": "STM32F446RET6",
              "firmware": "V1 unqualified", "compiler": version,
              "tools": {k: str(v) for k, v in found.items()}, "sources": sources(),
              "input_sha256": inputs(), "warnings": WARNINGS,
              "hardware_access": False}
    return found, report


def run(command, log):
    command = [str(v) for v in command]
    log.write(json.dumps(command) + "\n")
    log.flush()
    result = subprocess.run(command, cwd=FW, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, errors="replace")
    log.write(result.stdout)
    log.flush()
    if result.stdout:
        print(result.stdout, end="")
    if result.returncode:
        raise RuntimeError("Tool exited " + str(result.returncode) + "; see build.log")
    return result.stdout


def build(found, report, destination):
    out = Path(destination).resolve()
    # Restrict generated files to the explicitly ignored firmware/Debug tree.
    allowed = (FW / "Debug").resolve()
    if out == allowed or allowed not in out.parents:
        raise RuntimeError("--out must be a subdirectory of firmware/Debug")
    out.mkdir(parents=True, exist_ok=True)
    manifest = out / "manifest.json"
    report.update({"status": "building", "created_utc": datetime.now(timezone.utc).isoformat(),
                   "output_directory": str(out), "artifact_sha256": {}})
    manifest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    try:
        with (out / "build.log").open("w", encoding="utf-8") as log:
            objects = []
            flags = CPU + ["-std=gnu11", "-Og", "-g3", "-ffunction-sections", "-fdata-sections",
                           "-Wall", "-Wextra", "-Werror=implicit-function-declaration",
                           "-DUSE_HAL_DRIVER", "-DSTM32F446xx", "--specs=nano.specs",
                           "-ffile-prefix-map=" + str(FW) + "=firmware"]
            flags += ["-I" + p for p in INCLUDES]
            for source in report["sources"]:
                obj = out / "obj" / (source + ".o")
                obj.parent.mkdir(parents=True, exist_ok=True)
                asm = ["-x", "assembler-with-cpp"] if source.endswith(".s") else []
                run([found["gcc"]] + flags + asm + ["-c", source, "-o", obj], log)
                objects.append(obj)
            elf = out / (IMAGE + ".elf")
            link = CPU + ["-T" + LINKER, "--specs=nano.specs", "--specs=nosys.specs",
                          "-Wl,--gc-sections", "-Wl,--print-memory-usage",
                          "-Wl,-Map=" + str(out / (IMAGE + ".map")),
                          "-u", "_printf_float", "-u", "_scanf_float", "-static"]
            run([found["gcc"]] + link + objects +
                ["-Wl,--start-group", "-lc", "-lm", "-Wl,--end-group", "-o", elf], log)
            for extension, fmt in (("bin", "binary"), ("hex", "ihex")):
                run([found["objcopy"], "-O", fmt, elf, out / (IMAGE + "." + extension)], log)
            size_text = run([found["size"], elf], log)
            (out / "size.txt").write_text(size_text, encoding="utf-8")
        raw = (out / (IMAGE + ".bin")).read_bytes()
        if not 8 <= len(raw) <= 512 * 1024:
            raise RuntimeError("Invalid binary size")
        stack, reset = struct.unpack_from("<II", raw)
        if not (0x20000000 < stack <= 0x20020000 and stack % 8 == 0):
            raise RuntimeError("Initial stack is outside the STM32F446RE SRAM or misaligned")
        if not (reset & 1 and 0x08000000 <= (reset & ~1) < 0x08000000 + len(raw)):
            raise RuntimeError("Reset vector is not a Thumb address within this image")
        if inputs() != report["input_sha256"]:
            raise RuntimeError("Inputs changed during build; rerun on a stable source snapshot")
        report.update({"status": "build_pass_unqualified", "binary_bytes": len(raw),
                       "initial_stack": hex(stack), "reset_vector": hex(reset),
                       "artifact_sha256": {p.name: digest(p) for p in sorted(out.glob(IMAGE + ".*"))
                                           if p.suffix in (".elf", ".bin", ".hex", ".map")}})
    except Exception as exc:
        report.update({"status": "build_failed", "error": str(exc), "artifact_sha256": {}})
        raise
    finally:
        manifest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Built UNQUALIFIED V1 image: " + str(out))
    print("No programmer invoked; no hardware accessed. See manifest.json and build.log.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preflight", "build"))
    parser.add_argument("--toolchain", help="Directory containing arm-none-eabi-gcc/objcopy/size")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Build subdirectory within firmware/Debug")
    args = parser.parse_args()
    try:
        found, report = preflight(args.toolchain)
        if args.action == "preflight":
            print(json.dumps(report, indent=2))
        else:
            build(found, report, args.out)
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
