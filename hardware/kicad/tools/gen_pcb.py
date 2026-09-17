#!/usr/bin/env python3
"""gen_pcb.py - Generate hardware/kicad/LoRa_Boat_Controller.kicad_pcb (+ .kicad_pro) from the reconstructed v5
board (hardware/kicad/_build/v5_board.json) and the project footprint library.

Copper: every dark Gerber line -> track (net from copper connectivity); via flashes -> vias; the top +3V3 pour and the
bottom GND pour -> zones with the Gerber region as outline; the bottom 580x706 mil clear rectangle -> rule area
(no copper pour); floating dark regions -> no-net filled polygons.  Pads get a local clearance equal to the Allegro
anti-pad ring (5 mil) and zone connection "none" because Allegro's thermal spokes are plotted as explicit lines
(imported as tracks).  Silkscreen/outline are imported 1:1 from the films.  Coordinates: Allegro mil -> KiCad mm
via allegro_data.allegro_to_kicad (origin at KiCad 100,100 mm, Y flipped).

Inputs : hardware/kicad/_build/v5_board.json, LoRa_Boat_Controller.pretty (gen_footprints.py), the films.
Outputs: hardware/kicad/LoRa_Boat_Controller.kicad_pcb, hardware/kicad/LoRa_Boat_Controller.kicad_pro,
         hardware/kicad/_build/netmap.json (Allegro net -> KiCad net name)
Run from repo root: python hardware/kicad/tools/gen_pcb.py
"""
import os, sys, json, math
sys.path.insert(0, os.path.dirname(__file__))
import allegro_data as ad
import raster
from kicad_write import uid, f, mm, esc
from v1_design import kicad_ref, symbol_path

ROOT = ad.ROOT
KDIR = os.path.join(ROOT, 'hardware', 'kicad')
BUILD = os.path.join(KDIR, '_build')
PCB = os.path.join(KDIR, 'LoRa_Boat_Controller.kicad_pcb')
PRO = os.path.join(KDIR, 'LoRa_Boat_Controller.kicad_pro')
LIB = 'LoRa_Boat_Controller'

# Allegro net name -> readable KiCad net name.  Names by MCU pin where the old names were misleading.
NET_NAME = {
    '0': 'GND', '3.3V': '+3V3', 'N088060': 'VIN_RAW', 'N18028': 'SW_NODE', 'N17942': 'BST', 'N148600': 'EN',
    'N17576': 'FB_DIV', 'N061071': 'BST_RC', 'ADC': 'ADC_VBAT', 'N27791': 'VCAP1',
    'N04429': 'LORA_VCC', 'N27410': 'LORA_FILT', 'N04477': 'LORA_TX_PA0', 'N04485': 'LORA_RX_PA1', 'N24517': 'LORA_RST_PA3',
    'N04277': 'GPS_PB0', 'N04281': 'GPS_RX_PC11', 'N04285': 'GPS_TX_PC10',
    # N04855 lands on U5 pin 6 = CANL and N24691 on U5 pin 7 = CANH (TI SLLSES9D Table 6-1); the old NETLIST.md had them reversed
    'N04755': 'CAN_STB_PA11', 'N04759': 'CAN_RXD_PA10', 'N04763': 'CAN_TXD_PA12', 'N04855': 'CANL', 'N24691': 'CANH', 'N24886': 'CAN_VCC',
    'N04355': 'PWM_PA8_ESCHDR', 'N04395': 'PWM_PC6_SERVOHDR',
    'PA13 TMS': 'SWDIO', 'PA14 TCLK': 'SWCLK', 'PB3 TBO': 'SWO_TDO', 'PA15 TDI': 'TDI', 'RESET': 'NRST', 'VBAT': 'VBAT',
}
# Clearances measured on the v5 films (see docs/A0_PROVENANCE.md): the dynamic pours keep 5.0 mil from every
# other-net track, pad and via (Allegro anti-pads 78.04 mil on 68 mil pins, void gaps 5.01-5.02 mil around tracks).
ZONE_CLEARANCE_MIL = 5.0
PAD_CLEARANCE_MIL = 5.0
NETCLASS_CLEARANCE_MIL = 12.0   # design intent from senior design v2_rules.do; as-fabricated exceptions live in the .kicad_dru
ZONE_MIN_THICKNESS_MM = 0.1
EDGE_WIDTH_MIL = 5.0            # BOATCREWOUTLINE.art is drawn with a 5 mil aperture
# As-fabricated minimum spacings found by KiCad DRC on the imported copper (docs/V1_DESIGN_REVIEW.md, DRC section)
FAB_RULES = [
    ('fab_pour_clearance', "A.Type == 'Zone' || B.Type == 'Zone'", 5.0,
     'dynamic pours keep 5.0 mil from other-net copper (measured on 20 voids, F.Cu and B.Cu)'),
    ('fab_track_track', "A.Type == 'Track' && B.Type == 'Track'", 7.5,
     'adjacent-pin fan-out traces from the 0.5 mm LQFP-64 run at pin pitch: 19.685 - 12 = 7.685 mil (40 places, min 7.64)'),
    ('fab_track_via', "(A.Type == 'Track' && B.Type == 'Via') || (A.Type == 'Via' && B.Type == 'Track')", 9.5,
     'one place: CAN_RXD_PA10 track vs CAN_STB_PA11 via at 9.79 mil'),
    ('fab_track_pad', "(A.Type == 'Track' && B.Type == 'Pad') || (A.Type == 'Pad' && B.Type == 'Track')", 3.3,
     'U3 pad 62 (NC) vs GND track from pad 63: 3.37 mil; +3V3 track vs C3 pad 1 (GND): 4.8 mil'),
]
TRACK_MIL = 12.0
VIA_PAD_MIL, VIA_DRILL_MIL = 24.0, 13.0
CRTYD_MARGIN_MIL = 0.0   # courtyard = pad extents; v5 places parts closer than IPC courtyards (fabricated and assembled)
# Pads whose fabricated neighbours are closer than the 5 mil anti-pad ring (measured by DRC on the imported copper):
PAD_CLEARANCE_OVERRIDES = {('U3', '62'): 3.3,   # NC pad PB9: GND fan-out track from pad 63 passes at 3.37 mil
                           ('C3', '1'): 4.8}    # GND pad: +3V3 track passes at 4.80 mil

