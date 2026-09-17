#!/usr/bin/env python3
"""v2_design.py - The V2 design as data: parts, nets, sheet assignment and placement.  gen_v2.py turns this into the
KiCad schematic and board.  Requirement IDs (docs/V2_REQUIREMENTS.md) are noted per block; decision defaults from
docs/V2_REQUIREMENTS.md section 7 are marked [Dn].

Pin references in NETS: 'REF-<pad number>' or 'REF.<pin name>' (resolved against the KiCad symbol; a pin name must be
unique within the symbol).  Coordinates in PLACE are mm on an 80 x 46 mm board whose top-left corner is BOARD_ORIGIN
in KiCad; rotation is KiCad degrees (CCW as seen from the top); side 'F' or 'B'.
"""
BOARD_W, BOARD_H = 80.0, 46.0            # REQ-MECH-01 [D7]: 80 x 46 mm (3.15 x 1.81 in)
BOARD_ORIGIN = (50.0, 50.0)              # KiCad mm of the board's top-left corner
MOUNT_HOLES = [(4.0, 4.0), (76.0, 4.0), (4.0, 42.0), (76.0, 42.0)]   # M3, 72 x 38 mm pattern
PROJ = 'LoRa_Boat_Controller_V2'

V1LIB = 'LoRa_Boat_Controller'           # V1 project libs (reused footprints/symbols)

