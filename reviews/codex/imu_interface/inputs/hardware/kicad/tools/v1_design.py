#!/usr/bin/env python3
"""v1_design.py - Facts shared by gen_pcb.py and gen_sch.py so that schematic and board agree without one having
to run before the other: sheet assignment, deterministic sheet UUIDs, and the KiCad reference designators.

KiCad treats a reference that does not end in a digit as "not annotated" (blocks Update PCB from Schematic), so the
Allegro refdes that lack a number get a '1' suffix.  The original name is kept in the 'Allegro_RefDes' property of
every symbol and footprint and in docs/NETLIST.md / docs/BOM.csv.
"""
import re
from kicad_write import uid

SHEETS = [  # (name, file, paper, OrCAD lineage / description, refs)
    ('PowerSupply', 'PowerSupply.kicad_sch', 'A4', 'OrCAD blocks: Power Supply / POWER BLOCK (battery pads, R1240N buck, D21 catch diode, VBAT divider, TP4/TP5)',
     ['VIN', 'GND', 'CIN', 'U6', 'D21', 'L1', 'C12', 'R3', 'C14', 'R1', 'R2', 'R4', 'COUT', 'R5', 'R6', 'TP4', 'TP5']),
    ('MCU', 'MCU.kicad_sch', 'A3', 'OrCAD blocks: MCU OUTPUTS + MCU power (STM32F446RET6, decoupling C2-C10, CEXT on VCAP_1)',
     ['U3', 'CEXT', 'C10', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9']),
    ('CAN_Bus', 'CAN_Bus.kicad_sch', 'A4', 'OrCAD block: CANBUS module (TCAN1042H-Q1, C1, JST XH header; VCC supplied through the header)',
     ['U5', 'C1', 'CANHEADER']),
    ('LoRa_Module', 'LoRa_Module.kicad_sch', 'A4', 'OrCAD block: LORA Module (RYLR header, BLM15 ferrite pi-filter L3/L4 with C20-C23)',
     ['LORAMODULE', 'L3', 'L4', 'C20', 'C21', 'C22', 'C23']),
    ('GPS_Module', 'GPS_Module.kicad_sch', 'A4', 'OrCAD: TOP VIEW (GPS 1x5 header: 3V3, GND, PB0, USART3_RX, USART3_TX)',
     ['GPSMODULE']),
    ('PWM_Outputs', 'PWM_Outputs.kicad_sch', 'A4', 'OrCAD blocks: Speed Controller + Steering Servo headers (3V3 / signal / GND) with TP1, TP3',
     ['SPEEDCONTROLLER', 'STEERINGSERVO', 'TP1', 'TP3']),
    ('Debug', 'Debug.kicad_sch', 'A4', 'OrCAD block: JTAG Header (Samtec FTSH-105, ARM 10-pin Cortex debug pinout)',
     ['JTAG']),
]
SHEET_OF = {r: s[0] for s in SHEETS for r in s[4]}

def sheet_uuid(name):
    return uid('sch', 'sheet', name)

def root_uuid():
    return uid('sch', 'root')

def kicad_ref(allegro_ref):
    """Allegro refdes -> KiCad reference (numeric suffix added where KiCad needs one)."""
    return allegro_ref if re.search(r'\d$', allegro_ref) else allegro_ref + '1'

def allegro_ref(kref):
    """Inverse of kicad_ref for the refs of this design."""
    for r in SHEET_OF:
        if kicad_ref(r) == kref:
            return r
    return kref

def symbol_uuid(allegro_ref):
    return uid('sch', allegro_ref)

def symbol_path(allegro_ref):
    """KiCad path of the symbol as the PCB footprint stores it: /<sheet uuid>/<symbol uuid>."""
    return f'/{sheet_uuid(SHEET_OF[allegro_ref])}/{symbol_uuid(allegro_ref)}'
