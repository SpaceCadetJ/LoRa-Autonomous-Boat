#!/usr/bin/env python3
"""v5_reconstruct.py - Reconstruct the fabricated v5 board from the BOATCREW Gerbers + pstxnet.dat.

Inputs : Allegro/hardware/allegro-original/BoatcrewArtwork/*.art (v5 fab films), Allegro v5/Allegro/pstxnet.dat,
         pstxprt.dat, pstchip.dat (v5 netlist, 2025-05-09 17:12), senior design v2.dsn (footprint pad geometry).
Outputs: hardware/kicad/_build/v5_board.json   (components + pads + nets + vias + copper primitives + pours)
         hardware/kicad/_build/v5_labels_{F,B}.png (connectivity rasters, debug)
         docs/A0_PROVENANCE.md generated sections (placement v2->v5 diff, drill provenance, connectivity check)
Run from repo root: python hardware/kicad/tools/v5_reconstruct.py
"""
import os, sys, json, math, collections
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from scipy import ndimage
import allegro_data as ad
import raster

ROOT = ad.ROOT
BUILD = os.path.join(ROOT, 'hardware', 'kicad', '_build')
OUT_JSON = os.path.join(BUILD, 'v5_board.json')
OUT_MD = os.path.join(ROOT, 'docs', 'A0_PROVENANCE.md')
os.makedirs(BUILD, exist_ok=True)

TOL = 1.5       # mil, position tolerance for pad matching
STOL = 0.6      # mil, size tolerance
SCALE = 2.0     # px per mil for connectivity raster
PAD_CLR = 5.0   # mil, pour clearance measured on the films (anti-pads 78.04 on 68 mil pins; void gaps 5.01-5.02 mil)

# ECO report positions (senior design v5.brd, 2025-05-09 17:12:46) used only as a cross-check
ECO_POS = {'C10': (-44, 438), 'C23': (-924, 711), 'CANHEADER': (591, 1392), 'CEXT': (170, 493), 'CIN': (-1279, 254),
           'D21': (-760, 178), 'GPSMODULE': (109, 129), 'JTAG': (278, 1346), 'L1': (-543, 217), 'L3': (-1098, 740),
           'L4': (-1095, 674), 'LORAMODULE': (-837, 725), 'SPEEDCONTROLLER': (868, 666), 'STEERINGSERVO': (870, 432),
           'TP1': (615, 832), 'TP3': (610, 679), 'TP4': (-1326, 996), 'TP5': (-1084, 996), 'U3': (64, 868),
           'U5': (741, 1110), 'U6': (-1037, 160)}

# ----------------------------------------------------------------------------------------------
# 1. Footprint pad patterns (footprint frame, mils, Y up, rot CCW)
# ----------------------------------------------------------------------------------------------
def pad_from_padstack(ps, rot):
    """Return (shape, w, h, hole) for a DSN padstack dict, applying pin rotation to rect/obround dims."""
    hole = ps['hole']
    shape, w, h = None, 0.0, 0.0
    for s in ps['shapes']:
        if s['kind'] == 'rect':
            shape, w, h = 'rect', s['x2'] - s['x1'], s['y2'] - s['y1']; break
        if s['kind'] == 'circle':
            shape, w, h = 'circle', s['d'], s['d']; break
        if s['kind'] == 'path':
            (x1, y1), (x2, y2) = s['pts'][0], s['pts'][1]
            L = math.hypot(x2 - x1, y2 - y1)
            if abs(x2 - x1) > abs(y2 - y1):
                shape, w, h = 'obround', L + s['width'], s['width']
            else:
                shape, w, h = 'obround', s['width'], L + s['width']
            break
    if shape in ('rect', 'obround') and int(round(rot)) % 180 == 90:
        w, h = h, w
    return shape, w, h, hole

def dsn_pattern(dsn, image_name):
    img = dsn['images'].get(image_name)
    if img is None:
        for k in dsn['images']:
            if k.lower() == image_name.lower():
                img = dsn['images'][k]; break
    if img is None:
        return None
    pads = []
    for p in img['pins']:
        shape, w, h, hole = pad_from_padstack(dsn['padstacks'][p['padstack']], p['rot'])
        pads.append({'number': p['number'], 'x': p['x'], 'y': p['y'], 'shape': shape, 'w': w, 'h': h, 'hole': hole,
                     'padstack': p['padstack']})
    return pads

