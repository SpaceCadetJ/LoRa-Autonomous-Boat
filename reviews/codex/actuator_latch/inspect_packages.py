#!/usr/bin/env python3
"""Inspect three isolated ACT-04 TI footprints. --check uses only the stdlib.

Native capture loads existing files with KiCad 9.0.7 and writes native_geometry.json.
Portable check binds input/candidate copies, contract and review by SHA-256,
compares recorded native pads/artwork with parsed files, and runs in-memory
mutation guards. It neither exports a board nor qualifies electrical behavior.
"""
import argparse
import copy
import datetime
import hashlib
import json
from pathlib import Path
import re

P = Path(__file__).resolve().parent
RECORD = P / "native_geometry.json"
KICAD_VERSION = "9.0.7"
SCOPE = "ACT-04 U12/U13/U14 native/portable pad sets, TI example lands and proposed local artwork; no native board or hardware acceptance."
LAYERS = ["F.Cu", "F.Mask", "F.Paste", "F.SilkS", "F.Fab", "F.CrtYd"]
PARTS = {
 "U12": {"name":"TI_DCU0008A_LVC1G74", "mpn":"SN74LVC1G74DCUR", "pins":{"1":["CLK","input"],"2":["D","input"],"3":["~{Q}","output"],"4":["GND","power_in"],"5":["Q","output"],"6":["~{CLR}","input"],"7":["~{PRE}","input"],"8":["VCC","power_in"]}},
 "U13": {"name":"TI_DBV0005A_LVC1G04", "mpn":"SN74LVC1G04DBVR", "pins":{"1":["NC","no_connect"],"2":["A","input"],"3":["GND","power_in"],"4":["Y","output"],"5":["VCC","power_in"]}},
 "U14": {"name":"TI_DBV0006A_LVC1G11", "mpn":"SN74LVC1G11DBVR", "pins":{"1":["A","input"],"2":["GND","power_in"],"3":["B","input"],"4":["Y","output"],"5":["VCC","power_in"],"6":["C","input"]}},
}
HOLDS = {"manufacturer_acceptance": False, "assembly_qualified": False,
 "stencil_qualified": False, "board_fit_verified": False, "pcb_drc_performed": False,
 "thermal_qualified": False, "timing_qualified": False, "sequencing_qualified": False,
 "actuator_backdrive_qualified": False, "hardware_accepted": False}
DIMENSIONS = {
 "U12": {"nominal_body_xy":[2.3,2.0],"maximum_body_xy":[2.4,2.1],"maximum_height":0.9,
 "land":[0.85,0.3],"column_centers_x":[-1.55,1.55],"pitch":0.5,"corner_radius":0.05,
 "overall_land_span_x":3.95,"land_inner_gap_x":2.25,"courtyard_proposed":[4.5,2.6]},
 "U13": {"nominal_body_xy":[1.6,2.9],"maximum_body_xy":[1.75,3.05],"maximum_height":1.45,
 "land":[1.1,0.6],"column_centers_x":[-1.3,1.3],"pitch":0.95,"corner_radius":0.05,
 "overall_land_span_x":3.7,"land_inner_gap_x":1.5,"courtyard_proposed":[4.3,3.6]},
 "U14": {"nominal_body_xy":[1.6,2.9],"maximum_body_xy":[1.75,3.05],"maximum_height":1.45,
 "land":[1.1,0.6],"column_centers_x":[-1.3,1.3],"pitch":0.95,"corner_radius":0.05,
 "overall_land_span_x":3.7,"land_inner_gap_x":1.5,"courtyard_proposed":[4.3,3.6]},
}


def require(condition, message):
    if not condition:
        raise ValueError(message)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

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

def expected_dcu():
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

def portable(name):
    root = sexpr((P / ("inputs/" + name + ".kicad_mod")).read_text(encoding="utf-8-sig"))
    require(root[:2] == ["footprint", name], "Unexpected footprint identity")
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


