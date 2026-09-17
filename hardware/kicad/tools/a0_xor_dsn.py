#!/usr/bin/env python3
"""a0_xor_dsn.py - A0 check the brief asked for: can the DSN v2 wiring (senior design v2.dsn, exported from v2.brd)
be used directly for the fabricated v5 board?  Rasterizes the DSN v2 copper (wires, vias, polygons, and the pads of
the v2 placement) per layer into the Allegro frame and XORs it against the v5 films; also compares the DSN v2 via
list with the v5 via flashes and the DSN placement with the v5 placement.
Outputs: docs/img/v1_xor_dsn2_vs_v5_{F,B}_Cu.png, hardware/kicad/_build/dsn_vs_v5.json, and the generated section
'dsn' in docs/A0_PROVENANCE.md.   Run from repo root: python hardware/kicad/tools/a0_xor_dsn.py
"""
import os, sys, json, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image
import allegro_data as ad
import raster
import v5_reconstruct as v5

ROOT = ad.ROOT
IMG = os.path.join(ROOT, 'docs', 'img'); BUILD = os.path.join(ROOT, 'hardware', 'kicad', '_build')

def rot_xy(x, y, r):
    a = math.radians(r); c, s = math.cos(a), math.sin(a)
    return x * c - y * s, x * s + y * c

