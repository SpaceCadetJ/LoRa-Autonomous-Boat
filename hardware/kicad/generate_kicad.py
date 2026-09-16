#!/usr/bin/env python3
"""
Generate KiCad 9 project files from extracted Allegro DSN design data.
LoRa Autonomous Boat Controller - Cadence Allegro to KiCad conversion.

Source: senior design v2.dsn (Specctra DSN export from Allegro PCB Editor 22.1)
Target: STM32F446RET6 + TCAN1042H + R1240N + LoRa/GPS modules
"""

import json, uuid, os, time

# Load extracted design data
with open('design_data.json', 'r') as f:
    data = json.load(f)

placements = data['placements']
nets = data['nets']

# ============================================================
# FOOTPRINT MAPPING: Allegro -> KiCad standard library
# ============================================================
FOOTPRINT_MAP = {
    # 0402 caps (1005 metric)
    "CAP_CL05_SAM": "Capacitor_SMD:C_0402_1005Metric",
    # 0603 caps
    "CAP_0603_CL10A_1P6XP8_SAM": "Capacitor_SMD:C_0603_1608Metric",
    "CAP_CL10_SAM": "Capacitor_SMD:C_0603_1608Metric",
    "CAP_0603G_AVX": "Capacitor_SMD:C_0603_1608Metric",
    "CAPC17595_95N_KEM": "Capacitor_SMD:C_0603_1608Metric",
    "CAP_GJM1555C1H220JB01__MUR": "Capacitor_SMD:C_0402_1005Metric",
    # Larger caps
    "G-21_MUR": "Capacitor_SMD:C_0805_2012Metric",
    "G-31_MUR": "Capacitor_SMD:C_1206_3216Metric",
    "CAP_NTS_55_2P8T_NIP": "Capacitor_SMD:C_1210_3225Metric",
    # Resistors
    "RC0402N_PAN": "Resistor_SMD:R_0402_1005Metric",
    "RC0402N_YAG": "Resistor_SMD:R_0402_1005Metric",
    "RC0603N_YAG": "Resistor_SMD:R_0603_1608Metric",
    "RES_1005_SAM": "Resistor_SMD:R_0402_1005Metric",
    "RES_R0805_ROM": "Resistor_SMD:R_0805_2012Metric",
    # Inductors
    "IND_1608_TDK": "Inductor_SMD:L_0603_1608Metric",
    "IND_BLM15_0402_MUR": "Inductor_SMD:L_0402_1005Metric",
    # ICs
    "LQFP64-10X10MM": "Package_QFP:LQFP-64_10x10mm_P0.5mm",
    "D0008A_L": "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    "SOT-323-3_2X1P25_ONS": "Package_TO_SOT_SMD:SOT-323_SC-70",
    "SOT-23-6W_PE-SOT23-6W-0512_NMD": "Package_TO_SOT_SMD:SOT-23-6",
    # Connectors
    "CONN_B4B-XH-A_JST": "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical",
    "CONN_PPTC031_SUL": "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
    "CONN_SBH11-PBPC-D05-ST-BK_SUL": "Connector_IDC:IDC-Header_2x05_P2.54mm_Vertical",
    "CONN5_1LFBN-RC_SUL": "Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical",
    # Test points & terminals
    "AMV_TEST_POINT": "TestPoint:TestPoint_Pad_D1.0mm",
    "AMV_CON1": "Connector_PinHeader_2.54mm:PinHeader_1x01_P2.54mm_Vertical",
    "AMC_TEST_POINT": "TestPoint:TestPoint_Pad_D1.0mm",
}

def get_kicad_footprint(allegro_fp):
    """Map Allegro footprint name to KiCad library footprint."""
    # Strip the per-component suffix (e.g. _C1, _U3, etc)
    base = allegro_fp.strip("'")
    # Try progressively shorter prefixes
    for key in sorted(FOOTPRINT_MAP.keys(), key=len, reverse=True):
        if base.startswith(key):
            return FOOTPRINT_MAP[key]
    return f"LoRa_Boat_Controller:{base}"  # fallback to project lib