def expected(ref):
    if ref == "U12":
        return expected_dcu()
    count = len(PARTS[ref]["pins"])
    coords = [(-1.3,-.95),(-1.3,0),(-1.3,.95),(1.3,.95)]
    coords += [(1.3,-.95)] if count == 5 else [(1.3,0),(1.3,-.95)]
    pads = [pad(n,x,y,1.1,.6,ratio=1/12) for n,(x,y) in enumerate(coords,1)]
    groups = [
      ("F.Fab",.1,[((-.3,-1.45),(.8,-1.45)),((.8,-1.45),(.8,1.45)),
                   ((.8,1.45),(-.8,1.45)),((-.8,1.45),(-.8,-.95)),((-.8,-.95),(-.3,-1.45))]),
      ("F.SilkS",.12,[((-.9,-1.63),(.9,-1.63)),((-.9,1.63),(.9,1.63)),
                     ((-2.04,-1.48),(-2.04,-1.70)),((-2.04,-1.70),(-1.82,-1.70)),
                     ((-1.82,-1.70),(-2.04,-1.48))]),
      ("F.CrtYd",.05,[((-2.15,-1.8),(2.15,-1.8)),((2.15,-1.8),(2.15,1.8)),
                     ((2.15,1.8),(-2.15,1.8)),((-2.15,1.8),(-2.15,-1.8))]),
    ]
    return ordered({"pads":pads,"lines":[line(layer,a,b,w) for layer,w,pairs in groups for a,b in pairs]})


def manifest():
    contract = json.loads((P / "expected_contract.json").read_text(encoding="utf-8-sig"))
    review = json.loads((P / "package_review.json").read_text(encoding="utf-8-sig"))
    require(review["revision"] == "ACT-04" and review["qualifications"] == HOLDS, "Review scope or holds changed")
    require(set(review["parts"]) == set(PARTS), "Reviewed part set changed")
    paths = ["expected_contract.json", "package_review.json", Path(__file__).name]
    for ref, part in PARTS.items():
        actual = contract["candidate_parts"][ref]
        require(actual["mpn"] == part["mpn"] and actual["manufacturer"] == "Texas Instruments", ref + " identity changed")
        require(actual["footprint"] == "LoRa_Boat_Controller_V2:" + part["name"], ref + " footprint changed")
        require(actual["pins"] == part["pins"], ref + " pin map changed")
        reviewed = review["parts"][ref]
        require(reviewed["mpn"] == part["mpn"] and reviewed["pins"] == part["pins"], ref + " reviewed identity changed")
        require(reviewed["reviewed_dimensions_mm"] == DIMENSIONS[ref], ref + " reviewed dimensions changed")
        source = "inputs/" + part["name"] + ".kicad_mod"
        candidate = "source/hardware/kicad_v2/LoRa_Boat_Controller_V2.pretty/" + part["name"] + ".kicad_mod"
        require(sha(P/source) == sha(P/candidate), ref + " candidate footprint copy differs")
        paths += [source, candidate]
    return {rel:sha(P/rel) for rel in paths}, review


def validate(ref, data):
    require(data == expected(ref), ref + " reviewed pads, pin-1 artwork, body or courtyard changed")
    require([p["number"] for p in data["pads"]] == sorted(PARTS[ref]["pins"]), ref + " electrical pad set changed")
    return {"electrical_pad_set_matches_contract": True, "ti_example_land_dimensions_match": True,
      "top_view_numbering_and_pin_1_artwork_match": True, "nominal_body_and_proposed_courtyard_match": True,
      "reviewed_dimensions_mm": DIMENSIONS[ref], "no_three_d_model": True,
      "interpretation":"TI example land dimensions match. Local artwork, courtyard and manufacturing process remain proposals."}


def mutation_guards():
    rejected = []
    for ref in PARTS:
        for kind in ["pad_number", "land_width", "pin_1_marker"]:
            data = copy.deepcopy(expected(ref))
            if kind == "pad_number":
                data["pads"][0]["number"] = "99"
            elif kind == "land_width":
                data["pads"][0]["size_x_mm"] += .01
            else:
                marker = next(i for i in data["lines"] if i["layer"] == "F.SilkS" and i["start_mm"][0] < -1.8)
                marker["start_mm"][0] += .01
            try:
                validate(ref, data)
            except ValueError:
                rejected.append(ref + ":" + kind)
            else:
                raise ValueError("Mutation guard failed: " + ref + " " + kind)
    return {"mutations_rejected":len(rejected),"cases":rejected,"source_files_mutated":False}