# ref: (symbol lib, symbol name) ; footprint ; value ; MPN ; manufacturer ; sheet ; description
PARTS = {
    # ---- Power input (REQ-PWR-01/02) [D2: 2S-6S LiPo, ESC fed from the battery directly]
    'J1':  (('Connector_Generic', 'Conn_01x02'), 'Connector_AMASS:AMASS_XT30PW-M_1x02_P2.50mm_Horizontal', 'BATTERY XT30', 'XT30PW-M', 'Amass', 'Power', 'Battery input 7-25 V, board only (<= 3 A)'),
    'F1':  (('Device', 'Fuse'), 'Fuse:Fuse_1812_4532Metric', '3A', '0468003.NR', 'Littelfuse', 'Power', '3 A fast-acting 1812 fuse on the board feed'),
    'Q1':  (('Transistor_FET', 'AO3401A'), 'Package_TO_SOT_SMD:SOT-23', 'AO3401A', 'AO3401A', 'Alpha & Omega', 'Power', 'P-MOSFET reverse-polarity protection (-30 V, 4 A)'),
    'D2':  (('Device', 'D_Zener'), 'Diode_SMD:D_SOD-123', '12V', 'BZT52C12-7-F', 'Diodes Inc', 'Power', 'Gate-source clamp for Q1'),
    'R1':  (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '100k', 'RC0603FR-07100KL', 'Yageo', 'Power', 'Q1 gate pull-down'),
    'D1':  (('Diode', 'SMAJ33A'), 'Diode_SMD:D_SMA', 'SMAJ33A', 'SMAJ33A', 'Littelfuse', 'Power', '33 V unidirectional TVS on VIN_RAW (pin 1 = cathode to VIN_RAW)'),
    'C1':  (('Device', 'C_Polarized'), 'Capacitor_SMD:CP_Elec_6.3x7.7', '47uF 50V', 'EEE-FK1H470P', 'Panasonic', 'Power', 'Bulk input capacitor'),
    'C2':  (('Device', 'C'), 'Capacitor_SMD:C_1210_3225Metric', '10uF 50V', 'GRM32ER71H106KA12L', 'Murata', 'Power', 'Input ceramic'),
    'R33': (('Device', 'R'), 'Resistor_SMD:R_2512_6332Metric', '0.02R 1W', 'CRA2512-FZ-R020ELF', 'Bourns', 'Power', 'Board current shunt (REQ-PWR-06)'),
    'U8':  (('Amplifier_Current', 'INA180A1'), 'Package_TO_SOT_SMD:SOT-23-5', 'INA180A1', 'INA180A1IDBVR', 'Texas Instruments', 'Power', 'Current-sense amplifier, gain 20 (3 A = 1.2 V)'),
    'C37': (('Device', 'C'), 'Capacitor_SMD:C_0603_1608Metric', '100nF', 'KGM15ACG1H104KT', 'Kyocera AVX', 'Power', 'INA180 output filter'),
    'R31': (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '47k', 'RC0603FR-0747KL', 'Yageo', 'Power', 'Battery divider top (26 V -> 3.3 V)'),
    'R32': (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '6.8k', 'RC0603FR-076K8L', 'Yageo', 'Power', 'Battery divider bottom'),
    'C36': (('Device', 'C'), 'Capacitor_SMD:C_0603_1608Metric', '100nF', 'KGM15ACG1H104KT', 'Kyocera AVX', 'Power', 'Battery ADC filter'),
    # ---- 3.3 V buck: the proven V1 R1240N circuit, catch diode and inductor kept, all returns to GND (F-PWR-02/06)
    'U2':  ((V1LIB, 'R1240N001x'), f'{V1LIB}:SOT-23-6W_PE-SOT23-6W-0512_NMD', 'R1240N001B-TR-FE', 'R1240N001B-TR-FE', 'Nisshinbo', 'Power', '1.25 MHz async buck, 1.2 A'),
    'R2':  (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '5.1k', 'RC0603FR-075K1L', 'Yageo', 'Power', 'CE pull-up to VIN_BUCK'),
    'R3':  (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '51R', 'RC0603FR-0751RL', 'Yageo', 'Power', 'Bootstrap series R (per DS)'),
    'C3':  (('Device', 'C'), 'Capacitor_SMD:C_0603_1608Metric', '100nF 50V', 'CL10B104KB8NNNC', 'Samsung', 'Power', 'Bootstrap capacitor'),
    'L1':  (('Device', 'L'), 'Inductor_SMD:L_Bourns_SRN6045TA', '4.7uH 3A', 'SRN6045TA-4R7M', 'Bourns', 'Power', 'Replaces the EOL SLF7045 (F-BOM-01)'),
    'D3':  ((V1LIB, 'CMS06_Schottky'), f'{V1LIB}:M-FLAT_TOS-L', 'CMS06', 'CMS06(TE12L,Q,M)', 'Toshiba', 'Power', 'Catch diode 30 V 2 A'),
    'R4':  (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '15k', 'RC0603FR-0715KL', 'Yageo', 'Power', 'FB top: Vout = 0.8 * (1 + 15/4.7) = 3.35 V'),
    'R5':  (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '4.7k', 'RC0603FR-074K7L', 'Yageo', 'Power', 'FB bottom'),
    'C4':  (('Device', 'C'), 'Capacitor_SMD:C_0603_1608Metric', '470pF', '06035A471JAT2A', 'Kyocera AVX', 'Power', 'Feed-forward (CSPD)'),
    'C5':  (('Device', 'C'), 'Capacitor_SMD:C_1206_3216Metric', '10uF 25V', 'GRM31CR71E106KA12L', 'Murata', 'Power', '3.3 V output'),
    'C6':  (('Device', 'C'), 'Capacitor_SMD:C_1206_3216Metric', '10uF 25V', 'GRM31CR71E106KA12L', 'Murata', 'Power', '3.3 V output'),
    # ---- 5 V actuator buck (populate option) + BEC OR-ing (REQ-PWR-03/04) [D3]
    'U3':  (('Regulator_Switching', 'TPS54202DDC'), 'Package_TO_SOT_SMD:TSOT-23-6', 'TPS54202', 'TPS54202DDCR', 'Texas Instruments', 'Power', '5 V / 2 A buck for the servo rail (populate option)'),
    'R6':  (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '100k', 'RC0603FR-07100KL', 'Yageo', 'Power', 'EN pull-up'),
    'C7':  (('Device', 'C'), 'Capacitor_SMD:C_0603_1608Metric', '100nF', 'KGM15ACG1H104KT', 'Kyocera AVX', 'Power', 'BOOT capacitor'),
    'L2':  (('Device', 'L'), 'Inductor_SMD:L_Bourns_SRN6045TA', '4.7uH 3A', 'SRN6045TA-4R7M', 'Bourns', 'Power', '5 V buck inductor'),
    'R8':  (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '100k', 'RC0603FR-07100KL', 'Yageo', 'Power', 'FB top (Vout = 0.596 * (1 + 100/13.3) = 5.08 V)'),
    'R9':  (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '13.3k', 'RC0603FR-0713K3L', 'Yageo', 'Power', 'FB bottom'),
    'C8':  (('Device', 'C'), 'Capacitor_SMD:C_1210_3225Metric', '22uF 16V', 'GRM32ER61C226KE20L', 'Murata', 'Power', '5 V output'),
    'C9':  (('Device', 'C'), 'Capacitor_SMD:C_1210_3225Metric', '22uF 16V', 'GRM32ER61C226KE20L', 'Murata', 'Power', '5 V output'),
    'C10': (('Device', 'C'), 'Capacitor_SMD:C_1210_3225Metric', '10uF 50V', 'GRM32ER71H106KA12L', 'Murata', 'Power', '5 V buck input'),
    'D4':  (('Device', 'D_Schottky'), 'Diode_SMD:D_SMA', 'SS34', 'SS34', 'Vishay', 'Power', 'OR-ing: on-board 5 V -> VSERVO'),
    'D9':  (('Device', 'D_Schottky'), 'Diode_SMD:D_SMA', 'SS34', 'SS34', 'Vishay', 'Power', 'OR-ing: ESC BEC -> VSERVO'),
    'C11': (('Device', 'C_Polarized'), 'Capacitor_SMD:CP_Elec_6.3x7.7', '100uF 10V', 'EEE-FK1A101P', 'Panasonic', 'Power', 'VSERVO bulk'),
    'C12': (('Device', 'C'), 'Capacitor_SMD:C_0805_2012Metric', '10uF 16V', 'GRM21BR61C106KE15L', 'Murata', 'Power', 'VSERVO ceramic'),
    # ---- MCU (REQ-MCU-01..05, REQ-DBG-02)
    'U1':  (('MCU_ST_STM32F4', 'STM32F446RETx'), 'Package_QFP:LQFP-64_10x10mm_P0.5mm', 'STM32F446RET6', 'STM32F446RET6', 'STMicroelectronics', 'MCU', 'Cortex-M4 180 MHz'),
    'C15': (('Device', 'C'), 'Capacitor_SMD:C_0603_1608Metric', '100nF', 'KGM15ACG1H104KT', 'Kyocera AVX', 'MCU', 'VDD pin 19'),
    'C16': (('Device', 'C'), 'Capacitor_SMD:C_0603_1608Metric', '100nF', 'KGM15ACG1H104KT', 'Kyocera AVX', 'MCU', 'VDD pin 32'),
    'C17': (('Device', 'C'), 'Capacitor_SMD:C_0603_1608Metric', '100nF', 'KGM15ACG1H104KT', 'Kyocera AVX', 'MCU', 'VDD pin 48'),
    'C18': (('Device', 'C'), 'Capacitor_SMD:C_0603_1608Metric', '100nF', 'KGM15ACG1H104KT', 'Kyocera AVX', 'MCU', 'VDD pin 64'),
    'C19': (('Device', 'C'), 'Capacitor_SMD:C_0805_2012Metric', '10uF 10V', 'GRM21BR61A106KE19L', 'Murata', 'MCU', 'VDD bulk'),
    'C20': (('Device', 'C'), 'Capacitor_SMD:C_0603_1608Metric', '4.7uF 10V', 'CL10A475KP8NNNC', 'Samsung', 'MCU', 'VCAP_1 to VSS (REQ-MCU-01, fixes F-MCU-01)'),
    'FB1': (('Device', 'FerriteBead'), 'Inductor_SMD:L_0603_1608Metric', '600R', 'BLM18AG601SN1D', 'Murata', 'MCU', 'VDDA filter'),
    'C21': (('Device', 'C'), 'Capacitor_SMD:C_0603_1608Metric', '1uF', 'CL10A105KB8NNNC', 'Samsung', 'MCU', 'VDDA'),
    'C22': (('Device', 'C'), 'Capacitor_SMD:C_0603_1608Metric', '100nF', 'KGM15ACG1H104KT', 'Kyocera AVX', 'MCU', 'VDDA'),
    'C23': (('Device', 'C'), 'Capacitor_SMD:C_0603_1608Metric', '100nF', 'KGM15ACG1H104KT', 'Kyocera AVX', 'MCU', 'VBAT (tied to VDD, REQ-MCU-02)'),
    'C24': (('Device', 'C'), 'Capacitor_SMD:C_0603_1608Metric', '100nF', 'KGM15ACG1H104KT', 'Kyocera AVX', 'MCU', 'NRST (REQ-MCU-05)'),
    'R16': (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '10k', 'RC0603FR-0710KL', 'Yageo', 'MCU', 'BOOT0 pull-down (REQ-MCU-02)'),
    'SW1': (('Switch', 'SW_Push'), 'Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2', 'RESET', 'KMR221GLFS', 'C&K', 'MCU', 'Reset button'),
    'Y1':  (('Device', 'Crystal_GND24'), 'Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm', '8MHz', 'ABM8-8.000MHZ-10-1-U-T', 'Abracon', 'MCU', 'HSE, CL 10 pF (REQ-MCU-03)'),
    'C25': (('Device', 'C'), 'Capacitor_SMD:C_0603_1608Metric', '15pF C0G', '06035A150JAT2A', 'Kyocera AVX', 'MCU', 'HSE load'),
    'C26': (('Device', 'C'), 'Capacitor_SMD:C_0603_1608Metric', '15pF C0G', '06035A150JAT2A', 'Kyocera AVX', 'MCU', 'HSE load'),
    'Y2':  (('Device', 'Crystal'), 'Crystal:Crystal_SMD_3215-2Pin_3.2x1.5mm', '32.768kHz', 'ABS07-32.768KHZ-7-T', 'Abracon', 'MCU', 'LSE, CL 7 pF (REQ-MCU-04, populate option)'),
    'C27': (('Device', 'C'), 'Capacitor_SMD:C_0603_1608Metric', '10pF C0G', '06035A100JAT2A', 'Kyocera AVX', 'MCU', 'LSE load'),
    'C28': (('Device', 'C'), 'Capacitor_SMD:C_0603_1608Metric', '10pF C0G', '06035A100JAT2A', 'Kyocera AVX', 'MCU', 'LSE load'),
    'D5':  (('Device', 'LED'), 'LED_SMD:LED_0603_1608Metric', 'PWR green', 'LTST-C193KGKT-5A', 'Lite-On', 'MCU', 'Power LED (REQ-PWR-08)'),
    'D6':  (('Device', 'LED'), 'LED_SMD:LED_0603_1608Metric', 'LINK blue', 'LTST-C193TBKT-5A', 'Lite-On', 'MCU', 'Link LED'),
    'D7':  (('Device', 'LED'), 'LED_SMD:LED_0603_1608Metric', 'FIX yellow', 'LTST-C193KSKT-5A', 'Lite-On', 'MCU', 'GNSS fix LED'),
    'D8':  (('Device', 'LED'), 'LED_SMD:LED_0603_1608Metric', 'FAULT red', 'LTST-C193KRKT-5A', 'Lite-On', 'MCU', 'Fault / failsafe LED'),
    'R29': (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '1k', 'RC0603FR-071KL', 'Yageo', 'MCU', 'LED'),
    'R30': (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '1k', 'RC0603FR-071KL', 'Yageo', 'MCU', 'LED'),
    'R34': (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '1k', 'RC0603FR-071KL', 'Yageo', 'MCU', 'LED'),
    'R35': (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '1k', 'RC0603FR-071KL', 'Yageo', 'MCU', 'LED'),
    # ---- Radio (REQ-RF-01/04/05/07) [D1: RYLR998_M4 on the 5-pin pinout]
    'J4':  (('Connector_Generic', 'Conn_01x05'), f'{V1LIB}:CONN5_1LFBN-RC_SUL', 'LoRa RYLR998', 'PPTC051LFBN-RC', 'Sullins', 'Radio', '1x5 socket: VDD, NRST, RXD, TXD, GND (RYLR998 pinout)'),
    'FB2': (('Device', 'FerriteBead'), 'Inductor_SMD:L_0402_1005Metric', '600R', 'BLM15AG601SN1D', 'Murata', 'Radio', 'LoRa supply pi filter'),
    'FB3': (('Device', 'FerriteBead'), 'Inductor_SMD:L_0402_1005Metric', '600R', 'BLM15AG601SN1D', 'Murata', 'Radio', 'LoRa supply pi filter'),
    'C29': (('Device', 'C'), 'Capacitor_SMD:C_0805_2012Metric', '10uF 10V', 'GRM21BR61A106KE19L', 'Murata', 'Radio', 'Filter mid node to GND (fixes F-PWR-06)'),
    'C30': (('Device', 'C'), 'Capacitor_SMD:C_0805_2012Metric', '10uF 10V', 'GRM21BR61A106KE19L', 'Murata', 'Radio', 'LORA_VCC'),
    'C31': (('Device', 'C'), 'Capacitor_SMD:C_0603_1608Metric', '100nF', 'KGM15ACG1H104KT', 'Kyocera AVX', 'Radio', 'LORA_VCC'),
    'C32': (('Device', 'C'), 'Capacitor_SMD:C_0402_1005Metric', '47pF', 'GJM1555C1H470JB01D', 'Murata', 'Radio', 'LORA_VCC (RYLR998 reference design)'),
    'R17': (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '100R', 'RC0603FR-07100RL', 'Yageo', 'Radio', 'UART4_TX series'),
    'R18': (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '100R', 'RC0603FR-07100RL', 'Yageo', 'Radio', 'UART4_RX series'),
    'R19': (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '100R', 'RC0603FR-07100RL', 'Yageo', 'Radio', 'LoRa NRST series'),
    # ---- Navigation (REQ-NAV-01/02/05) [D5: ICM-20948]
    'J5':  (('Connector_Generic', 'Conn_01x06'), 'Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical', 'GNSS', 'PPTC061LFBN-RC', 'Sullins', 'Navigation', '1x6: VCC, GND, TX, RX, PPS, VBCKP'),
    'R20': (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '100R', 'RC0603FR-07100RL', 'Yageo', 'Navigation', 'USART3_TX series'),
    'R21': (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '100R', 'RC0603FR-07100RL', 'Yageo', 'Navigation', 'USART3_RX series'),
    'R22': (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '100R', 'RC0603FR-07100RL', 'Yageo', 'Navigation', 'PPS series'),
    'U6':  (('Sensor_Motion', 'ICM-20948'), f'{PROJ}:QFN-24_3x3mm_P0.4mm_NoEP', 'ICM-20948', 'ICM-20948', 'TDK InvenSense', 'Navigation', '9-axis IMU, I2C'),
    'C33': (('Device', 'C'), 'Capacitor_SMD:C_0603_1608Metric', '100nF', 'KGM15ACG1H104KT', 'Kyocera AVX', 'Navigation', 'REGOUT'),
    'C34': (('Device', 'C'), 'Capacitor_SMD:C_0603_1608Metric', '100nF', 'KGM15ACG1H104KT', 'Kyocera AVX', 'Navigation', 'VDD/VDDIO'),
    'C35': (('Device', 'C'), 'Capacitor_SMD:C_0805_2012Metric', '10uF 10V', 'GRM21BR61A106KE19L', 'Murata', 'Navigation', 'VDD bulk'),
    'R23': (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '2.2k', 'RC0603FR-072K2L', 'Yageo', 'Navigation', 'I2C SCL pull-up'),
    'R24': (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '2.2k', 'RC0603FR-072K2L', 'Yageo', 'Navigation', 'I2C SDA pull-up'),
    # ---- Actuators (REQ-CTL-03/05, REQ-PWR-03)
    'J2':  (('Connector_Generic', 'Conn_01x03'), 'Connector_JST:JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical', 'ESC', 'B3B-XH-A(LF)(SN)', 'JST', 'Actuators', '1: signal 5 V, 2: BEC in, 3: GND'),
    'J3':  (('Connector_Generic', 'Conn_01x03'), 'Connector_JST:JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical', 'SERVO', 'B3B-XH-A(LF)(SN)', 'JST', 'Actuators', '1: signal 5 V, 2: VSERVO out, 3: GND'),
    'U4':  (('74xGxx', '74AHCT1G125'), 'Package_TO_SOT_SMD:SOT-23-5', '74AHCT1G125', 'SN74AHCT1G125DBVR', 'Texas Instruments', 'Actuators', 'ESC PWM 3.3 -> 5 V buffer'),
    'U5':  (('74xGxx', '74AHCT1G125'), 'Package_TO_SOT_SMD:SOT-23-5', '74AHCT1G125', 'SN74AHCT1G125DBVR', 'Texas Instruments', 'Actuators', 'Servo PWM 3.3 -> 5 V buffer'),
    'C13': (('Device', 'C'), 'Capacitor_SMD:C_0603_1608Metric', '100nF', 'KGM15ACG1H104KT', 'Kyocera AVX', 'Actuators', 'U4 decoupling'),
    'C14': (('Device', 'C'), 'Capacitor_SMD:C_0603_1608Metric', '100nF', 'KGM15ACG1H104KT', 'Kyocera AVX', 'Actuators', 'U5 decoupling'),
    'R10': (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '100R', 'RC0603FR-07100RL', 'Yageo', 'Actuators', 'ESC signal series'),
    'R11': (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '10k', 'RC0603FR-0710KL', 'Yageo', 'Actuators', 'ESC signal pull-down (no pulse when unpowered)'),
    'R12': (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '100R', 'RC0603FR-07100RL', 'Yageo', 'Actuators', 'Servo signal series'),
    'R13': (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '10k', 'RC0603FR-0710KL', 'Yageo', 'Actuators', 'Servo signal pull-down'),
    'R14': (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '100k', 'RC0603FR-07100KL', 'Yageo', 'Actuators', 'U4 input pull-down (MCU unpowered -> output low)'),
    'R15': (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '100k', 'RC0603FR-07100KL', 'Yageo', 'Actuators', 'U5 input pull-down'),
    'D10': (('Device', 'D_TVS'), 'Diode_SMD:D_SOD-323', 'PESD5V0S1BA', 'PESD5V0S1BA,115', 'Nexperia', 'Actuators', 'ESC signal ESD'),
    'D11': (('Device', 'D_TVS'), 'Diode_SMD:D_SOD-323', 'PESD5V0S1BA', 'PESD5V0S1BA,115', 'Nexperia', 'Actuators', 'Servo signal ESD'),
    # ---- Debug (REQ-DBG-01/03) [D8: USB-C CDC]
    'J6':  (('Connector', 'USB_C_Receptacle_USB2.0_16P'), 'Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal', 'USB-C', 'USB4105-GF-A', 'GCT', 'Debug', 'USB 2.0 device console'),
    'U7':  (('Power_Protection', 'USBLC6-2SC6'), 'Package_TO_SOT_SMD:SOT-23-6', 'USBLC6-2SC6', 'USBLC6-2SC6', 'STMicroelectronics', 'Debug', 'USB ESD'),
    'R25': (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '5.1k', 'RC0603FR-075K1L', 'Yageo', 'Debug', 'CC1 pull-down (UFP)'),
    'R26': (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '5.1k', 'RC0603FR-075K1L', 'Yageo', 'Debug', 'CC2 pull-down (UFP)'),
    'R27': (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '47k', 'RC0603FR-0747KL', 'Yageo', 'Debug', 'VBUS sense top'),
    'R28': (('Device', 'R'), 'Resistor_SMD:R_0603_1608Metric', '22k', 'RC0603FR-0722KL', 'Yageo', 'Debug', 'VBUS sense bottom (5 V -> 1.6 V on PA9)'),
    'J7':  (('Connector_Generic', 'Conn_02x05_Odd_Even'), 'Connector_PinHeader_1.27mm:PinHeader_2x05_P1.27mm_Vertical_SMD', 'SWD', 'FTSH-105-01-L-DV-K', 'Samtec', 'Debug', 'ARM 10-pin Cortex debug'),
    # ---- Test points and mechanical (REQ-DBG-03, REQ-MECH-01)
    'TP1': (('Connector', 'TestPoint'), 'TestPoint:TestPoint_Pad_D1.5mm', 'ESC_PWM', '', '', 'Actuators', 'MCU-side ESC PWM'),
    'TP2': (('Connector', 'TestPoint'), 'TestPoint:TestPoint_Pad_D1.5mm', 'SERVO_PWM', '', '', 'Actuators', 'MCU-side servo PWM'),
    'TP3': (('Connector', 'TestPoint'), 'TestPoint:TestPoint_Pad_D1.5mm', '+3V3', '', '', 'Power', ''),
    'TP4': (('Connector', 'TestPoint'), 'TestPoint:TestPoint_Pad_D1.5mm', 'VSERVO', '', '', 'Power', ''),
    'TP5': (('Connector', 'TestPoint'), 'TestPoint:TestPoint_Pad_D1.5mm', 'VIN_RAW', '', '', 'Power', ''),
    'TP6': (('Connector', 'TestPoint'), 'TestPoint:TestPoint_Pad_D1.5mm', 'GND', '', '', 'Power', ''),
    'TP7': (('Connector', 'TestPoint'), 'TestPoint:TestPoint_Pad_D1.5mm', 'PPS', '', '', 'Navigation', ''),
    'H1':  (('Mechanical', 'MountingHole'), 'MountingHole:MountingHole_3.2mm_M3', 'M3', '', '', 'Power', 'Mounting hole'),
    'H2':  (('Mechanical', 'MountingHole'), 'MountingHole:MountingHole_3.2mm_M3', 'M3', '', '', 'Power', 'Mounting hole'),
    'H3':  (('Mechanical', 'MountingHole'), 'MountingHole:MountingHole_3.2mm_M3', 'M3', '', '', 'Power', 'Mounting hole'),
    'H4':  (('Mechanical', 'MountingHole'), 'MountingHole:MountingHole_3.2mm_M3', 'M3', '', '', 'Power', 'Mounting hole'),
}

