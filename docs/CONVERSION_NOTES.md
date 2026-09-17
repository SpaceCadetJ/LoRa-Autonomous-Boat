# Allegro → KiCad conversion notes (V1, as fabricated)

Rewritten 2026-09-16. The March-2026 version of this file described a conversion of the Specctra DSN (`senior design v2.dsn`); that DSN is an export of **v2.brd**, while the fabricated board is **v5.brd**. Between v2 and v5 the board was re-laid out on a smaller outline (66.5 × 37.3 mm instead of 76.2 × 76.2 mm), every part moved, U1/COUT1/TP2 were removed, D21 was added, and four footprints changed (see `A0_PROVENANCE.md`). Nothing from the old converter survives except the readable-net-name idea.

## Sources actually used

| Data | Source file(s) | Why this one |
|---|---|---|
| Copper, mask, silkscreen, outline | `Allegro/hardware/allegro-original/BoatcrewArtwork/BOATCREW*.art` (byte-identical copies in `Allegro v5/Allegro/`) | Plotted from `senior design v5.brd` on 2025-05-09 17:41:07, 30 minutes after the last netlist import; the last entry in `allegro.jrl` is this artwork run |
| Netlist | `Allegro v5/Allegro/pstxnet.dat`, `pstxprt.dat`, `pstchip.dat` | OrCAD packaging of 2025-05-09 17:12:27, imported into v5.brd at 17:12:46 (`netrev.lst`, `eco.txt`) |
| Pad geometry | `senior design v2.dsn` `(library (image …) (padstack …))` for the 21 footprints that did not change, the v5 films for the four that did | The DSN is the only text source of padstack shapes; the films confirm them pad by pad |
| Design rules | `senior design v2_rules.do` (12 mil width, 12 mil clearance, 5 mil to vias) | Only rule file in the repo; the fabricated copper violates it in places (documented in `LoRa_Boat_Controller.kicad_dru`) |
| Drill | derived from the v5 pad flashes + padstack hole sizes | The only drill file in the repo (`BOATCREWDRILL-1-2.drl`) is a v4 export; 35 of its 50 holes have no v5 pad |

## Method (all scripted, `hardware/kicad/tools/`)

1. `provenance.py` reads every Gerber/drill header → provenance table.
2. `v5_reconstruct.py` matches every footprint's pad pattern against the dark flashes of `BOATCREWTOPL.art` (1.5 mil tolerance), rasterizes both copper films at 2 px/mil, labels connected copper, joins layers through vias/PTH pads, and resolves which pads belong to which net from `pstxnet.dat` by constraint propagation (44/44 parts, 0 shorts, 0 opens). Film voids that the 5 mil pour clearance does not explain become rule areas (footprint body keep-outs, the 580 × 706 mil LoRa keep-out).
3. `gen_footprints.py` writes `LoRa_Boat_Controller.pretty/` (pads exact, solder-mask margins from the mask films, courtyard = pad extents).
4. `gen_pcb.py` writes the board: footprints at the film positions, every film line as a track with its net, vias, the +3V3 (top) and GND (bottom) pours as zones, rule areas, silkscreen and outline 1:1 from the films, plus `.kicad_pro` (rules) and `.kicad_dru` (as-fabricated exceptions).
5. `validate_pcb.py` (KiCad python) re-reads the board: 172/172 pad centres within 0.000 mil of the film flashes; fills zones; saves.
6. `xor_compare.py` rasterizes the KiCad Gerber export and the films in one frame → per-layer mismatch (F.Cu 0.87 %, B.Cu 0.23 %); hole-by-hole drill match 53/53.
7. `gen_symbols.py` + `gen_sch.py` write the hierarchical schematic from the same netlist; `check_netlist.py` proves schematic == board == `pstxnet.dat` pin sets.
8. `gen_bom.py`, `gen_docs.py`, `evidence_figs.py`, `a0_xor_dsn.py` produce the BOM, NETLIST/INDEX/this table, the evidence figures and the DSN-v2 comparison. `build_v1.py` runs the whole chain.

## Coordinate frames

