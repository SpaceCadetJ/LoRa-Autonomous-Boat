# SESSION HANDOFF — LoRa Autonomous Boat Controller
**Written by:** Claude Code (Opus 4.6), 2026-03-31  
**For:** Claude Desktop (KiCad MCP) and future Claude Code sessions  
**Owner:** Jay — EECS grad student, University of Arkansas, Dr. Tuan Dang's Cognitive Robotics Lab  
**Repo:** `C:\Users\Jay\OneDrive\Desktop\LoRa Autonomous Boat\LoRa Autonomous Boat`

---

## 1. WHO JAY IS AND HOW HE WORKS

Jay is building autonomous systems at the University of Arkansas Cognitive Robotics Lab. Background: Army aviation electrician, Bosch R&D QE. He operates at high tempo with direct, no-BS communication. He wants concrete deliverables — not plans, not skeletons, not discussions of possibilities. Reference images and existing designs over lengthy text descriptions.

**Tools open simultaneously:** KiCad 9.0, Claude Desktop (CD), Claude Code (CC, terminal), VS Code, Chrome, PowerShell.

**The pipeline:** CD (KiCad MCP) ↔ DIRECTIVES.md ↔ CC (file ops, git, code) ↔ STATUS.md ↔ CD

---

## 2. WHAT THE PROJECT IS

**LoRa Autonomous Boat Controller** — an Allegro→KiCad conversion of a proven senior design board. The physical board has already been fabricated and tested. All traces and components are known correct. This is a **polish and documentation** effort, not a design effort.

| Parameter | Value |
|-----------|-------|
| MCU | STM32F446RET6 (Cortex-M4, 180 MHz, 512 KB Flash, LQFP-64) |
| CAN Transceiver | TCAN1042HDRQ1 (SOIC-8) |
| Voltage Regulator | R1240N001B (SOT-23-6) |
| ESD Protection | SB007-03Q-TL-E (SOT-323) |
| LoRa | RYLR896/RYLR998 (915 MHz, UART AT commands) |
| GPS | Generic NMEA via UART |
| Board | 76.2 × 76.2 mm, 2-layer, 45 components |
| Input Voltage | Battery → 3.3V via R1240N buck |
| PWM | Motor (TIM3_CH1/PC6, 50Hz) + Rudder (TIM1_CH1/PA8, 50Hz) |
| Comms | LoRa UART4 (PA0/PA1 @ 115200), GPS USART3 (PC10/PC11 @ 9600), CAN (PA10/PA11/PA12) |

**Critical context:** The board works. The Allegro design is the source of truth. We're making the KiCad version match it perfectly, then cleaning up schematic organization and documentation.

---

## 3. EXACT FILE STATE

### KiCad Project (`hardware/kicad/`)

| File | Status | Notes |
|------|--------|-------|
| `LoRa_Boat_Controller.kicad_pro` | ✅ Exists | Project file |
| `LoRa_Boat_Controller.kicad_sch` | ⚠️ Needs work | Flat schematic — components placed in blocks, **NOT wired** |
| `LoRa_Boat_Controller.kicad_pcb` | ⚠️ Needs work | Component placement from Allegro, **NO traces routed** |
| `LoRa_Boat_Controller.kicad_sym` | ✅ Modified | Custom symbols: R1240N001x, TCAN1042H-Q1 |
| `sym-lib-table` | ✅ | Symbol library registration |
| `fp-lib-table` | ✅ | Footprint library registration |
| `design_data.json` | ✅ | Conversion data from DSN |
| `generate_kicad.py` | ✅ | Python conversion script |
| `senior design v2.dsn` | ✅ | Specctra DSN export (source of truth for netlist/placement) |

### Hierarchical Sub-Sheets (untracked, new)

| File | Status | Notes |
|------|--------|-------|
| `CAN_Bus.kicad_sch` | 🆕 Untracked | CAN bus module schematic |
| `GPS_Module.kicad_sch` | 🆕 Untracked | GPS module schematic |
| `LoRa_Module.kicad_sch` | 🆕 Untracked | LoRa wireless module schematic |
| `MCU.kicad_sch` | 🆕 Untracked | MCU module schematic |
| `PowerSupply.kicad_sch` | 🆕 Untracked | Power regulation module schematic |
| `PWM_Outputs.kicad_sch` | 🆕 Untracked | Motor/servo PWM drivers |