LAYERS = '''\t(layers
\t\t(0 "F.Cu" signal)
\t\t(2 "B.Cu" signal)
\t\t(9 "F.Adhes" user "F.Adhesive")
\t\t(11 "B.Adhes" user "B.Adhesive")
\t\t(13 "F.Paste" user)
\t\t(15 "B.Paste" user)
\t\t(5 "F.SilkS" user "F.Silkscreen")
\t\t(7 "B.SilkS" user "B.Silkscreen")
\t\t(1 "F.Mask" user)
\t\t(3 "B.Mask" user)
\t\t(17 "Dwgs.User" user "User.Drawings")
\t\t(19 "Cmts.User" user "User.Comments")
\t\t(21 "Eco1.User" user "User.Eco1")
\t\t(23 "Eco2.User" user "User.Eco2")
\t\t(25 "Edge.Cuts" user)
\t\t(27 "Margin" user)
\t\t(31 "F.CrtYd" user "F.Courtyard")
\t\t(29 "B.CrtYd" user "B.Courtyard")
\t\t(35 "F.Fab" user)
\t\t(33 "B.Fab" user)
\t)'''

def K(x_mil, y_mil):
    x, y = ad.allegro_to_kicad(x_mil, y_mil)
    return f'{f(x)} {f(y)}'

def pts_block(pts_mil, indent='\t\t\t'):
    return '\n'.join(f'{indent}(xy {K(x, y)})' for (x, y) in pts_mil)