Allegro/DSN/films share one origin (films have `Offset 0,0`), mils, Y up. KiCad: mm, Y down, Allegro origin placed at (100, 100) mm (`allegro_data.allegro_to_kicad`). KiCad plots Gerbers with Y pointing up again, so the comparison uses `raster.kicad_xform` (x − 3937 mil, y + 3937 mil). Footprint rotation: Allegro CCW degrees map 1:1 to KiCad footprint rotation (verified by the 0.000 mil pad check).

## Deliberate deviations from a "clean" KiCad project (fidelity first)

- Netclass clearance is the 12 mil design rule, but the fabricated copper has 7.7 mil between adjacent LQFP fan-out traces, 5 mil pour-to-copper gaps and two pads at 3.4/4.8 mil from a track; `LoRa_Boat_Controller.kicad_dru` states these measured minimums so DRC reports 0 errors without hiding them (they are V1 findings).
- Pads have `zone_connect none` and a 5 mil local clearance because Allegro plots thermal spokes as explicit lines; the spokes are imported as tracks.
- Vias are untented (44 mil mask openings on 24 mil pads, as on the films); KiCad therefore reports 37 solder-mask-bridge warnings — real on the fabricated board.
- Reference designators without a trailing digit get a `1` suffix (`CANHEADER1`, `CIN1`, `JTAG1`, …) because KiCad's annotation rule otherwise blocks *Update PCB from Schematic*; the Allegro name is kept in the `Allegro_RefDes` property.
- Silkscreen is imported as graphics from the film (the fabricated text), footprint references are on `F.Fab` only.
- The eight identical 0805 decoupling capacitors C2–C9 sit on the same nets (+3V3/GND); their refdes-to-position assignment follows a deterministic order (`v5_reconstruct.py` notes) and cannot be proven from copper alone.

## Footprint mapping (generated)

Allegro footprint → project footprint (pads exactly as fabricated) → nearest KiCad-library footprint (for reference only; the board uses the project footprints) → pad-geometry delta.

