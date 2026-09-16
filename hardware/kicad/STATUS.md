# PROJECT STATUS — LoRa Autonomous Boat Controller
**Last updated:** 2026-03-31 (Session 1 — CC)  
**Overall:** 🔶 In Progress — Allegro→KiCad conversion, cleanup phase

---

## Summary

| Area | Status | Details |
|------|--------|---------|
| **Schematic** | 🔴 Not wired | Components placed in blocks, sub-sheets created, NO wires |
| **PCB** | 🔴 Not routed | 45 components placed at Allegro coordinates, NO traces |
| **Custom Symbols** | 🟡 Needs verify | R1240N001x, TCAN1042H-Q1 — check pinouts vs datasheets |
| **Firmware** | ✅ Complete | main.c compiles, CubeMX .ioc configured |
| **BOM** | ✅ Complete | 45 components documented |
| **Netlist Reference** | ✅ Complete | 35 nets, full pin-level connectivity in docs/NETLIST.md |
| **Conversion Notes** | ✅ Complete | Known issues documented |
| **Git** | 🟡 Dirty | 6 untracked sub-sheets + modified .kicad_sym |

---

## Schematic State

### Root Sheet: `LoRa_Boat_Controller.kicad_sch`
- Flat schematic with components organized in functional blocks
- **NOT wired** — needs connections per NETLIST.md

### Sub-Sheets (untracked)
| Sheet | Components | Wired? |
|-------|-----------|--------|
| `MCU.kicad_sch` | STM32F446RET6 + decoupling caps | ❌ |
| `PowerSupply.kicad_sch` | R1240N001B + passives | ❌ |
| `CAN_Bus.kicad_sch` | TCAN1042HDRQ1 + passives | ❌ |
| `LoRa_Module.kicad_sch` | Connector + ferrites + decoupling | ❌ |
| `GPS_Module.kicad_sch` | Connector | ❌ |
| `PWM_Outputs.kicad_sch` | Motor + rudder connectors + TPs | ❌ |

### Known Issues
1. Power symbols (GND, +3V3) not added as proper KiCad power flags
2. PWM pin assignment discrepancy between schematic and firmware (PA8/PC6 swap)
3. Custom symbol pinouts (R1240N, TCAN1042H) need datasheet verification

---

## PCB State

- **Component count:** 45
- **Traces routed:** 0
- **Zones:** 0
- **Design rules:** Not configured (need 12mil clearance, 12mil trace, 35/25mil via)
- **Board outline:** Simple rectangle from DSN — may not match Allegro v5DRL final
- **Silkscreen:** Auto-generated positions, needs cleanup

---

## Firmware State

- **Project:** STM32CubeIDE, target STM32F446RET6
- **Application:** `Core/Src/main.c` (~750 lines)
  - LoRa AT command init + UART RX parsing
  - GPS NMEA ($GPRMC/$GNRMC) parsing
  - PWM servo control (50Hz, 2 channels)
  - GPS telemetry TX (every 5s)
- **Status:** Compiles clean, not yet flashed to hardware

---

## Open Questions

1. **PWM pin swap:** Which is correct — schematic (PA8=motor, PC6=rudder) or firmware (PC6=motor, PA8=rudder)? Board is fabricated, traces tell the truth.
2. **Board outline:** Does the DSN rectangle match the actual Allegro v5DRL board shape?
3. **Sub-sheet hierarchy:** Are the 6 new sub-sheets from CD properly linked to the root schematic?

---

## Session Log

| Session | Date | Agent | What Changed |
|---------|------|-------|-------------|
| 1 | 2026-03-31 | CC | Created workflow files (SESSION_HANDOFF.md, DIRECTIVES.md, STATUS.md) |
