#!/usr/bin/env python3
"""gen_symbols.py - Write the project symbol library hardware/kicad/LoRa_Boat_Controller.kicad_sym with the symbols
that the KiCad 9 standard libraries lack, pinned to the current datasheets (docs/research/DATASHEET_NOTES.md):
  R1240N001x       Nisshinbo (ex-Ricoh) R1240N asynchronous buck, SOT-23-6W: 1 CE, 2 VIN, 3 LX, 4 BST, 5 GND, 6 VFB
  TCAN1042H-Q1     TI TCAN1042HDRQ1 SOIC-8: 1 TXD, 2 GND, 3 VCC, 4 RXD, 5 NC, 6 CANL, 7 CANH, 8 STB
  CMS06_Schottky   Toshiba CMS06 M-FLAT: pin 1 anode, pin 2 cathode (KiCad Device:D has 1=K, so a project symbol is needed)
  VIN_RAW          power symbol for the battery input rail (Allegro net N088060)
Run from repo root: python hardware/kicad/tools/gen_symbols.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from kicad_write import uid
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
OUT = os.path.join(ROOT, 'hardware', 'kicad', 'LoRa_Boat_Controller.kicad_sym')

FONT = '(effects (font (size 1.27 1.27)))'
def prop(name, value, x, y, hide=False, justify=None):
    j = f' (justify {justify})' if justify else ''
    h = ' (hide yes)' if hide else ''
    return f'\t\t(property "{name}" "{value}" (at {x} {y} 0) (effects (font (size 1.27 1.27)){j}{h}))'

def pin(ptype, x, y, ang, name, num, length=2.54):
    return f'\t\t\t(pin {ptype} line (at {x} {y} {ang}) (length {length}) (name "{name}" {FONT}) (number "{num}" {FONT}))'

def rect(x1, y1, x2, y2):
    return f'\t\t\t(rectangle (start {x1} {y1}) (end {x2} {y2}) (stroke (width 0.254) (type default)) (fill (type background)))'

def ic(name, ref_prefix, value, footprint, datasheet, descr, keywords, pins, body):
    L = [f'\t(symbol "{name}"', '\t\t(pin_names (offset 1.016))', '\t\t(exclude_from_sim no)', '\t\t(in_bom yes)', '\t\t(on_board yes)',
         prop('Reference', ref_prefix, -7.62, body[1] + 1.27, justify='left'),
         prop('Value', value, -7.62, body[0] - 1.27 - 1.27, justify='left'),
         prop('Footprint', footprint, 0, -15.24, hide=True),
         prop('Datasheet', datasheet, 0, -17.78, hide=True),
         prop('Description', descr, 0, -20.32, hide=True),
         prop('ki_keywords', keywords, 0, 0, hide=True),
         f'\t\t(symbol "{name}_0_1"', rect(-body[2], body[1], body[2], body[0]), '\t\t)',
         f'\t\t(symbol "{name}_1_1"'] + pins + ['\t\t)', '\t\t(embedded_fonts no)', '\t)']
    return '\n'.join(L)

def main():
    syms = []
    # --- R1240N001x (SOT-23-6W): datasheet EA-190-240903 p.3 pin table
    syms.append(ic('R1240N001x', 'U', 'R1240N001B-TR-FE', 'LoRa_Boat_Controller:SOT-23-6W_PE-SOT23-6W-0512_NMD',
                   'https://www.nisshinbo-microdevices.co.jp/en/pdf/datasheet/r1240-ea.pdf',
                   '1.25 MHz asynchronous step-down DC/DC converter (external Schottky catch diode required), SOT-23-6W. Pins per Nisshinbo DS EA-190-240903.',
                   'buck regulator ricoh nisshinbo', [
                       pin('power_in', -10.16, 5.08, 0, 'VIN', '2'), pin('input', -10.16, 0, 0, 'CE', '1'),
                       pin('power_out', 10.16, 5.08, 180, 'LX', '3'), pin('passive', 10.16, 0, 180, 'BST', '4'),
                       pin('input', 10.16, -5.08, 180, 'VFB', '6'), pin('power_in', 0, -10.16, 90, 'GND', '5')],
                   (-7.62, 7.62, 7.62)))
    # --- TCAN1042H-Q1 (SOIC-8): TI SLLSES9D pin table (H variant: pin 5 NC)
    syms.append(ic('TCAN1042H-Q1', 'U', 'TCAN1042HDRQ1', 'LoRa_Boat_Controller:D0008A_L',
                   'https://www.ti.com/lit/ds/symlink/tcan1042h-q1.pdf',
                   'Automotive CAN FD transceiver, 5 V VCC (4.5-5.5 V), SOIC-8. Pins per TI SLLSES9D. STB has internal pull-up (HIGH = standby).',
                   'CAN transceiver', [
                       pin('input', -10.16, 5.08, 0, 'TXD', '1'), pin('output', -10.16, 2.54, 0, 'RXD', '4'), pin('input', -10.16, -2.54, 0, 'STB', '8'),
                       pin('bidirectional', 10.16, 2.54, 180, 'CANH', '7'), pin('bidirectional', 10.16, -2.54, 180, 'CANL', '6'),
                       pin('no_connect', 10.16, -5.08, 180, 'NC', '5'),
                       pin('power_in', 0, 10.16, 270, 'VCC', '3'), pin('power_in', 0, -10.16, 90, 'GND', '2')],
                   (-7.62, 7.62, 7.62)))
    # --- CMS06 Schottky with Toshiba pin numbering (1 = anode, 2 = cathode)
    d = ['\t(symbol "CMS06_Schottky"', '\t\t(pin_numbers hide)', '\t\t(pin_names (offset 1.016) hide)', '\t\t(exclude_from_sim no)', '\t\t(in_bom yes)', '\t\t(on_board yes)',
         prop('Reference', 'D', 0, 2.54), prop('Value', 'CMS06(TE12L,Q,M)', 0, -2.54),
         prop('Footprint', 'LoRa_Boat_Controller:M-FLAT_TOS-L', 0, -5.08, hide=True),
         prop('Datasheet', 'https://toshiba.semicon-storage.com/info/CMS06_datasheet_en_20190723.pdf', 0, -7.62, hide=True),
         prop('Description', 'Schottky barrier diode 30 V 2 A, M-FLAT. Pin 1 anode, pin 2 cathode (Toshiba numbering).', 0, -10.16, hide=True),
         prop('ki_keywords', 'diode schottky', 0, 0, hide=True),
         '\t\t(symbol "CMS06_Schottky_0_1"',
         '\t\t\t(polyline (pts (xy 1.27 0) (xy -1.27 0)) (stroke (width 0) (type default)) (fill (type none)))',
         '\t\t\t(polyline (pts (xy -1.27 1.27) (xy -1.27 -1.27) (xy 1.27 0) (xy -1.27 1.27)) (stroke (width 0.254) (type default)) (fill (type none)))',
         '\t\t\t(polyline (pts (xy 0.635 1.27) (xy 1.27 1.27) (xy 1.27 -1.27) (xy 1.905 -1.27)) (stroke (width 0.254) (type default)) (fill (type none)))',
         '\t\t)',
         '\t\t(symbol "CMS06_Schottky_1_1"',
         pin('passive', -3.81, 0, 0, 'A', '1'), pin('passive', 3.81, 0, 180, 'K', '2'),
         '\t\t)', '\t\t(embedded_fonts no)', '\t)']
    syms.append('\n'.join(d))
    # --- VIN_RAW power symbol (same shape as power:VCC)
    p = ['\t(symbol "VIN_RAW"', '\t\t(power)', '\t\t(pin_numbers hide)', '\t\t(pin_names (offset 0) hide)', '\t\t(exclude_from_sim no)', '\t\t(in_bom yes)', '\t\t(on_board yes)',
         prop('Reference', '#PWR', 0, -3.81, hide=True), prop('Value', 'VIN_RAW', 0, 3.556),
         prop('Footprint', '', 0, 0, hide=True), prop('Datasheet', '', 0, 0, hide=True),
         prop('Description', 'Battery input rail (Allegro net N088060); unregulated, unprotected on V1', 0, 0, hide=True),
         prop('ki_keywords', 'global power', 0, 0, hide=True),
         '\t\t(symbol "VIN_RAW_0_1"',
         '\t\t\t(polyline (pts (xy -0.762 1.27) (xy 0 2.54)) (stroke (width 0) (type default)) (fill (type none)))',
         '\t\t\t(polyline (pts (xy 0 0) (xy 0 2.54)) (stroke (width 0) (type default)) (fill (type none)))',
         '\t\t\t(polyline (pts (xy 0 2.54) (xy 0.762 1.27)) (stroke (width 0) (type default)) (fill (type none)))',
         '\t\t)',
         '\t\t(symbol "VIN_RAW_1_1"', pin('power_in', 0, 0, 90, '~', '1', length=0), '\t\t)', '\t\t(embedded_fonts no)', '\t)']
    syms.append('\n'.join(p))
    out = ['(kicad_symbol_lib', '\t(version 20241209)', '\t(generator "gen_symbols.py")', '\t(generator_version "9.0")'] + syms + [')']
    open(OUT, 'w', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')
    print('wrote', OUT)

if __name__ == '__main__':
    main()