# STM32F446RET6 LQFP-64 pin numbers used below (DS10693 Table 10)
U1 = {'VBAT': 1, 'PC13': 2, 'PC14': 3, 'PC15': 4, 'PH0': 5, 'PH1': 6, 'NRST': 7, 'PC0': 8, 'PC1': 9, 'PC2': 10, 'PC3': 11, 'VSSA': 12, 'VDDA': 13,
      'PA0': 14, 'PA1': 15, 'PA2': 16, 'PA3': 17, 'VSS1': 18, 'VDD1': 19, 'PA4': 20, 'PB0': 26, 'VCAP': 30, 'VSS2': 31, 'VDD2': 32, 'PC6': 37,
      'PA8': 41, 'PA9': 42, 'PA11': 44, 'PA12': 45, 'PA13': 46, 'VSS3': 47, 'VDD3': 48, 'PA14': 49, 'PC10': 51, 'PC11': 52, 'PB3': 55,
      'PB5': 57, 'PB6': 58, 'PB7': 59, 'BOOT0': 60, 'VSS4': 63, 'VDD4': 64}
def u1(name): return f'U1-{U1[name]}'

NETS = {
    'GND': ['J1-2', 'R1-2', 'D1-2', 'C1-2', 'C2-2', 'U8-2', 'C37-2', 'R32-2', 'C36-2', 'U2-5', 'D3-1', 'R5-2', 'C5-2', 'C6-2',
            'U3-1', 'R9-2', 'C8-2', 'C9-2', 'C10-2', 'C11-2', 'C12-2',
            u1('VSSA'), u1('VSS1'), u1('VSS2'), u1('VSS3'), u1('VSS4'), 'C15-2', 'C16-2', 'C17-2', 'C18-2', 'C19-2', 'C20-2', 'C21-2', 'C22-2', 'C23-2',
            'C24-2', 'SW1-2', 'R16-2', 'Y1-2', 'Y1-4', 'C25-2', 'C26-2', 'C27-2', 'C28-2', 'D5-1', 'D6-1', 'D7-1', 'D8-1',
            'J4-5', 'C29-2', 'C30-2', 'C31-2', 'C32-2', 'J5-2', 'U6-18', 'U6-20', 'U6.FSYNC', 'U6.SDO/AD0', 'C33-2', 'C34-2', 'C35-2',
            'J2-3', 'J3-3', 'U4-3', 'U5-3', 'U4-1', 'U5-1', 'C13-2', 'C14-2', 'R11-2', 'R13-2', 'R14-2', 'R15-2', 'D10-2', 'D11-2',
            'J6-A1', 'J6-A12', 'J6-B1', 'J6-B12', 'J6-S1', 'U7-2', 'R25-2', 'R26-2', 'R28-2', 'J7-3', 'J7-5', 'J7-9', 'TP6-1'],
    '+3V3': ['L1-2', 'R4-1', 'C4-2', 'C5-1', 'C6-1', 'U8-5', u1('VDD1'), u1('VDD2'), u1('VDD3'), u1('VDD4'), u1('VBAT'), 'C15-1', 'C16-1', 'C17-1', 'C18-1', 'C19-1', 'C23-1', 'FB1-1',
             'R29-1', 'FB2-1', 'J5-1', 'J5-6', 'U6-8', 'U6-13', 'U6.~{CS}', 'C34-1', 'C35-1', 'R23-1', 'R24-1', 'J7-1', 'TP3-1'],
    'VBAT_IN': ['J1-1', 'F1-1'],
    'VBAT_FUSED': ['F1-2', 'Q1-3'],
    'PGATE': ['Q1-1', 'R1-1', 'D2-2'],
    'VIN_RAW': ['Q1-2', 'D2-1', 'D1-1', 'C1-1', 'C2-1', 'R33-1', 'U8-3', 'R31-1', 'TP5-1'],
    'VIN_BUCK': ['R33-2', 'U8-4', 'U2-2', 'R2-1', 'U3-3', 'R6-1', 'C10-1'],
    'ISENSE': ['U8-1', 'C37-1', u1('PA4')],
    'VBAT_SENSE': ['R31-2', 'R32-1', 'C36-1', u1('PA2')],
    'EN_3V3': ['U2-1', 'R2-2'],
    'SW_3V3': ['U2-3', 'L1-1', 'D3-2', 'C3-1'],
    'BST_3V3': ['U2-4', 'R3-2'],
    'BST_RC': ['R3-1', 'C3-2'],
    'FB_3V3': ['U2-6', 'R4-2', 'R5-1', 'C4-1'],   # C4 feed-forward sits across R4 (VFB to +3V3), as V1's C14
    'EN_5V': ['U3-5', 'R6-2'],
    'SW_5V': ['U3-2', 'L2-1', 'C7-1'],
    'BOOT_5V': ['U3-6', 'C7-2'],
    '+5V_BUCK': ['L2-2', 'R8-1', 'C8-1', 'C9-1', 'D4-2'],
    'FB_5V': ['U3-4', 'R8-2', 'R9-1'],
    'BEC_IN': ['J2-2', 'D9-2'],
    'VSERVO': ['D4-1', 'D9-1', 'C11-1', 'C12-1', 'J3-2', 'U4-5', 'U5-5', 'C13-1', 'C14-1', 'TP4-1'],
    'VDDA': ['FB1-2', 'C21-1', 'C22-1', u1('VDDA')],
    'VCAP1': [u1('VCAP'), 'C20-1'],
    'NRST': [u1('NRST'), 'C24-1', 'SW1-1', 'J7-10'],
    'BOOT0': [u1('BOOT0'), 'R16-1'],
    'HSE_IN': [u1('PH0'), 'Y1-1', 'C25-1'],
    'HSE_OUT': [u1('PH1'), 'Y1-3', 'C26-1'],
    'LSE_IN': [u1('PC14'), 'Y2-1', 'C27-1'],
    'LSE_OUT': [u1('PC15'), 'Y2-2', 'C28-1'],
    'LED_PWR': ['R29-2', 'D5-2'],
    'LED_LINK': [u1('PC1'), 'R30-1'], 'LED_LINK_A': ['R30-2', 'D6-2'],
    'LED_FIX': [u1('PC2'), 'R34-1'], 'LED_FIX_A': ['R34-2', 'D7-2'],
    'LED_FAULT': [u1('PC3'), 'R35-1'], 'LED_FAULT_A': ['R35-2', 'D8-2'],
    'LORA_FILT': ['FB2-2', 'FB3-1', 'C29-1'],
    'LORA_VCC': ['FB3-2', 'C30-1', 'C31-1', 'C32-1', 'J4-1'],
    'LORA_TX_PA0': [u1('PA0'), 'R17-1'], 'LORA_RXD': ['R17-2', 'J4-3'],
    'LORA_RX_PA1': [u1('PA1'), 'R18-1'], 'LORA_TXD': ['R18-2', 'J4-4'],
    'LORA_NRST_PA3': [u1('PA3'), 'R19-1'], 'LORA_NRST': ['R19-2', 'J4-2'],
    'GNSS_TX_PC10': [u1('PC10'), 'R20-1'], 'GNSS_RXD': ['R20-2', 'J5-4'],
    'GNSS_RX_PC11': [u1('PC11'), 'R21-1'], 'GNSS_TXD': ['R21-2', 'J5-3'],
    'PPS_PB0': [u1('PB0'), 'R22-1', 'TP7-1'], 'GNSS_PPS': ['R22-2', 'J5-5'],
    'I2C1_SCL': [u1('PB6'), 'R23-2', 'U6.SCL/SCLK'],
    'I2C1_SDA': [u1('PB7'), 'R24-2', 'U6.SDA/SDI'],
    'IMU_INT': [u1('PB5'), 'U6.INT1'],
    'IMU_REGOUT': ['U6.REGOUT', 'C33-1'],
    'PWM_ESC_PC6': [u1('PC6'), 'U4-2', 'R14-1', 'TP1-1'],
    'ESC_SIG_5V': ['U4-4', 'R10-1'], 'ESC_SIG': ['R10-2', 'R11-1', 'D10-1', 'J2-1'],
    'PWM_SERVO_PA8': [u1('PA8'), 'U5-2', 'R15-1', 'TP2-1'],
    'SERVO_SIG_5V': ['U5-4', 'R12-1'], 'SERVO_SIG': ['R12-2', 'R13-1', 'D11-1', 'J3-1'],
    'VBUS': ['J6-A4', 'J6-A9', 'J6-B4', 'J6-B9', 'U7-5', 'R27-1'],
    'VBUS_SENSE': ['R27-2', 'R28-1', u1('PA9')],
    'USB_CC1': ['J6-A5', 'R25-1'], 'USB_CC2': ['J6-B5', 'R26-1'],
    'USB_DP_CONN': ['J6-A6', 'J6-B6', 'U7-1'], 'USB_DM_CONN': ['J6-A7', 'J6-B7', 'U7-3'],
    'USB_DP': ['U7-6', u1('PA12')], 'USB_DM': ['U7-4', u1('PA11')],
    'SWDIO': [u1('PA13'), 'J7-2'], 'SWCLK': [u1('PA14'), 'J7-4'], 'SWO': [u1('PB3'), 'J7-6'],
}
POWER_NETS = {'GND': ('power', 'GND', 'down'), '+3V3': ('power', '+3V3', 'up'), 'VIN_RAW': ('LoRa_Boat_Controller', 'VIN_RAW', 'up'),
              'VSERVO': (PROJ, 'VSERVO', 'up'), 'VBUS': ('power', 'VBUS', 'up')}