def main():
    dsn = ad.load_dsn()
    outline = ad.outline_rect()
    # frame: union of the v2 3x3 in board and the v5 outline
    bbox = (min(-1500, outline[0]) - 40, min(-1500, outline[1]) - 40, max(1500, outline[2]) + 40, max(1500, outline[3]) + 40)
    scale = 2.0
    rep = {}
    for lay, dsn_layer in (('F.Cu', 'TOP'), ('B.Cu', 'BOTTOM')):
        c = raster.Canvas(*bbox, scale=scale)
        # polygons (pours) first
        for p in dsn['polygons']:
            if p['layer'] == dsn_layer:
                c.polygon(p['pts'], 255)
        for w in dsn['wires']:
            if w['layer'] == dsn_layer:
                c.polyline(w['pts'], w['width'], 255)
        for v in dsn['vias']:
            ps = dsn['padstacks'].get(v['padstack'], {})
            d = next((s['d'] for s in ps.get('shapes', []) if s['kind'] == 'circle'), 24.0)
            c.circle(v['x'], v['y'], d, 255)
        # pads of the v2 placement
        for pl in dsn['placements']:
            if pl['x'] is None:
                continue
            img = dsn['images'].get(pl['image']) or dsn['images'].get(pl['image'].rsplit('_', 1)[0])
            if not img:
                continue
            for pin in img['pins']:
                shape, w, h, hole = v5.pad_from_padstack(dsn['padstacks'][pin['padstack']], pin['rot'])
                if hole is None and dsn_layer == 'BOTTOM':
                    continue
                x, y = rot_xy(pin['x'], pin['y'], pl['rot'])
                x += pl['x']; y += pl['y']
                if int(pl['rot']) % 180 == 90 and shape in ('rect', 'obround'):
                    w, h = h, w
                if shape == 'circle':
                    c.circle(x, y, w, 255)
                elif shape == 'obround':
                    c.obround(x, y, w, h, 255)
                else:
                    c.rect(x, y, w, h, 255)
        A = c.array()
        cf = raster.Canvas(*bbox, scale=scale); raster.draw_gerber(cf, ad.load_gerber(ad.GERBER[lay])); B = cf.array()
        both, only_dsn, only_fab = A & B, A & ~B, B & ~A
        rgb = np.zeros(A.shape + (3,), dtype=np.uint8)
        rgb[both] = (235, 235, 235); rgb[only_fab] = (230, 40, 40); rgb[only_dsn] = (40, 90, 230)
        Image.fromarray(rgb).save(os.path.join(IMG, f'v1_xor_dsn2_vs_v5_{lay.replace(".", "_")}.png'))
        u = int((A | B).sum()); x = int((A ^ B).sum())
        rep[lay] = {'dsn_px': int(A.sum()), 'fab_px': int(B.sum()), 'xor_px': x, 'xor_pct_of_union': 100.0 * x / max(1, u)}
        print(f'{lay}: DSN v2 vs v5 film XOR = {rep[lay]["xor_pct_of_union"]:.1f} % of union')
    # vias: DSN v2 vs v5 flashes
    F = [f for f in ad.flashes(ad.load_gerber(ad.GERBER['F.Cu'])) if f.obj.polarity_dark and f.kind == 'circle' and abs(f.w - 24) < 0.6]
    matched = sum(1 for v in dsn['vias'] if any(abs(f.x - v['x']) < 1 and abs(f.y - v['y']) < 1 for f in F))
    rep['vias'] = {'dsn_v2': len(dsn['vias']), 'v5_film': len(F), 'same_position': matched}
    # placement: DSN v2 vs v5 (from v5_board.json)
    b = json.load(open(os.path.join(BUILD, 'v5_board.json')))
    v5pos = {c['ref']: (c['x'], c['y'], c['rot']) for c in b['components']}
    same = [pl['ref'] for pl in dsn['placements'] if pl['ref'] in v5pos and pl['x'] is not None and abs(pl['x'] - v5pos[pl['ref']][0]) < 1 and abs(pl['y'] - v5pos[pl['ref']][1]) < 1]
    rep['placement'] = {'dsn_v2_components': sum(1 for p in dsn['placements'] if p['x'] is not None), 'v5_components': len(v5pos),
                        'unmoved': same, 'only_in_v2': sorted(p['ref'] for p in dsn['placements'] if p['ref'] not in v5pos),
                        'only_in_v5': sorted(r for r in v5pos if r not in {p['ref'] for p in dsn['placements']})}
    print('vias', rep['vias']); print('placement', {k: v for k, v in rep['placement'].items()})
    json.dump(rep, open(os.path.join(BUILD, 'dsn_vs_v5.json'), 'w'), indent=1)
    body = (f"DSN v2 copper rasterized (wires + vias + polygons + pads of the v2 placement) against the v5 films: "
            f"F.Cu XOR **{rep['F.Cu']['xor_pct_of_union']:.1f} %**, B.Cu XOR **{rep['B.Cu']['xor_pct_of_union']:.1f} %** of the union "
            f"([F.Cu image](img/v1_xor_dsn2_vs_v5_F_Cu.png), [B.Cu image](img/v1_xor_dsn2_vs_v5_B_Cu.png); blue = DSN v2 only, red = v5 film only). "
            f"Vias: DSN v2 has {rep['vias']['dsn_v2']}, v5 film has {rep['vias']['v5_film']}, at the same position: {rep['vias']['same_position']}. "
            f"Placement: {len(same)} of {rep['placement']['dsn_v2_components']} v2 components are at their v2 position on v5 ({', '.join(same) if same else 'none'}); "
            f"only in v2: {', '.join(rep['placement']['only_in_v2'])}; only in v5: {', '.join(rep['placement']['only_in_v5'])}. "
            f"Conclusion: the DSN v2 wiring cannot be reused; v5 is a re-layout on a 2.62 x 1.47 in outline. The reconstruction takes copper from the films and nets from pstxnet.dat.")
    md_path = os.path.join(ROOT, 'docs', 'A0_PROVENANCE.md')
    md = open(md_path, encoding='utf-8').read()
    Bt, Et = '<!-- BEGIN GENERATED a0_xor_dsn.py -->', '<!-- END GENERATED a0_xor_dsn.py -->'
    if Bt in md and Et in md:
        pre, rest = md.split(Bt, 1); _, post = rest.split(Et, 1); md = pre + Bt + '\n' + body + '\n' + Et + post
    else:
        md += '\n\n## Generated: DSN v2 wiring vs v5 films\n\n' + Bt + '\n' + body + '\n' + Et + '\n'
    open(md_path, 'w', encoding='utf-8').write(md)

if __name__ == '__main__':
    main()
