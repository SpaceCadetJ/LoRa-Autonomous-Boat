#!/usr/bin/env python3
"""allegro_data.py - Shared loaders for the Allegro/OrCAD source data of the LoRa Boat Controller V1.
Import from other tools (sys.path.insert the tools/ dir).  Nothing here writes files.

Provides:
  load_dsn(path)        -> dict: placements, images, padstacks, wires, polygons, vias, nets, rules, boundary
  load_pstxnet(path)    -> {net_name: [(ref, pin, pin_name), ...]}   (NC net dropped; pins normalised '01'->'1')
  load_pstxprt(path)    -> {ref: device_string}
  load_pstchip(path)    -> {device_string: {'part': .., 'jedec': .., 'value': .., 'pins': {number: name}}}
  load_gerber(path)     -> gerbonara GerberFile (units handled by helper functions below)
  flashes(gf)           -> [Flash(x_mil, y_mil, kind, w_mil, h_mil, dcode)]  in Allegro mils
  lines(gf), arcs(gf), regions(gf) -> primitives in mils
  load_drill(path)      -> [(x_mil, y_mil, dia_mil)]
  mil2mm(v), MM_PER_MIL, KICAD_ORIGIN, allegro_to_kicad(x_mil, y_mil) -> (x_mm, y_mm)

Coordinate conventions: Allegro/DSN = mils, Y up, origin = Allegro drawing origin (the Gerbers share it: Offset 0,0).
Gerber files are inches with FS 2.5 -> converted to mils here.  KiCad = mm, Y down.
"""
import os, re, math
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
ALLEGRO = os.path.join(ROOT, 'Allegro', 'hardware', 'allegro-original')
V5DIR = os.path.join(ALLEGRO, 'Allegro v5', 'Allegro')
FAB = os.path.join(ALLEGRO, 'BoatcrewArtwork')
DSN_PATH = os.path.join(V5DIR, 'senior design v2.dsn')
PSTXNET = os.path.join(V5DIR, 'pstxnet.dat')
PSTXPRT = os.path.join(V5DIR, 'pstxprt.dat')
PSTCHIP = os.path.join(V5DIR, 'pstchip.dat')
DRILL_V4 = os.path.join(V5DIR, 'BOATCREWDRILL-1-2.drl')
GERBER = {
    'F.Cu': os.path.join(FAB, 'BOATCREWTOPL.art'),
    'B.Cu': os.path.join(FAB, 'BOATCREWBOTL.art'),
    'F.Mask': os.path.join(FAB, 'BOATCREWMASK_TOP.art'),
    'B.Mask': os.path.join(FAB, 'BOATCREWMASK_BOT.art'),
    'F.SilkS': os.path.join(FAB, 'BOATCREWSILK_TOP.art'),
    'Edge.Cuts': os.path.join(FAB, 'BOATCREWOUTLINE.art'),
}

MM_PER_MIL = 0.0254
# KiCad placement of the Allegro origin (mm).  Board outline spans x -1502..1118 mil, y 36..1505 mil,
# so in KiCad it occupies x 61.85..128.40 mm, y 61.77..99.09 mm.
KICAD_ORIGIN = (100.0, 100.0)

def mil2mm(v):
    return v * MM_PER_MIL

def allegro_to_kicad(x_mil, y_mil):
    return (KICAD_ORIGIN[0] + x_mil * MM_PER_MIL, KICAD_ORIGIN[1] - y_mil * MM_PER_MIL)

def kicad_to_allegro(x_mm, y_mm):
    return ((x_mm - KICAD_ORIGIN[0]) / MM_PER_MIL, (KICAD_ORIGIN[1] - y_mm) / MM_PER_MIL)

# ----------------------------------------------------------------------------------------------
# Minimal S-expression reader for Specctra DSN (single-quote strings, spaces allowed in quotes)
# ----------------------------------------------------------------------------------------------
def _tokenize(text):
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in ' \t\r\n':
            i += 1
        elif c == '(' or c == ')':
            yield c; i += 1
        elif c == "'":
            j = text.index("'", i + 1)
            yield ('str', text[i + 1:j]); i = j + 1
        elif c == '"':
            j = text.index('"', i + 1)
            yield ('str', text[i + 1:j]); i = j + 1
        else:
            j = i
            while j < n and text[j] not in ' \t\r\n()':
                j += 1
            yield ('atom', text[i:j]); i = j

def _parse(tokens):
    stack = [[]]
    for t in tokens:
        if t == '(':
            stack.append([])
        elif t == ')':
            node = stack.pop()
            stack[-1].append(node)
        else:
            kind, val = t
            if kind == 'atom':
                try:
                    val = int(val) if re.fullmatch(r'-?\d+', val) else float(val) if re.fullmatch(r'-?\d*\.\d+(e-?\d+)?', val) else val
                except ValueError:
                    pass
            stack[-1].append(val)
    return stack[0]

