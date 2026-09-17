#!/usr/bin/env python3
"""xor_compare.py - Fidelity check: rasterize the KiCad-exported Gerbers (hardware/kicad/_build/gerber/) and the
fabrication films (BoatcrewArtwork/BOATCREW*.art) into the same Allegro-mil frame and XOR them per layer.
Also compares the KiCad drill file hole-by-hole with the v5 plated holes (pads + vias from v5_board.json).

Outputs: docs/img/v1_xor_<layer>.png (red = only in fab film, blue = only in KiCad, white = both),
         docs/img/v1_fab_<layer>.png / v1_kicad_<layer>.png, hardware/kicad/_build/xor_report.json, and the
         generated table in docs/A0_PROVENANCE.md (section 'xor').
Run from repo root (after gen_pcb.py + validate_pcb.py + kicad-cli gerber/drill export):
  python hardware/kicad/tools/xor_compare.py [--scale 2]
"""
import os, sys, json, re, glob
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image
import allegro_data as ad
import raster

ROOT = ad.ROOT
GDIR = os.path.join(ROOT, 'hardware', 'kicad', '_build', 'gerber')
IMG = os.path.join(ROOT, 'docs', 'img')
BUILD = os.path.join(ROOT, 'hardware', 'kicad', '_build')
LAYERS = {  # layer: (fab film, kicad export glob, description)
    'F.Cu': ('F.Cu', '*-F_Cu.gtl', 'top copper'),
    'B.Cu': ('B.Cu', '*-B_Cu.gbl', 'bottom copper'),
    'F.Mask': ('F.Mask', '*-F_Mask.gts', 'top solder mask openings'),
    'B.Mask': ('B.Mask', '*-B_Mask.gbs', 'bottom solder mask openings'),
    'F.SilkS': ('F.SilkS', '*-F_Silkscreen.gto', 'top silkscreen'),
    'Edge.Cuts': ('Edge.Cuts', '*-Edge_Cuts.gm1', 'board outline'),
}

