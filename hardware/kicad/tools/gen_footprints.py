#!/usr/bin/env python3
"""gen_footprints.py - Generate the project-local footprint library hardware/kicad/LoRa_Boat_Controller.pretty/
from the fabricated-board pad geometry (DSN v2 padstacks + v5 overrides, see v5_reconstruct.py) and the v5 solder
mask film (per-padstack mask margin).  Also writes hardware/kicad/_build/footprint_table.json used by
docs/CONVERSION_NOTES.md.
Inputs : hardware/kicad/_build/v5_board.json (run v5_reconstruct.py first)
Outputs: hardware/kicad/LoRa_Boat_Controller.pretty/<JEDEC>.kicad_mod, hardware/kicad/_build/footprint_table.json
Run from repo root: python hardware/kicad/tools/gen_footprints.py
"""
import os, sys, json, collections
sys.path.insert(0, os.path.dirname(__file__))
import allegro_data as ad
import v5_reconstruct as v5
from kicad_write import uid, f, mm, esc

ROOT = ad.ROOT
PRETTY = os.path.join(ROOT, 'hardware', 'kicad', 'LoRa_Boat_Controller.pretty')
BUILD = os.path.join(ROOT, 'hardware', 'kicad', '_build')
LIBNAME = 'LoRa_Boat_Controller'

# Nearest KiCad standard-library footprint (for the CONVERSION_NOTES mapping table only; NOT used on the board)
NEAREST = {
    'LQFP64-10x10mm': 'Package_QFP:LQFP-64_10x10mm_P0.5mm',
    'D0008A_L': 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
    'SOT-23-6W_PE-SOT23-6W-0512_NMD': 'Package_TO_SOT_SMD:SOT-23-6',
    'CAP_KGM21_KAV-L': 'Capacitor_SMD:C_0805_2012Metric',
    'CAP_0603_CL10A_1P6XP8_SAM-M': 'Capacitor_SMD:C_0603_1608Metric',
    'CAP_CL10_SAM-M': 'Capacitor_SMD:C_0603_1608Metric',
    'CAP_0603G_AVX-M': 'Capacitor_SMD:C_0603_1608Metric',
    'G-21_MUR-L': 'Capacitor_SMD:C_0805_2012Metric',
    'G-31_MUR-M': 'Capacitor_SMD:C_1206_3216Metric',
    'CAP_GJM1555C1H220JB01__MUR-L': 'Capacitor_SMD:C_0402_1005Metric',
    'CAP_NTS_55_2P8T_NIP': 'Capacitor_SMD:C_2220_5750Metric',
    'M-FLAT_TOS-L': 'Diode_SMD:D_SOD-123F',
    'IND_7045_TDK': 'Inductor_SMD:L_TDK_SLF7045',
    'IND_BLM15_0402_MUR-L': 'Inductor_SMD:L_0402_1005Metric',
    'RC0402N_PAN-M': 'Resistor_SMD:R_0402_1005Metric',
    'RC0402N_YAG-M': 'Resistor_SMD:R_0402_1005Metric',
    'RC0603N_YAG-M': 'Resistor_SMD:R_0603_1608Metric',
    'RES_R0805_ROM-M': 'Resistor_SMD:R_0805_2012Metric',
    'RES_1005_SAM-M': 'Resistor_SMD:R_0402_1005Metric',
    'CONN_B4B-XH-A_JST': 'Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical',
    'CONN_PPTC031_SUL': 'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical',
    'CONN5_1LFBN-RC_SUL': 'Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical',
    'SAMTEC_FTSH-105-XX-X-DV': 'Connector_PinHeader_1.27mm:PinHeader_2x05_P1.27mm_Vertical_SMD',
    'amv_test_point': 'TestPoint:TestPoint_THTPad_D3.0mm_Drill1.5mm',
    'amv_con1': 'TestPoint:TestPoint_THTPad_1.5x1.5mm_Drill0.7mm',
}
DESCR = {
    'LQFP64-10x10mm': 'LQFP-64 10x10 mm, 0.5 mm pitch (Allegro LQFP64-10X10MM, pads 47x12 mil)',
    'D0008A_L': 'SOIC-8 narrow, IPC least density (Allegro D0008A_L, oblong pads 21.65x49.21 mil)',
    'SOT-23-6W_PE-SOT23-6W-0512_NMD': 'SOT-23-6 (Allegro PE-SOT23-6W-0512_NMD, pads 35.5x22 mil)',
    'CAP_KGM21_KAV-L': '0805 MLCC, Kyocera-AVX KGM21 land pattern L (pads 36x47 mil, 55 mil pitch)',
    'IND_7045_TDK': 'TDK SLF7045 7x7 mm shielded power inductor (pads 86.61x94.88 mil, 216.14 mil pitch)',
    'M-FLAT_TOS-L': 'Toshiba M-FLAT (SOD-123F class) diode, L density (pads 71x38 mil, 163 mil pitch)',
    'SAMTEC_FTSH-105-XX-X-DV': 'Samtec FTSH-105 2x5 1.27 mm SMD header, pin numbering as fabricated on v5 (pin 1 = +x,+y)',
    'amv_test_point': 'Through-hole test point pad 3.4 mm / 1.4 mm hole (Allegro amv_test_point)',
    'amv_con1': 'Battery wire solder pad 1.6 mm / 0.6 mm hole (Allegro amv_con1)',
    'CAP_NTS_55_2P8T_NIP': 'Kemet KTS 5.5 mm MLCC land pattern (pads 65x213 mil, 203 mil pitch)',
}

