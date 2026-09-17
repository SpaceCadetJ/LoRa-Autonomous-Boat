#!/usr/bin/env python3
"""gen_sch.py - Generate the hierarchical KiCad 9 schematic of V1 from the v5 netlist (pstxnet.dat via
hardware/kicad/_build/v5_board.json), one sub-sheet per subsystem (OrCAD block lineage in each sheet's notes).

Wiring style: every pin gets a short wire stub ending in a net label (local when the net stays on one sheet,
hierarchical when it crosses sheets), a power symbol (GND, +3V3, VIN_RAW) or a no-connect flag.  Sheet pins on the
root sheet are joined with local labels.  Symbol/sheet UUIDs are deterministic so the PCB (gen_pcb.py) carries the
same symbol paths and "Update PCB from Schematic" finds every footprint by path.

Inputs : _build/v5_board.json, _build/netmap.json (gen_pcb.py), LoRa_Boat_Controller.kicad_sym (gen_symbols.py),
         KiCad 9 standard symbol libraries, optional _build/mpn.json {ref: {MPN, Manufacturer, Description}}.
Outputs: hardware/kicad/LoRa_Boat_Controller.kicad_sch (root) + PowerSupply/MCU/CAN_Bus/LoRa_Module/GPS_Module/
         PWM_Outputs/Debug.kicad_sch, hardware/kicad/_build/sch_paths.json (ref -> symbol path used by the PCB)
Run from repo root: python hardware/kicad/tools/gen_sch.py
"""
import os, sys, json, re
sys.path.insert(0, os.path.dirname(__file__))
import kicad_sym as ks
from kicad_write import uid, f, esc

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
KDIR = os.path.join(ROOT, 'hardware', 'kicad')
BUILD = os.path.join(KDIR, '_build')
PROJ = 'LoRa_Boat_Controller'
PROJLIB = os.path.join(KDIR, PROJ + '.kicad_sym')
G = 2.54          # grid
STUB = 2.54       # wire stub length from pin to label/power symbol
LABEL_ROOM = 20.0 # horizontal room reserved for labels either side of a symbol
POWER_NETS = {'GND': ('power', 'GND', 'down'), '+3V3': ('power', '+3V3', 'up'), 'VIN_RAW': (PROJLIB, 'VIN_RAW', 'up')}
# Pins that carry a single-node net in pstxnet.dat (i.e. are physically unconnected on the fabricated board)
FORCE_NC = {('U3', '1')}   # VBAT: net 'VBAT' has only U3-1 -> floating on V1

from v1_design import SHEETS, SHEET_OF, sheet_uuid, root_uuid as design_root_uuid, kicad_ref, symbol_uuid
PAPER = {'A4': (297.0, 210.0), 'A3': (420.0, 297.0)}

EXPLICIT_SYMBOL = {
    'U3': ('MCU_ST_STM32F4', 'STM32F446RETx'), 'U5': (PROJLIB, 'TCAN1042H-Q1'), 'U6': (PROJLIB, 'R1240N001x'),
    'D21': (PROJLIB, 'CMS06_Schottky'), 'L3': ('Device', 'FerriteBead'), 'L4': ('Device', 'FerriteBead'),
    'VIN': ('Connector_Generic', 'Conn_01x01'), 'GND': ('Connector_Generic', 'Conn_01x01'),
    'CANHEADER': ('Connector_Generic', 'Conn_01x04'), 'GPSMODULE': ('Connector_Generic', 'Conn_01x05'),
    'LORAMODULE': ('Connector_Generic', 'Conn_01x05'), 'SPEEDCONTROLLER': ('Connector_Generic', 'Conn_01x03'),
    'STEERINGSERVO': ('Connector_Generic', 'Conn_01x03'), 'JTAG': ('Connector_Generic', 'Conn_02x05_Odd_Even'),
}

def symbol_for(ref, jedec):
    if ref in EXPLICIT_SYMBOL:
        return EXPLICIT_SYMBOL[ref]
    if ref.startswith('TP'): return ('Connector', 'TestPoint')
    if ref.startswith('L'): return ('Device', 'L')
    if ref.startswith('C'): return ('Device', 'C')
    if ref.startswith('R'): return ('Device', 'R')
    raise KeyError(ref)

