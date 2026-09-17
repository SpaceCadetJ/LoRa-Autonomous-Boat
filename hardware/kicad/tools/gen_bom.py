#!/usr/bin/env python3
"""gen_bom.py - Build the V1 bill of materials with manufacturer part numbers.
  1. writes hardware/kicad/_build/mpn.json  (ref -> MPN / Manufacturer / Description / Confidence / price) from the
     research in docs/research/BOM_MPN_RESEARCH.md (table transcribed below; HIGH = exact part from the design's own
     device name, MEDIUM = series + value chosen, TBD = not determinable from the design)
  2. after gen_sch.py has embedded those properties, exports docs/BOM.csv with kicad-cli sch export bom and
     rewrites it with the columns Ref, Allegro_RefDes, Qty, Value, MPN, Manufacturer, Description, Footprint,
     Confidence, Unit price (qty 1), Source.
Run from repo root:  python hardware/kicad/tools/gen_bom.py [--json-only]
"""
import os, sys, json, csv, subprocess, io
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
KDIR = os.path.join(ROOT, 'hardware', 'kicad'); BUILD = os.path.join(KDIR, '_build')
KICAD_BIN = os.environ.get('KICAD_BIN', r'C:\Users\Jay\AppData\Local\Programs\KiCad\9.0\bin')
from v1_design import kicad_ref, allegro_ref

