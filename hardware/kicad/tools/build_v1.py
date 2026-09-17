#!/usr/bin/env python3
"""build_v1.py - One-shot rebuild + validation of the V1 KiCad reconstruction from the Allegro sources.
Steps (each is its own script in this folder; run individually for debugging):
  1 provenance.py      -> docs/A0_PROVENANCE.md (film/drill provenance table)
  2 v5_reconstruct.py  -> _build/v5_board.json (placement, nets, copper from the v5 films + pstxnet.dat)
  3 gen_footprints.py  -> LoRa_Boat_Controller.pretty/
  4 gen_pcb.py         -> LoRa_Boat_Controller.kicad_pcb / .kicad_pro / .kicad_dru
  5 validate_pcb.py    (KiCad python) -> pad-position check, zone fill, save
  6 kicad-cli pcb drc  -> _build/drc.json
  7 kicad-cli gerbers/drill -> _build/gerber/
  8 xor_compare.py     -> docs/img/v1_xor_*.png, docs/A0_PROVENANCE.md XOR table
  9 kicad-cli pcb render / export svg -> docs/img/v1_pcb_top.png, v1_pcb_bottom.png, v1_layer_*.svg
Usage (repo root):  python hardware/kicad/tools/build_v1.py [--skip-render] [--from N]
"""
import os, sys, subprocess, json, glob, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
KDIR = os.path.join(ROOT, 'hardware', 'kicad')
BUILD = os.path.join(KDIR, '_build')
IMG = os.path.join(ROOT, 'docs', 'img')
KICAD_BIN = os.environ.get('KICAD_BIN', r'C:\Users\Jay\AppData\Local\Programs\KiCad\9.0\bin')
KCLI = os.path.join(KICAD_BIN, 'kicad-cli.exe')
KPY = os.path.join(KICAD_BIN, 'python.exe')
PCB = os.path.join(KDIR, 'LoRa_Boat_Controller.kicad_pcb')
PY = sys.executable

def run(cmd, **kw):
    print('>>', ' '.join(f'"{c}"' if ' ' in c else c for c in cmd))
    r = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, **kw)
    out = (r.stdout or '') + (r.stderr or '')
    print('\n'.join(out.strip().splitlines()[-12:]))
    if r.returncode not in (0,):
        print(f'   (exit code {r.returncode})')
    return r.returncode

def main():
    start = int(sys.argv[sys.argv.index('--from') + 1]) if '--from' in sys.argv else 1
    os.makedirs(BUILD, exist_ok=True); os.makedirs(IMG, exist_ok=True)
    steps = [
        (1, [PY, os.path.join(HERE, 'provenance.py')]),
        (2, [PY, os.path.join(HERE, 'v5_reconstruct.py')]),
        (3, [PY, os.path.join(HERE, 'gen_footprints.py')]),
        (4, [PY, os.path.join(HERE, 'gen_pcb.py')]),
        (5, [KPY, os.path.join(HERE, 'validate_pcb.py')]),
        (6, [KCLI, 'pcb', 'drc', '--severity-all', '--format', 'json', '--output', os.path.join(BUILD, 'drc.json'), PCB]),
    ]
    for n, cmd in steps:
        if n >= start:
            rc = run(cmd)
            if rc != 0 and n in (2, 3, 4, 5):
                sys.exit(f'step {n} failed')
    if start <= 7:
        gd = os.path.join(BUILD, 'gerber')
        os.makedirs(gd, exist_ok=True)
        for old in glob.glob(os.path.join(gd, '*')):
            try:
                os.remove(old)
            except OSError:
                pass
        run([KCLI, 'pcb', 'export', 'gerbers', '--output', gd + os.sep, '--layers', 'F.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,Edge.Cuts', '--no-x2', '--no-netlist', PCB])
        run([KCLI, 'pcb', 'export', 'drill', '--output', gd + os.sep, '--format', 'excellon', '--excellon-units', 'in', '--excellon-zeros-format', 'suppressleading', PCB])
    if start <= 8:
        run([PY, os.path.join(HERE, 'xor_compare.py')])
    if start <= 9 and '--skip-render' not in sys.argv:
        for side in ('top', 'bottom'):
            run([KCLI, 'pcb', 'render', '--output', os.path.join(IMG, f'v1_pcb_{side}.png'), '--side', side, '--width', '2400', '--height', '1400',
                 '--quality', 'high', '--background', 'opaque', '--zoom', '1.0', PCB])
        for lay in ('F.Cu', 'B.Cu', 'F.Mask', 'B.Mask', 'F.SilkS', 'Edge.Cuts'):
            run([KCLI, 'pcb', 'export', 'svg', '--output', os.path.join(IMG, f'v1_layer_{lay.replace(".", "_")}.svg'), '--layers', lay + ',Edge.Cuts',
                 '--exclude-drawing-sheet', '--page-size-mode', '2', PCB])
    # summary
    try:
        d = json.load(open(os.path.join(BUILD, 'drc.json')))
        import collections
        print('DRC:', dict(collections.Counter((v['type'], v['severity']) for v in d['violations'])), 'unconnected:', len(d['unconnected_items']))
        x = json.load(open(os.path.join(BUILD, 'xor_report.json')))
        for lay, r in x['layers'].items():
            print(f"XOR {lay:10s} {r['xor_pct_of_union']:6.2f} % of union  {r['xor_pct_of_board']:6.3f} % of board")
        print('drill matched', x['drill'].get('matched_within_1mil'), '/', x['drill'].get('v5_holes'))
    except Exception as e:
        print('summary unavailable:', e)

if __name__ == '__main__':
    main()
