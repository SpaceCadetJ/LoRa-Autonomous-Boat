#!/usr/bin/env python3
"""gen_v2.py - Generate the V2 KiCad 9 project from v2_design.py.
  python gen_v2.py bom   -> docs/BOM_V2.csv (grouped by MPN, qty-1 catalogue prices)
  python gen_v2.py sch   -> only the 6 sub-sheets + root schematic and schematic-path bookkeeping; preserves PCB/project/BOM
  python gen_v2.py pcb   -> LoRa_Boat_Controller_V2.kicad_pcb: outline, mounting holes, every footprint from the KiCad/V1/V2
                            libraries embedded with its nets, GND zones on both layers, LoRa keep-out.  Unrouted; route_v2.py routes it.
  python gen_v2.py check -> pin/net consistency of v2_design.py against the library symbols (also run by 'sch')
  python gen_v2.py all   -> libraries, schematic, project, unrouted PCB and BOM; explicitly destructive to existing routing
Reuses hardware/kicad/tools (kicad_sym.py, gen_sch.Sheet, kicad_write).  Run from repo root.
"""
import os, sys, json, re, glob
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
V1TOOLS = os.path.join(ROOT, 'hardware', 'kicad', 'tools')
sys.path.insert(0, HERE); sys.path.insert(0, V1TOOLS)
import kicad_sym as ks
from kicad_write import uid, f, esc
import gen_sch
gen_sch.FORCE_NC = set()   # V1 forced U3-1 (VBAT) to no-connect; in V2 U3 is the TPS54202 and pin 1 is GND (review finding R-02)
import v2_design as D

V2DIR = os.path.join(ROOT, 'hardware', 'kicad_v2')
BUILD = os.path.join(V2DIR, '_build'); os.makedirs(BUILD, exist_ok=True)
PROJ = D.PROJ
V1LIB_SYM = os.path.join(ROOT, 'hardware', 'kicad', 'LoRa_Boat_Controller.kicad_sym')
V2LIB_SYM = os.path.join(V2DIR, PROJ + '.kicad_sym')
V1PRETTY = os.path.join(ROOT, 'hardware', 'kicad', 'LoRa_Boat_Controller.pretty')
V2PRETTY = os.path.join(V2DIR, PROJ + '.pretty')
KFP = os.environ.get('KICAD_FOOTPRINT_DIR', r'C:\Users\Jay\AppData\Local\Programs\KiCad\9.0\share\kicad\footprints')

def lib_path(lib):
    if lib == D.V1LIB: return V1LIB_SYM
    if lib == PROJ: return V2LIB_SYM
    return lib

def sym_of(ref):
    lib, name = D.PARTS[ref][0]
    return ks.load_symbol(lib_path(lib), name)

# ----------------------------------------------------------------------------------------------
def resolve_pins():
    """Return {ref: {pin_number: net}} and a list of errors."""
    errors = []
    pin_net = {ref: {} for ref in D.PARTS}
    syms = {ref: sym_of(ref) for ref in D.PARTS}
    def lookup(token):
        if '-' in token and token.split('-', 1)[0] in D.PARTS and re.fullmatch(r'[A-Za-z0-9_]+', token.split('-', 1)[1]):
            ref, num = token.split('-', 1)
        elif '.' in token:
            ref, name = token.split('.', 1)
            cands = [p for p in syms[ref]['pins'] if p['name'] == name]
            if len(cands) != 1:
                errors.append(f'{token}: pin name matches {len(cands)} pins'); return None
            num = cands[0]['number']
        else:
            errors.append(f'{token}: bad pin reference'); return None
        if ref not in syms or not any(p['number'] == num for p in syms[ref]['pins']):
            errors.append(f'{token}: no such pin on {D.PARTS[ref][0] if ref in D.PARTS else "?"}'); return None
        return ref, num
    for net, toks in D.NETS.items():
        for t in toks:
            r = lookup(t)
            if r is None: continue
            ref, num = r
            if num in pin_net[ref]:
                errors.append(f'{ref}-{num} in two nets: {pin_net[ref][num]} and {net}')
            pin_net[ref][num] = net
    nc = set()
    for t in D.NC_PINS:
        r = lookup(t)
        if r: nc.add(r)
    for ref, sym in syms.items():
        for p in sym['pins']:
            if p['number'] not in pin_net[ref] and (ref, p['number']) not in nc and p['type'] != 'no_connect' and ref != 'U1':
                errors.append(f'{ref}-{p["number"]} ({p["name"]}) is neither in a net nor in NC_PINS')
    return pin_net, syms, errors

