#!/usr/bin/env python3
"""placement_check.py - (KiCad python) Report every footprint's courtyard box (board mm, relative to BOARD_ORIGIN),
pairwise courtyard overlaps and parts that leave the board, so v2_design.PLACE can be corrected by hand.
Writes hardware/kicad_v2/_build/placement.json.
  "C:/Users/Jay/AppData/Local/Programs/KiCad/9.0/bin/python.exe" hardware/kicad_v2/tools/placement_check.py
"""
import os, sys, json, itertools
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
import pcbnew
import v2_design as D

def main():
    b = pcbnew.LoadBoard(os.path.join(ROOT, 'hardware', 'kicad_v2', D.PROJ + '.kicad_pcb'))
    ox, oy = D.BOARD_ORIGIN
    boxes = {}
    for fp in b.GetFootprints():
        ref = fp.GetReference()
        bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox() if fp.GetCourtyard(pcbnew.F_CrtYd).OutlineCount() else fp.GetBoundingBox(False, False)
        if bb.GetWidth() == 0:
            bb = fp.GetBoundingBox(False, False)
        x0, y0 = pcbnew.ToMM(bb.GetLeft()) - ox, pcbnew.ToMM(bb.GetTop()) - oy
        x1, y1 = pcbnew.ToMM(bb.GetRight()) - ox, pcbnew.ToMM(bb.GetBottom()) - oy
        boxes[ref] = (round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2))
    overlaps = []
    for a, c in itertools.combinations(sorted(boxes), 2):
        A, C = boxes[a], boxes[c]
        ix = min(A[2], C[2]) - max(A[0], C[0]); iy = min(A[3], C[3]) - max(A[1], C[1])
        if ix > 0.01 and iy > 0.01:
            overlaps.append((a, c, round(ix, 2), round(iy, 2)))
    outside = [(r, bx) for r, bx in boxes.items() if bx[0] < 0 or bx[1] < 0 or bx[2] > D.BOARD_W or bx[3] > D.BOARD_H]
    json.dump({'boxes': boxes, 'overlaps': overlaps, 'outside': outside}, open(os.path.join(ROOT, 'hardware', 'kicad_v2', '_build', 'placement.json'), 'w'), indent=1)
    print(f'{len(boxes)} footprints; {len(overlaps)} overlapping pairs; {len(outside)} outside the board')
    for a, c, ix, iy in overlaps:
        print(f'  OVERLAP {a:5s} {boxes[a]}  x  {c:5s} {boxes[c]}  by {ix} x {iy} mm')
    for r, bx in outside:
        print(f'  OUTSIDE {r} {bx}')
    sizes = {r: (round(bx[2] - bx[0], 1), round(bx[3] - bx[1], 1)) for r, bx in boxes.items()}
    print('sizes (w x h mm):', ', '.join(f'{r}:{w}x{h}' for r, (w, h) in sorted(sizes.items())))

if __name__ == '__main__':
    main()
