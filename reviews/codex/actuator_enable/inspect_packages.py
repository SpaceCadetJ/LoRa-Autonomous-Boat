#!/usr/bin/env python3
"""Capture the local TXU0102 footprint with KiCad; --check needs only the stdlib."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re

P = Path(__file__).resolve().parent
NAME = "TI_DCU0008A_TXU0102"
INPUT = "inputs/" + NAME + ".kicad_mod"
COPY = "source/hardware/kicad_v2/LoRa_Boat_Controller_V2.pretty/" + NAME + ".kicad_mod"
RECORD = P / "native_geometry.json"
KICAD_VERSION = "9.0.7"
SCOPE = "Native/portable U4 pad numbering, TI example land dimensions and local artwork; no native board validation."
LAYERS = ["F.Cu", "F.Mask", "F.Paste", "F.SilkS", "F.Fab", "F.CrtYd"]
PINS = {"1": ["B2Y", "tri_state"], "2": ["GND", "power_in"],
        "3": ["VCCA", "power_in"], "4": ["A2", "input"],
        "5": ["A1", "input"], "6": ["OE", "input"],
        "7": ["VCCB", "power_in"], "8": ["B1Y", "tri_state"]}
HOLDS = {"manufacturer_acceptance": False, "assembly_qualified": False,
         "stencil_qualified": False, "board_fit_verified": False,
         "pcb_drc_performed": False, "thermal_qualified": False,
         "sequencing_qualified": False, "actuator_backdrive_qualified": False,
         "hardware_accepted": False}
DIMENSIONS = {"nominal_body": [2.3, 2.0], "maximum_body": [2.4, 2.1],
              "maximum_height": 0.9, "land": [0.85, 0.3],
              "column_centers_x": [-1.55, 1.55], "pitch": 0.5,
              "corner_radius": 0.05, "overall_land_span_x": 3.95,
              "land_inner_gap_x": 2.25, "courtyard_proposed": [4.5, 2.6]}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest():
    contract = json.loads((P / "expected_contract.json").read_text(encoding="utf-8-sig"))
    part = contract["candidate_parts"]["U4"]
    require(part["mpn"] == "TXU0102DCUR" and part["manufacturer"] == "Texas Instruments", "U4 identity changed")
    require(part["footprint"] == "LoRa_Boat_Controller_V2:" + NAME, "U4 footprint changed")
    require(part["pins"] == PINS, "U4 physical pin map/types changed")
    review = json.loads((P / "package_review.json").read_text(encoding="utf-8-sig"))
    require(review["mpn"] == "TXU0102DCUR" and review["pins"] == PINS, "Package identity review changed")
    require(review["reviewed_dimensions_mm"] == DIMENSIONS, "Reviewed dimensions changed")
    require(review["qualifications"] == HOLDS, "Package qualifications changed")
    paths = [INPUT, COPY, "expected_contract.json", "package_review.json", Path(__file__).name]
    hashes = {rel: sha(P / rel) for rel in paths}
    require(hashes[INPUT] == hashes[COPY], "Input and candidate footprint copies differ")
    return hashes, review


def sexpr(source):
    stack, roots = [], []
    for token in re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', source):
        if token == "(":
            node = []
            (stack[-1] if stack else roots).append(node)
            stack.append(node)
        elif token == ")":
            require(bool(stack), "Unbalanced close parenthesis")
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


def num(value):
    return round(float(value), 6)


def pad(n, x, y, sx=.85, sy=.3, angle=0, layers=None, ratio=1/6):
    return {"number": str(n), "x_mm": num(x), "y_mm": num(y),
            "size_x_mm": num(sx), "size_y_mm": num(sy), "rotation_deg": num(angle),
            "layers": sorted(layers or ["F.Cu", "F.Mask", "F.Paste"]),
            "shape": "roundrect", "roundrect_ratio": num(ratio)}


def line(layer, a, b, width):
    ends = sorted([[num(v) for v in a], [num(v) for v in b]])
    return {"layer": layer, "start_mm": ends[0], "end_mm": ends[1], "width_mm": num(width)}


def ordered(data):
    return {"pads": sorted(data["pads"], key=lambda x: x["number"]),
            "lines": sorted(data["lines"], key=lambda x: (x["layer"], x["start_mm"], x["end_mm"]))}


def expected():
    pads = [pad(n, -1.55, -.75+.5*(n-1)) for n in range(1, 5)]
    pads += [pad(n, 1.55, .75-.5*(n-5)) for n in range(5, 9)]
    groups = [
        ("F.Fab", .1, [((-.65,-1),(1.15,-1)), ((1.15,-1),(1.15,1)),
                        ((1.15,1),(-1.15,1)), ((-1.15,1),(-1.15,-.5)), ((-1.15,-.5),(-.65,-1))]),
        ("F.SilkS", .12, [((-1.2,-1.18),(1.2,-1.18)), ((-1.2,1.18),(1.2,1.18)),
                           ((-2.13,-.95),(-2.13,-1.17)), ((-2.13,-1.17),(-1.91,-1.17)),
                           ((-1.91,-1.17),(-2.13,-.95))]),
        ("F.CrtYd", .05, [((-2.25,-1.3),(2.25,-1.3)), ((2.25,-1.3),(2.25,1.3)),
                           ((2.25,1.3),(-2.25,1.3)), ((-2.25,1.3),(-2.25,-1.3))]),
    ]
    lines = [line(layer, a, b, width) for layer, width, pairs in groups for a, b in pairs]
    return ordered({"pads": pads, "lines": lines})


def portable():
    root = sexpr((P / INPUT).read_text(encoding="utf-8-sig"))
    require(root[:2] == ["footprint", NAME], "Unexpected footprint identity")
    require(child(root, "attr")[1:] == ["smd"], "Unexpected footprint attributes")
    data = {"pads": [], "lines": []}
    for item in root:
        if not isinstance(item, list) or not item:
            continue
        if item[0] == "pad":
            require(item[2:4] == ["smd", "roundrect"], "Unexpected pad type or shape")
            at, size = child(item, "at"), child(item, "size")
            layers = child(item, "layers")[1:]
            require(set(layers) <= set(LAYERS), "Unexpected pad layer")
            data["pads"].append(pad(item[1], at[1], at[2], size[1], size[2],
                                    at[3] if len(at)>3 else 0, layers, child(item, "roundrect_rratio")[1]))
        elif item[0] == "fp_line":
            data["lines"].append(line(child(item,"layer")[1], child(item,"start")[1:],
                                      child(item,"end")[1:], child(child(item,"stroke"),"width")[1]))
        elif item[0] in {"fp_arc", "fp_poly", "fp_rect", "fp_circle", "fp_curve", "model"}:
            raise ValueError("Unexpected graphic or 3D model")
    return ordered(data)


def validate(data):
    require(data == expected(), "Reviewed pads, pin-1 artwork, body or courtyard changed")
    require([p["number"] for p in data["pads"]] == sorted(PINS), "Unexpected electrical pad set")
    return {"electrical_pad_set_matches_contract": True,
            "ti_example_land_dimensions_match": True,
            "top_view_numbering_and_pin_1_artwork_match": True,
            "nominal_body_and_proposed_courtyard_match": True,
            "reviewed_dimensions_mm": DIMENSIONS,
            "no_three_d_model": True,
            "interpretation": "Selected TI example land geometry matches. Local silk/courtyard and fabrication process remain proposals, not manufacturer or assembly acceptance."}


def capture():
    import pcbnew  # Not imported on the portable --check path.
    require(pcbnew.Version() == KICAD_VERSION, "Capture requires KiCad " + KICAD_VERSION)
    hashes, review = manifest()
    fp = pcbnew.FootprintLoad(str((P / INPUT).parent), NAME)
    require(fp is not None, "Native footprint load failed")
    layer_names = {getattr(pcbnew, n.replace(".", "_")): n for n in LAYERS}
    data = {"pads": [], "lines": []}
    for item in fp.Pads():
        require(item.GetAttribute() == pcbnew.PAD_ATTRIB_SMD, "Unexpected native pad type")
        require(item.GetShape() == pcbnew.PAD_SHAPE_ROUNDRECT, "Unexpected native pad shape")
        ids = list(item.GetLayerSet().Seq())
        require(set(ids) <= set(layer_names), "Unexpected native pad layers")
        at, size = item.GetPosition(), item.GetSize()
        data["pads"].append(pad(item.GetNumber(), pcbnew.ToMM(at.x), pcbnew.ToMM(at.y),
                                pcbnew.ToMM(size.x), pcbnew.ToMM(size.y), item.GetOrientationDegrees(),
                                [layer_names[i] for i in ids], item.GetRoundRectRadiusRatio()))
    for item in fp.GraphicalItems():
        if isinstance(item, pcbnew.PCB_TEXT):
            continue
        require(isinstance(item, pcbnew.PCB_SHAPE) and item.GetShape() == pcbnew.SHAPE_T_SEGMENT,
                "Unexpected native graphical shape")
        a, b = item.GetStart(), item.GetEnd()
        data["lines"].append(line(layer_names[item.GetLayer()], [pcbnew.ToMM(a.x), pcbnew.ToMM(a.y)],
                                  [pcbnew.ToMM(b.x), pcbnew.ToMM(b.y)], pcbnew.ToMM(item.GetWidth())))
    data = ordered(data)
    require(data == portable(), "Native and portable geometry interpretations differ")
    comparison = validate(data)
    require(manifest() == (hashes, review), "Inputs changed during capture")
    record = {"schema_version": 1, "captured_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "kicad_version": pcbnew.Version(), "scope": SCOPE, "input_sha256": hashes,
              "footprint": NAME, "references": ["U4"], "geometry": data,
              "dimensional_comparison": comparison, "manufacturer_review": review,
              "qualifications": HOLDS, "source_files_changed_by_inspector": False,
              "candidate_circuit_changed_by_inspector": False}
    RECORD.write_text(json.dumps(record, indent=2, allow_nan=False)+"\n", encoding="utf-8", newline="\n")
    print("PASS: native TXU0102 pads, lands, pin-1 artwork and proposed courtyard captured; board/assembly/hardware held")
    return True


def check():
    record = json.loads(RECORD.read_text(encoding="utf-8-sig"))
    hashes, review = manifest()
    require(record["schema_version"] == 1 and record["kicad_version"] == KICAD_VERSION, "Unexpected native record")
    require(record["scope"] == SCOPE and record["input_sha256"] == hashes, "Recorded source hashes changed")
    require(datetime.datetime.fromisoformat(record["captured_utc"]).utcoffset() == datetime.timedelta(0), "Capture time is not UTC")
    data = portable()
    require(record["geometry"] == data, "Recorded native geometry differs from source")
    require(record["dimensional_comparison"] == validate(data), "Recorded dimensional comparison differs")
    require(record["manufacturer_review"] == review, "Recorded package review differs")
    require(record["footprint"] == NAME and record["references"] == ["U4"], "Recorded footprint scope differs")
    require(record["qualifications"] == HOLDS, "Qualification gates changed")
    require(record["source_files_changed_by_inspector"] is False and record["candidate_circuit_changed_by_inspector"] is False,
            "Unexpected mutation claim")
    print("PASS: TXU0102 native record, hashes and reviewed geometry checked without pcbnew; board/assembly/hardware held")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Read-only recorded evidence check without KiCad")
    args = parser.parse_args()
    check() if args.check else capture()


if __name__ == "__main__":
    main()