# ----------------------------------------------------------------------------------------------
def write_project_lib():
    """VSERVO power symbol (project) + QFN-24 3x3 0.4 mm no-EP footprint for the ICM-20948."""
    from gen_symbols import prop, pin
    p = ['\t(symbol "VSERVO"', '\t\t(power)', '\t\t(pin_numbers hide)', '\t\t(pin_names (offset 0) hide)', '\t\t(exclude_from_sim no)', '\t\t(in_bom yes)', '\t\t(on_board yes)',
         prop('Reference', '#PWR', 0, -3.81, hide=True), prop('Value', 'VSERVO', 0, 3.556),
         prop('Footprint', '', 0, 0, hide=True), prop('Datasheet', '', 0, 0, hide=True),
         prop('Description', 'Actuator rail 5-6 V: ESC BEC or the on-board 5 V buck through OR-ing diodes (REQ-PWR-03/04)', 0, 0, hide=True),
         prop('ki_keywords', 'global power', 0, 0, hide=True),
         '\t\t(symbol "VSERVO_0_1"',
         '\t\t\t(polyline (pts (xy -0.762 1.27) (xy 0 2.54)) (stroke (width 0) (type default)) (fill (type none)))',
         '\t\t\t(polyline (pts (xy 0 0) (xy 0 2.54)) (stroke (width 0) (type default)) (fill (type none)))',
         '\t\t\t(polyline (pts (xy 0 2.54) (xy 0.762 1.27)) (stroke (width 0) (type default)) (fill (type none)))',
         '\t\t)', '\t\t(symbol "VSERVO_1_1"', pin('power_in', 0, 0, 90, '~', '1', length=0), '\t\t)', '\t\t(embedded_fonts no)', '\t)']
    out = ['(kicad_symbol_lib', '\t(version 20241209)', '\t(generator "gen_v2.py")', '\t(generator_version "9.0")'] + p + [')']
    open(V2LIB_SYM, 'w', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')
    # QFN-24 3x3 mm, 0.4 mm pitch, no exposed pad (ICM-20948): pads 0.20 x 0.60 mm centred 1.55 mm out (inner end 1.25 mm) so the
    # corner pads of adjacent sides clear each other by 0.21 mm (0.25 x 0.70 pads at 1.45 intersected at the corners -> DRC/mask bridge)
    os.makedirs(V2PRETTY, exist_ok=True)
    L = ['(footprint "QFN-24_3x3mm_P0.4mm_NoEP"', '\t(version 20241229)', '\t(generator "gen_v2.py")', '\t(generator_version "9.0")', '\t(layer "F.Cu")',
         '\t(descr "QFN-24 3x3 mm 0.4 mm pitch without exposed pad (TDK InvenSense ICM-20948); pads 0.20 x 0.60 mm, inner end 1.25 mm from centre (corner pads clear by 0.21 mm)")', '\t(tags "QFN 24 ICM-20948")',
         f'\t(property "Reference" "REF**" (at 0 -2.6 0) (layer "F.SilkS") (uuid "{uid("v2fp","qfn","ref")}") (effects (font (size 0.8 0.8) (thickness 0.12))))',
         f'\t(property "Value" "QFN-24_3x3mm_P0.4mm_NoEP" (at 0 2.6 0) (layer "F.Fab") (uuid "{uid("v2fp","qfn","val")}") (effects (font (size 0.8 0.8) (thickness 0.12))))',
         f'\t(property "Footprint" "" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{uid("v2fp","qfn","fp")}") (effects (font (size 1.27 1.27) (thickness 0.15))))',
         f'\t(property "Datasheet" "" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{uid("v2fp","qfn","ds")}") (effects (font (size 1.27 1.27) (thickness 0.15))))',
         f'\t(property "Description" "" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{uid("v2fp","qfn","de")}") (effects (font (size 1.27 1.27) (thickness 0.15))))',
         '\t(attr smd)',
         f'\t(fp_rect (start -1.5 -1.5) (end 1.5 1.5) (stroke (width 0.1) (type default)) (fill no) (layer "F.Fab") (uuid "{uid("v2fp","qfn","fab")}"))',
         f'\t(fp_rect (start -2.0 -2.0) (end 2.0 2.0) (stroke (width 0.05) (type default)) (fill no) (layer "F.CrtYd") (uuid "{uid("v2fp","qfn","cy")}"))',
         f'\t(fp_circle (center -1.9 -1.9) (end -1.75 -1.9) (stroke (width 0.12) (type default)) (fill yes) (layer "F.SilkS") (uuid "{uid("v2fp","qfn","dot")}"))',
         f'\t(fp_text user "${{REFERENCE}}" (at 0 0 0) (layer "F.Fab") (uuid "{uid("v2fp","qfn","reft")}") (effects (font (size 0.5 0.5) (thickness 0.08))))']
    n = 1
    for side in range(4):   # pin 1 top-left going down the left side (CCW from top view), 6 per side
        for i in range(6):
            off = -1.0 + 0.4 * i
            if side == 0:   x, y, rot = -1.55, off, 0      # left, top to bottom
            elif side == 1: x, y, rot = off, 1.55, 90      # bottom, left to right
            elif side == 2: x, y, rot = 1.55, -off, 0      # right, bottom to top
            else:           x, y, rot = -off, -1.55, 90    # top, right to left
            L.append(f'\t(pad "{n}" smd roundrect (at {f(x)} {f(y)} {rot}) (size 0.6 0.2) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25) (uuid "{uid("v2fp","qfn","pad",n)}"))')
            n += 1
    L += ['\t(embedded_fonts no)', ')']
    open(os.path.join(V2PRETTY, 'QFN-24_3x3mm_P0.4mm_NoEP.kicad_mod'), 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')

# ----------------------------------------------------------------------------------------------
def gen_schematic(pin_net, syms):
    from schematic_layout import generate_v2
    return generate_v2(sys.modules[__name__], pin_net, syms)


# ----------------------------------------------------------------------------------------------
def find_footprint_file(fpid):
    lib, name = fpid.split(':', 1)
    if lib == D.V1LIB: d = V1PRETTY
    elif lib == PROJ: d = V2PRETTY
    else: d = os.path.join(KFP, lib + '.pretty')
    p = os.path.join(d, name + '.kicad_mod')
    if not os.path.exists(p):
        raise FileNotFoundError(p)
    return p

def embed_footprint(fpid, ref, x, y, rot, value, pad_nets, netid, path, descr):
    tree = ks.parse(open(find_footprint_file(fpid), encoding='utf-8').read())[0]
    tree[1] = ks.Str(fpid)
    # drop version/generator; set layer, uuid, at, path
    out = [tree[0], tree[1]]
    body = [c for c in tree[2:] if not (isinstance(c, list) and c and c[0] in ('version', 'generator', 'generator_version'))]
    at = ['at', f(x), f(y)] + ([f(rot)] if rot else [])
    out += [['layer', ks.Str('F.Cu')], ['uuid', ks.Str(uid('v2fp', ref))], at, ['path', ks.Str(path)]]
    seen_props = set()
    for c in body:
        if not isinstance(c, list):
            out.append(c); continue
        k = c[0]
        if k in ('layer', 'uuid', 'at', 'path', 'sheetname', 'sheetfile', 'net_tie_pad_groups'):
            continue
        if k == 'property':
            pname = str(c[1]); seen_props.add(pname)
            if pname == 'Reference': c[2] = ks.Str(ref)
            elif pname == 'Value': c[2] = ks.Str(value)
            elif pname == 'Footprint': c[2] = ks.Str(fpid)
            elif pname == 'Description' and descr: c[2] = ks.Str(descr)
            for e in c:
                if isinstance(e, list) and e and e[0] == 'at' and len(e) >= 3:
                    ang = float(e[3]) if len(e) > 3 else 0.0
                    if len(e) > 3: e[3] = f((ang + rot) % 360)
                    elif rot: e.append(f(rot % 360))
            out.append(c); continue
        if k in ('fp_text',):
            for e in c:
                if isinstance(e, list) and e and e[0] == 'at' and len(e) >= 3:
                    ang = float(e[3]) if len(e) > 3 else 0.0
                    if len(e) > 3: e[3] = f((ang + rot) % 360)
                    elif rot: e.append(f(rot % 360))
            out.append(c); continue
        if k == 'pad':
            num = str(c[1])
            for e in c:
                if isinstance(e, list) and e and e[0] == 'at' and len(e) >= 3:
                    ang = float(e[3]) if len(e) > 3 else 0.0
                    if len(e) > 3: e[3] = f((ang + rot) % 360)
                    elif rot: e.append(f(rot % 360))
            net = pad_nets.get(num)
            # remove any existing net entry, insert ours after (layers ...)
            c = [e for e in c if not (isinstance(e, list) and e and e[0] == 'net')]
            if net is not None:
                idx = next((i for i, e in enumerate(c) if isinstance(e, list) and e and e[0] == 'layers'), len(c) - 1)
                c.insert(idx + 1, ['net', str(netid[net]), ks.Str(net)])
            out.append(c); continue
        out.append(c)
    for pname in ('Datasheet', 'Description'):
        if pname not in seen_props:
            out.append(['property', ks.Str(pname), ks.Str(descr if pname == 'Description' else ''), ['at', '0', '0', '0'], ['layer', ks.Str('F.Fab')], ['hide', 'yes'], ['uuid', ks.Str(uid('v2fp', ref, pname))], ['effects', ['font', ['size', '1.27', '1.27'], ['thickness', '0.15']]]])
    return ks.serialize(out, 1)

def gen_pcb(pin_net, paths):
    nets = sorted(D.NETS.keys(), key=lambda n: (n not in ('GND', '+3V3'), n))
    netid = {n: i + 1 for i, n in enumerate(nets)}
    ox, oy = D.BOARD_ORIGIN
    L = ['(kicad_pcb', '\t(version 20241229)', '\t(generator "gen_v2.py")', '\t(generator_version "9.0")',
         '\t(general\n\t\t(thickness 1.6)\n\t\t(legacy_teardrops no)\n\t)', '\t(paper "A4")',
         '\t(title_block\n\t\t(title "LoRa Autonomous Boat Controller V2")\n\t\t(date "2026-09-17")\n\t\t(rev "V2 draft")\n\t\t(company "University of Arkansas EECS")\n\t\t(comment 1 "Generated by hardware/kicad_v2/tools/gen_v2.py from v2_design.py; routed by route_v2.py (freerouting)")\n\t)',
         __import__('gen_pcb').LAYERS]
    L.append(f'''\t(setup
\t\t(stackup
\t\t\t(layer "F.SilkS" (type "Top Silk Screen"))
\t\t\t(layer "F.Paste" (type "Top Solder Paste"))
\t\t\t(layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))
\t\t\t(layer "F.Cu" (type "copper") (thickness 0.035))
\t\t\t(layer "dielectric 1" (type "core") (thickness 1.51) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
\t\t\t(layer "B.Cu" (type "copper") (thickness 0.035))
\t\t\t(layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))
\t\t\t(layer "B.Paste" (type "Bottom Solder Paste"))
\t\t\t(layer "B.SilkS" (type "Bottom Silk Screen"))
\t\t\t(copper_finish "ENIG")
\t\t\t(dielectric_constraints no)
\t\t)
\t\t(pad_to_mask_clearance 0.05)
\t\t(allow_soldermask_bridges_in_footprints no)
\t\t(pcbplotparams (layerselection 0x00000000_00000000_55555555_5755f5ff) (plot_on_all_layers_selection 0x00000000_00000000_00000000_00000000) (disableapertmacros no) (usegerberextensions no) (usegerberattributes yes) (usegerberadvancedattributes yes) (creategerberjobfile yes) (dashed_line_dash_ratio 12.0) (dashed_line_gap_ratio 3.0) (svgprecision 4) (plotframeref no) (mode 1) (useauxorigin no) (hpglpennumber 1) (hpglpenspeed 20) (hpglpendiameter 15.0) (pdf_front_fp_property_popups yes) (pdf_back_fp_property_popups yes) (pdf_metadata yes) (pdf_single_document no) (dxfpolygonmode yes) (dxfimperialunits yes) (dxfusepcbnewfont yes) (psnegative no) (psa4output no) (plot_black_and_white yes) (sketchpadsonfab no) (plotpadnumbers no) (hidednponfab no) (sketchdnponfab yes) (crossoutdnponfab yes) (subtractmaskfromsilk no) (outputformat 1) (mirror no) (drillshape 1) (scaleselection 1) (outputdirectory ""))
\t)''')
    L.append('\t(net 0 "")')
    for n in nets:
        L.append(f'\t(net {netid[n]} "{esc(n)}")')
    for ref, (sym, fpid, value, mpn, mfr, sheet, descr) in D.PARTS.items():
        if ref not in D.PLACE:
            raise SystemExit(f'no placement for {ref}')
        px, py, rot = D.PLACE[ref]
        L.append(embed_footprint(fpid, ref, ox + px, oy + py, rot, value, pin_net.get(ref, {}), netid, paths.get(ref, ''), descr))
    # outline
    corners = [(ox, oy), (ox + D.BOARD_W, oy), (ox + D.BOARD_W, oy + D.BOARD_H), (ox, oy + D.BOARD_H)]
    for i in range(4):
        (x1, y1), (x2, y2) = corners[i], corners[(i + 1) % 4]
        L.append(f'\t(gr_line\n\t\t(start {f(x1)} {f(y1)})\n\t\t(end {f(x2)} {f(y2)})\n\t\t(stroke\n\t\t\t(width 0.1)\n\t\t\t(type default)\n\t\t)\n\t\t(layer "Edge.Cuts")\n\t\t(uuid "{uid("v2edge", i)}")\n\t)')
    L.append(f'\t(gr_text "LoRa Boat V2"\n\t\t(at {f(ox + 6.5)} {f(oy + 36)} 0)\n\t\t(layer "F.SilkS")\n\t\t(uuid "{uid("v2txt", 1)}")\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.2 1.2)\n\t\t\t\t(thickness 0.2)\n\t\t\t)\n\t\t)\n\t)')
    # GND pours both layers, LoRa keep-out
    for i, lay in enumerate(('F.Cu', 'B.Cu')):
        pts = ''.join(f'\n\t\t\t\t(xy {f(x)} {f(y)})' for (x, y) in corners)
        L.append(f'\t(zone\n\t\t(net {netid["GND"]})\n\t\t(net_name "GND")\n\t\t(layer "{lay}")\n\t\t(uuid "{uid("v2zone", lay)}")\n\t\t(name "GND pour {lay}")\n\t\t(hatch edge 0.5)\n\t\t(priority 0)\n\t\t(connect_pads yes\n\t\t\t(clearance 0.2)\n\t\t)\n\t\t(min_thickness 0.2)\n\t\t(filled_areas_thickness no)\n\t\t(fill yes\n\t\t\t(thermal_gap 0.25)\n\t\t\t(thermal_bridge_width 0.3)\n\t\t)\n\t\t(polygon\n\t\t\t(pts{pts}\n\t\t\t)\n\t\t)\n\t)')
        for k, (x0, y0, x1, y1) in enumerate(D.KEEPOUTS):
            kp = ''.join(f'\n\t\t\t\t(xy {f(ox + a)} {f(oy + b)})' for (a, b) in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
            L.append(f'\t(zone\n\t\t(net 0)\n\t\t(net_name "")\n\t\t(layer "{lay}")\n\t\t(uuid "{uid("v2keep", lay, k)}")\n\t\t(name "LoRa module keep-out {lay} (REQ-RF-05)")\n\t\t(hatch edge 0.5)\n\t\t(priority 1)\n\t\t(connect_pads\n\t\t\t(clearance 0)\n\t\t)\n\t\t(min_thickness 0.25)\n\t\t(filled_areas_thickness no)\n\t\t(keepout\n\t\t\t(tracks allowed)\n\t\t\t(vias allowed)\n\t\t\t(pads allowed)\n\t\t\t(copperpour not_allowed)\n\t\t\t(footprints allowed)\n\t\t)\n\t\t(fill\n\t\t\t(thermal_gap 0.5)\n\t\t\t(thermal_bridge_width 0.5)\n\t\t)\n\t\t(polygon\n\t\t\t(pts{kp}\n\t\t\t)\n\t\t)\n\t)')
    L += ['\t(embedded_fonts no)', ')']
    out = os.path.join(V2DIR, PROJ + '.kicad_pcb')
    open(out, 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
    print('wrote', out, len(D.PARTS), 'footprints', len(nets), 'nets')

def gen_project():
    # Power class (0.6 mm tracks, 0.8/0.4 vias, 0.2 mm clearance) is limited to the nets that only touch coarse-pitch pads (XT30, fuse, SOT-23,
    # SMA diodes, inductors, bulk caps, JST).  +3V3 / VDDA / VBUS / LORA_* enter 0.5 mm and 0.4 mm pitch pads (U1, U6, J6): a 0.6 mm track cannot
    # land on a 0.3 mm pad without violating clearance to the neighbours and freerouting does not neck down, so those stay in Default
    # (0.25 mm tracks, 0.15 mm clearance; the 3V3 rail draws < 300 mA).  GND is carried by the two pours.
    power_nets = ['VIN_RAW', 'VIN_BUCK', 'VBAT_IN', 'VBAT_FUSED', 'VSERVO', '+5V_BUCK', 'BEC_IN', 'SW_3V3', 'SW_5V']
    pro = {
        "board": {"3dviewports": [], "design_settings": {
            "defaults": {"board_outline_line_width": 0.1, "copper_line_width": 0.2, "silk_line_width": 0.127, "silk_text_size_h": 1.0, "silk_text_size_v": 1.0, "silk_text_thickness": 0.15},
            "diff_pair_dimensions": [], "drc_exclusions": [], "meta": {"version": 2},
            "rule_severities": {"clearance": "error", "courtyards_overlap": "error", "solder_mask_bridge": "error", "silk_over_copper": "warning", "silk_overlap": "warning",
                                "missing_courtyard": "warning", "unconnected_items": "error", "track_width": "error", "hole_clearance": "error", "copper_edge_clearance": "error",
                                "footprint_type_mismatch": "ignore", "lib_footprint_issues": "warning", "lib_footprint_mismatch": "warning", "isolated_copper": "warning"},
            "rules": {"max_error": 0.005, "min_clearance": 0.127, "min_connection": 0.0, "min_copper_edge_clearance": 0.3, "min_hole_clearance": 0.25, "min_hole_to_hole": 0.25,
                      "min_microvia_diameter": 0.2, "min_microvia_drill": 0.1, "min_resolved_spokes": 2, "min_silk_clearance": 0.0, "min_text_height": 0.6, "min_text_thickness": 0.08,
                      "min_through_hole_diameter": 0.3, "min_track_width": 0.127, "min_via_annular_width": 0.15, "min_via_diameter": 0.6, "solder_mask_to_copper_clearance": 0.0, "use_height_for_length_calcs": True},
            "track_widths": [0.0, 0.25, 0.3, 0.5, 0.6], "via_dimensions": [{"diameter": 0.0, "drill": 0.0}, {"diameter": 0.6, "drill": 0.3}, {"diameter": 0.8, "drill": 0.4}],
            "zones_allow_external_fillets": False},
            "ipc2581": {"dist": "", "distpn": "", "internal_id": "", "mfg": "", "mpn": ""}, "layer_pairs": [], "layer_presets": [], "viewports": []},
        "boards": [], "cvpcb": {"equivalence_files": []}, "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": PROJ + ".kicad_pro", "version": 3},
        "net_settings": {"classes": [
            {"bus_width": 12, "clearance": 0.15, "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25, "diff_pair_width": 0.2, "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1,
             "name": "Default", "pcb_color": "rgba(0, 0, 0, 0.000)", "priority": 2147483647, "schematic_color": "rgba(0, 0, 0, 0.000)", "track_width": 0.25, "via_diameter": 0.6, "via_drill": 0.3, "wire_width": 6},
            {"bus_width": 12, "clearance": 0.2, "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25, "diff_pair_width": 0.2, "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1,
             "name": "Power", "pcb_color": "rgba(0, 0, 0, 0.000)", "priority": 0, "schematic_color": "rgba(0, 0, 0, 0.000)", "track_width": 0.6, "via_diameter": 0.8, "via_drill": 0.4, "wire_width": 6}],
            "meta": {"version": 4}, "net_colors": None, "netclass_assignments": None,
            "netclass_patterns": [{"netclass": "Power", "pattern": n} for n in power_nets]},
        "pcbnew": {"last_paths": {"gencad": "", "idf": "", "netlist": "", "plot": "", "pos_files": "", "specctra_dsn": "", "step": "", "svg": "", "vrml": ""}, "page_layout_descr_file": ""},
        "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []}, "sheets": [], "text_variables": {}}
    json.dump(pro, open(os.path.join(V2DIR, PROJ + '.kicad_pro'), 'w', encoding='utf-8'), indent=2)

def gen_bom():
    """docs/BOM_V2.csv grouped by MPN with qty-1 catalogue prices (v2_design.PRICE_USD) + _build/bom_v2.json."""
    import csv
    from collections import OrderedDict
    groups = OrderedDict()
    for ref, (sym, fp, val, mpn, mfr, sheet, descr) in D.PARTS.items():
        groups.setdefault((mpn, mfr, val, fp), []).append(ref)
    rows = []; total = 0.0; missing = []
    for (mpn, mfr, val, fp), refs in groups.items():
        unit = D.PRICE_USD.get(mpn, 0.0) if mpn else 0.0
        if mpn and mpn not in D.PRICE_USD: missing.append(mpn)
        ext = round(unit * len(refs), 2); total += ext
        descr = D.PARTS[refs[0]][6]; sheet = D.PARTS[refs[0]][5]
        rows.append({'Item': len(rows) + 1, 'Qty': len(refs), 'Refs': ' '.join(refs), 'Value': val, 'MPN': mpn, 'Manufacturer': mfr, 'Description': descr,
                     'Footprint': fp, 'Sheet': sheet, 'Unit price qty1 USD': f'{unit:.2f}' if mpn else '', 'Ext price USD': f'{ext:.2f}' if mpn else ''})
    out = os.path.join(ROOT, 'docs', 'BOM_V2.csv')
    with open(out, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
        w.writerow({'Item': '', 'Qty': sum(r['Qty'] for r in rows), 'Refs': 'TOTAL (board only, qty 1, catalogue prices as of ' + D.PRICE_DATE + ')', 'Ext price USD': f'{total:.2f}'})
    json.dump({'date': D.PRICE_DATE, 'lines': rows, 'total_usd': round(total, 2)}, open(os.path.join(V2DIR, '_build', 'bom_v2.json'), 'w'), indent=1)
    print(f'wrote {out}: {len(rows)} line items, {sum(r["Qty"] for r in rows)} parts, total ${total:.2f} at qty 1' + (f'; NO PRICE for {missing}' if missing else ''))

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if cmd not in ('check', 'bom', 'sch', 'pcb', 'all'):
        raise SystemExit('Usage: gen_v2.py check|bom|sch|pcb|all')
    # Read-only commands do not rewrite libraries, project settings, BOM or PCB.
    if cmd == 'bom':
        gen_bom()
        return
    pin_net, syms, errors = resolve_pins()
    if errors:
        raise SystemExit('DESIGN ERRORS: ' + '; '.join(errors))
    print(f'{len(D.PARTS)} parts, {len(D.NETS)} nets, {sum(len(v) for v in pin_net.values())} connected pins')
    if cmd == 'check':
        return
    if cmd == 'sch':
        gen_schematic(pin_net, syms)
        return
    if cmd == 'pcb':
        paths = {ref: f'/{uid("sch", PROJ, "sheet", part[5])}/{uid("sch", PROJ, ref)}'
                 for ref, part in D.PARTS.items() if syms[ref]['pins']}
        gen_pcb(pin_net, paths)
        return
    # Explicit full regeneration is intentionally separate from presentation updates.
    write_project_lib()
    paths = gen_schematic(pin_net, syms)
    gen_project()
    gen_pcb(pin_net, paths)
    gen_bom()


if __name__ == '__main__':
    main()