# pins deliberately unconnected (no-connect flags): everything else on a symbol that is not in NETS is an error
NC_PINS = {'J6-A8', 'J6-B8', 'U6-1', 'U6-2', 'U6-3', 'U6-4', 'U6-5', 'U6-6', 'U6-14', 'U6-15', 'U6-16', 'U6-17', 'U6-19', 'U6.AUX_DA', 'U6.AUX_CL',
           'J7-7', 'J7-8'}
# every STM32 pin not listed above is NC (37 in V1; fewer here)

SHEETS = [  # name, file, paper, description
    ('Power', 'Power.kicad_sch', 'A3', 'REQ-PWR-01..08: XT30 input, fuse, reverse P-FET, TVS, current shunt, 3.3 V buck (V1 circuit corrected), 5 V servo buck + BEC OR-ing, battery ADC divider'),
    ('MCU', 'MCU.kicad_sch', 'A3', 'REQ-MCU-01..05, REQ-DBG-02: STM32F446RET6, VCAP to VSS, VDDA filter, HSE 8 MHz + LSE, NRST/BOOT0, LEDs'),
    ('Radio', 'Radio.kicad_sch', 'A4', 'REQ-RF-01/04/05: RYLR998(_M4) socket, pi filter to GND, series resistors, NRST from MCU; antenna via SMA bulkhead pigtail'),
    ('Navigation', 'Navigation.kicad_sch', 'A4', 'REQ-NAV-01/02/05: GNSS 1x6 with PPS -> PB0 (TIM3_CH3), ICM-20948 on I2C1'),
    ('Actuators', 'Actuators.kicad_sch', 'A4', 'REQ-CTL-03/05, REQ-PWR-03: 74AHCT1G125 5 V buffers with input pull-downs, series R + TVS, ESC/SERVO JST XH; VSERVO never +3V3'),
    ('Debug', 'Debug.kicad_sch', 'A4', 'REQ-DBG-01: USB-C console with USBLC6 ESD and CC pull-downs; ARM 10-pin SWD'),
]