def sexp(path):
    txt = open(path, encoding='latin-1').read()
    return _parse(_tokenize(txt))

def _find(node, head):
    return [c for c in node if isinstance(c, list) and c and c[0] == head]

def _find1(node, head, default=None):
    f = _find(node, head)
    return f[0] if f else default

def norm_pin(p):
    p = str(p)
    return str(int(p)) if p.isdigit() else p

def load_dsn(path=DSN_PATH):
    tree = sexp(path)
    pcb = tree[0]
    out = {'source': pcb[1], 'rules': {}, 'placements': [], 'images': {}, 'padstacks': {},
           'wires': [], 'polygons': [], 'vias': [], 'nets': {}, 'boundary': None, 'layers': []}
    structure = _find1(pcb, 'structure')
    for b in _find(structure, 'boundary'):
        r = b[1]
        if r[0] == 'rect' and r[1] == 'signal':
            out['boundary'] = tuple(r[2:6])
    out['layers'] = [l[1] for l in _find(structure, 'layer')]
    for r in _find(structure, 'rule'):
        for item in r[1:]:
            out['rules'][item[0]] = item[1]
    v = _find1(structure, 'via')
    out['via_padstack'] = v[1] if v else None
    placement = _find1(pcb, 'placement')
    for comp in _find(placement, 'component'):
        image = comp[1]
        for pl in _find(comp, 'place'):
            ref = pl[1]
            if len(pl) < 5 or not isinstance(pl[2], (int, float)):
                out['placements'].append({'ref': ref, 'image': image, 'x': None, 'y': None, 'side': None, 'rot': None, 'value': None})
                continue
            prop = _find1(pl, 'property')
            value = None
            if prop:
                vv = _find1(prop, 'value')
                if vv: value = vv[1]
            out['placements'].append({'ref': ref, 'image': image, 'x': float(pl[2]), 'y': float(pl[3]),
                                      'side': pl[4], 'rot': float(pl[5]), 'value': value})
    library = _find1(pcb, 'library')
    for img in _find(library, 'image'):
        name = img[1]
        pins, outlines, keepouts = [], [], []
        for p in _find(img, 'pin'):
            # (pin PADSTACK [ (rotate R) ] NUMBER x y [ (rotate R) ])   -- Allegro puts (rotate) last
            padstack = p[1]; k = 2; rot = 0.0
            if isinstance(p[k], list) and p[k][0] == 'rotate':
                rot = float(p[k][1]); k += 1
            number, x, y = p[k], float(p[k + 1]), float(p[k + 2])
            for extra in p[k + 3:]:
                if isinstance(extra, list) and extra and extra[0] == 'rotate':
                    rot = float(extra[1])
            pins.append({'padstack': padstack, 'number': norm_pin(number), 'x': x, 'y': y, 'rot': rot})
        for o in _find(img, 'outline'):
            pth = o[1]
            if pth[0] == 'path':
                layer, width = pth[1], float(pth[2])
                pts = [(float(pth[i]), float(pth[i + 1])) for i in range(3, len(pth) - 1, 2) if not isinstance(pth[i], list)]
                outlines.append({'layer': layer, 'width': width, 'pts': pts})
        for kind in ('keepout', 'via_keepout', 'place_keepout'):
            for ko in _find(img, kind):
                keepouts.append({'kind': kind, 'raw': ko[1:]})
        out['images'][name] = {'pins': pins, 'outlines': outlines, 'keepouts': keepouts}
    for ps in _find(library, 'padstack'):
        name = ps[1]
        shapes, hole, plating, ptype = [], None, None, None
        for s in _find(ps, 'shape'):
            g = s[1]
            kind, layer = g[0], g[1]
            if kind == 'circle':
                shapes.append({'kind': 'circle', 'layer': layer, 'd': float(g[2]),
                               'x': float(g[3]) if len(g) > 3 else 0.0, 'y': float(g[4]) if len(g) > 4 else 0.0})
            elif kind == 'rect':
                shapes.append({'kind': 'rect', 'layer': layer, 'x1': float(g[2]), 'y1': float(g[3]), 'x2': float(g[4]), 'y2': float(g[5])})
            elif kind == 'polygon':
                pts = [(float(g[i]), float(g[i + 1])) for i in range(3, len(g) - 1, 2)]
                shapes.append({'kind': 'polygon', 'layer': layer, 'aperture': float(g[2]), 'pts': pts})
            elif kind == 'path':
                pts = [(float(g[i]), float(g[i + 1])) for i in range(3, len(g) - 1, 2)]
                shapes.append({'kind': 'path', 'layer': layer, 'width': float(g[2]), 'pts': pts})
        for h in _find(ps, 'hole'):
            g = h[1]
            if g[0] == 'circle':
                hole = float(g[2])
        pl = _find1(ps, 'plating'); plating = pl[1] if pl else None
        ty = _find1(ps, 'type'); ptype = ty[1] if ty else None
        out['padstacks'][name] = {'shapes': shapes, 'hole': hole, 'plating': plating, 'type': ptype}
    network = _find1(pcb, 'network')
    for net in _find(network, 'net'):
        name = str(net[1])
        pins = []
        for pl in _find(net, 'pins'):
            for p in pl[1:]:
                p = str(p)
                ref, pin = p.rsplit('-', 1)
                pins.append((ref, norm_pin(pin)))
        out['nets'][name] = pins
    wiring = _find1(pcb, 'wiring')
    if wiring:
        for w in _find(wiring, 'wire'):
            g = w[1]
            netn = _find1(w, 'net'); netname = str(netn[1]) if netn else None
            ty = _find1(w, 'type'); wtype = ty[1] if ty else None
            if g[0] == 'path':
                layer, width = g[1], float(g[2])
                coords = [c for c in g[3:] if not isinstance(c, list)]
                pts = [(float(coords[i]), float(coords[i + 1])) for i in range(0, len(coords) - 1, 2)]
                out['wires'].append({'layer': layer, 'width': width, 'pts': pts, 'net': netname, 'type': wtype})
            elif g[0] == 'polygon':
                layer = g[1]
                coords = [c for c in g[3:] if not isinstance(c, list)]
                pts = [(float(coords[i]), float(coords[i + 1])) for i in range(0, len(coords) - 1, 2)]
                out['polygons'].append({'layer': layer, 'pts': pts, 'net': netname, 'type': wtype})
        for v in _find(wiring, 'via'):
            netn = _find1(v, 'net'); netname = str(netn[1]) if netn else None
            out['vias'].append({'padstack': v[1], 'x': float(v[2]), 'y': float(v[3]), 'net': netname})
    return out