def main():
    b = json.load(open(os.path.join(BUILD, 'v5_board.json')))
    parts = ad.load_pstxprt(); chips = ad.load_pstchip()
    pin_names = {}
    for n, pins in b['nets'].items():
        for ref, pin, pname in pins:
            pin_names[(ref, pin)] = pname
    # nets
    allegro_nets = sorted(b['nets'].keys(), key=lambda n: (n not in ('0', '3.3V'), NET_NAME.get(n, n)))
    netid = {}
    lines = ['(kicad_pcb', '\t(version 20241229)', '\t(generator "gen_pcb.py")', '\t(generator_version "9.0")',
             '\t(general\n\t\t(thickness 1.6)\n\t\t(legacy_teardrops no)\n\t)', '\t(paper "A4")',
             '\t(title_block\n\t\t(title "LoRa Autonomous Boat Controller V1 (as fabricated)")\n\t\t(date "2025-05-09")\n\t\t(rev "senior design v5.brd")\n'
             '\t\t(company "University of Arkansas EECS")\n\t\t(comment 1 "Reconstructed from BOATCREW*.art (Cadence Allegro 22.1, 2025-05-09 17:41) + pstxnet.dat (2025-05-09 17:12)")\n'
             '\t\t(comment 2 "Generated by hardware/kicad/tools/gen_pcb.py - do not hand-edit; see README.md")\n\t)', LAYERS]
    lines.append(f'''\t(setup
\t\t(stackup
\t\t\t(layer "F.SilkS"
\t\t\t\t(type "Top Silk Screen")
\t\t\t)
\t\t\t(layer "F.Paste"
\t\t\t\t(type "Top Solder Paste")
\t\t\t)
\t\t\t(layer "F.Mask"
\t\t\t\t(type "Top Solder Mask")
\t\t\t\t(thickness 0.01)
\t\t\t)
\t\t\t(layer "F.Cu"
\t\t\t\t(type "copper")
\t\t\t\t(thickness 0.035)
\t\t\t)
\t\t\t(layer "dielectric 1"
\t\t\t\t(type "core")
\t\t\t\t(thickness 1.51)
\t\t\t\t(material "FR4")
\t\t\t\t(epsilon_r 4.5)
\t\t\t\t(loss_tangent 0.02)
\t\t\t)
\t\t\t(layer "B.Cu"
\t\t\t\t(type "copper")
\t\t\t\t(thickness 0.035)
\t\t\t)
\t\t\t(layer "B.Mask"
\t\t\t\t(type "Bottom Solder Mask")
\t\t\t\t(thickness 0.01)
\t\t\t)
\t\t\t(layer "B.Paste"
\t\t\t\t(type "Bottom Solder Paste")
\t\t\t)
\t\t\t(layer "B.SilkS"
\t\t\t\t(type "Bottom Silk Screen")
\t\t\t)
\t\t\t(copper_finish "None")
\t\t\t(dielectric_constraints no)
\t\t)
\t\t(pad_to_mask_clearance {f(mm(10.0))})
\t\t(tenting none)
\t\t(allow_soldermask_bridges_in_footprints no)
\t\t(pcbplotparams
\t\t\t(layerselection 0x00000000_00000000_55555555_5755f5ff)
\t\t\t(plot_on_all_layers_selection 0x00000000_00000000_00000000_00000000)
\t\t\t(disableapertmacros no)
\t\t\t(usegerberextensions no)
\t\t\t(usegerberattributes yes)
\t\t\t(usegerberadvancedattributes yes)
\t\t\t(creategerberjobfile yes)
\t\t\t(dashed_line_dash_ratio 12.0)
\t\t\t(dashed_line_gap_ratio 3.0)
\t\t\t(svgprecision 4)
\t\t\t(plotframeref no)
\t\t\t(mode 1)
\t\t\t(useauxorigin no)
\t\t\t(hpglpennumber 1)
\t\t\t(hpglpenspeed 20)
\t\t\t(hpglpendiameter 15.0)
\t\t\t(pdf_front_fp_property_popups yes)
\t\t\t(pdf_back_fp_property_popups yes)
\t\t\t(pdf_metadata yes)
\t\t\t(pdf_single_document no)
\t\t\t(dxfpolygonmode yes)
\t\t\t(dxfimperialunits yes)
\t\t\t(dxfusepcbnewfont yes)
\t\t\t(psnegative no)
\t\t\t(psa4output no)
\t\t\t(plot_black_and_white yes)
\t\t\t(sketchpadsonfab no)
\t\t\t(plotpadnumbers no)
\t\t\t(hidednponfab no)
\t\t\t(sketchdnponfab yes)
\t\t\t(crossoutdnponfab yes)
\t\t\t(subtractmaskfromsilk no)
\t\t\t(outputformat 1)
\t\t\t(mirror no)
\t\t\t(drillshape 1)
\t\t\t(scaleselection 1)
\t\t\t(outputdirectory "")
\t\t)
\t)''')
    lines.append('\t(net 0 "")')
    for i, n in enumerate(allegro_nets, start=1):
        netid[n] = i
        lines.append(f'\t(net {i} "{esc(NET_NAME.get(n, n))}")')
    json.dump({n: NET_NAME.get(n, n) for n in allegro_nets}, open(os.path.join(BUILD, 'netmap.json'), 'w'), indent=1)

    def netref(n):
        """Pad-style net reference (number + name)."""
        if n is None:
            return '(net 0 "")'
        return f'(net {netid[n]} "{esc(NET_NAME.get(n, n))}")'

    def netnum(n):
        """Track/via-style net reference (number only)."""
        return '(net 0)' if n is None else f'(net {netid[n]})'

    # ---- footprints
    fp_table = {t['jedec']: t for t in json.load(open(os.path.join(BUILD, 'footprint_table.json')))}
    for c in b['components']:
        ref, jedec, rot = c['ref'], c['jedec'], c['rot']
        t = fp_table[jedec]
        dev = c['device']
        is_th = any(p['hole'] for p in c['pads'])
        at = f'(at {K(c["x"], c["y"])} {f(rot)})' if rot else f'(at {K(c["x"], c["y"])})'
        kref = kicad_ref(ref)
        L = [f'\t(footprint "{LIB}:{esc(jedec)}"', '\t\t(layer "F.Cu")', f'\t\t(uuid "{uid("fp", ref)}")', f'\t\t{at}',
             f'\t\t(descr "{esc(t.get("descr", ""))}")' if t.get('descr') else None,
             f'\t\t(property "Reference" "{esc(kref)}"\n\t\t\t(at 0 0 {f(rot)})\n\t\t\t(layer "F.Fab")\n\t\t\t(uuid "{uid("fp", ref, "Reference")}")\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 0.6 0.6)\n\t\t\t\t\t(thickness 0.1)\n\t\t\t\t)\n\t\t\t)\n\t\t)',
             f'\t\t(property "Allegro_RefDes" "{esc(ref)}"\n\t\t\t(at 0 0 {f(rot)})\n\t\t\t(layer "F.Fab")\n\t\t\t(hide yes)\n\t\t\t(uuid "{uid("fp", ref, "Allegro_RefDes")}")\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t\t(thickness 0.15)\n\t\t\t\t)\n\t\t\t)\n\t\t)',
             f'\t\t(property "Value" "{esc(c["value"])}"\n\t\t\t(at 0 1.2 {f(rot)})\n\t\t\t(layer "F.Fab")\n\t\t\t(hide yes)\n\t\t\t(uuid "{uid("fp", ref, "Value")}")\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 0.6 0.6)\n\t\t\t\t\t(thickness 0.1)\n\t\t\t\t)\n\t\t\t)\n\t\t)',
             f'\t\t(property "Footprint" "{LIB}:{esc(jedec)}"\n\t\t\t(at 0 0 {f(rot)})\n\t\t\t(layer "F.Fab")\n\t\t\t(hide yes)\n\t\t\t(uuid "{uid("fp", ref, "Footprint")}")\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t\t(thickness 0.15)\n\t\t\t\t)\n\t\t\t)\n\t\t)',
             f'\t\t(property "Datasheet" ""\n\t\t\t(at 0 0 {f(rot)})\n\t\t\t(layer "F.Fab")\n\t\t\t(hide yes)\n\t\t\t(uuid "{uid("fp", ref, "Datasheet")}")\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t\t(thickness 0.15)\n\t\t\t\t)\n\t\t\t)\n\t\t)',
             f'\t\t(property "Description" "{esc(c["part"])}"\n\t\t\t(at 0 0 {f(rot)})\n\t\t\t(layer "F.Fab")\n\t\t\t(hide yes)\n\t\t\t(uuid "{uid("fp", ref, "Description")}")\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t\t(thickness 0.15)\n\t\t\t\t)\n\t\t\t)\n\t\t)',
             f'\t\t(property "Allegro_Device" "{esc(dev)}"\n\t\t\t(at 0 0 {f(rot)})\n\t\t\t(layer "F.Fab")\n\t\t\t(hide yes)\n\t\t\t(uuid "{uid("fp", ref, "Allegro_Device")}")\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t\t(thickness 0.15)\n\t\t\t\t)\n\t\t\t)\n\t\t)',
             f'\t\t(path "{symbol_path(ref)}")',
             '\t\t(attr through_hole)' if is_th else '\t\t(attr smd)']
        L = [x for x in L if x is not None]
        # local geometry (unrotated footprint frame, Y flipped)
        tp = t['pads']
        xs = [p['x'] + s * p['w'] / 2 for p in tp for s in (-1, 1)]; ys = [p['y'] + s * p['h'] / 2 for p in tp for s in (-1, 1)]
        bx0, bx1, by0, by1 = min(xs), max(xs), min(ys), max(ys)
        cm = CRTYD_MARGIN_MIL
        L.append(f'\t\t(fp_rect\n\t\t\t(start {f(mm(bx0 - cm))} {f(mm(-(by1 + cm)))})\n\t\t\t(end {f(mm(bx1 + cm))} {f(mm(-(by0 - cm)))})\n\t\t\t(stroke\n\t\t\t\t(width 0.05)\n\t\t\t\t(type default)\n\t\t\t)\n\t\t\t(fill no)\n\t\t\t(layer "F.CrtYd")\n\t\t\t(uuid "{uid("fp", ref, "crtyd")}")\n\t\t)')
        L.append(f'\t\t(fp_rect\n\t\t\t(start {f(mm(bx0))} {f(mm(-by1))})\n\t\t\t(end {f(mm(bx1))} {f(mm(-by0))})\n\t\t\t(stroke\n\t\t\t\t(width 0.1)\n\t\t\t\t(type default)\n\t\t\t)\n\t\t\t(fill no)\n\t\t\t(layer "F.Fab")\n\t\t\t(uuid "{uid("fp", ref, "fab")}")\n\t\t)')
        pads_by_num = {p['number']: p for p in c['pads']}
        for p in tp:
            inst = pads_by_num[p['n']]
            shape = {'rect': 'rect', 'circle': 'circle', 'obround': 'oval'}[p['shape']]
            n = inst['net']
            nr = netref(n)
            pf = pin_names.get((ref, p['n']))
            pfn = f'\n\t\t\t(pinfunction "{esc(pf)}")' if pf and pf != p['n'] else ''
            mg = f(mm(p['mask_margin']))
            clr = f(mm(PAD_CLEARANCE_OVERRIDES.get((ref, p['n']), PAD_CLEARANCE_MIL)))
            if p['hole']:
                L.append(f'\t\t(pad "{p["n"]}" thru_hole {shape}\n\t\t\t(at {f(mm(p["x"]))} {f(mm(-p["y"]))} {f(rot)})\n\t\t\t(size {f(mm(p["w"]))} {f(mm(p["h"]))})\n\t\t\t(drill {f(mm(p["hole"]))})\n\t\t\t(layers "*.Cu" "*.Mask")\n\t\t\t(remove_unused_layers no)\n\t\t\t{nr}{pfn}\n\t\t\t(solder_mask_margin {mg})\n\t\t\t(clearance {clr})\n\t\t\t(zone_connect 0)\n\t\t\t(uuid "{uid("fp", ref, "pad", p["n"])}")\n\t\t)')
            else:
                L.append(f'\t\t(pad "{p["n"]}" smd {shape}\n\t\t\t(at {f(mm(p["x"]))} {f(mm(-p["y"]))} {f(rot)})\n\t\t\t(size {f(mm(p["w"]))} {f(mm(p["h"]))})\n\t\t\t(layers "F.Cu" "F.Paste" "F.Mask")\n\t\t\t{nr}{pfn}\n\t\t\t(solder_mask_margin {mg})\n\t\t\t(clearance {clr})\n\t\t\t(zone_connect 0)\n\t\t\t(uuid "{uid("fp", ref, "pad", p["n"])}")\n\t\t)')
        L.append('\t\t(embedded_fonts no)')
        L.append('\t)')
        lines.append('\n'.join(L))

    # ---- board outline
    gE = ad.load_gerber(ad.GERBER['Edge.Cuts'])
    for i, l in enumerate(ad.lines(gE)):
        lines.append(f'\t(gr_line\n\t\t(start {K(l["x1"], l["y1"])})\n\t\t(end {K(l["x2"], l["y2"])})\n\t\t(stroke\n\t\t\t(width {f(mm(EDGE_WIDTH_MIL))})\n\t\t\t(type default)\n\t\t)\n\t\t(layer "Edge.Cuts")\n\t\t(uuid "{uid("edge", i)}")\n\t)')

    # ---- silkscreen 1:1 from the film
    gS = ad.load_gerber(ad.GERBER['F.SilkS'])
    k = 0
    for o in gS.objects:
        n = type(o).__name__; u = o.unit
        if n == 'Line':
            w = ad._to_mil(getattr(o.aperture, 'diameter', 0.0), u)
            lines.append(f'\t(gr_line\n\t\t(start {K(ad._to_mil(o.x1, u), ad._to_mil(o.y1, u))})\n\t\t(end {K(ad._to_mil(o.x2, u), ad._to_mil(o.y2, u))})\n\t\t(stroke\n\t\t\t(width {f(mm(w))})\n\t\t\t(type solid)\n\t\t)\n\t\t(layer "F.SilkS")\n\t\t(uuid "{uid("silk", k)}")\n\t)')
        elif n == 'Arc':
            w = ad._to_mil(getattr(o.aperture, 'diameter', 0.0), u)
            x1, y1, x2, y2 = ad._to_mil(o.x1, u), ad._to_mil(o.y1, u), ad._to_mil(o.x2, u), ad._to_mil(o.y2, u)
            cx, cy = ad._to_mil(o.x1 + o.cx, u), ad._to_mil(o.y1 + o.cy, u)
            pts = raster.arc_points(x1, y1, x2, y2, cx, cy, o.clockwise)
            if abs(x1 - x2) < 1e-6 and abs(y1 - y2) < 1e-6:
                r = math.hypot(x1 - cx, y1 - cy)
                lines.append(f'\t(gr_circle\n\t\t(center {K(cx, cy)})\n\t\t(end {K(cx + r, cy)})\n\t\t(stroke\n\t\t\t(width {f(mm(w))})\n\t\t\t(type solid)\n\t\t)\n\t\t(fill no)\n\t\t(layer "F.SilkS")\n\t\t(uuid "{uid("silk", k)}")\n\t)')
            else:
                mid = pts[len(pts) // 2]
                lines.append(f'\t(gr_arc\n\t\t(start {K(x1, y1)})\n\t\t(mid {K(mid[0], mid[1])})\n\t\t(end {K(x2, y2)})\n\t\t(stroke\n\t\t\t(width {f(mm(w))})\n\t\t\t(type solid)\n\t\t)\n\t\t(layer "F.SilkS")\n\t\t(uuid "{uid("silk", k)}")\n\t)')
        elif n == 'Region':
            pts = raster.region_outline_mil(o)
            lines.append(f'\t(gr_poly\n\t\t(pts\n{pts_block(pts)}\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type solid)\n\t\t)\n\t\t(fill yes)\n\t\t(layer "F.SilkS")\n\t\t(uuid "{uid("silk", k)}")\n\t)')
        k += 1

    # ---- tracks and vias
    for lay in ('F.Cu', 'B.Cu'):
        for i, l in enumerate(b['copper'][lay]['lines']):
            if not l['dark']:
                continue
            lines.append(f'\t(segment\n\t\t(start {K(l["x1"], l["y1"])})\n\t\t(end {K(l["x2"], l["y2"])})\n\t\t(width {f(mm(l["w"]))})\n\t\t(layer "{lay}")\n\t\t{netnum(l["net"])}\n\t\t(uuid "{uid("seg", lay, i)}")\n\t)')
    for i, v in enumerate(b['vias']):
        lines.append(f'\t(via\n\t\t(at {K(v["x"], v["y"])})\n\t\t(size {f(mm(v["pad"]))})\n\t\t(drill {f(mm(v["hole"]))})\n\t\t(layers "F.Cu" "B.Cu")\n\t\t{netnum(v["net"])}\n\t\t(uuid "{uid("via", i)}")\n\t)')

    # ---- zones: the dynamic pours (first dark region on each layer: +3V3 on F.Cu, GND on B.Cu).  Allegro's voids
    # and the pour islands it re-plots as separate regions are NOT imported: KiCad regenerates them from the measured
    # 5 mil clearance (island removal off), which the XOR check in xor_compare.py verifies.
    zc = f(mm(ZONE_CLEARANCE_MIL))
    for lay in ('F.Cu', 'B.Cu'):
        regs = [r for r in b['copper'][lay]['regions'] if r['dark']]
        for i, r in enumerate(regs):
            if r['net'] is None:
                continue  # pour island already covered by the zone fill
            nid = netid[r['net']]; nname = esc(NET_NAME.get(r['net'], r['net']))
            lines.append(f'\t(zone\n\t\t(net {nid})\n\t\t(net_name "{nname}")\n\t\t(layer "{lay}")\n\t\t(uuid "{uid("zone", lay, i)}")\n\t\t(name "{nname} pour ({lay}) from film")\n\t\t(hatch edge 0.5)\n\t\t(priority 0)\n\t\t(connect_pads no\n\t\t\t(clearance {zc})\n\t\t)\n\t\t(min_thickness {f(ZONE_MIN_THICKNESS_MM)})\n\t\t(filled_areas_thickness no)\n\t\t(fill yes\n\t\t\t(thermal_gap {f(mm(PAD_CLEARANCE_MIL))})\n\t\t\t(thermal_bridge_width {f(mm(TRACK_MIL))})\n\t\t\t(island_removal_mode 1)\n\t\t)\n\t\t(polygon\n\t\t\t(pts\n{pts_block(r["pts"], "\t\t\t\t")}\n\t\t\t)\n\t\t)\n\t)')
        # rule areas (copper pour not allowed) = film voids not explained by the 5 mil clearance: the LoRa module
        # keep-out rectangle (580 x 706 mil, both layers), footprint body keep-outs, Allegro fill smoothing
        for i, ko in enumerate(b.get('pour_keepouts', {}).get(lay, [])):
            what = 'LoRa module keep-out' if ko['area'] > 300000 else f'pour void near {ko["near"]}'
            lines.append(f'\t(zone\n\t\t(net 0)\n\t\t(net_name "")\n\t\t(layer "{lay}")\n\t\t(uuid "{uid("keepout", lay, i)}")\n\t\t(name "{what} ({lay}) from film")\n\t\t(hatch edge 0.5)\n\t\t(priority 1)\n\t\t(connect_pads\n\t\t\t(clearance 0)\n\t\t)\n\t\t(min_thickness 0.25)\n\t\t(filled_areas_thickness no)\n\t\t(keepout\n\t\t\t(tracks allowed)\n\t\t\t(vias allowed)\n\t\t\t(pads allowed)\n\t\t\t(copperpour not_allowed)\n\t\t\t(footprints allowed)\n\t\t)\n\t\t(fill\n\t\t\t(thermal_gap 0.5)\n\t\t\t(thermal_bridge_width 0.5)\n\t\t)\n\t\t(polygon\n\t\t\t(pts\n{pts_block(ko["pts"], "\t\t\t\t")}\n\t\t\t)\n\t\t)\n\t)')
    lines.append('\t(embedded_fonts no)')
    lines.append(')')
    open(PCB, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
    print('wrote', PCB, f'({len(b["components"])} footprints, {sum(len(b["copper"][l]["lines"]) for l in ("F.Cu","B.Cu"))} tracks, {len(b["vias"])} vias)')

    # ---- project file (design rules from senior design v2_rules.do, clearance adjusted to the fabricated copper)
    pro = {
        "board": {
            "3dviewports": [],
            "design_settings": {
                "defaults": {"board_outline_line_width": 0.1, "copper_line_width": 0.2, "copper_text_size_h": 1.5, "copper_text_size_v": 1.5,
                             "copper_text_thickness": 0.3, "courtyard_line_width": 0.05, "fab_line_width": 0.1, "other_line_width": 0.1,
                             "silk_line_width": 0.127, "silk_text_size_h": 1.0, "silk_text_size_v": 1.0, "silk_text_thickness": 0.15},
                "diff_pair_dimensions": [],
                "drc_exclusions": [],
                "meta": {"version": 2},
                "rule_severities": {
                    "annular_width": "error", "clearance": "error", "connection_width": "warning", "copper_edge_clearance": "error",
                    "copper_sliver": "warning", "courtyards_overlap": "error", "diff_pair_gap_out_of_range": "error",
                    "diff_pair_uncoupled_length_too_long": "error", "drill_out_of_range": "error", "duplicate_footprints": "warning",
                    "extra_footprint": "warning", "footprint": "error", "footprint_symbol_mismatch": "warning", "footprint_type_mismatch": "ignore",
                    "hole_clearance": "error", "hole_near_hole": "error", "invalid_outline": "error", "isolated_copper": "warning",
                    "item_on_disabled_layer": "error", "items_not_allowed": "error", "length_out_of_range": "error", "lib_footprint_issues": "warning",
                    "lib_footprint_mismatch": "warning", "malformed_courtyard": "error", "microvia_drill_out_of_range": "error",
                    "missing_courtyard": "ignore", "missing_footprint": "warning", "net_conflict": "warning", "npth_inside_courtyard": "ignore",
                    "padstack": "warning", "pth_inside_courtyard": "ignore", "shorting_items": "error", "silk_edge_clearance": "warning",
                    "silk_over_copper": "warning", "silk_overlap": "warning", "skew_out_of_range": "error", "solder_mask_bridge": "warning",
                    "starved_thermal": "error", "text_height": "warning", "text_thickness": "warning", "through_hole_pad_without_hole": "error",
                    "too_many_vias": "error", "track_dangling": "warning", "track_width": "error", "tracks_crossing": "error",
                    "unconnected_items": "error", "unresolved_variable": "error", "via_dangling": "warning", "zones_intersect": "error"
                },
                "rules": {
                    "max_error": 0.005, "min_clearance": mm(3.3), "min_connection": 0.0, "min_copper_edge_clearance": 0.0,
                    "min_hole_clearance": mm(5.0), "min_hole_to_hole": 0.25, "min_microvia_diameter": 0.2, "min_microvia_drill": 0.1,
                    "min_resolved_spokes": 0, "min_silk_clearance": 0.0, "min_text_height": 0.6, "min_text_thickness": 0.08,
                    "min_through_hole_diameter": mm(VIA_DRILL_MIL), "min_track_width": mm(TRACK_MIL), "min_via_annular_width": mm(5.0),
                    "min_via_diameter": mm(VIA_PAD_MIL), "solder_mask_to_copper_clearance": 0.0, "use_height_for_length_calcs": True
                },
                "teardrop_options": [{"td_onpadsmd": True, "td_onroundshapesonly": False, "td_ontrackend": False, "td_onviapad": True}],
                "teardrop_parameters": [
                    {"td_allow_use_two_tracks": True, "td_curve_segcount": 0, "td_height_ratio": 1.0, "td_length_ratio": 0.5, "td_maxheight": 2.0, "td_maxlen": 1.0, "td_on_pad_in_zone": False, "td_target_name": "td_round_shape", "td_width_to_size_filter_ratio": 0.9},
                    {"td_allow_use_two_tracks": True, "td_curve_segcount": 0, "td_height_ratio": 1.0, "td_length_ratio": 0.5, "td_maxheight": 2.0, "td_maxlen": 1.0, "td_on_pad_in_zone": False, "td_target_name": "td_rect_shape", "td_width_to_size_filter_ratio": 0.9},
                    {"td_allow_use_two_tracks": True, "td_curve_segcount": 0, "td_height_ratio": 1.0, "td_length_ratio": 0.5, "td_maxheight": 2.0, "td_maxlen": 1.0, "td_on_pad_in_zone": False, "td_target_name": "td_track_end", "td_width_to_size_filter_ratio": 0.9}
                ],
                "track_widths": [0.0, mm(TRACK_MIL)],
                "tuning_pattern_settings": {"diff_pair_defaults": {"corner_radius_percentage": 80, "corner_style": 1, "max_amplitude": 1.0, "min_amplitude": 0.2, "single_sided": False, "spacing": 1.0},
                                            "diff_pair_skew_defaults": {"corner_radius_percentage": 80, "corner_style": 1, "max_amplitude": 1.0, "min_amplitude": 0.2, "single_sided": False, "spacing": 0.6},
                                            "single_track_defaults": {"corner_radius_percentage": 80, "corner_style": 1, "max_amplitude": 1.0, "min_amplitude": 0.2, "single_sided": False, "spacing": 0.6}},
                "via_dimensions": [{"diameter": 0.0, "drill": 0.0}, {"diameter": mm(VIA_PAD_MIL), "drill": mm(VIA_DRILL_MIL)}],
                "zones_allow_external_fillets": False
            },
            "ipc2581": {"dist": "", "distpn": "", "internal_id": "", "mfg": "", "mpn": ""},
            "layer_pairs": [], "layer_presets": [], "viewports": []
        },
        "boards": [], "cvpcb": {"equivalence_files": []},
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": "LoRa_Boat_Controller.kicad_pro", "version": 3},
        "net_settings": {
            "classes": [{"bus_width": 12, "clearance": mm(NETCLASS_CLEARANCE_MIL), "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25, "diff_pair_width": 0.2,
                         "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1, "name": "Default", "pcb_color": "rgba(0, 0, 0, 0.000)",
                         "priority": 2147483647, "schematic_color": "rgba(0, 0, 0, 0.000)", "track_width": mm(TRACK_MIL), "via_diameter": mm(VIA_PAD_MIL),
                         "via_drill": mm(VIA_DRILL_MIL), "wire_width": 6}],
            "meta": {"version": 4},
            "net_colors": None, "netclass_assignments": None, "netclass_patterns": []
        },
        "pcbnew": {"last_paths": {"gencad": "", "idf": "", "netlist": "", "plot": "", "pos_files": "", "specctra_dsn": "", "step": "", "svg": "", "vrml": ""}, "page_layout_descr_file": ""},
        "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
        "sheets": [], "text_variables": {}
    }
    json.dump(pro, open(PRO, 'w', encoding='utf-8'), indent=2)
    print('wrote', PRO)

    # ---- custom DRC rules: as-fabricated exceptions to the 12 mil netclass rule (documented, measured)
    dru = ['(version 1)',
           '# LoRa Boat Controller V1 - as-fabricated copper rules.  Generated by hardware/kicad/tools/gen_pcb.py.',
           '# The netclass keeps the 12 mil clearance from senior design v2_rules.do; the fabricated v5 copper (BOATCREW films)',
           '# is tighter in the places listed below (Allegro itself reported 150 DRC errors on v5 at artwork time, batch_drc.log).',
           '# Each rule states the measured minimum; see docs/V1_DESIGN_REVIEW.md and docs/A0_PROVENANCE.md.', '']
    for name, cond, mil_, why in FAB_RULES:
        dru.append(f'# {why}')
        dru.append(f'(rule "{name}"\n\t(condition "{cond}")\n\t(constraint clearance (min {mil_:g}mil))\n)\n')
    open(os.path.join(KDIR, 'LoRa_Boat_Controller.kicad_dru'), 'w', encoding='utf-8', newline='\n').write('\n'.join(dru) + '\n')
    print('wrote', os.path.join(KDIR, 'LoRa_Boat_Controller.kicad_dru'))

if __name__ == '__main__':
    main()