def override_patterns():
    """Footprints that exist on v5 but not in the DSN v2 (or whose pads changed), taken from the v5 Gerber
    flashes and vendor land patterns (KGM21 from CAP_KGM21_KAV-L.xml)."""
    P = {}
    P['CAP_KGM21_KAV-L'] = [{'number': '1', 'x': -27.5, 'y': 0, 'shape': 'rect', 'w': 36, 'h': 47, 'hole': None, 'padstack': 'RX36Y47D0T'},
                            {'number': '2', 'x': 27.5, 'y': 0, 'shape': 'rect', 'w': 36, 'h': 47, 'hole': None, 'padstack': 'RX36Y47D0T'}]
    # Samtec FTSH-105: 2 rows x 5, 50 mil pitch, rows 160.24 mil apart.  Numbering AS FABRICATED (from the v5 copper
    # nets: pin1=3.3V top-right, even pins in the -y row, numbers increase towards -x):
    #   odd pins  (1,3,5,7,9)  row y=+80.12 at x=+100,+50,0,-50,-100
    #   even pins (2,4,6,8,10) row y=-80.12 at x=+100,+50,0,-50,-100
    P['SAMTEC_FTSH-105-XX-X-DV'] = []
    for i in range(5):
        x = 100 - 50 * i
        P['SAMTEC_FTSH-105-XX-X-DV'].append({'number': str(2 * i + 1), 'x': x, 'y': 80.12, 'shape': 'rect', 'w': 29.13, 'h': 109.84, 'hole': None, 'padstack': 'RX29P13Y109P84D0T'})
        P['SAMTEC_FTSH-105-XX-X-DV'].append({'number': str(2 * i + 2), 'x': x, 'y': -80.12, 'shape': 'rect', 'w': 29.13, 'h': 109.84, 'hole': None, 'padstack': 'RX29P13Y109P84D0T'})
    # TDK SLF7045: two pads, each plotted as 2 overlapping 86.61x78.74 rects offset 16.14 mil -> union 86.61 x 94.88,
    # pitch 216.14 mil.  'sub' lists the individual flashes (dx, dy, w, h) relative to the pad centre for matching.
    P['IND_7045_TDK'] = [{'number': '1', 'x': 0, 'y': 108.07, 'shape': 'rect', 'w': 86.61, 'h': 94.88, 'hole': None, 'padstack': 'RX86P61Y94P88(2xRX86P61Y78P74)',
                          'sub': [(0, -8.07, 86.61, 78.74), (0, 8.07, 86.61, 78.74)]},
                         {'number': '2', 'x': 0, 'y': -108.07, 'shape': 'rect', 'w': 86.61, 'h': 94.88, 'hole': None, 'padstack': 'RX86P61Y94P88(2xRX86P61Y78P74)',
                          'sub': [(0, -8.07, 86.61, 78.74), (0, 8.07, 86.61, 78.74)]}]
    # Toshiba M-FLAT: 71 x 38 mil pads, pitch 163
    P['M-FLAT_TOS-L'] = [{'number': '1', 'x': -81.5, 'y': 0, 'shape': 'rect', 'w': 38, 'h': 71, 'hole': None, 'padstack': 'RX38Y71D0T'},
                         {'number': '2', 'x': 81.5, 'y': 0, 'shape': 'rect', 'w': 38, 'h': 71, 'hole': None, 'padstack': 'RX38Y71D0T'}]
    return P

# v5 padstack overrides for footprints whose pads changed between the DSN (v2) and the v5 films
PADSTACK_V5 = {'EX60Y60D40P': ('circle', 68.0, 68.0, 40.0, 'EX68Y68D40P')}