def native_geometry(pcbnew, name):
    fp = pcbnew.FootprintLoad(str(P / "inputs"), name)
    require(fp is not None, "Native footprint load failed: " + name)
    layer_names = {getattr(pcbnew,n.replace(".","_")):n for n in LAYERS}
    data = {"pads":[],"lines":[]}
    for item in fp.Pads():
        require(item.GetAttribute() == pcbnew.PAD_ATTRIB_SMD, "Unexpected native pad type")
        require(item.GetShape() == pcbnew.PAD_SHAPE_ROUNDRECT, "Unexpected native pad shape")
        ids = list(item.GetLayerSet().Seq())
        require(set(ids) <= set(layer_names), "Unexpected native pad layers")
        at,size = item.GetPosition(),item.GetSize()
        data["pads"].append(pad(item.GetNumber(),pcbnew.ToMM(at.x),pcbnew.ToMM(at.y),
          pcbnew.ToMM(size.x),pcbnew.ToMM(size.y),item.GetOrientationDegrees(),
          [layer_names[i] for i in ids],item.GetRoundRectRadiusRatio()))
    for item in fp.GraphicalItems():
        if isinstance(item,pcbnew.PCB_TEXT):
            continue
        require(isinstance(item,pcbnew.PCB_SHAPE) and item.GetShape() == pcbnew.SHAPE_T_SEGMENT, "Unexpected native artwork")
        a,b=item.GetStart(),item.GetEnd()
        data["lines"].append(line(layer_names[item.GetLayer()],[pcbnew.ToMM(a.x),pcbnew.ToMM(a.y)],
          [pcbnew.ToMM(b.x),pcbnew.ToMM(b.y)],pcbnew.ToMM(item.GetWidth())))
    return ordered(data)


def capture():
    import pcbnew  # Not imported by portable --check or check().
    require(pcbnew.Version() == KICAD_VERSION, "Capture requires KiCad " + KICAD_VERSION)
    hashes,review = manifest()
    footprints = {}
    for ref,part in PARTS.items():
        data = native_geometry(pcbnew,part["name"])
        require(data == portable(part["name"]), ref + " native/portable geometry differs")
        footprints[ref] = {"name":part["name"],"geometry":data,"dimensional_comparison":validate(ref,data)}
    guards = mutation_guards()
    require(manifest() == (hashes,review), "Inputs changed during native capture")
    record = {"schema_version":1,"captured_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
      "kicad_version":pcbnew.Version(),"scope":SCOPE,"input_sha256":hashes,"footprints":footprints,
      "manufacturer_review":review,"qualifications":HOLDS,"mutation_guards":guards,
      "source_files_changed_by_inspector":False,"candidate_circuit_changed_by_inspector":False}
    RECORD.write_text(json.dumps(record,indent=2,allow_nan=False)+"\n",encoding="utf-8",newline="\n")
    print("PASS: native ACT-04 3 footprints / 19 pads / 9 mutation guards captured; assembly, timing and hardware held")
    return True


def check():
    record = json.loads(RECORD.read_text(encoding="utf-8-sig"))
    hashes,review = manifest()
    require(record["schema_version"] == 1 and record["kicad_version"] == KICAD_VERSION, "Unexpected native record")
    require(record["scope"] == SCOPE and record["input_sha256"] == hashes, "Recorded scope/hashes changed")
    require(datetime.datetime.fromisoformat(record["captured_utc"]).utcoffset() == datetime.timedelta(0), "Capture time is not UTC")
    require(set(record["footprints"]) == set(PARTS), "Native footprint set changed")
    for ref,part in PARTS.items():
        data = portable(part["name"])
        require(record["footprints"][ref] == {"name":part["name"],"geometry":data,"dimensional_comparison":validate(ref,data)}, ref + " native record differs")
    require(record["manufacturer_review"] == review and record["qualifications"] == HOLDS, "Review or holds changed")
    require(record["mutation_guards"] == mutation_guards(), "Mutation evidence differs")
    require(record["source_files_changed_by_inspector"] is False and record["candidate_circuit_changed_by_inspector"] is False, "Unexpected mutation claim")
    print("PASS: ACT-04 native geometry, hashes and 9 mutation guards verified without pcbnew; acceptance held")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true",help="Read-only portable evidence check")
    args=parser.parse_args()
    check() if args.check else capture()


if __name__ == "__main__":
    main()