# ----------------------------------------------------------------------------------------------
# OrCAD packaged netlist (pstxnet / pstxprt / pstchip)
# ----------------------------------------------------------------------------------------------
def load_pstxnet(path=PSTXNET, drop_nc=True):
    txt = open(path, encoding='latin-1').read().replace('\r', '')
    nets, cur = {}, None
    pat = re.compile(r"NET_NAME\n'([^']*)'|NODE_NAME\t(\S+) (\S+)\n[^\n]*\n\s*'([^']*)':;")
    for m in pat.finditer(txt):
        if m.group(1) is not None:
            cur = m.group(1); nets[cur] = []
        else:
            nets[cur].append((m.group(2), norm_pin(m.group(3)), m.group(4)))
    if drop_nc:
        nets.pop('NC', None)
    return nets

def load_pstxprt(path=PSTXPRT):
    txt = open(path, encoding='latin-1').read().replace('\r', '')
    parts = {}
    for m in re.finditer(r"PART_NAME\n\s*(\S+) '([^']*)':;", txt):
        parts[m.group(1)] = m.group(2)
    return parts

def load_pstchip(path=PSTCHIP):
    txt = open(path, encoding='latin-1').read().replace('\r', '')
    devs = {}
    for blk in txt.split('primitive ')[1:]:
        m = re.match(r"'([^']*)';", blk)
        if not m: continue
        name = m.group(1)
        pins = {}
        for pm in re.finditer(r"'([^']*)':\n\s*PIN_NUMBER='\(([^)]*)\)';", blk):
            pins[norm_pin(pm.group(2))] = pm.group(1)
        body = {}
        for bm in re.finditer(r"(PART_NAME|JEDEC_TYPE|VALUE)='([^']*)';", blk):
            body[bm.group(1)] = bm.group(2)
        devs[name] = {'part': body.get('PART_NAME'), 'jedec': body.get('JEDEC_TYPE'), 'value': body.get('VALUE'), 'pins': pins}
    return devs

# ----------------------------------------------------------------------------------------------
# Gerber / drill (gerbonara) -> mils
# ----------------------------------------------------------------------------------------------
class Flash:
    __slots__ = ('x', 'y', 'kind', 'w', 'h', 'dcode', 'obj')
    def __init__(self, x, y, kind, w, h, dcode, obj=None):
        self.x, self.y, self.kind, self.w, self.h, self.dcode, self.obj = x, y, kind, w, h, dcode, obj
    def __repr__(self):
        return f'Flash({self.x:.1f},{self.y:.1f},{self.kind},{self.w:g}x{self.h:g})'