# Placement (board mm, from the top-left corner; y down), rotation, side.  Connectors on the left/top/right/bottom edges.
PLACE = {
    # mounting holes (72 x 38 mm pattern)
    'H1': (4, 4, 0), 'H2': (76, 4, 0), 'H3': (4, 42, 0), 'H4': (76, 42, 0),
    # edge connectors: battery left, ESC top-left, servo bottom-left, USB-C top-right, SWD right, LoRa right edge, GNSS bottom-right
    'J1': (9.7, 23.0, 0), 'J2': (13.0, 5.0, 0), 'J3': (13.0, 42.0, 0), 'J6': (56.0, 2.5, 180), 'J7': (73.0, 13.0, 0), 'J4': (78.0, 28.0, 90), 'J5': (56.0, 43.5, 90),
    'SW1': (72.0, 21.0, 0),
    # ESC buffer chain right of J2 (top edge), BEC OR-ing diode under it
    'U4': (26.0, 3.5, 0), 'C13': (29.5, 4.0, 90), 'R14': (32.5, 4.0, 0), 'D9': (28.0, 7.3, 0), 'R10': (34.0, 7.0, 0), 'R11': (34.0, 9.5, 0), 'D10': (37.0, 9.5, 90),
    # input protection (row y=12), filtering (y=17), bulk + sense
    'F1': (17.5, 20.5, 0), 'Q1': (20.7, 12.0, 0), 'D2': (25.2, 12.0, 0), 'R1': (22.8, 9.3, 0),
    'D1': (18.2, 16.5, 0), 'C2': (24.5, 16.5, 0), 'R33': (26.0, 20.5, 0),
    'C1': (7.0, 30.0, 0), 'U8': (24.0, 25.5, 0), 'C37': (27.0, 25.5, 90), 'R31': (31.5, 21.0, 90), 'R32': (31.5, 24.5, 90), 'C36': (34.3, 23.5, 90),
    # 3.3 V buck
    'U2': (15.0, 30.5, 0), 'R2': (19.0, 30.5, 90), 'R3': (22.0, 29.0, 0), 'C3': (22.0, 31.5, 0), 'L1': (28.0, 31.0, 0), 'C5': (33.0, 28.5, 90), 'C6': (33.0, 33.5, 90),
    'D3': (15.5, 34.5, 0), 'R4': (20.0, 34.5, 90), 'R5': (22.5, 34.5, 90), 'C4': (20.0, 37.5, 0),
    # 5 V servo buck + OR-ing
    'U3': (40.0, 29.0, 0), 'R6': (36.5, 29.0, 90), 'C7': (40.0, 32.0, 0), 'L2': (47.0, 30.5, 0), 'R8': (40.0, 34.5, 0), 'R9': (40.0, 36.5, 0), 'C10': (36.3, 34.0, 90),
    'C8': (53.0, 28.5, 90), 'C9': (53.0, 34.0, 90), 'D4': (47.0, 37.0, 0), 'C11': (59.5, 30.0, 0), 'C12': (59.5, 36.0, 0),
    # servo buffer near J3
    'U5': (25.0, 41.5, 0), 'C14': (28.5, 41.5, 90), 'R15': (31.5, 41.5, 0), 'R12': (25.5, 38.0, 0), 'R13': (29.0, 38.0, 0), 'D11': (32.0, 38.0, 90),
    # MCU with decoupling around it, crystals at the PH0/PH1 (left) side
    'U1': (46.0, 17.0, 0), 'C15': (38.0, 13.0, 90), 'FB1': (38.0, 17.0, 90), 'C20': (38.0, 21.5, 90), 'C21': (36.2, 15.0, 90), 'C22': (36.0, 20.5, 90),
    'C19': (40.0, 8.5, 0), 'C16': (44.0, 8.5, 0), 'C18': (48.0, 8.5, 0), 'C17': (55.5, 16.0, 90), 'C23': (55.5, 20.0, 90), 'C24': (42.0, 26.0, 0), 'R16': (46.0, 26.0, 0),
    'Y1': (31.5, 12.5, 0), 'C25': (28.5, 13.3, 90), 'C26': (34.5, 13.3, 90),
    'Y2': (31.5, 17.0, 0), 'C27': (28.5, 16.7, 90), 'C28': (34.5, 16.7, 90),
    'D5': (38.0, 3.0, 0), 'R29': (38.0, 5.5, 90), 'D6': (41.2, 3.0, 0), 'R30': (41.2, 5.5, 90), 'D7': (44.4, 3.0, 0), 'R34': (44.4, 5.5, 90), 'D8': (47.6, 3.0, 0), 'R35': (47.6, 5.5, 90),
    # USB
    'U7': (58.0, 9.5, 0), 'R25': (55.0, 12.0, 0), 'R26': (59.0, 12.5, 0), 'R27': (63.0, 12.5, 0), 'R28': (63.0, 14.5, 0),
    # radio filter next to the LoRa socket
    'FB2': (69.0, 25.0, 0), 'FB3': (72.0, 25.0, 0), 'C29': (70.0, 27.5, 0), 'C30': (73.5, 27.5, 0), 'C31': (75.5, 30.3, 90), 'C32': (74.5, 34.0, 90),
    'R17': (71.5, 30.5, 0), 'R18': (71.5, 32.5, 0), 'R19': (71.5, 34.5, 0),
    # navigation: IMU bottom-right away from the inductors (25 mm), GNSS series resistors near J5
    'U6': (66.0, 36.0, 0), 'C33': (63.0, 37.5, 90), 'C34': (71.5, 37.0, 90), 'C35': (67.0, 31.5, 0), 'R23': (66.5, 27.0, 0), 'R24': (66.5, 29.0, 0),
    'R20': (56.0, 39.0, 0), 'R21': (59.5, 39.0, 0), 'R22': (66.0, 40.5, 0),
    # test points along the bottom edge
    'TP6': (31.0, 44.0, 0), 'TP1': (35.0, 44.0, 0), 'TP2': (39.0, 44.0, 0), 'TP3': (43.0, 44.0, 0), 'TP4': (47.0, 44.0, 0), 'TP5': (51.0, 44.0, 0), 'TP7': (70.0, 40.0, 0),
}
KEEPOUTS = []  # RYLR998_M4 (antenna on an external SMA pigtail) needs no on-board RF keep-out; if an antenna-equipped RYLR998 is used, mount it hanging off the right edge (antenna outboard)

