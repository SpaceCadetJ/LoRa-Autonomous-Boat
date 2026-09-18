#!/usr/bin/env python3
"""gen_sch.py - Generate the hierarchical KiCad 9 schematic of V1 from the v5 netlist (pstxnet.dat via
hardware/kicad/evidence/v1_schematic_inputs/v5_board.json), one sub-sheet per subsystem.

Wiring style: every pin gets a short wire stub ending in a net label (local when the net stays on one sheet,
hierarchical when it crosses sheets), a power symbol (GND, +3V3, VIN_RAW) or a no-connect flag.  Sheet pins on the
root sheet are joined with local labels.  Symbol/sheet UUIDs are deterministic so the PCB (gen_pcb.py) carries the
same symbol paths and "Update PCB from Schematic" finds every footprint by path.

Inputs : tracked evidence/v1_schematic_inputs/{v5_board,netmap,mpn}.json by default;
         --input-dir selects a freshly reconstructed input directory explicitly.
         LoRa_Boat_Controller.kicad_sym and KiCad 9 standard symbol libraries are also required.
Outputs: hardware/kicad/LoRa_Boat_Controller.kicad_sch (root) + PowerSupply/MCU/CAN_Bus/LoRa_Module/GPS_Module/
         PWM_Outputs/Debug.kicad_sch, hardware/kicad/_build/sch_paths.json (ref -> symbol path used by the PCB)
Run from repo root: python hardware/kicad/tools/gen_sch.py
"""
import argparse, hashlib, os, sys, json, re
sys.path.insert(0, os.path.dirname(__file__))
import kicad_sym as ks
from kicad_write import uid, f, esc

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
KDIR = os.path.join(ROOT, 'hardware', 'kicad')
BUILD = os.path.join(KDIR, '_build')
EVIDENCE = os.path.join(KDIR, 'evidence', 'v1_schematic_inputs')
PROJ = 'LoRa_Boat_Controller'
PROJLIB = os.path.join(KDIR, PROJ + '.kicad_sym')
G = 2.54          # grid
STUB = 2.54       # wire stub length from pin to label/power symbol
LABEL_ROOM = 20.0 # horizontal room reserved for labels either side of a symbol
POWER_NETS = {'GND': ('power', 'GND', 'down'), '+3V3': ('power', '+3V3', 'up'), 'VIN_RAW': (PROJLIB, 'VIN_RAW', 'up')}
# Pins that carry a single-node net in pstxnet.dat (i.e. are physically unconnected on the fabricated board)
FORCE_NC = {('U3', '1')}   # VBAT: net 'VBAT' has only U3-1 -> floating on V1