# ============================================================
# SYMBOL MAPPING: Component values -> KiCad symbol library
# ============================================================
def get_kicad_symbol(ref, value):
    """Map component to KiCad symbol library reference."""
    if ref.startswith('C'):
        return "Device:C"
    elif ref.startswith('R'):
        return "Device:R"
    elif ref.startswith('L'):
        return "Device:L"
    elif ref == 'U3':
        return "MCU_ST:STM32F446RETx"
    elif ref == 'U5':
        return "Interface_CAN_LIN:TCAN1042"
    elif ref == 'U6':
        return "Regulator_Switching:R1240N001x"  # custom, will need lib
    elif ref == 'U1':
        return "Device:D_Schottky"  # ESD protection
    elif ref.startswith('TP'):
        return "Connector:TestPoint"
    elif ref in ('GND', 'VIN'):
        return "Connector:Conn_01x01_Pin"
    elif ref in ('CANHEADER',):
        return "Connector:Conn_01x04_Pin"
    elif ref in ('SPEEDCONTROLLER', 'STEERINGSERVO'):
        return "Connector:Conn_01x03_Pin"
    elif ref == 'JTAG':
        return "Connector:Conn_02x05_Odd_Even"
    elif ref in ('GPSMODULE', 'LORAMODULE'):
        return "Connector:Conn_01x05_Pin"
    return "Device:R"  # fallback

# ============================================================
# STM32F446RET6 PIN MAP (LQFP-64)
# ============================================================
STM32_PINS = {
    1: "VBAT", 2: "PC13", 3: "PC14", 4: "PC15", 5: "PH0", 6: "PH1",
    7: "NRST", 8: "PC0", 9: "PC1", 10: "PC2", 11: "PC3", 12: "VSSA",
    13: "VDDA", 14: "PA0", 15: "PA1", 16: "PA2", 17: "PA3", 18: "VSS",
    19: "VDD", 20: "PA4", 21: "PA5", 22: "PA6", 23: "PA7", 24: "PC4",
    25: "PC5", 26: "PB0", 27: "PB1", 28: "PB2", 29: "PB10", 30: "PB11",
    31: "VCAP_1", 32: "VDD", 33: "PB12", 34: "PB13", 35: "PB14",
    36: "PB15", 37: "PC6", 38: "PC7", 39: "PC8", 40: "PC9",
    41: "PA8", 42: "PA9", 43: "PA10", 44: "PA11", 45: "PA12",
    46: "PA13", 47: "VSS", 48: "VDD", 49: "PA14", 50: "PA15",
    51: "PC10", 52: "PC11", 53: "PC12", 54: "PD2", 55: "PB3",
    56: "PB4", 57: "PB5", 58: "PB6", 59: "PB7", 60: "BOOT0",
    61: "PB8", 62: "PB9", 63: "VSS", 64: "VDD"
}

# ============================================================
# Net name cleanup 
# ============================================================
NET_NAME_MAP = {
    "0": "GND",
    "3.3V": "+3V3",
    "N088060": "VIN_RAW",
    "N068040": "VREG_OUT",
    "N18028": "SW_NODE",
    "N17576": "FB_DIV",
    "N17942": "BST",
    "N055670": "EN",
    "N061071": "COIL_SENSE",
    "N04429": "LORA_VCC",
    "N04477": "LORA_TX",
    "N04485": "LORA_RX",
    "N24517": "LORA_RST",
    "N04277": "GPS_RX",
    "N04281": "GPS_TX_PC11",
    "N04285": "GPS_TX_PC10",
    "N04755": "CAN_TX",
    "N04759": "CAN_RX",
    "N04763": "CAN_STB",
    "N04855": "CANH",
    "N24691": "CANL",
    "N24886": "CAN_VCC",
    "N04355": "PWM_MOTOR",
    "N04395": "PWM_RUDDER",
    "N27410": "LORA_FILT",
    "N27791": "VCAP1",
    "ADC": "ADC_VBAT",
    "VBAT": "VBAT",
    "RESET": "NRST",
    "PA14TCLK": "JTAG_TCK",
    "'PA13": "SWDIO",
    "'PA14": "SWCLK",
    "'PA15": "JTDI",
    "'PB3": "JTDO_SWO",
    "GND": "GND_BAT",
}

def clean_net_name(n):
    return NET_NAME_MAP.get(n, n)