### Allegro Originals (`Allegro/hardware/allegro-original/`)
- `Allegro v5/` — Final PCB layout (`.brd`), schematic (`.opj`), artwork
- `BoatcrewArtwork/` — Gerber exports (7 layers + drill)
- `LIBRARY_MASTER/` — Allegro footprint library

### Firmware (`firmware/`)
- STM32CubeIDE project for STM32F446RET6
- `Core/Src/main.c` — ~750 lines: LoRa init, GPS NMEA parsing, PWM control, CAN
- `BoatTHISTIMEITSDIFFERENT.ioc` — CubeMX config
- HAL + CMSIS drivers included

### Documentation (`docs/`)
- `BOM.csv` — 45 components
- `NETLIST.md` — Complete pin-level net connectivity (authoritative wiring reference)
- `CONVERSION_NOTES.md` — Allegro→KiCad conversion details + known issues

---

## 4. KNOWN ISSUES

### Schematic
1. **Components placed but NOT wired** — Use `docs/NETLIST.md` as the authoritative wiring reference
2. **Flat structure** — Should be reorganized into hierarchical sheets matching original OrCAD blocks (sub-sheets exist but may need wiring/verification)
3. **Power symbols** — GND, +3V3, VBAT need proper KiCad power flags
4. **Custom symbols** — R1240N and TCAN1042H pinouts should be verified against datasheets

### PCB
1. **NO traces routed** — Placement is correct from Allegro, all routing must be done manually
2. **Board outline** — Simple rectangle from DSN; may not match final Allegro v5DRL revision
3. **No copper zones** — Ground pour needs to be recreated
4. **No design rules** — Clearance 12mil/0.3048mm, trace 12mil, via 35mil pad/25mil drill
5. **Silkscreen** — Reference designator positions need cleanup

### Firmware/Schematic Discrepancy
**PWM pins appear swapped** between schematic and firmware:
- Schematic: PA8 → Motor (N04355), PC6 → Rudder (N04395)
- Firmware: PC6/TIM3_CH1 → Motor, PA8/TIM1_CH1 → Rudder
- **The board is fabricated and working** — verify against actual traces to determine which is correct

---

## 5. WORKFLOW — WHO DOES WHAT

### The Golden Rule
**CD (Claude Desktop via KiCad MCP)** owns `.kicad_sch` and `.kicad_pcb` files. **CC (Claude Code)** owns everything else. **Jay** makes final calls in KiCad GUI for anything the MCP can't handle cleanly.

### Task Assignment Table

| Task Type | Assign To | Why |
|-----------|-----------|-----|
| Schematic wiring/editing | CD via KiCad MCP | MCP handles hierarchy UUIDs correctly |
| PCB zone/net class setup | JAY in KiCad GUI | S-expression too fragile for text editing |
| PCB trace routing | JAY in KiCad GUI | Interactive router required |
| Text file edits (MD, CSV, source) | CC via DIRECTIVES.md | Reliable grep+replace, bulk ops |
| Firmware code generation | CC | Needs technical context, produces complete files |
| Documentation generation | CC | Project knowledge → markdown |
| Git operations (commit, branch, PR) | CC | Terminal access |
| Python analysis scripts | CC | File parsing, data extraction |
| BOM/netlist verification | CC | Cross-reference Allegro data vs KiCad |
| Part number corrections (bulk) | CC | grep+replace across repo |
| Schematic component additions with hierarchy UUIDs | JAY in KiCad GUI | UUIDs cannot be text-edited (TITAN lesson) |

### CC Anti-Patterns (from TITAN lessons — still apply)

1. **Never edit `.kicad_sch` or `.kicad_pcb` directly** — hierarchy UUIDs, s-expression fragility
2. **Never create zones or net classes via text** — format fragility
3. **Never do schematic + PCB edits in the same session** — cascade failure risk
4. **Always backup before modification** — `cp "file" "file.bak_sessionN"`
5. **Always update STATUS.md as the LAST task** — or it gets forgotten
6. **Always write CHANGES_SESSIONN.md** — audit trail

### The Directive Template

```markdown
# DIRECTIVES — CD ↔ CC Pipeline
Last updated: [timestamp]
Pipeline status: [ACTIVE / PAUSED]

## TASK 1: [Specific task name]
**Assigned to:** [CC / CD / JAY]
**File:** [exact path]
**Backup first:** cp "original" "original.bak_sessionN"
**Action:** [precise instructions]
**Validation:** [how to verify]

## TASK N+1: UPDATE STATUS.md (ALWAYS LAST — CC)
Report everything completed, with file sizes and validation results.
Write CHANGES_SESSIONN.md listing exactly what changed.
```