# ---------------------------------------------------------------------------------------------------------------------
# BOM pricing: unit price in USD at qty 1 from distributor catalogue listings (Digi-Key / Mouser / LCSC) as read on
# PRICE_DATE.  Estimates for planning only; re-quote at order time.  Parts without an MPN (test points, holes) cost 0.
PRICE_DATE = '2026-09-16'
PRICE_USD = {
    'XT30PW-M': 1.20, '0468003.NR': 0.55, 'AO3401A': 0.35, 'BZT52C12-7-F': 0.15, 'SMAJ33A': 0.45, 'EEE-FK1H470P': 0.60,
    'GRM32ER71H106KA12L': 0.85, 'CRA2512-FZ-R020ELF': 0.55, 'INA180A1IDBVR': 0.95, 'KGM15ACG1H104KT': 0.10, 'R1240N001B-TR-FE': 1.45,
    'CL10B104KB8NNNC': 0.10, 'SRN6045TA-4R7M': 0.55, 'CMS06(TE12L,Q,M)': 0.60, '06035A471JAT2A': 0.15, 'GRM31CR71E106KA12L': 0.45,
    'TPS54202DDCR': 0.75, 'GRM32ER61C226KE20L': 0.60, 'SS34': 0.35, 'EEE-FK1A101P': 0.40, 'GRM21BR61C106KE15L': 0.25,
    'STM32F446RET6': 9.80, 'GRM21BR61A106KE19L': 0.20, 'CL10A475KP8NNNC': 0.12, 'BLM18AG601SN1D': 0.12, 'CL10A105KB8NNNC': 0.10,
    'KMR221GLFS': 0.65, 'ABM8-8.000MHZ-10-1-U-T': 0.95, '06035A150JAT2A': 0.15, 'ABS07-32.768KHZ-7-T': 0.70, '06035A100JAT2A': 0.15,
    'LTST-C193KGKT-5A': 0.30, 'LTST-C193TBKT-5A': 0.30, 'LTST-C193KSKT-5A': 0.30, 'LTST-C193KRKT-5A': 0.30, 'PPTC051LFBN-RC': 0.60,
    'BLM15AG601SN1D': 0.12, 'GJM1555C1H470JB01D': 0.12, 'PPTC061LFBN-RC': 0.65, 'ICM-20948': 11.50, 'B3B-XH-A(LF)(SN)': 0.25,
    'SN74AHCT1G125DBVR': 0.45, 'PESD5V0S1BA,115': 0.25, 'USB4105-GF-A': 1.10, 'USBLC6-2SC6': 0.55, 'FTSH-105-01-L-DV-K': 3.20,
}
PRICE_USD.update({m: 0.10 for m in ('RC0603FR-07100KL', 'RC0603FR-0747KL', 'RC0603FR-076K8L', 'RC0603FR-075K1L', 'RC0603FR-0751RL', 'RC0603FR-0715KL',
                                    'RC0603FR-074K7L', 'RC0603FR-0713K3L', 'RC0603FR-0710KL', 'RC0603FR-071KL', 'RC0603FR-07100RL', 'RC0603FR-072K2L', 'RC0603FR-0722KL')})
