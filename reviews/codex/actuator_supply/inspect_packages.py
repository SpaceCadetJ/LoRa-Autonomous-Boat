#!/usr/bin/env python3
"""Capture D_SMC with KiCad; --check verifies recorded evidence using only the stdlib."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re

P = Path(__file__).resolve().parent
RECORD = P / "native_geometry.json"
INPUT = "inputs/D_SMC.kicad_mod"
COPY = "source/hardware/kicad_v2/LoRa_Boat_Controller_V2.pretty/D_SMC.kicad_mod"
KICAD_VERSION = "9.0.7"
SCOPE = "D_SMC electrical pads, selected dimensions and cathode artwork only; no board validation."
LAYERS = ["F.Cu", "F.Mask", "F.Paste", "F.SilkS", "F.Fab", "F.CrtYd"]
QUALIFICATIONS = {
    "manufacturer_land_acceptance": False, "assembly_qualified": False,
    "stencil_qualified": False, "board_fit_verified": False,
    "pcb_drc_performed": False, "thermal_qualified": False,
    "source_sharing_qualified": False, "dual_source_accepted": False,
    "actuator_load_qualified": False, "hardware_accepted": False,
}
SOURCE_REVIEW = {
    "reviewed_utc_date": "2026-10-12",
    "mpn": "SS34-E3/57T",
    "identity_url": "https://www.vishay.com/en/product/88751/tab/quality/",
    "datasheet_url": "https://www.vishay.com/docs/88751/ss32.pdf",
    "datasheet": "Vishay 88751, revision 23-Apr-2020, pages 1-3",
    "identity_status": "Exact orderable name appears in the manufacturer's quality table; no stock assertion.",
    "grade": "Commercial/non-automotive E3",
    "case": "SMC (DO-214AB)",
    "polarity": "Manufacturer cathode band maps to captured footprint pad 1 on the left; pad 2 is anode.",
    "limits": {
        "repetitive_peak_reverse_v": 40,
        "average_forward_current_a": 3,
        "average_current_condition": "At lead temperature per derating curve; not a general ambient or stall-current allowance.",
        "surge_current_a": 100,
        "surge_condition": "8.3 ms single half-sine superimposed on rated load; not repetitive actuator qualification.",
        "max_forward_v": 0.5,
        "forward_condition": "3 A, 25 C, 300 us pulse, 1 percent duty cycle; no all-temperature drop bound.",
        "max_reverse_ma_25c": 0.5,
        "max_reverse_ma_100c": 20,
        "reverse_condition": "Rated DC blocking voltage, pulsed table conditions; not a measured low-voltage leakage value.",
        "junction_temperature_c": [-55, 150],
        "typical_theta_ja_c_per_w": 55,
        "typical_theta_jl_c_per_w": 17,
        "thermal_condition": "Datasheet mounting condition uses 14 x 14 mm copper pad areas; board-dependent typical values.",
    },
    "land_example_mm": {
        "minimum_land_length": 1.52, "minimum_land_width": 3.2,
        "maximum_inner_gap": 4.69, "reference_overall_span": 8.13,
    },
    "comparison_status": "Selected minimum/maximum dimensions pass; captured span differs from the reference example.",
    "limitations": [
        "This is a selected dimensional comparison, not approval of copper, solder-mask, paste or placement.",
        "A populated diode has reverse leakage; do not claim zero backfeed or approved source sharing.",
        "Stored charge, reversed external supply and regenerative actuator energy require circuit review.",
        "Source URLs were read for this review; no downloaded manufacturer PDF hash is claimed."
    ],
}
CONTEXT_HOLDS = {
    "C11_identity": {
        "source_mpn": "EEE-FK1A101P",
        "source_value": "100uF 10V",
        "status": "Unresolved: exact source identity was not confirmed in the current Panasonic product search/FK catalog.",
        "primary_catalog_url": "https://industrial.panasonic.com/cdbs/www-data/pdf/RDE0000/ABA0000C1181.pdf",
        "primary_catalog_date": "10-Feb-2026",
        "qualifications": {
            "exact_identity_verified": False, "land_verified": False,
            "ripple_verified": False, "reverse_voltage_accepted": False,
        },
        "note": "Failed identity confirmation is not proof the part never existed. Do not borrow ratings from a nearby MPN or substitute silently.",
    },
    "VSERVO": [
        "After the separate four-pin rail amendment, VSERVO retains C11,C12,D4,D9,J3 and TP4.",
        "BEC_ONLY requires D4 absent and D9 fitted; ONBOARD requires D4 fitted and D9 absent. Both remain proposed populations.",
        "Actual actuator voltage, PWM input compatibility, startup/stall current, regenerative energy, harness and hotplug behavior remain unknown.",
        "No C11/C12, connector, circuit or board qualification is supplied by this footprint inspection."
    ],
}

def require(ok, message):
    if not ok:
        raise ValueError(message)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def manifest():
    contract = json.loads((P / "expected_contract.json").read_text(encoding="utf-8-sig"))
    for ref in ("D4", "D9"):
        part = contract["candidate_parts"][ref]
        require(part["footprint"] == "LoRa_Boat_Controller_V2:D_SMC", "Unexpected diode footprint")
        require(part["mpn"] == "SS34-E3/57T" and part["manufacturer"] == "Vishay", "Unexpected diode identity")
        require(part["pins"] == {"1": ["K", "passive"], "2": ["A", "passive"]}, "Unexpected diode pin mapping")
    hashes = {name: sha(P / name) for name in (INPUT, COPY, "expected_contract.json", Path(__file__).name)}
    require(hashes[INPUT] == hashes[COPY], "Captured and candidate D_SMC differ")
    return hashes

def sexpr(source):
    stack, roots = [], []
    for token in re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', source):
        if token == "(":
            node = []
            (stack[-1] if stack else roots).append(node)
            stack.append(node)
        elif token == ")":
            require(bool(stack), "Unbalanced closing parenthesis")
            stack.pop()
        else:
            require(bool(stack), "Atom outside footprint")
            stack[-1].append(json.loads(token) if token.startswith('"') else token)
    require(not stack and len(roots) == 1, "Malformed footprint")
    return roots[0]

def child(node, key):
    found = [v for v in node if isinstance(v, list) and v and v[0] == key]
    require(len(found) == 1, "Expected one " + key)
    return found[0]

def number(value):
    return round(float(value), 6)

def pad(number_, x, y, sx, sy, angle, layers, ratio):
    return {"number": str(number_), "x_mm": number(x), "y_mm": number(y),
            "size_x_mm": number(sx), "size_y_mm": number(sy), "rotation_deg": number(angle),
            "layers": sorted(layers), "shape": "roundrect", "roundrect_ratio": number(ratio)}

def line(layer, x1, y1, x2, y2):
    ends = sorted([[number(x1), number(y1)], [number(x2), number(y2)]])
    return {"layer": layer, "start_mm": ends[0], "end_mm": ends[1]}

def order(data):
    return {"pads": sorted(data["pads"], key=lambda p: p["number"]),
            "lines": sorted(data["lines"], key=lambda x: (x["layer"], x["start_mm"], x["end_mm"]))}

def portable():
    root = sexpr((P / INPUT).read_text(encoding="utf-8-sig"))
    require(root[:2] == ["footprint", "D_SMC"], "Unexpected footprint identity")
    data = {"pads": [], "lines": []}
    for item in root:
        if not isinstance(item, list) or not item:
            continue
        if item[0] == "pad":
            require(item[2:4] == ["smd", "roundrect"], "Unexpected pad kind")
            at, size, layers = child(item, "at"), child(item, "size"), child(item, "layers")[1:]
            require(set(layers) <= set(LAYERS), "Unsupported pad layer")
            ratio = child(item, "roundrect_rratio")[1]
            data["pads"].append(pad(item[1], at[1], at[2], size[1], size[2],
                                    at[3] if len(at) > 3 else 0, layers, ratio))
        elif item[0] == "fp_line":
            start, end = child(item, "start"), child(item, "end")
            data["lines"].append(line(child(item, "layer")[1], *start[1:], *end[1:]))
        elif item[0] in {"fp_arc", "fp_poly", "fp_rect", "fp_circle", "fp_curve"}:
            raise ValueError("Unexpected graphical shape")
    return order(data)

def validate(data):
    front = ["F.Cu", "F.Mask", "F.Paste"]
    expected = [pad(n, x, 0, 3.3, 2.5, 90, front, .1) for n, x in (("1", -3.4), ("2", 3.4))]
    require(data["pads"] == expected, "D_SMC pad set, geometry, layers or rounding changed")
    markers = [
        line("F.Fab", -.64944, -.79908, -.64944, .80112),
        line("F.Fab", -1.55114, .00102, -.64944, .00102),
        line("F.SilkS", -4.91, -3.25, -4.91, 3.25),
    ]
    require(all(item in data["lines"] for item in markers), "Cathode artwork no longer agrees with pad 1")
    require(len(data["lines"]) == 17, "Unexpected graphical line count")
    # The quarter-turn swaps local pad size axes; all lengths below are board X/Y extents.
    length, width = data["pads"][0]["size_y_mm"], data["pads"][0]["size_x_mm"]
    center_pitch = data["pads"][1]["x_mm"] - data["pads"][0]["x_mm"]
    result = {
        "physical_land_length_mm": number(length), "physical_land_width_mm": number(width),
        "center_pitch_mm": number(center_pitch), "inner_gap_mm": number(center_pitch-length),
        "overall_span_mm": number(center_pitch+length),
        "selected_drawing_constraints_pass": length >= 1.52 and width >= 3.2 and center_pitch-length <= 4.69,
        "exact_reference_span_match": False,
        "pad_1_cathode_artwork_verified": True, "pad_2_anode_mapping_verified": True,
    }
    require(result["selected_drawing_constraints_pass"], "Selected manufacturer land constraints failed")
    return result

def capture():
    import pcbnew  # Never imported by --check.
    require(pcbnew.Version() == KICAD_VERSION, "Capture requires KiCad " + KICAD_VERSION)
    hashes = manifest()
    footprint = pcbnew.FootprintLoad(str((P / INPUT).parent), "D_SMC")
    require(footprint is not None, "Native D_SMC load failed")
    layer_names = {getattr(pcbnew, n.replace(".", "_")): n for n in LAYERS}
    data = {"pads": [], "lines": []}
    for p in footprint.Pads():
        require(p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD, "Unexpected native pad type")
        require(p.GetShape() == pcbnew.PAD_SHAPE_ROUNDRECT, "Unexpected native pad shape")
        ids = list(p.GetLayerSet().Seq())
        require(set(ids) <= set(layer_names), "Unsupported native pad layer")
        at, size = p.GetPosition(), p.GetSize()
        data["pads"].append(pad(p.GetNumber(), pcbnew.ToMM(at.x), pcbnew.ToMM(at.y),
                                pcbnew.ToMM(size.x), pcbnew.ToMM(size.y),
                                p.GetOrientationDegrees(), [layer_names[i] for i in ids],
                                p.GetRoundRectRadiusRatio()))
    for item in footprint.GraphicalItems():
        if isinstance(item, pcbnew.PCB_TEXT):
            continue
        require(isinstance(item, pcbnew.PCB_SHAPE) and item.GetShape() == pcbnew.SHAPE_T_SEGMENT,
                "Unexpected native graphic")
        start, end = item.GetStart(), item.GetEnd()
        data["lines"].append(line(layer_names[item.GetLayer()], pcbnew.ToMM(start.x), pcbnew.ToMM(start.y),
                                  pcbnew.ToMM(end.x), pcbnew.ToMM(end.y)))
    data = order(data)
    require(data == portable(), "Native and portable footprint interpretations disagree")
    comparison = validate(data)
    require(manifest() == hashes, "Footprint or contract changed during capture")
    record = {
        "schema_version": 1, "captured_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "kicad_version": pcbnew.Version(), "scope": SCOPE, "input_sha256": hashes,
        "footprint": "D_SMC", "references": ["D4", "D9"], "geometry": data,
        "dimensional_comparison": comparison, "manufacturer_review": SOURCE_REVIEW,
        "context_holds": CONTEXT_HOLDS, "qualifications": QUALIFICATIONS,
        "source_files_changed": False, "candidate_circuit_changed": False,
    }
    RECORD.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
    print("PASS: native D_SMC pads/cathode/dimensions captured; assembly, C11 and actuator qualification remain held")
    return True

def check():
    record = json.loads(RECORD.read_text(encoding="utf-8-sig"))
    require(record["schema_version"] == 1 and record["kicad_version"] == KICAD_VERSION, "Unexpected native record")
    require(record["scope"] == SCOPE and record["input_sha256"] == manifest(), "Recorded input hashes changed")
    data = portable()
    require(record["geometry"] == data, "Recorded native geometry differs from captured footprint")
    require(record["dimensional_comparison"] == validate(data), "Recorded dimensional comparison changed")
    require(record["footprint"] == "D_SMC" and record["references"] == ["D4", "D9"], "Unexpected footprint scope")
    require(record["manufacturer_review"] == SOURCE_REVIEW and record["context_holds"] == CONTEXT_HOLDS,
            "Source review or contextual holds changed")
    require(record["qualifications"] == QUALIFICATIONS, "Qualification gates changed")
    require(record["source_files_changed"] is False and record["candidate_circuit_changed"] is False,
            "Unexpected circuit/source mutation claim")
    print("PASS: D_SMC native record, hashes, pads, cathode and selected dimensions checked without pcbnew; hardware held")
    return True

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Read-only captured-evidence check without KiCad")
    args = parser.parse_args()
    check() if args.check else capture()

if __name__ == "__main__":
    main()