def nice_value(ref, part, value):
    v = (value or '').strip()
    m = re.fullmatch(r'(\.?\d*\.?\d+)\s*([UuNnPp])[Ff]', v)
    if m:
        num = m.group(1); num = ('0' + num) if num.startswith('.') else num
        return f'{num}{m.group(2).lower()}F'
    m = re.fullmatch(r'(\d*\.?\d+)\s*[Uu][Hh]', v)
    if m: return f'{m.group(1)}uH'
    m = re.fullmatch(r'(\d*\.?\d+)([Kk])', v)
    if m: return f'{m.group(1)}k'
    if ref in ('L3', 'L4'): return 'BLM15 ferrite'
    if ref == 'U3': return 'STM32F446RET6'
    if ref == 'U5': return 'TCAN1042HDRQ1'
    if ref == 'U6': return 'R1240N001B-TR-FE'
    if ref == 'D21': return 'CMS06(TE12L,Q,M)'
    if ref.startswith('TP'): return 'TP'
    if part and part not in ('C', 'R', 'INDUCTOR', 'TEST POINT', 'CON1'):
        return part
    return v

class Sheet:
    def __init__(self, name, file, paper, descr, refs):
        self.name, self.file, self.paper, self.descr, self.refs = name, file, paper, descr, refs
        self.uuid = sheet_uuid(name)                 # sheet-symbol uuid (used in instance paths, shared with gen_pcb)
        self.screen_uuid = uid('sch', 'screen', name)  # the sub-sheet file's own uuid
        self.items = []        # s-expression strings
        self.libs = {}         # 'lib:name' -> tree
        self.hier = set()      # hierarchical label net names used here
        self.pwr_n = 0
        self.notes = []
        self.n = 0             # running counter -> unique, deterministic UUIDs per sheet

    def _u(self, tag):
        self.n += 1
        return uid('sch', self.name, tag, self.n)

    def add_lib(self, sym):
        self.libs[str(sym['tree'][1])] = sym['tree']

    def wire(self, x1, y1, x2, y2):
        self.items.append(f'\t(wire\n\t\t(pts\n\t\t\t(xy {f(x1)} {f(y1)}) (xy {f(x2)} {f(y2)})\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n\t\t(uuid "{self._u("wire")}")\n\t)')

    def label(self, net, x, y, angle, kind='label'):
        """kind: 'label' (sheet-local), 'hierarchical_label', or 'global_label'."""
        shape = '\n\t\t(shape passive)' if kind != 'label' else ''
        self.items.append(f'\t({kind} "{esc(net)}"{shape}\n\t\t(at {f(x)} {f(y)} {angle})\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid "{self._u("label")}")\n\t)')
        if kind == 'hierarchical_label':
            self.hier.add(net)

    def no_connect(self, x, y):
        self.items.append(f'\t(no_connect\n\t\t(at {f(x)} {f(y)})\n\t\t(uuid "{self._u("nc")}")\n\t)')

    def text(self, s, x, y, size=1.27):
        self.items.append(f'\t(text "{esc(s)}"\n\t\t(exclude_from_sim no)\n\t\t(at {f(x)} {f(y)} 0)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size {size} {size})\n\t\t\t)\n\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid "{self._u("text")}")\n\t)')

    def power(self, net, x, y, rot, root_uuid):
        lib, name, _ = POWER_NETS[net]
        sym = ks.load_symbol(lib, name); self.add_lib(sym)
        self.pwr_n += 1
        ref = f'#PWR{self.name[:3].upper()}{self.pwr_n:02d}'
        libid = str(sym['tree'][1])
        self.items.append(self._symbol(libid, x, y, rot, ref, net, {}, sym, root_uuid, power=True))

    def _symbol(self, libid, x, y, rot, ref, value, props, sym, root_uuid, power=False, suuid=None):
        suuid = suuid or self._u('pwr')
        pins = ''.join(f'\n\t\t(pin "{p["number"]}"\n\t\t\t(uuid "{self._u("pin")}")\n\t\t)' for p in sym['pins'])
        hide_ref = '\n\t\t\t(hide yes)' if power else ''
        bb = ks.symbol_bbox(sym['tree'])
        ry = y - bb[3] - 1.5 if not power else y - 3.81
        vy = y - bb[1] + 1.5 if not power else y + 3.556 if False else y - 3.556
        if power:
            # value (net name) drawn above for 'up' symbols, below for GND
            side = POWER_NETS.get(value, (None, None, 'up'))[2]
            vy = y - 3.556 if side == 'up' else y + 3.556
            if rot == 180:
                vy = y + 3.556 if side == 'up' else y - 3.556
        lines = [f'\t(symbol\n\t\t(lib_id "{esc(libid)}")\n\t\t(at {f(x)} {f(y)} {rot})\n\t\t(unit 1)\n\t\t(exclude_from_sim no)\n\t\t(in_bom {"no" if power else "yes"})\n\t\t(on_board {"no" if power else "yes"})\n\t\t(dnp no)\n\t\t(uuid "{suuid}")',
                 f'\t\t(property "Reference" "{esc(ref)}"\n\t\t\t(at {f(x)} {f(ry)} 0)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t){hide_ref}\n\t\t\t)\n\t\t)',
                 f'\t\t(property "Value" "{esc(value)}"\n\t\t\t(at {f(x)} {f(vy)} 0)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)']
        for k, v in props.items():
            lines.append(f'\t\t(property "{esc(k)}" "{esc(v)}"\n\t\t\t(at {f(x)} {f(y)} 0)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)')
        path = f'/{root_uuid}/{self.uuid}'
        lines.append(pins)
        lines.append(f'\t\t(instances\n\t\t\t(project "{PROJ}"\n\t\t\t\t(path "{path}"\n\t\t\t\t\t(reference "{esc(ref)}")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)')
        return '\n'.join(lines)

    def place(self, ref, sym, x, y, value, props, pin_nets, net_sheets, root_uuid):
        """Place a component symbol at (x,y) and wire every pin to a label / power symbol / no-connect."""
        libid = str(sym['tree'][1])
        self.add_lib(sym)
        props = dict(props); props['Allegro_RefDes'] = ref
        self.items.append(self._symbol(libid, x, y, 0, kicad_ref(ref), value, props, sym, root_uuid, suuid=symbol_uuid(ref)))
        for p in sym['pins']:
            px, py = x + p['x'], y - p['y']          # KiCad symbol Y is up; sheet Y is down
            a = int(p['angle']) % 360
            out = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[a]   # direction away from the body (sheet coords)
            net = pin_nets.get(p['number'])
            if p['type'] == 'no_connect' or net is None or (ref, p['number']) in FORCE_NC:
                self.no_connect(px, py); continue
            ex, ey = px + out[0] * STUB, py + out[1] * STUB
            self.wire(px, py, ex, ey)
            angle = {(-1, 0): 180, (1, 0): 0, (0, 1): 270, (0, -1): 90}[out]
            if net in POWER_NETS and out[1] != 0:      # vertical pin: power symbol (rotated if it must point the other way)
                want = POWER_NETS[net][2]
                natural = 'down' if out[1] > 0 else 'up'
                self.power(net, ex, ey, 0 if natural == want else 180, root_uuid)
            elif net in POWER_NETS:                    # horizontal pin (connector rows): global label, keeps the row tidy
                self.label(net, ex, ey, angle, 'global_label')
            else:
                hier = len(net_sheets[net]) > 1
                self.label(net, ex, ey, angle, 'hierarchical_label' if hier else 'label')

    def render(self, root_uuid, root=False, sheets_block=''):
        W, H = PAPER[self.paper]
        libs = '\n'.join(ks.serialize(t, 1) for _, t in sorted(self.libs.items()))
        out = ['(kicad_sch', '\t(version 20250114)', '\t(generator "gen_sch.py")', '\t(generator_version "9.0")',
               f'\t(uuid "{root_uuid if root else self.screen_uuid}")', f'\t(paper "{self.paper}")',
               f'\t(title_block\n\t\t(title "LoRa Autonomous Boat Controller V1 - {self.name}")\n\t\t(date "2025-05-09")\n\t\t(rev "as fabricated (senior design v5.brd)")\n\t\t(company "University of Arkansas EECS")\n\t\t(comment 1 "{esc(self.descr)}")\n\t\t(comment 2 "Generated by hardware/kicad/tools/gen_sch.py from pstxnet.dat (2025-05-09 17:12); see README.md")\n\t)',
               '\t(lib_symbols\n' + libs + '\n\t)']
        out += self.items
        out.append(sheets_block)
        if root:
            out.append('\t(sheet_instances\n\t\t(path "/"\n\t\t\t(page "1")\n\t\t)\n\t)')
        out.append('\t(embedded_fonts no)')
        out.append(')')
        return '\n'.join(x for x in out if x) + '\n'