def mask_margin_mil(pad):
    mt = pad.get('mask_top')
    if not mt:
        return 0.0
    return max((mt[1] - pad['w']) / 2.0, (mt[2] - pad['h']) / 2.0)

def main():
    b = json.load(open(os.path.join(BUILD, 'v5_board.json')))
    dsn = ad.load_dsn()
    parts = ad.load_pstxprt(); chips = ad.load_pstchip()
    refs_jedec = {ref: chips[dev]['jedec'] for ref, dev in parts.items()}
    patterns = v5.build_patterns(dsn, refs_jedec)
    # per-padstack mask margin measured from the v5 film (use any instance)
    margin = {}
    for c in b['components']:
        for p in c['pads']:
            margin.setdefault(p['padstack'], mask_margin_mil(p))
    os.makedirs(PRETTY, exist_ok=True)
    table = []
    for jedec, pads in sorted(patterns.items()):
        name = jedec
        is_th = any(p['hole'] for p in pads)
        xs = [p['x'] + s * p['w'] / 2 for p in pads for s in (-1, 1)]
        ys = [p['y'] + s * p['h'] / 2 for p in pads for s in (-1, 1)]
        bx0, bx1, by0, by1 = min(xs), max(xs), min(ys), max(ys)
        cy_margin = 0.0  # mil courtyard margin (pad extents only; v5 placement is tighter than IPC courtyards)
        L = []
        L.append(f'(footprint "{esc(name)}"')
        L.append('\t(version 20241229)')
        L.append('\t(generator "gen_footprints.py")')
        L.append('\t(generator_version "9.0")')
        L.append('\t(layer "F.Cu")')
        L.append(f'\t(descr "{esc(DESCR.get(jedec, "Allegro footprint " + jedec + " as fabricated on senior design v5.brd"))}")')
        L.append(f'\t(tags "allegro {esc(jedec)}")')
        L.append(f'\t(property "Reference" "REF**"\n\t\t(at 0 {f(mm(-(by1 + 40)))} 0)\n\t\t(layer "F.Fab")\n\t\t(uuid "{uid(name, "ref")}")\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 0.8 0.8)\n\t\t\t\t(thickness 0.12)\n\t\t\t)\n\t\t)\n\t)')
        L.append(f'\t(property "Value" "{esc(name)}"\n\t\t(at 0 {f(mm(-(by0 - 40)))} 0)\n\t\t(layer "F.Fab")\n\t\t(uuid "{uid(name, "val")}")\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 0.8 0.8)\n\t\t\t\t(thickness 0.12)\n\t\t\t)\n\t\t)\n\t)')
        for prop in ('Datasheet', 'Description'):
            L.append(f'\t(property "{prop}" ""\n\t\t(at 0 0 0)\n\t\t(layer "F.Fab")\n\t\t(hide yes)\n\t\t(uuid "{uid(name, prop)}")\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t\t(thickness 0.15)\n\t\t\t)\n\t\t)\n\t)')
        L.append('\t(attr through_hole)' if is_th else '\t(attr smd)')
        # courtyard + fab outline (pad bbox + margin); Y flipped (KiCad Y down)
        L.append(f'\t(fp_rect\n\t\t(start {f(mm(bx0 - cy_margin))} {f(mm(-(by1 + cy_margin)))})\n\t\t(end {f(mm(bx1 + cy_margin))} {f(mm(-(by0 - cy_margin)))})\n\t\t(stroke\n\t\t\t(width 0.05)\n\t\t\t(type default)\n\t\t)\n\t\t(fill no)\n\t\t(layer "F.CrtYd")\n\t\t(uuid "{uid(name, "crtyd")}")\n\t)')
        L.append(f'\t(fp_rect\n\t\t(start {f(mm(bx0))} {f(mm(-by1))})\n\t\t(end {f(mm(bx1))} {f(mm(-by0))})\n\t\t(stroke\n\t\t\t(width 0.1)\n\t\t\t(type default)\n\t\t)\n\t\t(fill no)\n\t\t(layer "F.Fab")\n\t\t(uuid "{uid(name, "fab")}")\n\t)')
        L.append(f'\t(fp_text user "${{REFERENCE}}"\n\t\t(at 0 0 0)\n\t\t(layer "F.Fab")\n\t\t(uuid "{uid(name, "reftext")}")\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 0.6 0.6)\n\t\t\t\t(thickness 0.1)\n\t\t\t)\n\t\t)\n\t)')
        for p in pads:
            shape = {'rect': 'rect', 'circle': 'circle', 'obround': 'oval'}[p['shape']]
            mg = margin.get(p['padstack'], 0.0)
            if p['hole']:
                L.append(f'\t(pad "{p["number"]}" thru_hole {shape}\n\t\t(at {f(mm(p["x"]))} {f(mm(-p["y"]))})\n\t\t(size {f(mm(p["w"]))} {f(mm(p["h"]))})\n\t\t(drill {f(mm(p["hole"]))})\n\t\t(layers "*.Cu" "*.Mask")\n\t\t(remove_unused_layers no)\n\t\t(solder_mask_margin {f(mm(mg))})\n\t\t(uuid "{uid(name, "pad", p["number"])}")\n\t)')
            else:
                L.append(f'\t(pad "{p["number"]}" smd {shape}\n\t\t(at {f(mm(p["x"]))} {f(mm(-p["y"]))})\n\t\t(size {f(mm(p["w"]))} {f(mm(p["h"]))})\n\t\t(layers "F.Cu" "F.Paste" "F.Mask")\n\t\t(solder_mask_margin {f(mm(mg))})\n\t\t(uuid "{uid(name, "pad", p["number"])}")\n\t)')
        L.append('\t(embedded_fonts no)')
        L.append(')')
        open(os.path.join(PRETTY, name + '.kicad_mod'), 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
        table.append({'jedec': jedec, 'kicad': f'{LIBNAME}:{name}', 'nearest_std': NEAREST.get(jedec, '(none)'),
                      'pads': [{'n': p['number'], 'x': p['x'], 'y': p['y'], 'shape': p['shape'], 'w': p['w'], 'h': p['h'], 'hole': p['hole'],
                                'padstack': p['padstack'], 'mask_margin': margin.get(p['padstack'], 0.0)} for p in pads],
                      'used_by': sorted(r for r, j in refs_jedec.items() if j == jedec)})
    json.dump(table, open(os.path.join(BUILD, 'footprint_table.json'), 'w'), indent=1)
    print(f'wrote {len(table)} footprints to {PRETTY}')

if __name__ == '__main__':
    main()
