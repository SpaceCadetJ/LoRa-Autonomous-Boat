#!/usr/bin/env python3
"""raster.py - Rasterize gerbonara GerberFile objects (in Allegro mils, Y up) into numpy bitmaps, honouring
polarity (LPD/LPC) in file order.  Used by v5_reconstruct.py (connectivity) and xor_compare.py (fidelity).
Nothing here writes files unless save_png() is called.
"""
import math
import numpy as np
from PIL import Image, ImageDraw

class Canvas:
    """Bitmap covering [xmin,xmax] x [ymin,ymax] mils at `scale` px/mil (Y up in mils, Y down in pixels)."""
    def __init__(self, xmin, ymin, xmax, ymax, scale=2.0):
        self.xmin, self.ymin, self.xmax, self.ymax, self.scale = xmin, ymin, xmax, ymax, scale
        self.w = int(math.ceil((xmax - xmin) * scale)) + 1
        self.h = int(math.ceil((ymax - ymin) * scale)) + 1
        self.img = Image.new('L', (self.w, self.h), 0)
        self.draw = ImageDraw.Draw(self.img)

    def px(self, x, y):
        return ((x - self.xmin) * self.scale, (self.ymax - y) * self.scale)

    def to_px_len(self, v):
        return v * self.scale

    # ---- primitives (all args in mils) ----
    def circle(self, x, y, d, fill):
        cx, cy = self.px(x, y); r = d * self.scale / 2.0
        self.draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)

    def rect(self, x, y, w, h, fill):
        cx, cy = self.px(x, y); hw, hh = w * self.scale / 2.0, h * self.scale / 2.0
        self.draw.rectangle([cx - hw, cy - hh, cx + hw, cy + hh], fill=fill)

    def obround(self, x, y, w, h, fill):
        cx, cy = self.px(x, y); hw, hh = w * self.scale / 2.0, h * self.scale / 2.0
        r = min(hw, hh)
        self.draw.rounded_rectangle([cx - hw, cy - hh, cx + hw, cy + hh], radius=r, fill=fill)

    def line(self, x1, y1, x2, y2, width, fill):
        p1, p2 = self.px(x1, y1), self.px(x2, y2)
        wpx = max(1, int(round(width * self.scale)))
        self.draw.line([p1, p2], fill=fill, width=wpx)
        r = width * self.scale / 2.0
        if r >= 0.5:
            for (cx, cy) in (p1, p2):
                self.draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)

    def polygon(self, pts, fill):
        if len(pts) < 3:
            return
        self.draw.polygon([self.px(x, y) for (x, y) in pts], fill=fill)

    def polyline(self, pts, width, fill):
        for i in range(len(pts) - 1):
            self.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], width, fill)

    def array(self):
        return np.array(self.img) > 127

    def save_png(self, path):
        self.img.save(path)

# ---------------------------------------------------------------------------------------------
def _unit_mil(v, unit):
    return v * 1000.0 if str(unit) in ('inch', 'in') else v / 0.0254

def arc_points(x1, y1, x2, y2, cx, cy, clockwise, step_deg=3.0):
    """Flatten a circular arc (Gerber semantics: from p1 to p2 around center c) into points incl. endpoints."""
    a1 = math.atan2(y1 - cy, x1 - cx); a2 = math.atan2(y2 - cy, x2 - cx)
    r = math.hypot(x1 - cx, y1 - cy)
    if clockwise:
        if a2 >= a1: a2 -= 2 * math.pi
        sweep = a1 - a2
    else:
        if a2 <= a1: a2 += 2 * math.pi
        sweep = a2 - a1
    if abs(x1 - x2) < 1e-9 and abs(y1 - y2) < 1e-9:
        sweep = 2 * math.pi
    n = max(2, int(math.ceil(math.degrees(sweep) / step_deg)))
    pts = []
    for i in range(n + 1):
        t = i / n
        a = a1 - sweep * t if clockwise else a1 + sweep * t
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    pts[0] = (x1, y1); pts[-1] = (x2, y2)
    return pts

