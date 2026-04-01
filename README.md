# LoRa Autonomous Boat Controller

Embedded control system for an autonomous RC boat using LoRa wireless communication, GPS navigation, and CAN bus interfacing. Originally developed as a senior design project at the University of Arkansas.

## System Overview

The controller board receives thrust and rudder commands from a remote handset over 915 MHz LoRa (RYLR module), parses GPS NMEA sentences for position telemetry, and drives a brushless motor ESC and rudder servo via PWM. A CAN bus transceiver provides expansion for additional sensor nodes.

### Key Specifications

| Parameter | Value |
|---|---|
| MCU | STM32F446RET6 (Cortex-M4, 180 MHz, 512 KB Flash, LQFP-64) |
| CAN Transceiver | TCAN1042HDRQ1 (TI, 5 Mbps, SOIC-8) |
| Voltage Regulator | R1240N001B (Ricoh, 1.5 MHz buck, SOT-23-6) |
| ESD Protection | SB007-03Q-TL-E (ON Semi, SOT-323) |
| LoRa Module | RYLR896/RYLR998 (915 MHz, AT command interface) |
| GPS Module | Generic NMEA ($GPRMC/$GNRMC) via UART |
| Input Voltage | Battery (regulated to 3.3V) |
| Motor PWM | TIM3_CH1 / PC6, 50 Hz, 1000–2000 µs |
| Rudder PWM | TIM1_CH1 / PA8, 50 Hz, 1100–1900 µs |
| LoRa UART | UART4 (PA0 TX, PA1 RX) @ 115200 baud |
| GPS UART | USART3 (PC10 TX, PC11 RX) @ 9600 baud |
| Debug | JTAG (4-pin SWD + SWO via 2x5 IDC header) |
| Board Size | 76.2 × 76.2 mm (3.0" × 3.0"), 2-layer |
| Components | 45 total |

### LoRa Protocol

The boat node (address 1) communicates with the RC handset (address 2) on network ID 18 at 915 MHz. LoRa parameters: SF12, BW 125 kHz, CR 4/4.

**Incoming commands (from RC handset):**
- `THRUST,<0–100>` — Motor speed (0 = stop, 100 = full)
- `RUDDER,<0–100>` — Rudder position (0 = full left, 50 = center, 100 = full right)
- `GPS,<lat>,<lon>` — Position from other node (logged/displayed)

**Outgoing telemetry (every 5s when GPS fix is valid):**
- `GPS,<lat>,<lon>` — Boat position sent to RC handset

## Repository Structure

```
├── hardware/
│   ├── allegro-original/       # Original Cadence Allegro / OrCAD Capture design
│   │   ├── Allegro v5/         # PCB layout (.brd), schematic (.opj/.dsn), artwork
│   │   ├── BoatcrewArtwork/    # Gerber artwork exports (7 layers + drill)
│   │   └── LIBRARY_MASTER/     # Allegro footprint library (padstacks + symbols)
│   │
│   └── kicad/                  # KiCad 9 conversion (generated from DSN data)
│       ├── LoRa_Boat_Controller.kicad_pro    # Project file
│       ├── LoRa_Boat_Controller.kicad_sch    # Schematic (flat, block-organized)
│       ├── LoRa_Boat_Controller.kicad_pcb    # PCB with original placement coordinates
│       ├── LoRa_Boat_Controller.kicad_sym    # Custom symbols (R1240N, TCAN1042H)
│       ├── LoRa_Boat_Controller.pretty/      # Project-local footprint library
│       ├── sym-lib-table                     # Symbol library registration
│       └── fp-lib-table                      # Footprint library registration
│
├── firmware/                   # STM32CubeIDE project (STM32F446RET6)
│   ├── Core/
│   │   ├── Inc/                # Headers (main.h, HAL config, interrupt handlers)
│   │   └── Src/                # Source (main.c — LoRa, GPS, PWM, CAN logic)
│   ├── Drivers/                # STM32F4xx HAL + CMSIS
│   ├── BoatTHISTIMEITSDIFFERENT.ioc  # STM32CubeMX pin/peripheral configuration
│   ├── STM32F446RETX_FLASH.ld        # Flash linker script
│   └── STM32F446RETX_RAM.ld          # RAM linker script
│
├── docs/
│   ├── BOM.csv                 # Bill of Materials (45 components)
│   ├── NETLIST.md              # Net connectivity reference
│   └── CONVERSION_NOTES.md    # Allegro → KiCad conversion details
│
├── .gitignore
└── README.md
```

## Hardware Design

### Original (Cadence Allegro)

The PCB was designed in OrCAD Capture (schematic) + Allegro PCB Editor (layout), both from Cadence SPB 22.1. The design went through 6 board revisions, with `senior design v5DRL.brd` being the final fabrication-ready version.

**Schematic blocks:** Power Supply, MCU Power, MCU Outputs, CAN Bus Module, LoRa Module, GPS Module, Speed Controller, Steering Servo, JTAG Header.

### KiCad Conversion

The KiCad project was machine-generated from the Specctra DSN export (`senior design v2.dsn`), which contains complete component placement, footprint geometry, and netlist data. The conversion pipeline:

1. Parsed DSN S-expression format for placement coordinates, net connectivity, and library definitions
2. Mapped 45 Allegro footprints to KiCad standard library equivalents
3. Generated `.kicad_pcb` with mil-to-mm coordinate conversion (Y-axis flip for KiCad convention)
4. Generated `.kicad_sch` with components organized into functional blocks
5. Created project-local symbol library for R1240N and TCAN1042H

**What works:** Component placement positions match the Allegro layout. Footprint assignments use KiCad standard libraries. Net names are cleaned up from auto-generated OrCAD names to readable signal names.

**What needs manual work in KiCad:**
- Schematic wiring (components are placed but not yet wired — use `NETLIST.md` as reference)
- Copper trace routing on the PCB (placement is correct, routing must be redone)
- Copper pour / ground plane zones
- Design rule setup (clearances, trace widths)
- Silkscreen cleanup
- Verify footprint pad geometry against datasheets

## Firmware

The firmware is a bare-metal STM32 HAL application generated from STM32CubeMX. The main application logic (750 lines in `main.c`) implements:

- **LoRa initialization** — AT command sequence for address, network, frequency, and spreading factor configuration
- **LoRa RX parsing** — Interrupt-driven UART with `+RCV=` message parsing for THRUST, RUDDER, and GPS commands
- **GPS NMEA parsing** — $GPRMC/$GNRMC sentence parsing with checksum validation, DD.MM → decimal degree conversion
- **PWM control** — 50 Hz servo-compatible PWM on two channels with microsecond pulse width mapping
- **GPS telemetry TX** — Periodic LoRa transmission of GPS coordinates to the RC handset

### Building

Open `BoatTHISTIMEITSDIFFERENT.ioc` in STM32CubeMX to regenerate the project, or import the firmware directory into STM32CubeIDE. Target: STM32F446RETx, toolchain: GCC ARM.

## Companion Hardware

This repository covers the **boat node** only. The system requires a companion **RC handset** running on an STM32L072 with a matching RYLR LoRa module (address 2, same network/frequency parameters). The handset firmware is not included in this repository.

## License

Senior design project — University of Arkansas EECS.