def build_patterns(dsn, refs_jedec):
    pats = {}
    ov = override_patterns()
    for jedec in sorted(set(refs_jedec.values())):
        if jedec in ov:
            pats[jedec] = ov[jedec]; continue
        p = dsn_pattern(dsn, jedec)
        if p is None:
            raise SystemExit(f'no pad pattern for footprint {jedec}')
        for pad in p:
            if pad['padstack'] in PADSTACK_V5:
                shape, w, h, hole, name = PADSTACK_V5[pad['padstack']]
                pad.update(shape=shape, w=w, h=h, hole=hole, padstack=name)
        pats[jedec] = p
    return pats

def rot_xy(x, y, rot):
    r = math.radians(rot); c, s = math.cos(r), math.sin(r)
    return (x * c - y * s, x * s + y * c)

def rotated_pattern(pads, rot):
    out = []
    swap = int(rot) % 180 == 90
    for p in pads:
        x, y = rot_xy(p['x'], p['y'], rot)
        w, h = (p['h'], p['w']) if swap else (p['w'], p['h'])
        q = dict(p); q.update(x=x, y=y, w=w, h=h)
        if 'sub' in p:
            q['sub'] = [(rot_xy(dx, dy, rot)[0], rot_xy(dx, dy, rot)[1], (sh if swap else sw), (sw if swap else sh)) for (dx, dy, sw, sh) in p['sub']]
        out.append(q)
    return out

def pad_flash_specs(p):
    """Flash specs (x, y, shape, w, h) that must all exist for pad p (composite pads have several)."""
    if 'sub' in p:
        return [(p['x'] + dx, p['y'] + dy, p['shape'], sw, sh) for (dx, dy, sw, sh) in p['sub']]
    return [(p['x'], p['y'], p['shape'], p['w'], p['h'])]

# ----------------------------------------------------------------------------------------------
# 2. Flash index of the v5 F.Cu film (all parts are top side; PTH pads are also flashed on B.Cu)
# ----------------------------------------------------------------------------------------------
class FlashIndex:
    def __init__(self, flashes):
        self.f = flashes
        self.by_shape = collections.defaultdict(list)
        for i, fl in enumerate(flashes):
            self.by_shape[(fl.kind, round(fl.w, 1), round(fl.h, 1))].append(i)

    def find(self, x, y, shape, w, h):
        cands = []
        for (k, kw, kh), idxs in self.by_shape.items():
            if k != shape or abs(kw - w) > STOL or abs(kh - h) > STOL:
                continue
            for i in idxs:
                fl = self.f[i]
                if abs(fl.x - x) <= TOL and abs(fl.y - y) <= TOL:
                    cands.append(i)
        return cands

def match_pattern(fi, pads):
    """All placements (X, Y, rot, {pin: flash_idx}) of the pattern in the flash index."""
    found = {}
    for rot in (0, 90, 180, 270):
        rp = rotated_pattern(pads, rot)
        s0 = pad_flash_specs(rp[0])[0]
        anchors = [i for (k, kw, kh), idxs in fi.by_shape.items() if k == s0[2] and abs(kw - s0[3]) <= STOL and abs(kh - s0[4]) <= STOL for i in idxs]
        for i0 in anchors:
            X = fi.f[i0].x - s0[0]; Y = fi.f[i0].y - s0[1]
            assign = {}
            ok = True
            for p in rp:
                idxs = []
                for (sx, sy, sh, sw, shh) in pad_flash_specs(p):
                    c = fi.find(X + sx, Y + sy, sh, sw, shh)
                    if not c:
                        ok = False; break
                    idxs.append(c[0])
                if not ok:
                    break
                assign[p['number']] = idxs
            if ok:
                key = (round(X, 1), round(Y, 1), rot)
                found[key] = assign
    return [(k[0], k[1], k[2], v) for k, v in found.items()]

# ----------------------------------------------------------------------------------------------
# 3. Copper connectivity by rasterization + connected components
# ----------------------------------------------------------------------------------------------
def copper_labels(gf, bbox):
    c = raster.Canvas(*bbox, scale=SCALE)
    raster.draw_gerber(c, gf)
    arr = c.array()
    labels, n = ndimage.label(arr, structure=np.ones((3, 3)))
    return c, labels, n

