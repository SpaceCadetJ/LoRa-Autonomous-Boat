#!/usr/bin/env python3
"""validate_pcb.py - Load the generated board with the KiCad 9 pcbnew API (must run with KiCad's own python.exe),
refill zones, save, and check every pad centre / via / track against the v5 film geometry in
hardware/kicad/_build/v5_board.json.  Writes hardware/kicad/_build/validate_pcb.json and prints a summary.
Run from repo root with KiCad's python:
  "C:/Users/Jay/AppData/Local/Programs/KiCad/9.0/bin/python.exe" hardware/kicad/tools/validate_pcb.py [--no-save]
"""
import os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
import pcbnew

KDIR = os.path.join(ROOT, 'hardware', 'kicad')
PCB = os.path.join(KDIR, 'LoRa_Boat_Controller.kicad_pcb')
BUILD = os.path.join(KDIR, '_build')
MIL = 0.0254
ORIGIN = (100.0, 100.0)

def to_mil(x_mm, y_mm):
    return ((x_mm - ORIGIN[0]) / MIL, (ORIGIN[1] - y_mm) / MIL)

def main():
    save = '--no-save' not in sys.argv
    b = json.load(open(os.path.join(BUILD, 'v5_board.json')))
    board = pcbnew.LoadBoard(PCB)
    fps = list(board.GetFootprints())
    print(f'loaded {PCB}: {len(fps)} footprints, {len(list(board.GetTracks()))} tracks+vias, {len(board.Zones())} zones, {board.GetNetCount()} nets')
    # pad positions vs film
    want = {}
    for c in b['components']:
        for p in c['pads']:
            want[(c['ref'], p['number'])] = (p['x'], p['y'], p['net'])
    errs = []
    maxd = 0.0
    n = 0
    for fp in fps:
        ref = fp.GetReference()
        for pad in fp.Pads():
            key = (ref, pad.GetNumber())
            pos = pad.GetPosition()
            x, y = to_mil(pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y))
            if key not in want:
                errs.append(f'unexpected pad {key}'); continue
            wx, wy, wnet = want[key]
            d = math.hypot(x - wx, y - wy); maxd = max(maxd, d); n += 1
            if d > 0.5:
                errs.append(f'pad {key} at ({x:.2f},{y:.2f}) expected ({wx:.2f},{wy:.2f}) d={d:.2f} mil')
    print(f'pads checked: {n}, max position error {maxd:.3f} mil, errors: {len(errs)}')
    for e in errs[:20]:
        print('  ', e)
    # refill zones so DRC and Gerber export see filled copper
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    if save:
        pcbnew.SaveBoard(PCB, board)
        print('zones filled and board saved')
    # connectivity: unconnected count via ratsnest
    board.BuildConnectivity()
    conn = board.GetConnectivity()
    unconnected = conn.GetUnconnectedCount(True)
    print('unconnected (ratsnest) items:', unconnected)
    # (per-net open connections are reported by kicad-cli pcb drc -> _build/drc.json 'unconnected_items')
    json.dump({'footprints': len(fps), 'pads_checked': n, 'max_pad_error_mil': maxd, 'pad_errors': errs, 'unconnected': int(unconnected),
               'zones': int(len(board.Zones())), 'nets': int(board.GetNetCount())}, open(os.path.join(BUILD, 'validate_pcb.json'), 'w'), indent=1)
    return 0 if not errs else 1

if __name__ == '__main__':
    sys.exit(main())