def main():
    scale = 2.0
    if '--scale' in sys.argv:
        scale = float(sys.argv[sys.argv.index('--scale') + 1])
    os.makedirs(IMG, exist_ok=True)
    outline = ad.outline_rect()
    bbox = (outline[0] - 40, outline[1] - 40, outline[2] + 40, outline[3] + 40)
    board_area_px = (outline[2] - outline[0]) * (outline[3] - outline[1]) * scale * scale
    X = raster.kicad_xform(ad.KICAD_ORIGIN)
    report = {}
    for lay, (fab_key, kglob, desc) in LAYERS.items():
        kfiles = glob.glob(os.path.join(GDIR, kglob))
        if not kfiles:
            print('missing KiCad export for', lay); continue
        cf = raster.Canvas(*bbox, scale=scale); raster.draw_gerber(cf, ad.load_gerber(ad.GERBER[fab_key]))
        ck = raster.Canvas(*bbox, scale=scale); raster.draw_gerber(ck, ad.load_gerber(kfiles[0]), xform=X)
        A, B = cf.array(), ck.array()
        only_fab, only_kicad, both = A & ~B, B & ~A, A & B
        union = A | B
        n_union = int(union.sum()); n_x = int(only_fab.sum() + only_kicad.sum())
        rep = {'fab_px': int(A.sum()), 'kicad_px': int(B.sum()), 'union_px': n_union, 'xor_px': n_x,
               'only_fab_px': int(only_fab.sum()), 'only_kicad_px': int(only_kicad.sum()),
               'xor_pct_of_union': 100.0 * n_x / max(1, n_union), 'xor_pct_of_board': 100.0 * n_x / board_area_px,
               'scale_px_per_mil': scale}
        report[lay] = rep
        # composite: white = both, red = only fab, blue = only kicad
        rgb = np.zeros(A.shape + (3,), dtype=np.uint8)
        rgb[both] = (235, 235, 235); rgb[only_fab] = (230, 40, 40); rgb[only_kicad] = (40, 90, 230)
        Image.fromarray(rgb).save(os.path.join(IMG, f'v1_xor_{lay.replace(".", "_")}.png'))
        cf.save_png(os.path.join(IMG, f'v1_fab_{lay.replace(".", "_")}.png'))
        ck.save_png(os.path.join(IMG, f'v1_kicad_{lay.replace(".", "_")}.png'))
        print(f'{lay:10s} fab={rep["fab_px"]:9d} kicad={rep["kicad_px"]:9d} xor={n_x:8d} ({rep["xor_pct_of_union"]:.2f}% of union, {rep["xor_pct_of_board"]:.3f}% of board area)  only_fab={rep["only_fab_px"]} only_kicad={rep["only_kicad_px"]}')

    # ---- drill: KiCad Excellon (inches, suppress-leading) vs v5 plated holes
    b = json.load(open(os.path.join(BUILD, 'v5_board.json')))
    want = [(p['x'], p['y'], p['hole']) for c in b['components'] for p in c['pads'] if p['hole']] + [(v['x'], v['y'], v['hole']) for v in b['vias']]
    kdrl = glob.glob(os.path.join(GDIR, '*.drl'))
    drill_rep = {}
    if kdrl:
        got = []
        import gerbonara as gn, warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            d = gn.ExcellonFile.open(kdrl[0])
        for o in d.objects:
            if type(o).__name__ != 'Flash':
                continue
            u = o.unit
            x, y = X(ad._to_mil(o.x, u), ad._to_mil(o.y, u))
            got.append((x, y, ad._to_mil(o.tool.diameter, u)))
        matched = 0; worst = 0.0; size_mismatch = []
        unmatched_want = []
        for (wx, wy, wd) in want:
            best = None
            for (gx, gy, gd) in got:
                dd = ((gx - wx) ** 2 + (gy - wy) ** 2) ** 0.5
                if best is None or dd < best[0]:
                    best = (dd, gd)
            if best and best[0] <= 1.0:
                matched += 1; worst = max(worst, best[0])
                if abs(best[1] - wd) > 0.2:
                    size_mismatch.append((wx, wy, wd, best[1]))
            else:
                unmatched_want.append((wx, wy, wd))
        from collections import Counter
        drill_rep = {'v5_holes': len(want), 'kicad_holes': len(got), 'matched_within_1mil': matched, 'worst_offset_mil': worst,
                     'size_mismatches': size_mismatch, 'v5_holes_missing_in_kicad': unmatched_want,
                     'v5_by_size': dict(Counter(round(w[2], 2) for w in want)), 'kicad_by_size': dict(Counter(round(g[2], 2) for g in got))}
        print('drill:', {k: v for k, v in drill_rep.items() if k not in ('size_mismatches', 'v5_holes_missing_in_kicad')},
              'size_mismatches', len(size_mismatch), 'missing', len(unmatched_want))
    json.dump({'layers': report, 'drill': drill_rep}, open(os.path.join(BUILD, 'xor_report.json'), 'w'), indent=1)

    # ---- markdown section
    rows = ['| Layer | Film px | KiCad px | XOR px | XOR % of union | XOR % of board area | only film | only KiCad | image |', '|---|---:|---:|---:|---:|---:|---:|---:|---|']
    for lay, r in report.items():
        img = f'v1_xor_{lay.replace(".", "_")}.png'
        rows.append(f"| {lay} | {r['fab_px']} | {r['kicad_px']} | {r['xor_px']} | {r['xor_pct_of_union']:.2f} % | {r['xor_pct_of_board']:.3f} % | {r['only_fab_px']} | {r['only_kicad_px']} | [{img}](img/{img}) |")
    rows.append('')
    rows.append(f"Raster: {scale:g} px/mil ({1000 * scale:g} dpi). Red = copper only in the fabrication film, blue = only in the KiCad export.")
    if drill_rep:
        rows.append(f"\nDrill (KiCad export vs v5 plated holes): {drill_rep['matched_within_1mil']} of {drill_rep['v5_holes']} holes match within 1 mil "
                    f"(worst offset {drill_rep['worst_offset_mil']:.3f} mil); KiCad file has {drill_rep['kicad_holes']} holes; "
                    f"size mismatches: {len(drill_rep['size_mismatches'])}; per size v5={drill_rep['v5_by_size']} kicad={drill_rep['kicad_by_size']}.")
    body = '\n'.join(rows)
    md_path = os.path.join(ROOT, 'docs', 'A0_PROVENANCE.md')
    md = open(md_path, encoding='utf-8').read()
    Bt, Et = '<!-- BEGIN GENERATED xor_compare.py -->', '<!-- END GENERATED xor_compare.py -->'
    if Bt in md and Et in md:
        pre, rest = md.split(Bt, 1); _, post = rest.split(Et, 1); md = pre + Bt + '\n' + body + '\n' + Et + post
    else:
        md += '\n\n## Generated: Gerber XOR (KiCad export vs fabrication films)\n\n' + Bt + '\n' + body + '\n' + Et + '\n'
    open(md_path, 'w', encoding='utf-8').write(md)

if __name__ == '__main__':
    main()