def label_at(canvas, labels, x, y):
    px, py = canvas.px(x, y)
    ix, iy = int(round(px)), int(round(py))
    if 0 <= ix < labels.shape[1] and 0 <= iy < labels.shape[0]:
        return int(labels[iy, ix])
    return 0

class UF:
    def __init__(self): self.p = {}
    def find(self, a):
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]; a = self.p[a]
        return a
    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb: self.p[rb] = ra

# ----------------------------------------------------------------------------------------------
def main():
    dsn = ad.load_dsn()
    nets = ad.load_pstxnet()
    parts = ad.load_pstxprt()
    chips = ad.load_pstchip()
    pin_net = {}
    for n, pins in nets.items():
        for ref, pin, pname in pins:
            pin_net[(ref, pin)] = n
    refs_jedec = {ref: chips[dev]['jedec'] for ref, dev in parts.items()}
    patterns = build_patterns(dsn, refs_jedec)

    gF = ad.load_gerber(ad.GERBER['F.Cu']); gB = ad.load_gerber(ad.GERBER['B.Cu'])
    gMT = ad.load_gerber(ad.GERBER['F.Mask']); gMB = ad.load_gerber(ad.GERBER['B.Mask'])
    F = [f for f in ad.flashes(gF) if f.obj.polarity_dark]
    B = [f for f in ad.flashes(gB) if f.obj.polarity_dark]
    MT = ad.flashes(gMT); MB = ad.flashes(gMB)
    fi = FlashIndex(F)
    outline = ad.outline_rect()
    bbox = (outline[0] - 60, outline[1] - 60, outline[2] + 60, outline[3] + 60)

    # --- connectivity rasters
    cF, labF, nF = copper_labels(gF, bbox)
    cB, labB, nB = copper_labels(gB, bbox)
    cF.save_png(os.path.join(BUILD, 'v5_copper_F.png')); cB.save_png(os.path.join(BUILD, 'v5_copper_B.png'))
    print(f'copper islands: F.Cu {nF}, B.Cu {nB}')
    uf = UF()
    vias = [f for f in F if f.kind == 'circle' and abs(f.w - 24.0) < STOL]
    for v in vias:
        lf, lb = label_at(cF, labF, v.x, v.y), label_at(cB, labB, v.x, v.y)
        if lf and lb: uf.union(('F', lf), ('B', lb))
    # PTH pads (present on both films) also join layers
    bset = {(round(f.x, 1), round(f.y, 1)) for f in B}
    for f in F:
        if (round(f.x, 1), round(f.y, 1)) in bset and not (f.kind == 'circle' and abs(f.w - 24.0) < STOL):
            lf, lb = label_at(cF, labF, f.x, f.y), label_at(cB, labB, f.x, f.y)
            if lf and lb: uf.union(('F', lf), ('B', lb))

    def flash_group(idx):
        fl = F[idx]
        return uf.find(('F', label_at(cF, labF, fl.x, fl.y)))

    # --- candidates per component
    cands = {}
    for ref, jedec in refs_jedec.items():
        cands[ref] = match_pattern(fi, patterns[jedec])
        if not cands[ref]:
            print(f'!! no placement candidates for {ref} ({jedec})')

    # --- constraint propagation: group -> net
    group_net = {}
    assigned = {}
    used_flashes = set()
    notes = {}

    def flat(assign):
        return [i for v in assign.values() for i in v]

    def implied(ref, cand):
        X, Y, rot, assign = cand
        m = {}
        for pin, fidxs in assign.items():
            n = pin_net.get((ref, pin))
            g = flash_group(fidxs[0])
            if n is None:
                continue  # NC pin: no constraint
            if g in m and m[g] != n:
                return None  # self-conflict
            m[g] = n
        return m

    def consistent(m):
        return all(group_net.get(g, n) == n for g, n in m.items())

    remaining = set(cands)
    rounds = 0
    while remaining and rounds < 200:
        rounds += 1
        progress = False
        # 1) forced assignments
        for ref in sorted(remaining):
            ok = []
            for cand in cands[ref]:
                if any(f in used_flashes for f in flat(cand[3])):
                    continue
                m = implied(ref, cand)
                if m is None or not consistent(m):
                    continue
                ok.append((cand, m))
            if len(ok) == 1:
                cand, m = ok[0]
                assigned[ref] = cand; used_flashes.update(flat(cand[3])); group_net.update(m)
                remaining.discard(ref); progress = True
            elif len(ok) == 0:
                notes[ref] = 'NO CONSISTENT CANDIDATE'
        if progress:
            continue
        # 2) no forced move: pick the component whose consistent candidates are all "equivalent" (add no new info)
        best = None
        for ref in sorted(remaining):
            ok = []
            for cand in cands[ref]:
                if any(f in used_flashes for f in flat(cand[3])):
                    continue
                m = implied(ref, cand)
                if m is None or not consistent(m):
                    continue
                new_info = {g: n for g, n in m.items() if g not in group_net}
                ok.append((cand, m, new_info))
            if not ok:
                continue
            # prefer candidates that add no new info (interchangeable), else fewest candidates
            ok.sort(key=lambda t: (len(t[2]), t[0][0], t[0][1], t[0][2]))
            score = (len(ok[0][2]), len(ok))
            if best is None or score < best[0]:
                best = (score, ref, ok)
        if best is None:
            break
        score, ref, ok = best
        cand, m, new_info = ok[0]
        assigned[ref] = cand; used_flashes.update(flat(cand[3])); group_net.update(m)
        remaining.discard(ref)
        notes[ref] = f'interchangeable among {len(ok)} candidate spots/rotations; picked by deterministic order' if len(ok) > 1 else ''
    if remaining:
        print('!! unresolved components:', sorted(remaining), {r: notes.get(r) for r in remaining})

    # --- verification: shorts & opens
    shorts, opens = [], []
    grp_nets = collections.defaultdict(set)
    net_groups = collections.defaultdict(set)
    for ref, (X, Y, rot, assign) in assigned.items():
        for pin, fidxs in assign.items():
            n = pin_net.get((ref, pin))
            g = flash_group(fidxs[0])
            if n is None:
                continue
            grp_nets[g].add(n); net_groups[n].add(g)
    for g, ns in grp_nets.items():
        if len(ns) > 1: shorts.append((g, sorted(ns)))
    for n, gs in net_groups.items():
        if len(gs) > 1: opens.append((n, len(gs)))
    # vias net
    via_out = []
    for v in vias:
        g = uf.find(('F', label_at(cF, labF, v.x, v.y)))
        via_out.append({'x': v.x, 'y': v.y, 'net': group_net.get(g), 'pad': 24.0, 'hole': 13.0})
    # all copper groups with a net (for track net assignment)
    root_net = {}
    for g, n in group_net.items():
        root_net[g] = n

    # --- mask openings per pad
    def mask_at(mflashes, x, y):
        for m in mflashes:
            if abs(m.x - x) <= TOL and abs(m.y - y) <= TOL:
                return (m.kind, m.w, m.h)
        return None

    comps = []
    for ref in sorted(assigned):
        X, Y, rot, assign = assigned[ref]
        jedec = refs_jedec[ref]
        pat = rotated_pattern(patterns[jedec], rot)
        pads = []
        for p in pat:
            fl = F[assign[p['number']][0]]
            g = flash_group(assign[p['number']][0])
            px, py = (X + p['x'], Y + p['y']) if 'sub' in p else (fl.x, fl.y)
            mt = mask_at(MT, fl.x, fl.y); mb = mask_at(MB, fl.x, fl.y) if p['hole'] else None
            if 'sub' in p and mt:
                mt = (mt[0], mt[1], mt[2] + abs(p['sub'][0][1] - p['sub'][1][1]))  # union of the two sub-flash mask openings
            pads.append({'number': p['number'], 'x': px, 'y': py, 'shape': p['shape'], 'w': p['w'], 'h': p['h'],
                         'hole': p['hole'], 'padstack': p['padstack'], 'net': pin_net.get((ref, p['number'])),
                         'group_net': group_net.get(g), 'mask_top': mt, 'mask_bot': mb,
                         'fx': p['x'], 'fy': p['y']})
        dev = parts[ref]
        comps.append({'ref': ref, 'jedec': jedec, 'device': dev, 'part': chips[dev]['part'], 'value': chips[dev]['value'],
                      'x': X, 'y': Y, 'rot': rot, 'side': 'F', 'pads': pads, 'note': notes.get(ref, ''),
                      'eco_xy': ECO_POS.get(ref)})

    # --- copper primitives with nets (for the PCB generator)
    def prim_net(canvas, labels, layer, x, y):
        l = label_at(canvas, labels, x, y)
        return group_net.get(uf.find((layer, l))) if l else None
    copper = {}
    for lay, gf, canvas, labels in (('F.Cu', gF, cF, labF), ('B.Cu', gB, cB, labB)):
        Lyr = 'F' if lay == 'F.Cu' else 'B'
        lines_, regs_, clears_ = [], [], []
        for o in gf.objects:
            n = type(o).__name__
            if n == 'Line':
                u = o.unit
                x1, y1, x2, y2 = (ad._to_mil(o.x1, u), ad._to_mil(o.y1, u), ad._to_mil(o.x2, u), ad._to_mil(o.y2, u))
                w = ad._to_mil(getattr(o.aperture, 'diameter', 0.0), u)
                lines_.append({'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'w': w,
                               'net': prim_net(canvas, labels, Lyr, (x1 + x2) / 2, (y1 + y2) / 2), 'dark': bool(o.polarity_dark)})
            elif n == 'Region':
                pts = raster.region_outline_mil(o)
                cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
                netname = None
                if o.polarity_dark:
                    # sample the net at an interior point of the region (and at a few vertices as fallback)
                    from shapely.geometry import Polygon
                    ns = collections.Counter()
                    try:
                        rp = Polygon(pts).buffer(0).representative_point()
                        nn = prim_net(canvas, labels, Lyr, rp.x, rp.y)
                        if nn: ns[nn] += 3
                    except Exception:
                        pass
                    for (x, y) in pts[::max(1, len(pts) // 25)]:
                        nn = prim_net(canvas, labels, Lyr, x, y)
                        if nn: ns[nn] += 1
                    netname = ns.most_common(1)[0][0] if ns else None
                regs_.append({'pts': pts, 'net': netname, 'dark': bool(o.polarity_dark), 'npts': len(pts)})
            elif n == 'Flash' and not o.polarity_dark:
                u = o.unit; kind, w, h = ad._aperture_dims(o.aperture, u)
                clears_.append({'x': ad._to_mil(o.x, u), 'y': ad._to_mil(o.y, u), 'kind': kind, 'w': w, 'h': h})
        copper[lay] = {'lines': lines_, 'regions': regs_, 'clear_flashes': clears_}

    # --- pour keep-outs: film voids NOT explained by the 5 mil clearance around other-net pads/tracks/vias.
    # These are the component-body route keep-outs, the LoRa module keep-out rectangle and Allegro's fill smoothing.
    # Pour islands that Allegro re-plots as separate dark regions inside a void are subtracted (they are copper).
    from shapely.geometry import Polygon, box, Point, LineString
    from shapely.ops import unary_union, split
    def hole_free(poly):
        out = []
        stack = [poly]
        while stack:
            g = stack.pop()
            if g.is_empty or g.area < 1:
                continue
            if g.geom_type != 'Polygon':
                stack.extend(list(g.geoms)); continue
            if not g.interiors:
                out.append(g); continue
            hx = g.interiors[0].centroid.x
            cutter = LineString([(hx, g.bounds[1] - 1), (hx, g.bounds[3] + 1)])
            pieces = split(g, cutter)
            if len(pieces.geoms) <= 1:
                out.append(Polygon(g.exterior)); continue
            stack.extend(list(pieces.geoms))
        return out
    def padpoly(p):
        if p['shape'] == 'circle':
            return Point(p['x'], p['y']).buffer(p['w'] / 2, 32)
        return box(p['x'] - p['w'] / 2, p['y'] - p['h'] / 2, p['x'] + p['w'] / 2, p['y'] + p['h'] / 2)
    pour_keepouts = {}
    for lay in ('F.Cu', 'B.Cu'):
        C = copper[lay]
        pournet = C['regions'][0]['net'] if C['regions'] else None
        clears = [Polygon(r['pts']).buffer(0) for r in C['regions'] if not r['dark']]
        for cf in C['clear_flashes']:
            if cf['kind'] == 'circle':
                clears.append(Point(cf['x'], cf['y']).buffer(cf['w'] / 2, 48))
            else:
                clears.append(box(cf['x'] - cf['w'] / 2, cf['y'] - cf['h'] / 2, cf['x'] + cf['w'] / 2, cf['y'] + cf['h'] / 2))
        voids = unary_union(clears)
        islands = unary_union([Polygon(r['pts']).buffer(0) for r in C['regions'][1:] if r['dark']]) if len(C['regions']) > 1 else None
        items = []
        for c in comps:
            for p in c['pads']:
                if p['hole'] or lay == 'F.Cu':
                    items.append(padpoly(p).buffer(PAD_CLR + 0.5))
        for l in C['lines']:
            if l['dark'] and l['net'] != pournet:
                items.append(LineString([(l['x1'], l['y1']), (l['x2'], l['y2'])]).buffer(l['w'] / 2 + PAD_CLR + 0.5))
        for v in via_out:
            if v['net'] != pournet:
                items.append(Point(v['x'], v['y']).buffer(12 + PAD_CLR + 0.5, 48))
        un = voids.difference(unary_union(items))
        if islands is not None and not islands.is_empty:
            un = un.difference(islands.buffer(0.01))
        polys = []
        for g in hole_free(un):
            if g.area < 100:
                continue
            g = g.simplify(0.25)
            cx, cy = g.centroid.x, g.centroid.y
            near = min(comps, key=lambda c: (c['x'] - cx) ** 2 + (c['y'] - cy) ** 2)
            polys.append({'pts': [(float(x), float(y)) for (x, y) in g.exterior.coords[:-1]], 'area': float(g.area), 'near': near['ref']})
        polys.sort(key=lambda p: -p['area'])
        pour_keepouts[lay] = polys
        print(f'{lay}: {len(polys)} pour keep-outs from film voids (total {sum(p["area"] for p in polys):.0f} mil2)')

    # --- drill provenance (v4 drill file vs v5 PTH pads)
    drill = ad.load_drill()
    pth = [(p['x'], p['y'], p['hole']) for c in comps for p in c['pads'] if p['hole']] + [(v['x'], v['y'], 13.0) for v in via_out]
    d_unmatched = [d for d in drill if not any(abs(d[0] - x) < 1 and abs(d[1] - y) < 1 for x, y, h in pth)]
    p_unmatched = [p for p in pth if not any(abs(p[0] - x) < 1 and abs(p[1] - y) < 1 for x, y, h in drill)]

    out = {'source': {'films': 'BoatcrewArtwork/BOATCREW*.art (senior design v5.brd, 2025-05-09 17:41)',
                      'netlist': 'Allegro v5/Allegro/pstxnet.dat (2025-05-09 17:12)', 'footprints': 'senior design v2.dsn + v5 overrides'},
           'outline_mil': outline, 'bbox_mil': bbox, 'components': comps, 'vias': via_out, 'nets': {n: [list(p) for p in v] for n, v in nets.items()},
           'copper': copper, 'pour_keepouts': pour_keepouts, 'shorts': shorts, 'opens': opens,
           'drill_v4_vs_v5': {'drill_holes': len(drill), 'v5_pth': len(pth), 'drill_without_v5_pad': len(d_unmatched), 'v5_pad_without_drill': len(p_unmatched)},
           'islands': {'F.Cu': nF, 'B.Cu': nB}}
    json.dump(out, open(OUT_JSON, 'w'), indent=1, default=float)
    print(f'wrote {OUT_JSON}: {len(comps)} components, {len(via_out)} vias, shorts={len(shorts)} opens={len(opens)}')
    for s in shorts: print('  SHORT', s)
    for o in opens: print('  OPEN', o)
    unlabeled_vias = [v for v in via_out if v['net'] is None]
    if unlabeled_vias: print('  vias without net:', unlabeled_vias)

    # --- markdown sections
    v2 = {p['ref']: p for p in dsn['placements']}
    rows = ['| Ref | v2 image (DSN) | v2 x,y,rot (mil) | v5 footprint | v5 x,y,rot (mil) | moved | ECO xy | note |', '|---|---|---|---|---|---|---|---|']
    moved = 0
    for c in comps:
        r = c['ref']; p2 = v2.get(r)
        img2 = p2['image'] if p2 else '(absent in v2)'
        if p2 and p2['x'] is not None:
            xy2 = f"{p2['x']:.0f}, {p2['y']:.0f}, {p2['rot']:.0f}"
            d = math.hypot(p2['x'] - c['x'], p2['y'] - c['y'])
            mv = f'{d:.0f} mil' if d > 1 else 'no'
            if d > 1: moved += 1
        else:
            xy2, mv = '-', '-'
        eco = c['eco_xy']
        ecos = '-' if eco is None else ('ok' if abs(eco[0] - c['x']) < 1.5 and abs(eco[1] - c['y']) < 1.5 else f'MISMATCH {eco}')
        rows.append(f"| {r} | {img2} | {xy2} | {c['jedec']} | {c['x']:.2f}, {c['y']:.2f}, {c['rot']} | {mv} | {ecos} | {c['note']} |")
    gone = [p['ref'] for p in dsn['placements'] if p['ref'] not in assigned]
    sec1 = '\n'.join(rows) + f"\n\nComponents present in DSN v2 but absent from v5: **{', '.join(gone)}**. Components moved between v2 and v5: **{moved} of {len(comps)}** (the v5 board is a re-layout on a smaller outline)."
    sec2 = (f"v4 drill file `BOATCREWDRILL-1-2.drl`: {len(drill)} holes. v5 films: {len(pth)} plated holes (pads {len(pth) - len(via_out)} + vias {len(via_out)}).\n"
            f"Drill holes with no v5 pad within 1 mil: **{len(d_unmatched)}**. v5 holes with no drill entry: **{len(p_unmatched)}**. "
            f"=> the drill file is not the v5 fab drill; hole positions for KiCad are taken from the v5 pad flashes, hole sizes from the padstacks "
            f"(VIA 13 mil, headers 40 mil, JST 49 mil, TP 55.12 mil, battery pads 23.62 mil).")
    sec3 = (f"Copper islands: F.Cu {nF}, B.Cu {nB}. Pads matched: {sum(len(c['pads']) for c in comps)}. Vias: {len(via_out)} "
            f"({sum(1 for v in via_out if v['net'] == '0')} on GND). Shorts (islands carrying two nets): **{len(shorts)}** {shorts if shorts else ''}. "
            f"Opens (nets split across islands): **{len(opens)}** {opens if opens else ''}. Unresolved refs: {sorted(remaining) if remaining else 'none'}.")
    md = open(OUT_MD, encoding='utf-8').read()
    for tag, body in (('placement', sec1), ('drill', sec2), ('connectivity', sec3)):
        B, E = f'<!-- BEGIN GENERATED v5_reconstruct.py {tag} -->', f'<!-- END GENERATED v5_reconstruct.py {tag} -->'
        if B in md and E in md:
            pre, rest = md.split(B, 1); _, post = rest.split(E, 1); md = pre + B + '\n' + body + '\n' + E + post
        else:
            md += f'\n\n## Generated: {tag}\n\n' + B + '\n' + body + '\n' + E + '\n'
    open(OUT_MD, 'w', encoding='utf-8').write(md)
    print('updated', OUT_MD)
    for c in comps:
        if c['eco_xy'] and not (abs(c['eco_xy'][0] - c['x']) < 1.5 and abs(c['eco_xy'][1] - c['y']) < 1.5):
            print('  ECO mismatch', c['ref'], c['eco_xy'], (c['x'], c['y']))
    return out

if __name__ == '__main__':
    main()