PRICE_DATE = '2026-09-16'
# (refs, MPN, manufacturer, description, confidence, unit price qty1 USD, source note)
TABLE = [
    (['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'C22'], 'KGM21NR71H104KT', 'Kyocera AVX', '0.1 uF 10% 50 V X7R MLCC 0805', 'HIGH', 0.11, 'Mouser'),
    (['C10', 'CEXT'], 'CL10A475KP8NNNC', 'Samsung Electro-Mechanics', '4.7 uF 10% 10 V X5R MLCC 0603 (design gives CL10A + 0603 only; 10 V chosen)', 'MEDIUM', 0.11, 'Mouser'),
    (['C12'], 'CL10B104KB8NNNC', 'Samsung Electro-Mechanics', '0.1 uF 10% 50 V X7R MLCC 0603 (design gives CL10 + 0603 only)', 'MEDIUM', 0.16, 'Mouser'),
    (['C14'], '06035A471JAT2A', 'Kyocera AVX', '470 pF 5% 50 V C0G MLCC 0603 (global PN KGM15ACG1H471JT)', 'MEDIUM', 0.12, 'Mouser'),
    (['C20', 'C21'], 'GRM21BR61C106KE15L', 'Murata', '10 uF 10% 16 V X5R MLCC 0805 (design gives GRM21 only)', 'MEDIUM', 0.12, 'Mouser'),
    (['C23'], 'GJM1555C1H220JB01D', 'Murata', '22 pF 5% 50 V C0G MLCC 0402 - NOTE: device name encodes 22 pF, schematic value says 47 pF (GJM1555C1H470JB01D); resolve', 'HIGH (MPN) / value conflict', 0.15, 'Mouser'),
    (['CIN'], 'KTS500B106M55N0T00', 'Nippon Chemi-Con', '10 uF 20% 50 V X7R MLCC 2220 (NTS series; not Kemet, not 1210)', 'HIGH', 4.37, 'Mouser'),
    (['COUT'], 'GRM31CR71E106KA12L', 'Murata', '10 uF 10% 25 V X7R MLCC 1206 (design gives GRM31 only)', 'MEDIUM', 0.33, 'Mouser'),
    (['D21'], 'CMS06(TE12L,Q,M)', 'Toshiba', 'Schottky barrier diode 30 V 2 A, M-FLAT (buck catch diode)', 'HIGH', 0.88, 'Mouser'),
    (['L1'], 'SLF7045T-4R7M2R0-PF', 'TDK', '4.7 uH 20% 2.0 A shielded power inductor 7x7x4.5 mm - EOL (TDK PCN 2024-07-30, last ship 2026-12-31); substitute VLS6045EX-4R7M-H needs a new footprint', 'HIGH (obsolete)', 0.37, 'Arrow residual stock'),
    (['L3', 'L4'], 'BLM15AG601SN1D', 'Murata', 'Ferrite bead 600 ohm @100 MHz 300 mA 0402 - value not specified in the design (typical pick)', 'TBD', 0.10, 'Mouser'),
    (['R1'], 'ERJ-2RKF1502X', 'Panasonic', '15 kohm 1% 0.1 W thick film 0402', 'MEDIUM', 0.11, 'Mouser'),
    (['R2'], 'RC0603FR-074K7L', 'Yageo', '4.7 kohm 1% 0.1 W thick film 0603', 'MEDIUM', 0.10, 'Mouser'),
    (['R3'], 'RC0402FR-0751RL', 'Yageo', '51 ohm 1% 1/16 W thick film 0402', 'MEDIUM', 0.11, 'Mouser'),
    (['R4'], 'ERJ-2RKF5101X', 'Panasonic', '5.1 kohm 1% 0.1 W thick film 0402', 'MEDIUM', 0.10, 'Mouser'),
    (['R5'], 'RC0805FR-0730KL', 'Yageo', '30 kohm 1% 0805 thick film (design intent ROHM MCR10EZPF3002, no longer orderable)', 'MEDIUM (substitute)', 0.10, 'estimate'),
    (['R6'], 'RC1005F103CS', 'Samsung Electro-Mechanics', '10 kohm 1% 1/16 W thick film 0402', 'MEDIUM', 0.10, 'Digi-Key'),
    (['U3'], 'STM32F446RET6', 'STMicroelectronics', 'Arm Cortex-M4 180 MHz, 512 KB flash, 128 KB SRAM, LQFP-64 (TR = tape-and-reel of the same die)', 'HIGH', 10.57, 'Mouser'),
    (['U5'], 'TCAN1042HDRQ1', 'Texas Instruments', 'Automotive CAN FD transceiver, 5 V VCC, SOIC-8 (Mouser flags EOL; TI successor TCAN1044A-Q1)', 'HIGH', 2.19, 'Mouser'),
    (['U6'], 'R1240N001B-TR-FE', 'Nisshinbo Micro Devices (ex-Ricoh)', '1.25 MHz asynchronous step-down DC/DC, 4.5-30 V in, 1.2 A, SOT-23-6W', 'HIGH', 1.77, 'Mouser'),
    (['JTAG'], 'FTSH-105-01-L-DV-K', 'Samtec', '2x5 1.27 mm SMT header, keyed (ARM Cortex 10-pin debug)', 'HIGH', 1.24, 'Mouser'),
    (['CANHEADER'], 'B4B-XH-A(LF)(SN)', 'JST', 'XH 2.5 mm 4-position vertical through-hole header', 'HIGH', 0.21, 'Digi-Key'),
    (['GPSMODULE', 'LORAMODULE'], 'PPTC051LFBN-RC', 'Sullins Connector Solutions', '1x5 2.54 mm female header, through-hole', 'HIGH', 0.38, 'Digi-Key'),
    (['SPEEDCONTROLLER', 'STEERINGSERVO'], 'PPTC031LFBN-RC', 'Sullins Connector Solutions', '1x3 2.54 mm female header, through-hole', 'HIGH', 0.30, 'Digi-Key'),
    (['TP1', 'TP3', 'TP4', 'TP5'], '', '', 'Bare plated test-point pad 3.4 mm / 1.4 mm hole (no part; Keystone 5020 would need a footprint change)', 'TBD', 0.0, '-'),
    (['VIN', 'GND'], '', '', 'Bare battery wire solder pad 1.6 mm / 0.6 mm hole (no part)', 'n/a', 0.0, '-'),
]

def main():
    mpn = {}
    for refs, part, mfr, descr, conf, price, src in TABLE:
        for r in refs:
            mpn[r] = {'MPN': part, 'Manufacturer': mfr, 'Description': descr, 'Confidence': conf, 'Price_qty1_USD': price, 'Source': src}
    os.makedirs(BUILD, exist_ok=True)
    json.dump(mpn, open(os.path.join(BUILD, 'mpn.json'), 'w'), indent=1)
    print('wrote', os.path.join(BUILD, 'mpn.json'), len(mpn), 'refs')
    if '--json-only' in sys.argv:
        return
    # export from the schematic (the properties MPN/Manufacturer were embedded by gen_sch.py)
    tmp = os.path.join(BUILD, 'bom_kicad.csv')
    subprocess.run([os.path.join(KICAD_BIN, 'kicad-cli.exe'), 'sch', 'export', 'bom', '--output', tmp,
                    '--fields', 'Reference,Allegro_RefDes,Value,Footprint,MPN,Manufacturer,Description', '--labels', 'Reference,Allegro_RefDes,Value,Footprint,MPN,Manufacturer,Description',
                    '--exclude-dnp', os.path.join(KDIR, 'LoRa_Boat_Controller.kicad_sch')], check=True, capture_output=True)
    rows = list(csv.DictReader(open(tmp, encoding='utf-8-sig')))
    out = []
    total = 0.0
    for r in sorted(rows, key=lambda r: r['Reference']):
        if r['Reference'].startswith('#'):
            continue
        aref = r.get('Allegro_RefDes') or allegro_ref(r['Reference'])
        m = mpn.get(aref, {})
        price = m.get('Price_qty1_USD', 0.0); total += price
        out.append({'Ref': r['Reference'], 'Allegro_RefDes': aref, 'Qty': 1, 'Value': r['Value'], 'MPN': m.get('MPN', r.get('MPN', '')),
                    'Manufacturer': m.get('Manufacturer', ''), 'Description': m.get('Description', r.get('Description', '')),
                    'Footprint': r['Footprint'], 'Confidence': m.get('Confidence', 'TBD'), 'Unit price qty1 USD': f'{price:.2f}' if price else '',
                    'Price source (%s)' % PRICE_DATE: m.get('Source', '')})
    path = os.path.join(ROOT, 'docs', 'BOM.csv')
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
    print(f'wrote {path}: {len(out)} lines, one-board qty-1 total USD {total:.2f} (see docs/research/BOM_MPN_RESEARCH.md)')

if __name__ == '__main__':
    main()
