#!/usr/bin/env python3
"""check_netlist.py - Prove the KiCad schematic and board carry exactly the pstxnet.dat connectivity.
  1. kicad-cli sch export netlist (kicadxml) -> nets {name: [(ref, pin)]}  (refs mapped back to Allegro refdes)
  2. pstxnet.dat -> nets (Allegro names mapped through _build/netmap.json; single-node nets = unconnected pins)
  3. pcbnew: board pads -> nets; footprint paths vs schematic symbol paths (Update-PCB-from-Schematic equivalence)
Writes hardware/kicad/_build/netlist_check.json and prints PASS/FAIL.  Run with KiCad's python from repo root:
  "C:/Users/Jay/AppData/Local/Programs/KiCad/9.0/bin/python.exe" hardware/kicad/tools/check_netlist.py
"""
import os, sys, json, subprocess, xml.etree.ElementTree as ET
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
KDIR = os.path.join(ROOT, 'hardware', 'kicad'); BUILD = os.path.join(KDIR, '_build')
KICAD_BIN = os.environ.get('KICAD_BIN', r'C:\Users\Jay\AppData\Local\Programs\KiCad\9.0\bin')
import allegro_data as ad
from v1_design import allegro_ref, symbol_path, kicad_ref

def sch_netlist():
    xml = os.path.join(BUILD, 'netlist.xml')
    subprocess.run([os.path.join(KICAD_BIN, 'kicad-cli.exe'), 'sch', 'export', 'netlist', '--format', 'kicadxml', '--output', xml,
                    os.path.join(KDIR, 'LoRa_Boat_Controller.kicad_sch')], check=True, capture_output=True)
    t = ET.parse(xml).getroot()
    nets = {}
    for n in t.find('nets'):
        nodes = frozenset((allegro_ref(x.get('ref')), ad.norm_pin(x.get('pin'))) for x in n.findall('node'))
        if nodes:
            nets[n.get('name')] = nodes
    comps = {}
    for c in t.find('components'):
        sp = c.find('sheetpath'); ts = c.find('tstamps')
        comps[allegro_ref(c.get('ref'))] = {'kref': c.get('ref'), 'footprint': c.findtext('footprint'), 'value': c.findtext('value'),
                                            'path': (sp.get('tstamps') if sp is not None else '/') + (ts.text if ts is not None else '')}
    return nets, comps

def main():
    netmap = json.load(open(os.path.join(BUILD, 'netmap.json')))
    pst = ad.load_pstxnet()
    want = {netmap.get(n, n): frozenset((r, p) for r, p, _ in pins) for n, pins in pst.items()}
    got, comps = sch_netlist()
    # compare as sets of pin-sets (net names in KiCad carry sheet prefixes for local nets)
    want_sets = {v: k for k, v in want.items() if len(v) > 1}
    got_sets = {v: k for k, v in got.items() if len(v) > 1}
    missing = [(want_sets[s], sorted(s)) for s in want_sets if s not in got_sets]
    extra = [(got_sets[s], sorted(s)) for s in got_sets if s not in want_sets]
    single = sorted(k for k, v in want.items() if len(v) == 1)
    # name check: the KiCad net name must end with the mapped readable name
    name_mismatch = [(want_sets[s], got_sets[s]) for s in want_sets if s in got_sets and not got_sets[s].split('/')[-1] == want_sets[s]]
    # board check
    import pcbnew
    board = pcbnew.LoadBoard(os.path.join(KDIR, 'LoRa_Boat_Controller.kicad_pcb'))
    pcb_pins = {}
    path_mismatch = []
    fp_mismatch = []
    for fp in board.GetFootprints():
        aref = allegro_ref(fp.GetReference())
        for pad in fp.Pads():
            n = pad.GetNetname()
            if n:
                pcb_pins.setdefault(n, set()).add((aref, ad.norm_pin(pad.GetNumber())))
        p = fp.GetPath().AsString()
        if aref in comps and comps[aref]['path'] != p:
            path_mismatch.append((aref, comps[aref]['path'], p))
        if aref in comps and comps[aref]['footprint'] != fp.GetFPIDAsString():
            fp_mismatch.append((aref, comps[aref]['footprint'], fp.GetFPIDAsString()))
    pcb_sets = {frozenset(v): k for k, v in pcb_pins.items() if len(v) > 1}
    pcb_missing = [(want_sets[s], sorted(s)) for s in want_sets if s not in pcb_sets]
    pcb_extra = [(pcb_sets[s], sorted(s)) for s in pcb_sets if s not in want_sets]
    sch_refs = set(comps); pcb_refs = {allegro_ref(fp.GetReference()) for fp in board.GetFootprints()}
    rep = {'pstxnet_nets': len(want), 'pstxnet_multi_pin_nets': len(want_sets), 'pstxnet_single_pin_nets': single,
           'sch_nets_matching': len(want_sets) - len(missing), 'sch_missing': missing, 'sch_extra': extra, 'sch_name_mismatch': name_mismatch,
           'pcb_nets_matching': len(want_sets) - len(pcb_missing), 'pcb_missing': pcb_missing, 'pcb_extra': pcb_extra,
           'sch_refs': len(sch_refs), 'pcb_refs': len(pcb_refs), 'refs_only_in_sch': sorted(sch_refs - pcb_refs), 'refs_only_in_pcb': sorted(pcb_refs - sch_refs),
           'footprint_path_mismatch': path_mismatch, 'footprint_lib_mismatch': fp_mismatch}
    ok = not (missing or extra or pcb_missing or pcb_extra or path_mismatch or fp_mismatch or (sch_refs ^ pcb_refs) or name_mismatch)
    rep['PASS'] = ok
    json.dump(rep, open(os.path.join(BUILD, 'netlist_check.json'), 'w'), indent=1, default=list)
    print(json.dumps({k: v for k, v in rep.items() if k not in ('sch_missing', 'sch_extra', 'pcb_missing', 'pcb_extra', 'footprint_path_mismatch', 'footprint_lib_mismatch', 'sch_name_mismatch')}, indent=1))
    for k in ('sch_missing', 'sch_extra', 'pcb_missing', 'pcb_extra', 'footprint_path_mismatch', 'footprint_lib_mismatch', 'sch_name_mismatch'):
        if rep[k]:
            print(k, rep[k][:8])
    print('NETLIST CHECK:', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(main())