# ============================================================
# Generate KiCad project file (.kicad_pro)
# ============================================================
def gen_project():
    return json.dumps({
        "board": {"3dviewports": [], "design_settings": {"defaults": {
            "board_outline_line_width": 0.1,
            "copper_line_width": 0.2,
            "copper_text_size_h": 1.5,
            "copper_text_size_v": 1.5,
            "copper_text_thickness": 0.3,
        }}, "layers": {"0": ["F.Cu", "signal"], "31": ["B.Cu", "signal"]},
        },
        "meta": {"filename": "LoRa_Boat_Controller.kicad_pro", "version": 1},
        "net_settings": {"classes": [{"name": "Default", "clearance": 0.2,
            "track_width": 0.25, "via_diameter": 0.6, "via_drill": 0.3}]},
        "schematic": {"meta": {"version": 1}},
        "sheets": [["", ""]],
    }, indent=2)

# ============================================================
# Generate KiCad schematic (.kicad_sch) - KiCad 9 format
# ============================================================
def new_uuid():
    return str(uuid.uuid4())

def gen_schematic():
    """Generate a flat KiCad schematic with all components and wiring notes."""
    lines = []
    lines.append('(kicad_sch')
    lines.append('  (version 20231120)')
    lines.append('  (generator "allegro_to_kicad_converter")')
    lines.append('  (generator_version "1.0")')
    lines.append(f'  (uuid "{new_uuid()}")')
    lines.append('  (paper "A3")')
    lines.append('')
    lines.append('  (title_block')
    lines.append('    (title "LoRa Autonomous Boat Controller")')
    lines.append('    (date "2026-03-31")')
    lines.append('    (rev "1.0")')
    lines.append('    (comment 1 "Converted from Cadence Allegro / OrCAD Capture")')
    lines.append('    (comment 2 "STM32F446RET6 + TCAN1042H + R1240N + LoRa/GPS")')
    lines.append('    (comment 3 "Original: SeniorDesign_Board.opj (SPB 22.1)")')
    lines.append('  )')
    lines.append('')

    # Build a pin-to-net lookup
    pin_net = {}  # ref-pin -> net_name
    for net_name, pin_list in nets.items():
        cn = clean_net_name(net_name)
        for pin_str in pin_list:
            pin_net[pin_str] = cn

    # Functional block layout positions (schematic coordinates in mm)
    BLOCKS = {
        'power_supply': {'title': 'Power Supply', 'x': 30, 'y': 40,
            'refs': ['VIN', 'GND', 'CIN', 'U6', 'U1', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6',
                     'C12', 'C14', 'L1', 'COUT', 'COUT1']},
        'mcu': {'title': 'MCU - STM32F446RET6', 'x': 140, 'y': 40,
            'refs': ['U3', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'C10', 'CEXT']},
        'can_bus': {'title': 'CAN Bus Transceiver', 'x': 250, 'y': 40,
            'refs': ['U5', 'CANHEADER']},
        'lora': {'title': 'LoRa Module (RYLR)', 'x': 250, 'y': 120,
            'refs': ['LORAMODULE', 'L3', 'L4', 'C20', 'C21', 'C22', 'C23']},
        'gps': {'title': 'GPS Module', 'x': 250, 'y': 190,
            'refs': ['GPSMODULE']},
        'outputs': {'title': 'PWM Outputs', 'x': 30, 'y': 190,
            'refs': ['SPEEDCONTROLLER', 'STEERINGSERVO']},
        'debug': {'title': 'Debug / JTAG', 'x': 140, 'y': 190,
            'refs': ['JTAG', 'TP1', 'TP3', 'TP4', 'TP5']},
    }

    # Place text labels for each block
    for bname, bdata in BLOCKS.items():
        bx, by = bdata['x'], bdata['y']
        uid = new_uuid()
        lines.append(f'  (text "{bdata["title"]}"')
        lines.append(f'    (exclude_from_sim no)')
        lines.append(f'    (at {bx} {by-5} 0)')
        lines.append(f'    (effects (font (size 3 3) (thickness 0.5) bold))')
        lines.append(f'    (uuid "{uid}")')
        lines.append(f'  )')

    # Place each component as a symbol instance
    placed_refs = set()
    comp_idx = 0
    for bname, bdata in BLOCKS.items():
        bx, by = bdata['x'], bdata['y']
        col = 0
        row = 0
        for ref in bdata['refs']:
            comp = next((p for p in placements if p['ref'] == ref), None)
            if not comp:
                continue
            placed_refs.add(ref)
            
            sx = bx + (col % 4) * 30
            sy = by + (col // 4) * 35 + row
            col += 1

            sym_lib = get_kicad_symbol(ref, comp['value'])
            fp_lib = get_kicad_footprint(comp['footprint'])
            uid = new_uuid()

            lines.append(f'  (symbol')
            lines.append(f'    (lib_id "{sym_lib}")')
            lines.append(f'    (at {sx} {sy} 0)')
            lines.append(f'    (unit 1)')
            lines.append(f'    (exclude_from_sim no)')
            lines.append(f'    (in_bom yes)')
            lines.append(f'    (on_board yes)')
            lines.append(f'    (dnp no)')
            lines.append(f'    (uuid "{uid}")')
            lines.append(f'    (property "Reference" "{ref}"')
            lines.append(f'      (at {sx} {sy-3} 0)')
            lines.append(f'      (effects (font (size 1.27 1.27)))')
            lines.append(f'    )')
            lines.append(f'    (property "Value" "{comp["value"]}"')
            lines.append(f'      (at {sx} {sy+3} 0)')
            lines.append(f'      (effects (font (size 1.27 1.27)))')
            lines.append(f'    )')
            lines.append(f'    (property "Footprint" "{fp_lib}"')
            lines.append(f'      (at {sx} {sy+5} 0)')
            lines.append(f'      (effects (font (size 1.27 1.27)) hide)')
            lines.append(f'    )')
            lines.append(f'  )')
            lines.append('')

    # Any unplaced components
    ux, uy = 30, 260
    for comp in placements:
        if comp['ref'] not in placed_refs:
            ref = comp['ref']
            sym_lib = get_kicad_symbol(ref, comp['value'])
            fp_lib = get_kicad_footprint(comp['footprint'])
            uid = new_uuid()
            lines.append(f'  (symbol')
            lines.append(f'    (lib_id "{sym_lib}")')
            lines.append(f'    (at {ux} {uy} 0)')
            lines.append(f'    (unit 1)')
            lines.append(f'    (exclude_from_sim no)')
            lines.append(f'    (in_bom yes)')
            lines.append(f'    (on_board yes)')
            lines.append(f'    (dnp no)')
            lines.append(f'    (uuid "{uid}")')
            lines.append(f'    (property "Reference" "{ref}"')
            lines.append(f'      (at {ux} {uy-3} 0)')
            lines.append(f'      (effects (font (size 1.27 1.27)))')
            lines.append(f'    )')
            lines.append(f'    (property "Value" "{comp["value"]}"')
            lines.append(f'      (at {ux} {uy+3} 0)')
            lines.append(f'      (effects (font (size 1.27 1.27)))')
            lines.append(f'    )')
            lines.append(f'    (property "Footprint" "{fp_lib}"')
            lines.append(f'      (at {ux} {uy+5} 0)')
            lines.append(f'      (effects (font (size 1.27 1.27)) hide)')
            lines.append(f'    )')
            lines.append(f'  )')
            ux += 30

    lines.append(')')
    return '\n'.join(lines)


# ============================================================
# Generate KiCad PCB (.kicad_pcb) with real placement from DSN
# ============================================================
def gen_pcb():
    """Generate KiCad PCB with footprints placed at Allegro coordinates."""
    lines = []
    
    # Coordinate conversion: Allegro mils -> KiCad mm
    # Allegro origin is lower-left, KiCad is upper-left
    # Board boundary: -1500 to 1500 mils = 3000 mils = 76.2mm
    MIL_TO_MM = 0.0254
    # Center offset - shift Allegro coords so board sits nicely in KiCad
    BOARD_CENTER_X = 0  # Allegro center
    BOARD_CENTER_Y = 0
    KICAD_OFFSET_X = 150  # mm from KiCad origin
    KICAD_OFFSET_Y = 100  # mm from KiCad origin
    
    def ax_to_kx(x_mil):
        return KICAD_OFFSET_X + (x_mil - BOARD_CENTER_X) * MIL_TO_MM
    
    def ay_to_ky(y_mil):
        # Flip Y axis (Allegro Y+ is up, KiCad Y+ is down)
        return KICAD_OFFSET_Y - (y_mil - BOARD_CENTER_Y) * MIL_TO_MM
    
    lines.append('(kicad_pcb')
    lines.append('  (version 20240108)')
    lines.append('  (generator "allegro_to_kicad_converter")')
    lines.append('  (generator_version "1.0")')
    lines.append(f'  (general (thickness 1.6) (legacy_teardrops no))')
    lines.append(f'  (paper "A4")')
    lines.append('')
    
    # Layers
    lines.append('  (layers')
    lines.append('    (0 "F.Cu" signal)')
    lines.append('    (31 "B.Cu" signal)')
    lines.append('    (32 "B.Adhes" user "B.Adhesive")')
    lines.append('    (33 "F.Adhes" user "F.Adhesive")')
    lines.append('    (34 "B.Paste" user)')
    lines.append('    (35 "F.Paste" user)')
    lines.append('    (36 "B.SilkS" user "B.Silkscreen")')
    lines.append('    (37 "F.SilkS" user "F.Silkscreen")')
    lines.append('    (38 "B.Mask" user "B.Mask")')
    lines.append('    (39 "F.Mask" user "F.Mask")')
    lines.append('    (40 "Dwgs.User" user "User.Drawings")')
    lines.append('    (41 "Cmts.User" user "User.Comments")')
    lines.append('    (42 "Eco1.User" user "User.Eco1")')
    lines.append('    (43 "Eco2.User" user "User.Eco2")')
    lines.append('    (44 "Edge.Cuts" user)')
    lines.append('    (45 "Margin" user)')
    lines.append('    (46 "B.CrtYd" user "B.Courtyard")')
    lines.append('    (47 "F.CrtYd" user "F.Courtyard")')
    lines.append('    (48 "B.Fab" user "B.Fab")')
    lines.append('    (49 "F.Fab" user "F.Fab")')
    lines.append('  )')
    lines.append('')
    
    # Setup
    lines.append('  (setup')
    lines.append('    (pad_to_mask_clearance 0.05)')
    lines.append('    (allow_soldermask_bridges_in_footprints no)')
    lines.append('    (pcbplotparams (layerselection 0x00010fc_ffffffff)')
    lines.append('      (plot_on_all_layers_selection 0x0000000_00000000))')
    lines.append('  )')
    lines.append('')
    
    # Nets
    net_idx = 0
    net_map = {}
    lines.append(f'  (net {net_idx} "")')
    net_idx += 1
    for net_name in sorted(nets.keys()):
        cn = clean_net_name(net_name)
        if cn not in net_map:
            net_map[cn] = net_idx
            lines.append(f'  (net {net_idx} "{cn}")')
            net_idx += 1
    lines.append('')
    
    # Board outline (Edge.Cuts) - rectangular 76.2 x 76.2 mm
    bx1 = ax_to_kx(-1500)
    by1 = ay_to_ky(1500)
    bx2 = ax_to_kx(1500)
    by2 = ay_to_ky(-1500)
    lines.append(f'  (gr_rect')
    lines.append(f'    (start {bx1:.4f} {by1:.4f})')
    lines.append(f'    (end {bx2:.4f} {by2:.4f})')
    lines.append(f'    (stroke (width 0.1) (type solid))')
    lines.append(f'    (fill none)')
    lines.append(f'    (layer "Edge.Cuts")')
    lines.append(f'    (uuid "{new_uuid()}")')
    lines.append(f'  )')
    lines.append('')
    
    # Footprints with placement
    for comp in placements:
        ref = comp['ref']
        val = comp['value']
        fp = get_kicad_footprint(comp['footprint'])
        
        # Convert coordinates
        kx = ax_to_kx(comp['x'])
        ky = ay_to_ky(comp['y'])
        rot = comp['rotation']
        layer = "F.Cu" if comp['side'] == 'front' else "B.Cu"
        
        uid = new_uuid()
        
        lines.append(f'  (footprint "{fp}"')
        lines.append(f'    (layer "{layer}")')
        lines.append(f'    (uuid "{uid}")')
        lines.append(f'    (at {kx:.4f} {ky:.4f} {rot})')
        lines.append(f'    (property "Reference" "{ref}"')
        lines.append(f'      (at 0 -2 {rot})')
        lines.append(f'      (layer "{layer.replace("Cu", "SilkS")}")')
        lines.append(f'      (uuid "{new_uuid()}")')
        lines.append(f'      (effects (font (size 0.8 0.8) (thickness 0.15)))')
        lines.append(f'    )')
        lines.append(f'    (property "Value" "{val}"')
        lines.append(f'      (at 0 2 {rot})')
        lines.append(f'      (layer "{layer.replace("Cu", "Fab")}")')
        lines.append(f'      (uuid "{new_uuid()}")')
        lines.append(f'      (effects (font (size 0.8 0.8) (thickness 0.15)))')
        lines.append(f'    )')
        lines.append(f'    (property "Footprint" "{fp}"')
        lines.append(f'      (at 0 0 0)')
        lines.append(f'      (layer "{layer.replace("Cu", "Fab")}")')
        lines.append(f'      (uuid "{new_uuid()}")')
        lines.append(f'      (effects (font (size 1.27 1.27) (thickness 0.15)) hide)')
        lines.append(f'    )')
        lines.append(f'  )')
        lines.append('')
    
    lines.append(')')
    return '\n'.join(lines)


# ============================================================
# Generate symbol library for non-standard parts
# ============================================================
def gen_symbol_lib():
    """Generate a project-local symbol library for parts not in KiCad stdlib."""
    lines = []
    lines.append('(kicad_symbol_lib')
    lines.append('  (version 20231120)')
    lines.append('  (generator "allegro_to_kicad_converter")')
    lines.append('  (generator_version "1.0")')
    lines.append('')
    
    # R1240N001x - Ricoh buck converter (SOT-23-6)
    lines.append('  (symbol "R1240N001x"')
    lines.append('    (pin_names (offset 0.254))')
    lines.append('    (exclude_from_sim no)')
    lines.append('    (in_bom yes)')
    lines.append('    (on_board yes)')
    lines.append('    (property "Reference" "U"')
    lines.append('      (at -6.35 6.35 0)')
    lines.append('      (effects (font (size 1.27 1.27)) (justify left))')
    lines.append('    )')
    lines.append('    (property "Value" "R1240N001x"')
    lines.append('      (at -6.35 -6.35 0)')
    lines.append('      (effects (font (size 1.27 1.27)) (justify left))')
    lines.append('    )')
    lines.append('    (property "Footprint" "Package_TO_SOT_SMD:SOT-23-6"')
    lines.append('      (at 0 0 0)')
    lines.append('      (effects (font (size 1.27 1.27)) hide)')
    lines.append('    )')
    lines.append('    (property "Datasheet" ""')
    lines.append('      (at 0 0 0)')
    lines.append('      (effects (font (size 1.27 1.27)) hide)')
    lines.append('    )')
    lines.append('    (symbol "R1240N001x_0_1"')
    lines.append('      (rectangle (start -7.62 5.08) (end 7.62 -5.08)')
    lines.append('        (stroke (width 0.254) (type default))')
    lines.append('        (fill (type background)))')
    lines.append('    )')
    lines.append('    (symbol "R1240N001x_1_1"')
    lines.append('      (pin input line (at -10.16 2.54 0) (length 2.54) (name "EN" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))')
    lines.append('      (pin power_in line (at -10.16 0 0) (length 2.54) (name "VIN" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))')
    lines.append('      (pin output line (at 10.16 2.54 180) (length 2.54) (name "SW" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))')
    lines.append('      (pin passive line (at 10.16 0 180) (length 2.54) (name "BST" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))')
    lines.append('      (pin power_in line (at 0 -7.62 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))')
    lines.append('      (pin passive line (at 10.16 -2.54 180) (length 2.54) (name "FB" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))')
    lines.append('    )')
    lines.append('  )')
    lines.append('')
    
    # TCAN1042H-Q1 (if not in KiCad stdlib)
    lines.append('  (symbol "TCAN1042H_Q1"')
    lines.append('    (pin_names (offset 0.254))')
    lines.append('    (exclude_from_sim no)')
    lines.append('    (in_bom yes)')
    lines.append('    (on_board yes)')
    lines.append('    (property "Reference" "U"')
    lines.append('      (at -7.62 7.62 0)')
    lines.append('      (effects (font (size 1.27 1.27)) (justify left))')
    lines.append('    )')
    lines.append('    (property "Value" "TCAN1042H-Q1"')
    lines.append('      (at -7.62 -7.62 0)')
    lines.append('      (effects (font (size 1.27 1.27)) (justify left))')
    lines.append('    )')
    lines.append('    (property "Footprint" "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"')
    lines.append('      (at 0 0 0)')
    lines.append('      (effects (font (size 1.27 1.27)) hide)')
    lines.append('    )')
    lines.append('    (property "Datasheet" ""')
    lines.append('      (at 0 0 0)')
    lines.append('      (effects (font (size 1.27 1.27)) hide)')
    lines.append('    )')
    lines.append('    (symbol "TCAN1042H_Q1_0_1"')
    lines.append('      (rectangle (start -7.62 6.35) (end 7.62 -6.35)')
    lines.append('        (stroke (width 0.254) (type default))')
    lines.append('        (fill (type background)))')
    lines.append('    )')
    lines.append('    (symbol "TCAN1042H_Q1_1_1"')
    lines.append('      (pin input line (at -10.16 5.08 0) (length 2.54) (name "TXD" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))')
    lines.append('      (pin power_in line (at 0 -8.89 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))')
    lines.append('      (pin power_in line (at 0 8.89 270) (length 2.54) (name "VCC" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))')
    lines.append('      (pin output line (at -10.16 2.54 0) (length 2.54) (name "RXD" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))')
    lines.append('      (pin no_connect line (at -10.16 0 0) (length 2.54) (name "NC" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))')
    lines.append('      (pin bidirectional line (at 10.16 2.54 180) (length 2.54) (name "CANL" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))')
    lines.append('      (pin bidirectional line (at 10.16 5.08 180) (length 2.54) (name "CANH" (effects (font (size 1.27 1.27)))) (number "7" (effects (font (size 1.27 1.27)))))')
    lines.append('      (pin input line (at -10.16 -2.54 0) (length 2.54) (name "STB" (effects (font (size 1.27 1.27)))) (number "8" (effects (font (size 1.27 1.27)))))')
    lines.append('    )')
    lines.append('  )')
    lines.append('')
    
    lines.append(')')
    return '\n'.join(lines)


# ============================================================
# Write all files
# ============================================================
outdir = '/home/claude/repo/hardware/kicad'

with open(os.path.join(outdir, 'LoRa_Boat_Controller.kicad_pro'), 'w') as f:
    f.write(gen_project())
print("[OK] LoRa_Boat_Controller.kicad_pro")

with open(os.path.join(outdir, 'LoRa_Boat_Controller.kicad_sch'), 'w') as f:
    f.write(gen_schematic())
print("[OK] LoRa_Boat_Controller.kicad_sch")

with open(os.path.join(outdir, 'LoRa_Boat_Controller.kicad_pcb'), 'w') as f:
    f.write(gen_pcb())
print("[OK] LoRa_Boat_Controller.kicad_pcb")

with open(os.path.join(outdir, 'LoRa_Boat_Controller.kicad_sym'), 'w') as f:
    f.write(gen_symbol_lib())
print("[OK] LoRa_Boat_Controller.kicad_sym")

# Sym-lib-table (project-local symbol library registration)
with open(os.path.join(outdir, 'sym-lib-table'), 'w') as f:
    f.write('(sym_lib_table\n')
    f.write('  (lib (name "LoRa_Boat_Controller")')
    f.write('(type "KiCad")')
    f.write('(uri "${KIPRJMOD}/LoRa_Boat_Controller.kicad_sym")')
    f.write('(options "")(descr "Project-local symbols for LoRa Boat Controller"))\n')
    f.write(')\n')
print("[OK] sym-lib-table")

# Fp-lib-table (project-local footprint library registration)
with open(os.path.join(outdir, 'fp-lib-table'), 'w') as f:
    f.write('(fp_lib_table\n')
    f.write('  (lib (name "LoRa_Boat_Controller")')
    f.write('(type "KiCad")')
    f.write(f'(uri "${{KIPRJMOD}}/LoRa_Boat_Controller.pretty")')
    f.write('(options "")(descr "Project-local footprints for LoRa Boat Controller"))\n')
    f.write(')\n')
print("[OK] fp-lib-table")

print(f"\nGeneration complete!")
PYEOF