<!-- BEGIN GENERATED gen_docs.py footprints -->
| Allegro footprint (JEDEC_TYPE) | Project footprint | Used by | Pads (mil, as fabricated) | Nearest KiCad-library footprint | Pad delta vs library |
|---|---|---|---|---|---|
| `CAP_0603G_AVX-M` | `LoRa_Boat_Controller:CAP_0603G_AVX-M` | C14 | 2: rect 42x40@(35.5,0); 1: rect 42x40@(-35.5,0) | `Capacitor_SMD:C_0603_1608Metric` | same package class; pad sizes differ by a few mil |
| `CAP_0603_CL10A_1P6XP8_SAM-M` | `LoRa_Boat_Controller:CAP_0603_CL10A_1P6XP8_SAM-M` | C10, CEXT1 | 2: rect 42x37@(34.5,0); 1: rect 42x37@(-34.5,0) | `Capacitor_SMD:C_0603_1608Metric` | same package class; pad sizes differ by a few mil |
| `CAP_CL10_SAM-M` | `LoRa_Boat_Controller:CAP_CL10_SAM-M` | C12 | 2: rect 33.81x33.5@(36.59,0); 1: rect 33.81x33.5@(-36.59,0) | `Capacitor_SMD:C_0603_1608Metric` | same package class; pad sizes differ by a few mil |
| `CAP_GJM1555C1H220JB01__MUR-L` | `LoRa_Boat_Controller:CAP_GJM1555C1H220JB01__MUR-L` | C23 | 2: rect 20x20@(16.5,0); 1: rect 20x20@(-16.5,0) | `Capacitor_SMD:C_0402_1005Metric` | same package class; pad sizes differ by a few mil |
| `CAP_KGM21_KAV-L` | `LoRa_Boat_Controller:CAP_KGM21_KAV-L` | C1, C2, C22, C3, C4, C5, C6, C7, C8, C9 | 1: rect 36x47@(-27.5,0); 2: rect 36x47@(27.5,0) | `Capacitor_SMD:C_0805_2012Metric` | 36x47 mil at 55 mil pitch vs 0805 lib 1.0x1.45 mm at 1.9 mm (39x57 at 75) |
| `CAP_NTS_55_2P8T_NIP` | `LoRa_Boat_Controller:CAP_NTS_55_2P8T_NIP` | CIN1 | 2: rect 65x213@(101.5,0); 1: rect 65x213@(-101.5,0) | `Capacitor_SMD:C_2220_5750Metric` | 65x213 mil at 203 mil pitch for the 5.7x5.0 mm Chemi-Con NTS body |
| `CONN5_1LFBN-RC_SUL` | `LoRa_Boat_Controller:CONN5_1LFBN-RC_SUL` | GPSMODULE1, LORAMODULE1 | 5 pads circle 68x68 hole 40 | `Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical` | 68 mil pad / 40 mil hole (DSN v2 had 60/40) |
| `CONN_B4B-XH-A_JST` | `LoRa_Boat_Controller:CONN_B4B-XH-A_JST` | CANHEADER1 | 4: circle 69x69@(-295.28,0) hole 49; 3: circle 69x69@(-196.85,0) hole 49; 2: circle 69x69@(-98.42,0) hole 49; 1: circle 69x69@(0,0) hole 49 | `Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical` | 69 mil pad / 49 mil hole at 98.42 mil (2.5 mm) pitch |
| `CONN_PPTC031_SUL` | `LoRa_Boat_Controller:CONN_PPTC031_SUL` | SPEEDCONTROLLER1, STEERINGSERVO1 | 3: circle 68x68@(-200,0) hole 40; 2: circle 68x68@(-100,0) hole 40; 1: circle 68x68@(0,0) hole 40 | `Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical` | 68 mil pad / 40 mil hole (DSN v2 had 60/40) |
| `D0008A_L` | `LoRa_Boat_Controller:D0008A_L` | U5 | 8 pads obround 49.21x21.65 | `Package_SO:SOIC-8_3.9x4.9mm_P1.27mm` | oblong 21.65x49.21 mil at 50 mil pitch vs SOIC-8 lib 1.55x0.6 mm rect |
| `G-21_MUR-L` | `LoRa_Boat_Controller:G-21_MUR-L` | C20, C21 | 2: rect 26x47@(32.5,0); 1: rect 26x47@(-32.5,0) | `Capacitor_SMD:C_0805_2012Metric` | same package class; pad sizes differ by a few mil |
| `G-31_MUR-M` | `LoRa_Boat_Controller:G-31_MUR-M` | COUT1 | 2: rect 50x65@(60,0); 1: rect 50x65@(-60,0) | `Capacitor_SMD:C_1206_3216Metric` | same package class; pad sizes differ by a few mil |
| `IND_7045_TDK` | `LoRa_Boat_Controller:IND_7045_TDK` | L1 | 1: rect 86.61x94.88@(0,108.07); 2: rect 86.61x94.88@(0,-108.07) | `Inductor_SMD:L_TDK_SLF7045` | custom 86.6x94.9 mil pads at 216 mil pitch; TDK recommends 2.2x1.5 mm at 6.3 mm |
| `IND_BLM15_0402_MUR-L` | `LoRa_Boat_Controller:IND_BLM15_0402_MUR-L` | L3, L4 | 2: rect 20x20@(16.5,0); 1: rect 20x20@(-16.5,0) | `Inductor_SMD:L_0402_1005Metric` | same package class; pad sizes differ by a few mil |
| `LQFP64-10x10mm` | `LoRa_Boat_Controller:LQFP64-10x10mm` | U3 | 64 pads rect 12x47 | `Package_QFP:LQFP-64_10x10mm_P0.5mm` | 47x12 mil pads vs 1.5x0.3 mm (59x11.8): fab pads are 12 mil shorter |
| `M-FLAT_TOS-L` | `LoRa_Boat_Controller:M-FLAT_TOS-L` | D21 | 1: rect 38x71@(-81.5,0); 2: rect 38x71@(81.5,0) | `Diode_SMD:D_SOD-123F` | 71x38 mil at 163 mil pitch; Toshiba recommends 2.1x1.4 mm at 4.4 mm (173 mil) |
| `RC0402N_PAN-M` | `LoRa_Boat_Controller:RC0402N_PAN-M` | R1, R4 | 2: rect 33.81x21.68@(25.76,0); 1: rect 33.81x21.68@(-25.76,0) | `Resistor_SMD:R_0402_1005Metric` | same package class; pad sizes differ by a few mil |
| `RC0402N_YAG-M` | `LoRa_Boat_Controller:RC0402N_YAG-M` | R3 | 2: rect 34x22@(26,0); 1: rect 34x22@(-26,0) | `Resistor_SMD:R_0402_1005Metric` | same package class; pad sizes differ by a few mil |
| `RC0603N_YAG-M` | `LoRa_Boat_Controller:RC0603N_YAG-M` | R2 | 2: rect 38x34@(34.5,0); 1: rect 38x34@(-34.5,0) | `Resistor_SMD:R_0603_1608Metric` | same package class; pad sizes differ by a few mil |
| `RES_1005_SAM-M` | `LoRa_Boat_Controller:RES_1005_SAM-M` | R6 | 2: rect 31.84x21.68@(25.76,0); 1: rect 31.84x21.68@(-25.76,0) | `Resistor_SMD:R_0402_1005Metric` | same package class; pad sizes differ by a few mil |
| `RES_R0805_ROM-M` | `LoRa_Boat_Controller:RES_R0805_ROM-M` | R5 | 2: rect 36x55@(35.5,0); 1: rect 36x55@(-35.5,0) | `Resistor_SMD:R_0805_2012Metric` | same package class; pad sizes differ by a few mil |
| `SAMTEC_FTSH-105-XX-X-DV` | `LoRa_Boat_Controller:SAMTEC_FTSH-105-XX-X-DV` | JTAG1 | 10 pads rect 29.13x109.84 | `Connector_PinHeader_1.27mm:PinHeader_2x05_P1.27mm_Vertical_SMD` | 29.13x109.84 mil = Samtec 0.029x0.110 in; row spacing 160.24 mil = 0.160 in |
| `SOT-23-6W_PE-SOT23-6W-0512_NMD` | `LoRa_Boat_Controller:SOT-23-6W_PE-SOT23-6W-0512_NMD` | U6 | 6 pads rect 35.5x22 | `Package_TO_SOT_SMD:SOT-23-6` | 35.5x22 mil vs lib 1.06x0.65 mm (41.7x25.6) |
| `amv_con1` | `LoRa_Boat_Controller:amv_con1` | GND1, VIN1 | 1: circle 62.99x62.99@(0,0) hole 23.62 | `TestPoint:TestPoint_THTPad_1.5x1.5mm_Drill0.7mm` | 62.99 mil (1.6 mm) pad, 23.62 mil (0.6 mm) hole |
| `amv_test_point` | `LoRa_Boat_Controller:amv_test_point` | TP1, TP3, TP4, TP5 | 1: circle 133.86x133.86@(0,0) hole 55.12 | `TestPoint:TestPoint_THTPad_D3.0mm_Drill1.5mm` | 133.86 mil (3.4 mm) pad, 55.12 mil (1.4 mm) hole |
<!-- END GENERATED gen_docs.py footprints -->

## Symbols

`MCU_ST_STM32F4:STM32F446RETx` (KiCad library, pin 30 = VCAP_1, pin 31 = VSS — matches DS10693 Table 10), `Device:C/R/L/FerriteBead`, `Connector_Generic:Conn_01x0N` / `Conn_02x05_Odd_Even`, `Connector:TestPoint`, and four project symbols verified against the current datasheets (`docs/research/DATASHEET_NOTES.md`): `R1240N001x` (Nisshinbo EA-190-240903: 1 CE, 2 VIN, 3 LX, 4 BST, 5 GND, 6 VFB), `TCAN1042H-Q1` (TI SLLSES9D: 1 TXD, 2 GND, 3 VCC, 4 RXD, 5 NC, 6 CANL, 7 CANH, 8 STB), `CMS06_Schottky` (Toshiba: 1 anode, 2 cathode — KiCad's `Device:D` numbers them the other way round), and the `VIN_RAW` power symbol.