def region_outline_mil(o):
    """Return flattened outline points (mils) of a gerbonara Region, expanding arc segments."""
    u = o.unit
    pts = [(_unit_mil(x, u), _unit_mil(y, u)) for (x, y) in o.outline]
    arcs = getattr(o, 'arc_centers', None) or []
    if not any(arcs):
        return pts
    out = []
    n = len(pts)
    for i in range(n):
        p1 = pts[i]; p2 = pts[(i + 1) % n]
        arc = arcs[i] if i < len(arcs) else None
        if arc:
            clockwise, (cx, cy) = arc
            seg = arc_points(p1[0], p1[1], p2[0], p2[1], _unit_mil(cx, u), _unit_mil(cy, u), clockwise)
            out.extend(seg[:-1])
        else:
            out.append(p1)
    return out

def kicad_xform(origin_mm=(100.0, 100.0)):
    """Transform for KiCad-exported Gerber/Excellon coordinates -> Allegro mils (Y up).
    KiCad plots with Y pointing up, i.e. gerber_y = -kicad_y; the Allegro origin sits at KiCad origin_mm.
    Input coordinates are the plotted values converted to mils."""
    ox, oy = origin_mm[0] / 0.0254, origin_mm[1] / 0.0254
    return lambda x, y: (x - ox, oy + y)

def draw_gerber(canvas, gf, dark_only=False, dark=255, clear=0, xform=None):
    """Draw every object of a gerbonara GerberFile on the canvas in file order with polarity.
    xform: optional (x_mil, y_mil) -> (x_mil, y_mil) similarity applied after arc flattening (may flip Y)."""
    T = xform or (lambda x, y: (x, y))
    for o in gf.objects:
        fill = dark if o.polarity_dark else clear
        if dark_only and not o.polarity_dark:
            continue
        n = type(o).__name__
        u = o.unit
        if n == 'Flash':
            ap = o.aperture; an = type(ap).__name__
            x, y = T(_unit_mil(o.x, u), _unit_mil(o.y, u))
            rot = float(getattr(ap, 'rotation', 0.0) or 0.0)
            if an == 'CircleAperture':
                canvas.circle(x, y, _unit_mil(ap.diameter, u), fill)
            elif an == 'RectangleAperture':
                w, h = _unit_mil(ap.w, u), _unit_mil(ap.h, u)
                if abs((rot % 180) - 90) < 1e-6:
                    w, h = h, w
                canvas.rect(x, y, w, h, fill)
            elif an == 'ObroundAperture':
                w, h = _unit_mil(ap.w, u), _unit_mil(ap.h, u)
                if abs((rot % 180) - 90) < 1e-6:
                    w, h = h, w
                canvas.obround(x, y, w, h, fill)
            elif an == 'PolygonAperture':
                canvas.circle(x, y, _unit_mil(ap.diameter, u), fill)
            else:
                # aperture macro etc.: render its primitives via bounding box fallback
                try:
                    (x0, y0), (x1, y1) = o.bounding_box(unit=u)
                    cx, cy = T((_unit_mil(x0, u) + _unit_mil(x1, u)) / 2, (_unit_mil(y0, u) + _unit_mil(y1, u)) / 2)
                    canvas.rect(cx, cy, _unit_mil(x1 - x0, u), _unit_mil(y1 - y0, u), fill)
                except Exception:
                    pass
        elif n == 'Line':
            w = _unit_mil(getattr(o.aperture, 'diameter', 0.0) or getattr(o.aperture, 'w', 0.0), u)
            (x1, y1), (x2, y2) = T(_unit_mil(o.x1, u), _unit_mil(o.y1, u)), T(_unit_mil(o.x2, u), _unit_mil(o.y2, u))
            canvas.line(x1, y1, x2, y2, w, fill)
        elif n == 'Arc':
            w = _unit_mil(getattr(o.aperture, 'diameter', 0.0) or getattr(o.aperture, 'w', 0.0), u)
            # gerbonara Arc.cx/cy are RELATIVE to the start point (Gerber I/J semantics)
            pts = arc_points(_unit_mil(o.x1, u), _unit_mil(o.y1, u), _unit_mil(o.x2, u), _unit_mil(o.y2, u),
                             _unit_mil(o.x1 + o.cx, u), _unit_mil(o.y1 + o.cy, u), o.clockwise)
            canvas.polyline([T(x, y) for (x, y) in pts], w, fill)
        elif n == 'Region':
            canvas.polygon([T(x, y) for (x, y) in region_outline_mil(o)], fill)

def render_gerber_file(path, bbox, scale=2.0):
    import gerbonara as gn
    gf = gn.GerberFile.open(path)
    c = Canvas(*bbox, scale=scale)
    draw_gerber(c, gf)
    return c
