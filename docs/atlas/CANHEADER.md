# CAN bus

Four-pin bus/supply header; its H/L names are corrected while original pin membership is preserved.

Allegro reference **CANHEADER** → KiCad reference **CANHEADER1**.

BOM: B4B-XH-A; MPN `B4B-XH-A(LF)(SN)`; JST; confidence: HIGH.
Footprint: `LoRa_Boat_Controller:CONN_B4B-XH-A_JST`. [Full BOM](../BOM.csv).

## Read before wiring

- Electrical pin numbers below come from v5 pstxnet.dat, not a physical left-to-right view. Board side, connector key, cable view, and pin-1 marking require physical verification. All voltages and waveforms are design/code expectations, not bench measurements.
- CANH = pin 3 / U5-7 / N24691; CANL = pin 4 / U5-6 / N04855. Historical March 2026 documentation reversed them; use the v5 pin mapping here.
- V1 RXD is wired U5-4 → U3-43/PA10. PA10 has no CAN alternate function; no CAN initialization exists in current firmware.
- U5-8/STB goes to PA11, U5-1/TXD goes to PA12. The CAN transceiver supply source and bus termination require review.

## Electrical pin map

| Pin | Readable net | Allegro net | MCU | Firmware role |
|---|---|---|---|---|
| 1 | GND | 0 | U3-18 VSS; U3-31 VSS_2; U3-47 VSS_3; U3-63 VSS_4; U3-12 VSSA/VREF- | Common reference |
| 2 | CAN_VCC | N24886 | No direct MCU pin | No CAN initialization; transceiver supply net connects header to U5-3 and C1-2 |
| 3 | CANH | N24691 | No direct MCU pin | Bus line to U5-7; CAN firmware not implemented |
| 4 | CANL | N04855 | No direct MCU pin | Bus line to U5-6; CAN firmware not implemented |

## Verification targets — not measured results

### Pin 1 — GND

**Domain:** 0 V reference (expected). **Direction:** Reference.

Unpowered continuity to GND1/TP5; resistance/continuity has not been measured.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:127](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L127); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:169](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L169); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:172](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L172); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:175](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L175); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:178](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L178); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:181](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L181); [docs/atlas/evidence/v1-netmap.json:3](../../docs/atlas/evidence/v1-netmap.json#L3).

### Pin 2 — CAN_VCC

**Domain:** External supply unidentified; TCAN1042H needs 4.5–5.5 V. **Direction:** External connector → CAN supply (source unresolved).

Confirm supply source and polarity. This net is separate from +3V3 and VIN_RAW in v5.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:395](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L395); [docs/atlas/evidence/v1-netmap.json:12](../../docs/atlas/evidence/v1-netmap.json#L12); [docs/research/DATASHEET_NOTES.md:37](../../docs/research/DATASHEET_NOTES.md#L37).

### Pin 3 — CANH

**Domain:** Differential CAN bus; not a TTL UART pin. **Direction:** Bidirectional bus via U5.

Check continuity header pin 3 → U5-7 and external termination; no working bus is claimed.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:385](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L385); [docs/atlas/evidence/v1-netmap.json:7](../../docs/atlas/evidence/v1-netmap.json#L7); [docs/research/DATASHEET_NOTES.md:36](../../docs/research/DATASHEET_NOTES.md#L36).

### Pin 4 — CANL

**Domain:** Differential CAN bus; not a TTL UART pin. **Direction:** Bidirectional bus via U5.

Check continuity header pin 4 → U5-6 and external termination; no working bus is claimed.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:76](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L76); [docs/atlas/evidence/v1-netmap.json:8](../../docs/atlas/evidence/v1-netmap.json#L8); [docs/research/DATASHEET_NOTES.md:36](../../docs/research/DATASHEET_NOTES.md#L36).

[Atlas index and snapshot provenance](README.md) · [Schematic PDF](../img/v1_schematic.pdf) · [PCB top](../img/v1_pcb_top.png) · [PCB bottom](../img/v1_pcb_bottom.png)
