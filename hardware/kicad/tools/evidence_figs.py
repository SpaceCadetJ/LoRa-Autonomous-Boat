#!/usr/bin/env python3
"""evidence_figs.py - Copper-evidence figures for the three A4 questions, drawn from the fabricated v5 films
(hardware/kicad/_build/v5_board.json = film copper with nets resolved from pstxnet.dat):
  docs/img/v1_evidence_pwm.png   PA8 (U3-41) -> SPEEDCONTROLLER-2 and PC6 (U3-37) -> STEERINGSERVO-2
  docs/img/v1_evidence_vcap.png  CEXT: pin 1 -> U3 pin 30 (VCAP_1), pin 2 -> +3V3 pour (not VSS)
  docs/img/v1_evidence_can.png   PA12 -> U5-1 TXD, PA11 -> U5-8 STB, PA10 -> U5-4 RXD (no CAN AF on PA10)
Each figure: grey = all F.Cu copper of the film, coloured = the traced nets, labelled pads.  Also writes
hardware/kicad/_build/evidence.json with the pad-to-pad connectivity statements the figures illustrate.
Run from repo root: python hardware/kicad/tools/evidence_figs.py
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import allegro_data as ad
import raster

ROOT = ad.ROOT
BUILD = os.path.join(ROOT, 'hardware', 'kicad', '_build'); IMG = os.path.join(ROOT, 'docs', 'img')
SCALE = 3.0

FIGS = [
    ('v1_evidence_pwm.png', 'PWM outputs: PA8/TIM1_CH1 reaches the SPEEDCONTROLLER header, PC6/TIM3_CH1 the STEERINGSERVO header',
     {'N04355': (220, 40, 40), 'N04395': (30, 120, 220)},
     [('U3', '41', 'U3-41 PA8'), ('SPEEDCONTROLLER', '2', 'SPEEDCONTROLLER-2'), ('TP1', '1', 'TP1'),
      ('U3', '37', 'U3-37 PC6'), ('STEERINGSERVO', '2', 'STEERINGSERVO-2'), ('TP3', '1', 'TP3')],
     (-300, 200, 1000, 1000)),
    ('v1_evidence_vcap.png', 'VCAP: CEXT pin 1 to U3 pin 30 (VCAP_1); CEXT pin 2 returns to the +3V3 pour, not to VSS',
     {'N27791': (220, 40, 40), '3.3V': (240, 160, 30), '0': (40, 160, 70)},
     [('U3', '30', 'U3-30 VCAP_1'), ('CEXT', '1', 'CEXT-1'), ('CEXT', '2', 'CEXT-2 (+3V3)'), ('U3', '31', 'U3-31 VSS'), ('U3', '32', 'U3-32 VDD')],
     (-100, 350, 400, 700)),
    ('v1_evidence_can.png', 'CAN: PA12 -> U5-1 TXD, PA11 -> U5-8 STB, PA10 -> U5-4 RXD (PA10 has no CAN alternate function)',
     {'N04763': (220, 40, 40), 'N04755': (30, 120, 220), 'N04759': (30, 170, 60)},
     [('U3', '45', 'U3-45 PA12'), ('U5', '1', 'U5-1 TXD'), ('U3', '44', 'U3-44 PA11'), ('U5', '8', 'U5-8 STB'),
      ('U3', '43', 'U3-43 PA10'), ('U5', '4', 'U5-4 RXD')],
     (150, 700, 950, 1350)),
]

def main():
    b = json.load(open(os.path.join(BUILD, 'v5_board.json')))
    pads = {(c['ref'], p['number']): p for c in b['components'] for p in c['pads']}
    outline = b['outline_mil']
    gF = ad.load_gerber(ad.GERBER['F.Cu']); gB = ad.load_gerber(ad.GERBER['B.Cu'])
    statements = []
    try:
        font = ImageFont.truetype('arial.ttf', 22); small = ImageFont.truetype('arial.ttf', 16)
    except Exception:
        font = small = ImageFont.load_default()
    for fname, title, nets, marks, crop in FIGS:
        bbox = (crop[0], crop[1], crop[2], crop[3])
        base = raster.Canvas(*bbox, scale=SCALE); raster.draw_gerber(base, gF)
        A = base.array()
        rgb = np.full(A.shape + (3,), 255, dtype=np.uint8)
        rgb[A] = (200, 200, 200)
        # bottom copper of the traced nets, dashed look: draw in lighter tone first
        for lay, gf, tone in (('B.Cu', gB, 0.45), ('F.Cu', gF, 1.0)):
            # colour per net (bottom layer drawn first in a lighter tone, top layer solid on top)
            for net, col in nets.items():
                cn = raster.Canvas(*bbox, scale=SCALE)
                for l in b['copper'][lay]['lines']:
                    if l['dark'] and l['net'] == net:
                        cn.line(l['x1'], l['y1'], l['x2'], l['y2'], l['w'], 255)
                for v in b['vias']:
                    if v['net'] == net:
                        cn.circle(v['x'], v['y'], v['pad'], 255)
                for (ref, num), p in pads.items():
                    if p['net'] == net and (lay == 'F.Cu' or p['hole']):
                        if p['shape'] == 'circle': cn.circle(p['x'], p['y'], p['w'], 255)
                        elif p['shape'] == 'obround': cn.obround(p['x'], p['y'], p['w'], p['h'], 255)
                        else: cn.rect(p['x'], p['y'], p['w'], p['h'], 255)
                Mn = cn.array()
                colv = tuple(int(255 - (255 - ch) * tone) for ch in col)
                rgb[Mn] = colv
        im = Image.fromarray(rgb); d = ImageDraw.Draw(im)
        for i, (ref, num, label) in enumerate(marks):
            p = pads.get((ref, num))
            if not p: continue
            px, py = base.px(p['x'], p['y'])
            r = 14
            d.ellipse([px - r, py - r, px + r, py + r], outline=(0, 0, 0), width=3)
            dy = (-46, 18, -80)[i % 3]   # stagger labels of neighbouring pads (0.5 mm pitch on the LQFP)
            d.line([px, py, px, py + dy + (12 if dy > 0 else 20)], fill=(0, 0, 0), width=2)
            d.text((px + 6, py + dy), label, fill=(0, 0, 0), font=font, stroke_width=3, stroke_fill=(255, 255, 255))
            statements.append({'figure': fname, 'pad': f'{ref}-{num}', 'net_allegro': p['net'], 'x_mil': p['x'], 'y_mil': p['y']})
        d.rectangle([0, 0, im.width, 34], fill=(255, 255, 255))
        d.text((8, 6), title, fill=(0, 0, 0), font=font)
        legend = '   '.join(f'{n}' for n in nets)
        d.text((8, im.height - 24), f'grey = all F.Cu copper of the v5 film; coloured = nets {legend} (F.Cu solid, B.Cu lighter); crop x {crop[0]}..{crop[2]} mil, y {crop[1]}..{crop[3]} mil', fill=(0, 0, 0), font=small, stroke_width=2, stroke_fill=(255, 255, 255))
        im.save(os.path.join(IMG, fname))
        print('wrote', fname, im.size)
    json.dump(statements, open(os.path.join(BUILD, 'evidence.json'), 'w'), indent=1)

if __name__ == '__main__':
    main()
