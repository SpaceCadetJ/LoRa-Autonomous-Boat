"""Capture existing V2 electrical evidence without modifying CAD or firmware.

The netlist is the published native-review export, not a freshly regenerated
netlist. Its identity and current design-source identity are recorded separately.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent / "evidence.json"


def main():
    paths = [
        "hardware/kicad_v2/tools/v2_design.py",
        "hardware/kicad_v2/Navigation.kicad_sch",
        "hardware/kicad_v2/Actuators.kicad_sch",
        "hardware/kicad_v2/Power.kicad_sch",
        "hardware/kicad_v2/MCU.kicad_sch",
        "reviews/codex/publication/native-review/v2/netlist.xml",
        "reviews/codex/publication/native-review/v2/erc.json",
    ]
    netlist = ET.parse(ROOT / paths[-2])
    interested = {
        "U6": {"8", "9", "12", "13", "22", "23", "24"},
        "U4": {"5"}, "U5": {"5"}, "R6": {"1", "2"},
        "U3": {"3", "5"}, "U8": {"1", "3", "4", "5"},
        "C37": {"1", "2"}, "C20": {"1", "2"},
        "U1": {"30"}, "D1": {"1", "2"},
    }
    pins = {}
    for net in netlist.findall("./nets/net"):
        for node in net.findall("node"):
            ref, pin = node.get("ref"), node.get("pin")
            if pin in interested.get(ref, set()):
                pins[f"{ref}.{pin}"] = {
                    "net": net.get("name"),
                    "pin_function": node.get("pinfunction"),
                }
    divider = 6.8 / (47 + 6.8)
    divider_max = 6.8 * 1.01 / (47 * 0.99 + 6.8 * 1.01)
    vout = 0.596 * (1 + 100 / 13.3)
    ripple = vout * (25.2 - vout) / (25.2 * 4.7e-6 * 390000)
    data = {
        "schema_version": 1,
        "captured_date": "2026-09-17",
        "status": "electrical_review_blocked_not_a_release",
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "sources": [{"path": p, "sha256": hashlib.sha256(
            (ROOT / p).read_bytes()).hexdigest()} for p in paths],
        "basis": "Published native-review netlist plus separately hashed live design sources. No new native export or hardware measurement.",
        "pins": dict(sorted(pins.items())),
        "calculations": {
            "battery_divider_ratio_nominal": divider,
            "battery_divider_ratio_worst_1percent_resistors": divider_max,
            "adc_at_25_2V_nominal_V": 25.2 * divider,
            "adc_at_26V_worst_resistors_V": 26 * divider_max,
            "buck5_output_nominal_V": vout,
            "buck5_ripple_25_2V_390kHz_nominal_4_7uH_A": ripple,
            "buck5_peak_at_2A_A": 2 + ripple / 2,
            "buck5_minimum_highside_limit_A": 2.5,
            "proposed_ISENSE_1k_100nF_time_constant_s": 1000 * 100e-9,
        },
    }
    OUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Captured {len(pins)} pin mappings and {len(paths)} source hashes in {OUT}")


if __name__ == "__main__":
    main()