from v1_design import SHEETS, SHEET_OF, sheet_uuid, root_uuid as design_root_uuid, kicad_ref, symbol_uuid
PAPER = {'A4': (297.0, 210.0), 'A3': (420.0, 297.0), 'A2': (594.0, 420.0), 'A1': (841.0, 594.0)}

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
    """One schematic sheet.  ref_fn/uuid_fn map a design refdes to the KiCad reference / symbol uuid (V1 uses the
    Allegro refdes with the '1'-suffix rule; V2 passes identity functions).  proj = KiCad project name for instances."""
    def __init__(self, name, file, paper, descr, refs, ref_fn=None, uuid_fn=None, proj=None, title=None):
        self.name, self.file, self.paper, self.descr, self.refs = name, file, paper, descr, refs
        self.ref_fn = ref_fn or kicad_ref
        self.uuid_fn = uuid_fn or symbol_uuid
        self.proj = proj or PROJ
        self.title = title or 'LoRa Autonomous Boat Controller V1'
        self.uuid = uid('sch', self.proj, 'sheet', name) if proj else sheet_uuid(name)   # sheet-symbol uuid (instance paths)
        self.screen_uuid = uid('sch', self.proj, 'screen', name) if proj else uid('sch', 'screen', name)  # the file's own uuid
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
        justify = 'left bottom'
        if kind == 'label' and angle == 180:
            angle = 0
            justify = 'right bottom'
        elif kind != 'label':
            # KiCad port-label orientation denotes the pointing end, opposite
            # to the outward text direction used by this drawing API.
            angle = (angle + 180) % 360
            justify = 'right' if angle == 0 else 'left'
        shape = '(shape passive)' if kind != 'label' else ''
        self.items.append(f'({kind} "{esc(net)}" {shape} (at {f(x)} {f(y)} {angle}) (effects (font (size 1.27 1.27)) (justify {justify})) (uuid "{self._u("label")}"))')
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
        bb = ks.symbol_bbox(sym['tree'])
        rx = vx = x
        top_clearance = 7 if len(sym['pins']) > 2 and any(int(p['angle']) % 180 == 90 for p in sym['pins']) else 0
        ry, vy = y - bb[3] - 12 - top_clearance, y - bb[3] - 8.5 - top_clearance
        justify = ''
        if power:
            side = POWER_NETS.get(value, (None, None, 'up'))[2]
            ry = y - 3.81
            vy = y + (3.556 if side == 'down' else -3.556) * (-1 if rot == 180 else 1)
        elif len(sym['pins']) <= 2:
            if any(int(p['angle']) % 180 == 90 for p in sym['pins']):
                rx = vx = x + bb[2] + 3
                ry, vy = y - 1.5, y + 2
                justify = '(justify left)'
            else:
                ry, vy = y - bb[3] - 3.5, y - bb[1] + 3.5
        def prop(name, text, px, py, hide=False, align=''):
            return f'(property "{esc(name)}" "{esc(text)}" (at {f(px)} {f(py)} 0) (effects (font (size 1.27 1.27)) {align} {"(hide yes)" if hide else ""}))'
        fields = [prop('Reference',ref,rx,ry,power,justify),prop('Value',value,vx,vy,False,justify)]
        fields += [prop(k,v,x,y,True) for k,v in props.items()]
        pins = ''.join(f'(pin "{p["number"]}" (uuid "{self._u("pin")}"))' for p in sym['pins'])
        return f'(symbol (lib_id "{esc(libid)}") (at {f(x)} {f(y)} {rot}) (unit 1) (exclude_from_sim no) (in_bom {"no" if power else "yes"}) (on_board {"no" if power else "yes"}) (dnp no) (uuid "{suuid}") {" ".join(fields)} {pins} (instances (project "{self.proj}" (path "/{root_uuid}/{self.uuid}" (reference "{esc(ref)}") (unit 1)))))'


    def place(self, ref, sym, x, y, value, props, pin_nets, net_sheets, root_uuid):
        """Preserve pin membership; keep properties and pin labels in separate lanes."""
        libid = str(sym['tree'][1])
        self.add_lib(sym)
        props = dict(props)
        if self.ref_fn is kicad_ref:
            props['Allegro_RefDes'] = ref
        self.items.append(self._symbol(libid,x,y,0,self.ref_fn(ref),value,props,sym,root_uuid,suuid=self.uuid_fn(ref)))
        vertical = {}
        for p in sym['pins']:
            px, py = round(x + p['x'], 6), round(y - p['y'], 6)
            a = int(p['angle']) % 360
            net = pin_nets.get(p['number'])
            if p['type'] == 'no_connect' or net is None or (ref,p['number']) in FORCE_NC:
                self.no_connect(px,py)
                continue
            if a in (90,270):
                vertical.setdefault((a,py,net),[]).append(px)
                continue
            dx = -1 if a == 0 else 1
            ex = px + dx * 5.08
            self.wire(px,py,ex,py)
            kind = 'global_label' if net in POWER_NETS else 'hierarchical_label' if len(net_sheets[net]) > 1 else 'label'
            self.label(net,ex,py,180 if dx < 0 else 0,kind)
        prior_power_ends = []
        for (a,py,net), xs in vertical.items():
            dy = 1 if a == 90 else -1
            ey = py + dy * 5.08
            if net in POWER_NETS:
                # Adjacent unlike supply pins (e.g. buffer VCC and /OE-to-GND)
                # need separate text rows above the device.
                if any(aa == a and abs(yy-py) < .001 and abs(xx-min(xs)) < 10 for aa,yy,xx in prior_power_ends):
                    ey += dy * 5.08
                prior_power_ends.append((a,py,min(xs)))
            for px in xs:
                self.wire(px,py,px,ey)
            xs = sorted(set(xs))
            if len(xs) > 1:
                for left, right in zip(xs, xs[1:]):
                    self.wire(left,ey,right,ey)
                for px in xs[1:-1]:
                    self.items.append(f'(junction (at {f(px)} {f(ey)}) (diameter 0) (color 0 0 0 0) (uuid "{self._u("junction")}"))')
            ex = xs[0]
            if net in POWER_NETS:
                natural = 'down' if dy > 0 else 'up'
                self.power(net,ex,ey,0 if natural == POWER_NETS[net][2] else 180,root_uuid)
            else:
                self.wire(ex,ey,ex+2.54,ey)
                self.label(net,ex+2.54,ey,0,'hierarchical_label' if len(net_sheets[net])>1 else 'label')


    def render(self, root_uuid, root=False, sheets_block=''):
        libs = '\n'.join(ks.serialize(t,1) for _,t in sorted(self.libs.items()))
        version = 'V1 / v5' if self.proj == PROJ else 'V2 draft'
        title = self.title + ' - ' + self.name
        out = ['(kicad_sch','(version 20250114)','(generator "gen_sch.py")','(generator_version "9.0")',
               f'(uuid "{root_uuid if root else self.screen_uuid}")',f'(paper "{self.paper}")',
               f'(title_block (title "{esc(title)}") (date "2026-09-17") (rev "{version}") (company "LoRa Controller Project") (comment 1 "Annotated functional groups; connectivity preserved") (comment 2 "Build and review: docs/build/README.md"))',
               '(lib_symbols\n'+libs+'\n)']
        out += self.items
        out.append(sheets_block)
        if root:
            out.append('(sheet_instances (path "/" (page "1")))')
        out += ['(embedded_fonts no)',')']
        return '\n'.join(x for x in out if x)+'\n'