def load_gerber(path):
    import gerbonara as gn
    return gn.GerberFile.open(path)

def _to_mil(gf_unit_value, unit):
    # gerbonara objects carry .unit ('inch' or 'mm')
    if str(unit) in ('inch', 'in', 'Inch'):
        return gf_unit_value * 1000.0
    return gf_unit_value / MM_PER_MIL

def _aperture_dims(ap, unit):
    n = type(ap).__name__
    if n == 'CircleAperture':
        d = _to_mil(ap.diameter, unit); return ('circle', d, d)
    if n == 'RectangleAperture':
        return ('rect', _to_mil(ap.w, unit), _to_mil(ap.h, unit))
    if n == 'ObroundAperture':
        return ('obround', _to_mil(ap.w, unit), _to_mil(ap.h, unit))
    if n == 'PolygonAperture':
        d = _to_mil(ap.diameter, unit); return ('polygon', d, d)
    return (n, 0.0, 0.0)

def flashes(gf):
    out = []
    for o in gf.objects:
        if type(o).__name__ != 'Flash':
            continue
        u = o.unit
        kind, w, h = _aperture_dims(o.aperture, u)
        out.append(Flash(_to_mil(o.x, u), _to_mil(o.y, u), kind, w, h, getattr(o.aperture, 'number', None), o))
    return out

def lines(gf):
    out = []
    for o in gf.objects:
        if type(o).__name__ != 'Line':
            continue
        u = o.unit
        kind, w, h = _aperture_dims(o.aperture, u)
        out.append({'x1': _to_mil(o.x1, u), 'y1': _to_mil(o.y1, u), 'x2': _to_mil(o.x2, u), 'y2': _to_mil(o.y2, u),
                    'width': w, 'kind': kind, 'obj': o})
    return out

def arcs(gf):
    out = []
    for o in gf.objects:
        if type(o).__name__ != 'Arc':
            continue
        u = o.unit
        kind, w, h = _aperture_dims(o.aperture, u)
        out.append({'x1': _to_mil(o.x1, u), 'y1': _to_mil(o.y1, u), 'x2': _to_mil(o.x2, u), 'y2': _to_mil(o.y2, u),
                    'cx': _to_mil(o.cx, u), 'cy': _to_mil(o.cy, u), 'clockwise': o.clockwise, 'width': w, 'obj': o})
    return out

def regions(gf):
    out = []
    for o in gf.objects:
        if type(o).__name__ != 'Region':
            continue
        u = o.unit
        pts = [(_to_mil(x, u), _to_mil(y, u)) for (x, y) in o.outline]
        arcs_ = getattr(o, 'arc_centers', None)
        out.append({'pts': pts, 'arc_centers': arcs_, 'polarity_dark': o.polarity_dark, 'obj': o})
    return out

def load_drill(path=DRILL_V4):
    import warnings, gerbonara as gn
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        d = gn.ExcellonFile.open(path)
    out = []
    for o in d.objects:
        if type(o).__name__ != 'Flash':
            continue
        u = o.unit
        out.append((_to_mil(o.x, u), _to_mil(o.y, u), _to_mil(o.tool.diameter, u)))
    return out

def outline_rect(path=None):
    """Board outline from BOATCREWOUTLINE.art as (xmin, ymin, xmax, ymax) in mils."""
    gf = load_gerber(path or GERBER['Edge.Cuts'])
    xs, ys = [], []
    for l in lines(gf):
        xs += [l['x1'], l['x2']]; ys += [l['y1'], l['y2']]
    return (min(xs), min(ys), max(xs), max(ys))

if __name__ == '__main__':
    d = load_dsn()
    print('DSN', d['source'], 'placements', len(d['placements']), 'images', len(d['images']), 'padstacks', len(d['padstacks']),
          'wires', len(d['wires']), 'polygons', len(d['polygons']), 'vias', len(d['vias']), 'nets', len(d['nets']))
    print('rules', d['rules'], 'via', d['via_padstack'], 'boundary', d['boundary'])
    n = load_pstxnet(); print('pstxnet nets', len(n), sum(len(v) for v in n.values()), 'pins')
    p = load_pstxprt(); print('pstxprt parts', len(p))
    c = load_pstchip(); print('pstchip devices', len(c))
    print('outline mil', outline_rect())
    for lay, path in GERBER.items():
        gf = load_gerber(path)
        print(lay, 'flashes', len(flashes(gf)), 'lines', len(lines(gf)), 'arcs', len(arcs(gf)), 'regions', len(regions(gf)))
    print('drill holes', len(load_drill()))
