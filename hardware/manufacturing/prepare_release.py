"""Prepare source-derived ordering and assembly REVIEW files; never release a board.

Use KiCad's Python (pcbnew), from any directory:
  python hardware/manufacturing/prepare_release.py --boards 1
  python hardware/manufacturing/prepare_release.py --boards 1 --check

Reads existing BOM/PCB files only. Writes only hardware/manufacturing/{v1,v2}/
and run_manifest.json. No CAD save, primary generator, network or order API is used.
CSV files are machine-import exports of this engineering script, not workbook models.
"""
import argparse
import collections
import csv
import datetime
import hashlib
import html
import io
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "hardware/manufacturing"
POLICY_PATH = "hardware/manufacturing/procurement_policy.json"
SELF = "hardware/manufacturing/prepare_release.py"
DESIGNS = {
    "v1": {"bom": "docs/BOM.csv", "pcb": "hardware/kicad/LoRa_Boat_Controller.kicad_pcb",
           "release": "Existing V1 reconstruction: reference/repair only; known electrical defects and inferred drill provenance prevent a new-build release."},
    "v2": {"bom": "docs/BOM_V2.csv", "pcb": "hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_pcb",
           "release": "V2 vehicle-node design draft: not fabrication released; routing/electrical/firmware/assembly review remains. Handheld hardware is not included."},
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def natural(text):
    return [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", text)]


def csv_text(rows, fields):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def read_bom(variant, text):
    rows = []
    skipped_total = None
    for line, item in enumerate(csv.DictReader(io.StringIO(text)), 2):
        refs = item.get("Refs", item.get("Ref", "")).split()
        if not item.get("Item", "") and refs and refs[0] == "TOTAL":
            skipped_total = int(item["Qty"])
            continue
        qty = int(item["Qty"])
        if qty != len(refs):
            raise ValueError(f"{variant} BOM row {line}: quantity {qty} differs from {refs}")
        for ref in refs:
            rows.append({"Reference": ref, "Allegro reference": item.get("Allegro_RefDes", ""),
                         "Value": item["Value"], "MPN": item["MPN"].strip(),
                         "Manufacturer": item["Manufacturer"].strip(), "Footprint": item["Footprint"],
                         "Description": item["Description"], "Source confidence": item.get("Confidence", "not specified"),
                         "Source": DESIGNS[variant]["bom"], "Source line": line})
    refs = [row["Reference"] for row in rows]
    assert len(refs) == len(set(refs)), f"Duplicate {variant} BOM reference"
    if skipped_total is not None:
        assert skipped_total == len(rows), "BOM TOTAL disagrees with counted references"
    return rows, skipped_total


def inspect_board(path):
    import pcbnew
    board = pcbnew.LoadBoard(str(path))
    # Use Edge.Cuts centerline geometry, not the bbox that includes stroke width.
    # Current boards use rectangular four-segment outlines; refuse an unsupported revision.
    edges = [d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]
    if len(edges) != 4 or any(e.GetShape() != pcbnew.SHAPE_T_SEGMENT for e in edges):
        raise ValueError("Assembly extractor requires review for non-rectangular Edge.Cuts")
    points = [(pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)) for e in edges for p in (e.GetStart(), e.GetEnd())]
    xs, ys = {p[0] for p in points}, {p[1] for p in points}
    if len(xs) != 2 or len(ys) != 2 or any(points.count(p) != 2 for p in points):
        raise ValueError("Outline is not a closed rectangular profile")
    origin = (min(xs), min(ys))
    dims = (round(max(xs)-min(xs), 6), round(max(ys)-min(ys), 6))
    footprints = {}
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref in footprints:
            raise ValueError("Duplicate PCB reference: " + ref)
        point = fp.GetPosition()
        pads = []
        for p in fp.Pads():
            xy, size, drill = p.GetPosition(), p.GetSize(), p.GetDrillSize()
            pads.append({"number": p.GetNumber(), "net": p.GetNetname(),
                         "x": pcbnew.ToMM(xy.x)-origin[0], "y": pcbnew.ToMM(xy.y)-origin[1],
                         "w": pcbnew.ToMM(size.x), "h": pcbnew.ToMM(size.y),
                         "rotation": p.GetOrientationDegrees(), "circle": p.GetShape() == pcbnew.PAD_SHAPE_CIRCLE,
                         "drill_x": pcbnew.ToMM(drill.x), "drill_y": pcbnew.ToMM(drill.y)})
        footprints[ref] = {"reference": ref, "value": fp.GetValue(), "footprint": fp.GetFPIDAsString(),
                           "x": pcbnew.ToMM(point.x)-origin[0], "y": pcbnew.ToMM(point.y)-origin[1],
                           "rotation": fp.GetOrientationDegrees(), "side": "Bottom" if fp.IsFlipped() else "Top", "pads": pads}
    return {"origin_board_mm": list(origin), "dimensions_mm": list(dims), "footprints": footprints,
            "kicad_version": pcbnew.Version(), "coordinate_note": "Origin = upper-left Edge.Cuts centerline corner (stroke excluded); +X right, +Y down as viewed from top. Rotations are raw KiCad angles, not assembler-normalized rotations."}


def classify(row, variant, policy, board):
    ref = row["Reference"]
    notes = []
    status = "CANDIDATE"
    option = "base population"
    if ref in policy["bare_features"]:
        return "BOARD_FEATURE", "Not a purchased component", "bare PCB feature"
    if not row["MPN"] or not row["Manufacturer"]:
        status = "HOLD"
        notes.append("Exact manufacturer/orderable part is missing")
    if variant == "v1" and row["Source confidence"] != "HIGH":
        status = "HOLD"
        notes.append("Source confidence: " + row["Source confidence"] + "; confirm the suggested selection")
    if ref in policy["holds"]:
        status = "HOLD"
        notes.append(policy["holds"][ref])
    for name, selection in policy["population_options"].items():
        if ref in selection["refs"]:
            status = "HOLD"
            option = name
            notes.append(selection["decision"])
    if row["Footprint"] != board["footprints"][ref]["footprint"]:
        status = "HOLD"
        notes.append("BOM footprint differs from embedded PCB footprint")
    if status == "CANDIDATE":
        notes.append("Exact MPN text from source BOM; live availability, lifecycle, suffix, price and package not independently reverified")
    return status, "; ".join(notes), option


def is_orientation_sensitive(row):
    return (row["Reference"].startswith(("U", "Q", "D", "J")) or "CONN" in row["Footprint"].upper()
            or "CP_Elec" in row["Footprint"] or row["Reference"].startswith(("GPS", "LORA", "SPEED", "STEERING", "CAN")))


def assembly_svg(variant, board, rows, side):
    width, height = board["dimensions_mm"]
    vwidth = max(104, width+10)
    ox, oy = (vwidth-width)/2, 17
    flip = side == "Bottom"
    def x(raw): return ox + (width-raw if flip else raw)
    def esc(raw): return html.escape(str(raw), quote=True)
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vwidth:.3f} {height+42:.3f}" width="1400" role="img" aria-labelledby="title desc">',
           f'<title id="title">{variant.upper()} {side.lower()} assembly pad map</title>',
           '<desc id="desc">Source-derived pad positions and electrical pin-one marks. A planning drawing, not a fabrication release or verified package polarity guide.</desc>',
           '<rect width="100%" height="100%" fill="#f8fafc"/>',
           '<style>text{font-family:Arial,sans-serif;fill:#142337}.ref{font-size:.88px;font-weight:700;paint-order:stroke;stroke:#f8fafc;stroke-width:.28px;stroke-linejoin:round}.pin{fill:#ef6b26;stroke:#9d3b04;stroke-width:.08}.body{fill:none;stroke:#768aa5;stroke-width:.13}</style>',
           f'<text x="4" y="5.3" font-size="2.6" font-weight="700">{variant.upper()}  /  {side.upper()} ASSEMBLY REFERENCE</text>',
           f'<text x="4" y="9" font-size="1.45">{width:.3f} × {height:.3f} mm · electrical pad geometry · NOT FABRICATION RELEASED</text>',
           f'<text x="4" y="12.2" font-size="1.25">{"Underside view: mirrored horizontally from PCB top coordinates." if flip else "Top view: +X right, +Y down. Hover a part for its value and source MPN."}</text>',
           f'<rect x="{ox:.3f}" y="{oy}" width="{width:.3f}" height="{height:.3f}" rx=".2" fill="#e9f0f4" stroke="#20364c" stroke-width=".25"/>']
    count = 0
    label_boxes = []
    for row in rows:
        fp = board["footprints"][row["Reference"]]
        if fp["side"] != side:
            continue
        count += 1
        pads = fp["pads"]
        svg.append(f'<g><title>{esc(row["Reference"])} | {esc(row["Value"])} | {esc(row["MPN"] or "bare PCB feature")} | {esc(row["Status"])} | KiCad {fp["rotation"]:g} deg</title>')
        if pads:
            xmin = min(p["x"]-max(p["w"], p["h"])/2 for p in pads)
            xmax = max(p["x"]+max(p["w"], p["h"])/2 for p in pads)
            ymin = min(p["y"]-max(p["w"], p["h"])/2 for p in pads)
            ymax = max(p["y"]+max(p["w"], p["h"])/2 for p in pads)
            left = x(xmax) if flip else x(xmin)
            svg.append(f'<rect class="body" x="{left:.3f}" y="{oy+ymin:.3f}" width="{xmax-xmin:.3f}" height="{ymax-ymin:.3f}"/>')
        for p in pads:
            px, py = x(p["x"]), oy+p["y"]
            pin1 = p["number"] in ("1", "01")
            fill = "#ef6b26" if pin1 else "#627e99"
            angle = p["rotation"] if flip else -p["rotation"]
            if p["circle"]:
                svg.append(f'<ellipse cx="{px:.3f}" cy="{py:.3f}" rx="{p["w"]/2:.3f}" ry="{p["h"]/2:.3f}" fill="{fill}"/>')
            else:
                svg.append(f'<rect x="{px-p["w"]/2:.3f}" y="{py-p["h"]/2:.3f}" width="{p["w"]:.3f}" height="{p["h"]:.3f}" rx=".08" fill="{fill}" transform="rotate({angle:.3f} {px:.3f} {py:.3f})"/>')
            if p["drill_x"]:
                svg.append(f'<ellipse cx="{px:.3f}" cy="{py:.3f}" rx="{p["drill_x"]/2:.3f}" ry="{p["drill_y"]/2:.3f}" fill="#f8fafc"/>')
        anchor_x, anchor_y = x(fp["x"]), oy+fp["y"]
        half = .27*len(row["Reference"])+.2
        offsets = [(0,.3), (0,-1), (0,1.5), (-1.6,.3), (1.6,.3), (0,-2.3), (0,2.8), (-2.8,-1), (2.8,1.5)]
        chosen = (anchor_x, anchor_y+.3)
        for dx, dy in offsets:
            lx, ly = anchor_x+dx, anchor_y+dy
            candidate = (lx-half, ly-.85, lx+half, ly+.2)
            if candidate[0] < ox or candidate[2] > ox+width or candidate[1] < oy or candidate[3] > oy+height:
                continue
            if all(candidate[2] < b[0] or candidate[0] > b[2] or candidate[3] < b[1] or candidate[1] > b[3] for b in label_boxes):
                chosen = (lx,ly)
                break
        lx, ly = chosen
        label_boxes.append((lx-half, ly-.85, lx+half, ly+.2))
        if abs(lx-anchor_x)+abs(ly-anchor_y-.3) > .6:
            svg.append(f'<line x1="{anchor_x:.3f}" y1="{anchor_y:.3f}" x2="{lx:.3f}" y2="{ly-.3:.3f}" stroke="#314a62" stroke-width=".09"/>')
        svg.append(f'<text class="ref" text-anchor="middle" x="{lx:.3f}" y="{ly:.3f}">{esc(row["Reference"])}</text></g>')
    if count == 0:
        svg.append(f'<text x="{vwidth/2}" y="{oy+height/2}" text-anchor="middle" font-size="2.6">No footprints on this side in the source board</text>')
    y = oy+height+5
    svg += [f'<circle cx="5" cy="{y-.4}" r=".8" fill="#ef6b26"/><text x="7" y="{y}" font-size="1.45">Orange = electrical pad 1/01. It does not universally mean cathode or positive.</text>',
            f'<text x="4" y="{y+3.2}" font-size="1.25">Match IC dots, diode bands, capacitor polarity and connector keys to the exact package drawing.</text>',
            f'<text x="4" y="{y+6.1}" font-size="1.25">Grey outlines show pad envelopes, not component bodies. Check orientation_review.csv before assembly.</text>',
            f'<text x="4" y="{y+9}" font-size="1.25">{count} source footprints on this side. No bench, package, solder-paste or machine-rotation approval is implied.</text>', '</svg>']
    return "\n".join(svg)+"\n"