def load_inputs(input_dir=None):
    """Read one coherent input set; tracked captures are checked before use.

    Explicit directories retain the legacy optional MPN behavior. The default
    uses pinned evidence even if an unrelated/stale local _build is present.
    """
    source = os.path.abspath(input_dir) if input_dir else EVIDENCE
    names = ('v5_board.json', 'netmap.json', 'mpn.json')
    if input_dir is None:
        with open(os.path.join(source, 'manifest.json'), encoding='utf-8') as fh:
            manifest = json.load(fh)
        expected = {item['file']: item['sha256'] for item in manifest['captures']}
        for name in names:
            with open(os.path.join(source, name), 'rb') as fh:
                digest = hashlib.sha256(fh.read()).hexdigest()
            if digest != expected.get(name):
                raise ValueError(f'Captured schematic input hash mismatch: {name}')
    result = []
    for name in names:
        path = os.path.join(source, name)
        if name == 'mpn.json' and input_dir is not None and not os.path.exists(path):
            result.append({})
        else:
            with open(path, encoding='utf-8') as fh:
                result.append(json.load(fh))
    print('V1 schematic inputs:', os.path.relpath(source, ROOT))
    return tuple(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', help='Directory with v5_board.json, netmap.json and optional mpn.json; defaults to verified tracked evidence')
    args = parser.parse_args()
    from schematic_layout import generate_v1
    generate_v1(sys.modules[__name__], args.input_dir)


if __name__ == '__main__':
    main()
