"""Independent output checks for the ordering review packet; standard library only."""
import csv
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "hardware/manufacturing"


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def main():
    manifest = json.loads((OUT / "run_manifest.json").read_text(encoding="utf-8"))
    for item in manifest["sources"] + manifest["outputs"]:
        raw = (ROOT / item["path"]).read_bytes()
        assert len(raw) == item["bytes"] and hashlib.sha256(raw).hexdigest() == item["sha256"], item["path"]
    for variant, expected in (("v1", 44), ("v2", 118)):
        review = read_csv(OUT / variant / "bom_review.csv")
        assert len(review) == expected and len({r["Reference"] for r in review}) == expected
        index = {r["Reference"]: r for r in review}
        candidates = {r["Reference"] for r in review if r["Status"] == "CANDIDATE"}
        held = {r["Reference"] for r in read_csv(OUT / variant / "holds.csv")}
        assert not candidates & held
        for suffix, boards in (("1board",1), ("fleet5",5), ("selected",manifest["selected_boards"])):
            rows = read_csv(OUT / variant / f"distributor_candidates_{suffix}.csv")
            seen = []
            for row in rows:
                refs = row["Customer Reference"].split()
                seen.extend(refs)
                assert int(row["Quantity"]) == len(refs)*boards, row
                for ref in refs:
                    assert ref in candidates and index[ref]["MPN"] == row["Manufacturer Part Number"]
                    assert index[ref]["Manufacturer"] == row["Manufacturer"]
            assert len(seen) == len(set(seen)) and set(seen) == candidates
            assert sum(int(r["Quantity"]) for r in rows) == len(candidates)*boards
        positions = read_csv(OUT / variant / "positions_review.csv")
        assert {r["Reference"] for r in positions} == set(index)
        for side in ("top", "bottom"):
            ET.parse(OUT / variant / f"assembly_{side}.svg")
        if variant == "v1":
            assert "C23" in held and all(ref not in candidates for ref in ("VIN1","GND1","TP1","TP3","TP4","TP5"))
            assert index["C23"]["Value"] == "47pF" and index["C23"]["MPN"] == "GJM1555C1H220JB01D"
        else:
            assert {"U3","Y2","C27","C28","J5","J7"} <= held
            assert not any(ref.startswith(("H","TP")) for ref in candidates)
        print(f"PASS {variant}: {expected} unique references; exact MPNs, holds and all quantity modes reconcile; positions and SVG parse.")
    for doc in (ROOT / "docs/build").glob("*.md"):
        for target in re.findall(r"\]\(([^)]+)\)", doc.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#"):
                continue
            assert (doc.parent / target.split("#",1)[0]).is_file(), f"Broken link: {doc.name} -> {target}"
    print("PASS source/output hashes and local ordering/assembly document links.")


if __name__ == "__main__":
    main()