def build_variant(variant, source, policy, boards):
    rows, total = read_bom(variant, source[DESIGNS[variant]["bom"]].decode("utf-8-sig"))
    board = inspect_board(ROOT / DESIGNS[variant]["pcb"])
    bom_refs = {r["Reference"] for r in rows}
    pcb_refs = set(board["footprints"])
    if bom_refs != pcb_refs:
        raise ValueError(f"{variant} BOM/PCB reference mismatch: only BOM {bom_refs-pcb_refs}; only PCB {pcb_refs-bom_refs}")
    assert set(policy["holds"]) <= bom_refs, "Stale policy references"
    for opt in policy["population_options"].values():
        assert set(opt["refs"]) <= bom_refs, "Stale option references"
    positions, orientations = [], []
    for r in rows:
        status, note, option = classify(r, variant, policy, board)
        r.update({"Status": status, "Review note": note, "Population": option, "Per board": 1, "Selected boards": boards, "Selected quantity": boards, "Fleet 5 quantity": 5})
        fp = board["footprints"][r["Reference"]]
        p1 = next((p for p in fp["pads"] if p["number"] in ("1", "01")), None)
        positions.append({"Reference": r["Reference"], "Value": r["Value"], "MPN": r["MPN"], "Side": fp["side"],
                          "X mm from outline left": round(fp["x"], 5), "Y mm from outline top": round(fp["y"], 5),
                          "KiCad rotation degrees": fp["rotation"], "Pad 1 net": p1["net"] if p1 else "no pad 1",
                          "Status": "REVIEW ONLY - not assembler-normalized centroid", "Footprint": fp["footprint"]})
        if is_orientation_sensitive(r):
            pads = "; ".join(f'{p["number"]}={p["net"] or "NC"}' for p in sorted(fp["pads"], key=lambda p: natural(p["number"])))
            orientations.append({"Reference": r["Reference"], "MPN": r["MPN"], "Value": r["Value"], "Side": fp["side"],
                                 "KiCad rotation degrees": fp["rotation"], "Pad 1 net": p1["net"] if p1 else "no pad 1", "Pad map": pads,
                                 "Required check": "Match exact manufacturer pin numbering/polarity/key to this electrical pad map; pin 1 is not a universal polarity mark", "Verified by": "", "Verified date": ""})
    rows.sort(key=lambda r: natural(r["Reference"]))
    groups = collections.defaultdict(list)
    for r in rows:
        if r["Status"] == "CANDIDATE":
            groups[(r["MPN"], r["Manufacturer"])].append(r["Reference"])
    outputs = {}
    fields = ["Reference", "Allegro reference", "Value", "MPN", "Manufacturer", "Per board", "Selected boards", "Selected quantity", "Fleet 5 quantity", "Status", "Population", "Review note", "Footprint", "Source confidence", "Source", "Source line", "Description"]
    outputs[f"{variant}/bom_review.csv"] = csv_text(rows, fields)
    outputs[f"{variant}/holds.csv"] = csv_text([r for r in rows if r["Status"] == "HOLD"], fields)
    for suffix, count in (("1board", 1), ("fleet5", 5), ("selected", boards)):
        import_rows = [{"Manufacturer Part Number": mpn, "Quantity": len(refs)*count, "Manufacturer": maker, "Customer Reference": " ".join(sorted(refs, key=natural))} for (mpn, maker), refs in sorted(groups.items())]
        outputs[f"{variant}/distributor_candidates_{suffix}.csv"] = csv_text(import_rows, ["Manufacturer Part Number", "Quantity", "Manufacturer", "Customer Reference"])
    outputs[f"{variant}/positions_review.csv"] = csv_text(positions, list(positions[0]))
    outputs[f"{variant}/orientation_review.csv"] = csv_text(orientations, list(orientations[0]))
    outputs[f"{variant}/assembly_top.svg"] = assembly_svg(variant, board, rows, "Top")
    outputs[f"{variant}/assembly_bottom.svg"] = assembly_svg(variant, board, rows, "Bottom")
    outputs[f"{variant}/pcb_assembly_data.json"] = json.dumps(board, indent=2)+"\n"
    status_counts = dict(collections.Counter(r["Status"] for r in rows))
    summary = {"release_state": "NOT_RELEASED", "reason": DESIGNS[variant]["release"], "footprints": len(rows),
               "bom_total_row_excluded": total is not None, "source_total": total, "counts_by_reference": status_counts,
               "candidate_order_lines": len(groups), "selected_boards": boards,
               "candidate_quantity_selected": status_counts.get("CANDIDATE", 0)*boards,
               "candidate_quantity_fleet5": status_counts.get("CANDIDATE", 0)*5,
               "board_dimensions_mm": board["dimensions_mm"], "board_origin_mm": board["origin_board_mm"],
               "bom_pcb_reference_match": True, "footprint_mapping_mismatches": [r["Reference"] for r in rows if "BOM footprint differs" in r["Review note"]],
               "drc_rerun": False, "physical_package_orientation_verified": False, "kicad_version": board["kicad_version"]}
    outputs[f"{variant}/summary.json"] = json.dumps(summary, indent=2)+"\n"
    external = [
        {"Item": "LoRa radio module", "MPN": "", "Quantity": "TBD", "Decision needed": "Confirm exact radio model, firmware and mating pinout; board BOM includes only socket"},
        {"Item": "GNSS module", "MPN": "", "Quantity": "TBD", "Decision needed": "Select exact breakout/module, supply, update rate and pin mapping; board BOM includes only socket"},
        {"Item": "Antenna and RF pigtail", "MPN": "", "Quantity": "TBD", "Decision needed": "Match selected radio connector, band, enclosure and regional configuration"},
        {"Item": "Actuator mating housings / contacts / cables", "MPN": "", "Quantity": "TBD", "Decision needed": "Select wire gauge, contact plating, lengths and verified harness orientation"},
        {"Item": "Battery / ESC / servo or ground-vehicle drives", "MPN": "", "Quantity": "TBD", "Decision needed": "Application-specific load and power plan; not included in controller board BOM"},
        {"Item": "Enclosure / seals / mounting screws / standoffs", "MPN": "", "Quantity": "TBD", "Decision needed": "Mechanical stack and environmental protection not selected; mounting holes are not hardware items"},
        {"Item": "Handheld and audio/display/control hardware", "MPN": "", "Quantity": "TBD", "Decision needed": "Separate future product BOM; not represented by either vehicle-node PCB"},
        {"Item": "Programming cable / debug probe / test leads", "MPN": "", "Quantity": "TBD", "Decision needed": "Reusable tools; do not multiply automatically by fleet size"},
    ]
    outputs[f"{variant}/external_parts_review.csv"] = csv_text(external, ["Item", "MPN", "Quantity", "Decision needed"])
    return outputs, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--boards", type=int, default=1, help="Quantity for selected-order CSV; always also exports one-board and fleet-five CSVs")
    parser.add_argument("--check", action="store_true", help="Compare generated artifacts without writing")
    args = parser.parse_args()
    if not 1 <= args.boards <= 10000:
        parser.error("--boards must be between 1 and 10000")
    paths = [SELF, POLICY_PATH, "hardware/kicad_v2/tools/v2_design.py"] + [p for spec in DESIGNS.values() for p in (spec["bom"], spec["pcb"])]
    source = {p: (ROOT / p).read_bytes() for p in paths}
    policy = json.loads(source[POLICY_PATH])
    sources = [{"path": p, "sha256": sha(raw), "bytes": len(raw)} for p, raw in source.items()]
    outputs, summaries = {}, {}
    for variant in DESIGNS:
        generated, summary = build_variant(variant, source, policy[variant], args.boards)
        outputs.update(generated)
        summaries[variant] = summary
    inputs_stable = all((ROOT / p).read_bytes() == raw for p, raw in source.items())
    if not inputs_stable:
        raise RuntimeError("A BOM, PCB, policy or script changed during extraction; retry after the writer finishes")
    manifest = {"generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "selected_boards": args.boards,
                "purpose": "Ordering/assembly review package; no purchase or fabrication release", "sources": sources,
                "checks": {"input_hashes_stable": inputs_stable, "bom_pcb_refs_identical": True, "no_primary_generator_run": True,
                           "no_board_save": True, "live_stock_price_or_mpn_validation": False, "drc_rerun": False},
                "variants": summaries,
                "outputs": [{"path": "hardware/manufacturing/"+p, "sha256": sha(t.encode("utf-8")), "bytes": len(t.encode("utf-8"))} for p,t in sorted(outputs.items())]}
    old_path = OUT / "run_manifest.json"
    if old_path.exists():
        old = json.loads(old_path.read_text(encoding="utf-8"))
        if {k:v for k,v in old.items() if k != "generated_at"} == {k:v for k,v in manifest.items() if k != "generated_at"}:
            manifest["generated_at"] = old["generated_at"]
    outputs["run_manifest.json"] = json.dumps(manifest, indent=2)+"\n"
    stale = []
    for rel, content in outputs.items():
        destination = OUT / rel
        if args.check:
            if not destination.exists() or destination.read_text(encoding="utf-8") != content:
                stale.append(rel)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8", newline="\n")
    if stale:
        raise SystemExit("Stale manufacturing artifacts: " + ", ".join(stale))
    print(json.dumps({"action": "verified" if args.check else "generated", "selected_boards": args.boards, "variants": summaries}, indent=2))


if __name__ == "__main__":
    main()