def main():
    b = json.load(open(os.path.join(BUILD, 'v5_board.json')))
    netmap = json.load(open(os.path.join(BUILD, 'netmap.json')))
    mpn = json.load(open(os.path.join(BUILD, 'mpn.json'))) if os.path.exists(os.path.join(BUILD, 'mpn.json')) else {}
    comps = {c['ref']: c for c in b['components']}
    root_uuid = design_root_uuid()
    # pin -> net (KiCad name), net -> sheets
    sheet_of = SHEET_OF
    missing = [r for r in comps if r not in sheet_of]
    if missing:
        raise SystemExit(f'components without a sheet: {missing}')
    pin_nets = {}
    net_sheets = {}
    for c in b['components']:
        for p in c['pads']:
            if p['net'] is None:
                continue
            kn = netmap.get(p['net'], p['net'])
            pin_nets[(c['ref'], p['number'])] = kn
            net_sheets.setdefault(kn, set()).add(sheet_of[c['ref']])
    allegro_of = {v: k for k, v in netmap.items()}
    sheets = []
    paths = {}
    for (name, file, paper, descr, refs) in SHEETS:
        sh = Sheet(name, file, paper, descr, refs)
        W, H = PAPER[paper]
        sh.text(f'{name}: {descr}', 12.7, 12.7, 1.5)
        # shelf packing
        x0, y0 = 12.7 + LABEL_ROOM, 25.4
        cx, cy, row_h = x0, y0, 0.0
        for ref in refs:
            c = comps[ref]
            lib, sname = symbol_for(ref, c['jedec'])
            sym = ks.load_symbol(lib, sname)
            bb = ks.symbol_bbox(sym['tree'])
            w = (bb[2] - bb[0]) + 2 * LABEL_ROOM
            h = (bb[3] - bb[1]) + 2 * STUB + 10.0
            if cx + w > W - 12.7:
                cx, cy, row_h = x0, cy + row_h, 0.0
            sx = round((cx + LABEL_ROOM - bb[0]) / G) * G
            sy = round((cy + STUB + 5.0 + bb[3]) / G) * G
            pn = {p['number']: pin_nets.get((ref, p['number'])) for p in sym['pins']}
            props = {'Footprint': f'{PROJ}:{c["jedec"]}', 'Datasheet': '', 'Description': c['part'] or '',
                     'Allegro_Device': c['device']}
            for p in sym['tree']:
                if isinstance(p, list) and p and p[0] == 'property' and str(p[1]) in ('Datasheet', 'Description') and str(p[2]):
                    props[str(p[1])] = str(p[2])
            if ref in mpn:
                props['MPN'] = mpn[ref].get('MPN', ''); props['Manufacturer'] = mpn[ref].get('Manufacturer', '')
                if mpn[ref].get('Description'): props['Description'] = mpn[ref]['Description']
            sh.place(ref, sym, sx, sy, nice_value(ref, c['part'], c['value']), props, pn, net_sheets, root_uuid)
            paths[ref] = f'/{sh.uuid}/{symbol_uuid(ref)}'
            cx += w; row_h = max(row_h, h)
        # net cross-reference note
        nets_here = sorted({n for (r, p), n in pin_nets.items() if sheet_of[r] == name})
        xref = ', '.join(f'{n}<-{allegro_of.get(n, n)}' for n in nets_here if allegro_of.get(n, n) != n)
        sh.text('Allegro net names: ' + xref, 12.7, H - 10.0, 1.0)
        def pwr_flag(sh, i, net, x, y):
            flag = ks.load_symbol('power', 'PWR_FLAG'); sh.add_lib(flag)
            sh.items.append(sh._symbol(str(flag['tree'][1]), x, y, 0, f'#FLG{sh.name[:3].upper()}{i:02d}', 'PWR_FLAG', {}, flag, root_uuid, power=True))
            sh.wire(x, y, x, y + G)
            if net in POWER_NETS:
                sh.power(net, x, y + G, 0 if net == 'GND' else 180, root_uuid)
            else:
                sh.label(net, x, y + G, 270, 'label')
        if name == 'PowerSupply':
            # PWR_FLAGs: the rails are sourced by connector pins / the inductor, so KiCad needs explicit flags
            fx, fy = W - 60.0, H - 40.0
            for i, net in enumerate(('VIN_RAW', '+3V3', 'GND')):
                pwr_flag(sh, i + 1, net, round((fx + 15 * i) / G) * G, round(fy / G) * G)
            sh.text('PWR_FLAG: VIN_RAW comes from the battery solder pad, +3V3 from L1 - neither is a power output pin', fx - 40, fy + 12, 1.0)
        if name == 'CAN_Bus':
            pwr_flag(sh, 1, 'CAN_VCC', round((W - 50.0) / G) * G, round((H - 40.0) / G) * G)
            sh.text('PWR_FLAG: CAN_VCC (TCAN1042H VCC, 4.5-5.5 V) is supplied externally through CANHEADER pin 2', W - 110, H - 26, 1.0)
        if name == 'MCU':
            sh.text('VBAT (pin 1) is unconnected on the fabricated board (single-node net in pstxnet.dat); BOOT0 (pin 60) is unconnected.', 12.7, H - 16.0, 1.0)
        sheets.append(sh)
    # ---- root sheet with sheet symbols + local labels joining the sheet pins
    root = Sheet('Root', PROJ + '.kicad_sch', 'A3', 'Top level: one sheet per OrCAD block', [])
    root.text('LoRa Autonomous Boat Controller V1 - as fabricated (senior design v5.brd, 2025-05-09). Hierarchy mirrors the OrCAD Capture blocks.', 12.7, 12.7, 2.0)
    root.text('Power rails GND, +3V3 and VIN_RAW are global power symbols; every other inter-sheet net enters through the sheet pins below.', 12.7, 17.78, 1.27)
    blocks = []
    cols = 4; gx, gy = 100.0, 25.4
    for i, sh in enumerate(sheets):
        hier = sorted(sh.hier)
        h = max(25.4, G * (len(hier) + 2))
        w = 63.5
        col, row = i % cols, i // cols
        x = round((12.7 + 12.7 + col * gx) / G) * G
        y = round((gy + row * 125.0) / G) * G
        pins = ''
        for k, net in enumerate(hier):
            py = y + G * (k + 1)
            pins += f'\n\t\t(pin "{esc(net)}" passive\n\t\t\t(at {f(x)} {f(py)} 180)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(justify right)\n\t\t\t)\n\t\t\t(uuid "{uid("sheetpin", sh.name, net)}")\n\t\t)'
            root.wire(x, py, x - 2 * G, py)
            root.label(net, x - 2 * G, py, 180, 'label')
        blocks.append(f'\t(sheet\n\t\t(at {f(x)} {f(y)})\n\t\t(size {f(w)} {f(h)})\n\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(dnp no)\n\t\t(fields_autoplaced yes)\n\t\t(stroke\n\t\t\t(width 0.1524)\n\t\t\t(type solid)\n\t\t)\n\t\t(fill\n\t\t\t(color 0 0 0 0.0000)\n\t\t)\n\t\t(uuid "{sh.uuid}")\n'
                      f'\t\t(property "Sheetname" "{sh.name}"\n\t\t\t(at {f(x)} {f(y - 0.7116)} 0)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(justify left bottom)\n\t\t\t)\n\t\t)\n'
                      f'\t\t(property "Sheetfile" "{sh.file}"\n\t\t\t(at {f(x)} {f(y + h + 0.5846)} 0)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(justify left top)\n\t\t\t)\n\t\t){pins}\n'
                      f'\t\t(instances\n\t\t\t(project "{PROJ}"\n\t\t\t\t(path "/{root_uuid}"\n\t\t\t\t\t(page "{i + 2}")\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)')
        root.text(sh.descr, x, y + h + 6.0, 0.9)
    open(os.path.join(KDIR, root.file), 'w', encoding='utf-8', newline='\n').write(root.render(root_uuid, root=True, sheets_block='\n'.join(blocks)))
    for sh in sheets:
        open(os.path.join(KDIR, sh.file), 'w', encoding='utf-8', newline='\n').write(sh.render(root_uuid))
    json.dump({'root_uuid': root_uuid, 'sheet_uuid': {sh.name: sh.uuid for sh in sheets}, 'paths': paths}, open(os.path.join(BUILD, 'sch_paths.json'), 'w'), indent=1)
    print('wrote', root.file, 'and', len(sheets), 'sub-sheets;', len(paths), 'symbols;', 'hierarchical nets:', sorted({n for sh in sheets for n in sh.hier}))

if __name__ == '__main__':
    main()
