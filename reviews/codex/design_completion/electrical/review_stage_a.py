"""Independent read-only binary/vector review plus isolated contract mutation.

Only the sibling evidence JSON and disposable test fixture are written.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import shutil

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent


def main():
    manifest = json.loads((ROOT / "firmware_v2/evidence/stage_a_build.json").read_text())
    binary = ROOT / "firmware_v2/build/stage_a/v2_stage_a_unqualified.bin"
    elf = binary.with_suffix(".elf")
    tool_dir = Path(manifest["commands"][0]["argv"][0]).parent
    nm = tool_dir / ("arm-none-eabi-nm.exe" if (tool_dir / "arm-none-eabi-nm.exe").exists() else "arm-none-eabi-nm")
    symbols = {}
    for line in subprocess.check_output([str(nm), "-n", str(elf)], text=True).splitlines():
        fields = line.split()
        if len(fields) == 3:
            symbols[fields[2]] = int(fields[0], 16)
    vectors = struct.unpack_from("<16I", binary.read_bytes())
    named_vectors = {1: "Reset_Handler", 2: "NMI_Handler", 3: "HardFault_Handler",
                     4: "MemManage_Handler", 5: "BusFault_Handler", 6: "UsageFault_Handler", 15: "SysTick_Handler"}
    result = {"basis": "Local Stage A binaries and exact recorded build inputs; no hardware execution",
              "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
              "binary_bytes": binary.stat().st_size,
              "initial_stack": hex(vectors[0]), "vector_table": hex(symbols["g_pfnVectors"]),
              "vectors": {name: {"word": hex(vectors[index]), "symbol": hex(symbols[name]),
                                  "matches": vectors[index] == (symbols[name] | 1)} for index, name in named_vectors.items()},
              "input_hash_mismatches": [p for p, h in manifest["input_sha256"].items()
                                         if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != h]}
    assert result["binary_sha256"] == manifest["artifact_sha256"][binary.name]
    assert all(x["matches"] for x in result["vectors"].values())
    spec = importlib.util.spec_from_file_location("stage_builder", ROOT / "firmware_v2/tools/build.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    contract = json.loads((ROOT / "firmware_v2/board_contract.json").read_text())
    report = json.loads((ROOT / contract["schematic_evidence"]).read_text())
    paths = {"firmware_v2/board_contract.json", contract["schematic_evidence"], contract["netlist"]}
    paths.update(p for p in report["input_manifest"] if p.startswith("hardware/kicad_v2/")
                 and p.endswith((".kicad_sch", ".kicad_sym")))
    with tempfile.TemporaryDirectory(prefix="stage-review-", dir=HERE) as tmp:
        scratch = Path(tmp).resolve()
        assert scratch.parent == HERE and scratch.name.startswith("stage-review-")
        for p in paths:
            target = scratch / p
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / p, target)
        contract["target"] = "STM32F103C8T6"
        (scratch / "firmware_v2/board_contract.json").write_text(json.dumps(contract))
        try:
            builder.pin_contract(scratch)
            result["wrong_target_rejected"] = False
        except ValueError:
            result["wrong_target_rejected"] = True
    (HERE / "stage_a_review.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
