#!/usr/bin/env python3
"""Capture native footprint geometry; --check is read-only and needs only Python's stdlib."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re

P = Path(__file__).resolve().parent
CONTRACT = P / "expected_contract.json"
RECORD = P / "native_geometry.json"
KICAD_VERSION = "9.0.7"
SCOPE = "Native footprint parsing, electrical pad-number sets and selected reviewed dimensions only."
HOLDS = {
    "board_fit_verified": False, "pcb_drc_performed": False,
    "manufacturer_acceptance": False, "assembly_qualified": False,
    "stencil_qualified": False, "thermal_vias_qualified": False,
    "inductor_start_lead_orientation_verified": False, "hardware_accepted": False,
}
LAYERS = ["F.Cu", "B.Cu", "F.Mask", "B.Mask", "F.Paste", "B.Paste"]

def require(condition, message):
    if not condition:
        raise ValueError(message)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def manifest_and_groups():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8-sig"))
    groups = {}
    hashes = {"expected_contract.json": sha(CONTRACT), Path(__file__).name: sha(Path(__file__))}
    for ref, part in sorted(contract["candidate_parts"].items()):
        lib, name = part["footprint"].split(":", 1)
        require(lib == "LoRa_Boat_Controller_V2", "Unexpected candidate library")
        require(name == Path(name).name and "/" not in name and "\\" not in name, "Unsafe footprint name")
        expected = sorted(part["pins"])
        if name in groups:
            require(groups[name]["expected_electrical_pad_numbers"] == expected, "Conflicting symbol pad sets")
        else:
            groups[name] = {"references": [], "expected_electrical_pad_numbers": expected}
        groups[name]["references"].append(ref)
    require(len(groups) == 7, "Expected exactly seven candidate footprint identities")
    for name in groups:
        rel = "inputs/footprints/" + name + ".kicad_mod"
        copy = "source/hardware/kicad_v2/LoRa_Boat_Controller_V2.pretty/" + name + ".kicad_mod"
        hashes[rel], hashes[copy] = sha(P / rel), sha(P / copy)
        require(hashes[rel] == hashes[copy], "Candidate footprint differs from captured input: " + name)
        groups[name].update(path=rel, candidate_copy_path=copy)
    return hashes, groups

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
    require(not stack and len(roots) == 1, "Malformed footprint root")
    return roots[0]

def child(node, key):
    found = [v for v in node if isinstance(v, list) and v and v[0] == key]
    require(len(found) == 1, "Expected one " + key)
    return found[0]

def pad_data(number, x, y, sx, sy, angle, layers):
    return {"number": str(number), "x_mm": round(float(x), 6), "y_mm": round(float(y), 6),
            "size_x_mm": round(float(sx), 6), "size_y_mm": round(float(sy), 6),
            "rotation_deg": round(float(angle), 6), "layers": sorted(layers)}

def ordered(pads):
    return sorted(pads, key=lambda p: (p["number"], p["x_mm"], p["y_mm"]))

def portable_pads(path):
    root = sexpr(path.read_text(encoding="utf-8-sig"))
    require(root[0] == "footprint", "Unexpected root")
    pads = []
    for p in (v for v in root if isinstance(v, list) and v and v[0] == "pad"):
        require(p[2] == "smd", "Only the captured SMD footprints are supported")
        at, size, layers = child(p, "at"), child(p, "size"), child(p, "layers")[1:]
        require(set(layers) <= set(LAYERS), "Unsupported pad layer")
        pads.append(pad_data(p[1], at[1], at[2], size[1], size[2], at[3] if len(at) > 3 else 0, layers))
    return ordered(pads)

def verify_pads(name, pads, expected):
    electrical = [p["number"] for p in pads if set(p["layers"]) & {"F.Cu", "B.Cu"}]
    require(sorted(electrical) == expected, "Electrical pad numbers differ from symbol: " + name)
    front = ["F.Cu", "F.Mask", "F.Paste"]
    reviewed = "Pad-number set checked; no exact-manufacturer land acceptance asserted."
    if name == "TI_DDA0008B_LMR36520":
        target = []
        for n, y in enumerate((-1.905, -.635, .635, 1.905), 1):
            target.append(pad_data(n, -2.7, y, 1.55, .6, 0, front))
            target.append(pad_data(9-n, 2.7, y, 1.55, .6, 0, front))
        target += [pad_data("9", 0, 0, 2.95, 4.9, 0, ["F.Cu"]),
                   pad_data("", 0, 0, 2.71, 3.4, 0, ["F.Mask", "F.Paste"])]
        require(pads == ordered(target), "Reviewed DDA dimensions/layers changed")
        reviewed = "DDA reviewed geometry matched; EP paste assumes TI's 0.125 mm stencil example. No vias or stencil acceptance."
    elif name in {"C_TDK_C3225X7R1E226M250AB", "C_TDK_C5750X7S2A106K230KB"}:
        center, sx, sy = (1.65, 1.1, 2.2) if "C3225" in name else (2.85, 1.3, 4.6)
        target = [pad_data(n, x, 0, sx, sy, 0, front) for n, x in (("1", -center), ("2", center))]
        require(pads == ordered(target), "Reviewed TDK land geometry changed")
        reviewed = "Reviewed TDK land dimensions matched; assembly, stencil and board fit remain unqualified."
    return reviewed

def entries(groups, get_pads):
    result = []
    for name, group in sorted(groups.items()):
        pads = get_pads(P / group["path"])
        review = verify_pads(name, pads, group["expected_electrical_pad_numbers"])
        result.append({"footprint": name, **group, "pads": pads,
                       "electrical_pad_set_matches_contract": True, "review_scope": review})
    return result

def capture():
    import pcbnew  # Deliberately absent from the portable --check path.
    require(pcbnew.Version() == KICAD_VERSION, "Native capture requires KiCad " + KICAD_VERSION)
    layer_ids = {getattr(pcbnew, label.replace(".", "_")): label for label in LAYERS}
    def native_pads(path):
        footprint = pcbnew.FootprintLoad(str(path.parent), path.stem)
        require(footprint is not None, "Native load failed: " + path.name)
        actual = []
        for p in footprint.Pads():
            require(p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD, "Native pad is not SMD")
            ids = list(p.GetLayerSet().Seq())
            require(set(ids) <= set(layer_ids), "Native pad has unsupported layers")
            at, size = p.GetPosition(), p.GetSize()
            actual.append(pad_data(p.GetNumber(), pcbnew.ToMM(at.x), pcbnew.ToMM(at.y),
                                   pcbnew.ToMM(size.x), pcbnew.ToMM(size.y),
                                   p.GetOrientationDegrees(), [layer_ids[i] for i in ids]))
        return ordered(actual)
    hashes, groups = manifest_and_groups()
    native = entries(groups, native_pads)
    require(native == entries(groups, portable_pads), "Native/portable pad interpretations disagree")
    require(manifest_and_groups()[0] == hashes, "Inputs changed during native inspection")
    record = {"schema_version": 1, "captured_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "kicad_version": pcbnew.Version(), "scope": SCOPE, "input_sha256": hashes,
              "footprint_count": len(native), "entries": native, "qualifications": HOLDS,
              "candidate_circuit_changed": False, "source_files_changed": False,
              "limitations": ["A successful footprint load is not ERC, DRC, board fit or electrical qualification.",
                              "Only pad geometry and electrical numbering are cross-checked; no 3D-model or land-pattern approval.",
                              "Generic inductor/start-lead orientation and other generic footprints remain assembly review items."]}
    RECORD.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
    print("PASS: captured seven footprints with KiCad " + pcbnew.Version() + "; assembly and hardware remain held")

def check():
    record = json.loads(RECORD.read_text(encoding="utf-8-sig"))
    hashes, groups = manifest_and_groups()
    require(record["schema_version"] == 1 and record["kicad_version"] == KICAD_VERSION, "Unexpected native record")
    require(record["scope"] == SCOPE and record["input_sha256"] == hashes, "Captured inputs or inspector changed")
    require(record["entries"] == entries(groups, portable_pads), "Recorded native pad geometry is stale")
    require(record["footprint_count"] == 7 and record["qualifications"] == HOLDS, "Qualification scope changed")
    require(record["candidate_circuit_changed"] is False and record["source_files_changed"] is False, "Unexpected mutation claim")
    print("PASS: seven recorded native footprints, hashes and reviewed dimensions checked without pcbnew; hardware remains held")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check captured evidence without KiCad; never writes")
    args = parser.parse_args()
    check() if args.check else capture()

if __name__ == "__main__":
    main()