---

## 6. PRIORITY ACTIONS

### P0 — Schematic Wiring (CD)
1. Wire all components in each sub-sheet using `docs/NETLIST.md` as reference
2. Add proper power symbols (GND, +3V3, VIN_RAW)
3. Verify hierarchical sheet connections between sub-sheets and root
4. Run ERC — fix all errors

### P1 — PCB Cleanup (JAY in KiCad GUI)
1. Verify board outline matches Allegro v5DRL final
2. Set up design rules (12mil clearance, 12mil trace, 35/25mil via)
3. Add ground pour zone
4. Route traces (or verify against Allegro artwork)
5. Clean up silkscreen
6. Run DRC

### P2 — Verification (CC)
1. Cross-reference KiCad netlist against `docs/NETLIST.md`
2. Cross-reference KiCad BOM against `docs/BOM.csv`
3. Resolve PWM pin swap discrepancy (schematic vs firmware)
4. Verify all 45 component values match Allegro originals

### P3 — Polish (CC + CD)
1. Clean up documentation
2. Verify firmware pin assignments match final schematic
3. Final git commit with clean state

---

## 7. REFERENCE DATA

### Net Summary (35 nets)

**Power:** GND, +3V3, VIN_RAW, GND_BAT, VCAP1, VREG_OUT

**Power Supply:** EN, SW_NODE, BST, FB_DIV, COIL_SENSE, ADC_VBAT

**LoRa:** LORA_TX (PA0→mod), LORA_RX (PA1←mod), LORA_RST (PA3), LORA_VCC, LORA_FILT

**GPS:** GPS_RX (PB0→mod), GPS_TX_PC11 (PC11←mod), GPS_TX_PC10 (PC10→mod)

**CAN:** CAN_TX (PA11→U5), CAN_RX (PA10←U5), CAN_STB (PA12), CANH, CANL, CAN_VCC

**PWM:** PWM_MOTOR (PA8 or PC6 — verify), PWM_RUDDER (PC6 or PA8 — verify)

**Debug:** SWDIO (PA13), SWCLK (PA14), JTDI (PA15), JTDO_SWO (PB3), JTAG_TCK, NRST, VBAT

### Component Summary
- 17× capacitors (C1-C10, C12, C14, C20-C23, CEXT, CIN, COUT, COUT1)
- 6× resistors (R1-R6)
- 3× inductors (L1, L3, L4)
- 1× MCU (U3: STM32F446RET6)
- 1× CAN transceiver (U5: TCAN1042HDRQ1)
- 1× buck converter (U6: R1240N001B)
- 1× ESD diode (U1: SB007-03Q-TL-E)
- 5× connectors (CANHEADER, GPSMODULE, LORAMODULE, SPEEDCONTROLLER, STEERINGSERVO, JTAG)
- 4× test points (TP1, TP3, TP4, TP5)
- 2× battery terminals (VIN, GND)

---

## 8. REPO STRUCTURE

```
LoRa Autonomous Boat/
├── Allegro/hardware/allegro-original/   # Source of truth (fabricated design)
│   ├── Allegro v5/                      # Final PCB + schematic
│   ├── BoatcrewArtwork/                 # Gerber exports
│   └── LIBRARY_MASTER/                  # Allegro libraries
├── hardware/kicad/                      # KiCad 9 conversion (active work)
│   ├── LoRa_Boat_Controller.kicad_*     # Project, schematic, PCB, symbols
│   ├── *_Module.kicad_sch               # Hierarchical sub-sheets
│   ├── SESSION_HANDOFF.md               # This file
│   ├── DIRECTIVES.md                    # CC↔CD task pipeline
│   └── STATUS.md                        # Current project state
├── firmware/                            # STM32CubeIDE project
│   ├── Core/Src/main.c                  # Application logic (~750 lines)
│   └── BoatTHISTIMEITSDIFFERENT.ioc    # CubeMX config
└── docs/
    ├── BOM.csv                          # 45-component BOM
    ├── NETLIST.md                       # Authoritative wiring reference
    └── CONVERSION_NOTES.md              # Conversion details + known issues
```

---

*The board is fabricated and working. The Allegro design is ground truth. Every change to the KiCad version should bring it closer to matching the Allegro original — not "improving" on it. Jay's time is the bottleneck.*
