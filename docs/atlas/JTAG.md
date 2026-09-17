# Debug / JTAG

Ten numbered electrical pins; do not infer cable orientation from the table.

Allegro reference **JTAG** → KiCad reference **JTAG1**.

BOM: FTSH-105-XX-X-DV; MPN `FTSH-105-01-L-DV-K`; Samtec; confidence: HIGH.
Footprint: `LoRa_Boat_Controller:SAMTEC_FTSH-105-XX-X-DV`. [Full BOM](../BOM.csv).

## Read before wiring

- Electrical pin numbers below come from v5 pstxnet.dat, not a physical left-to-right view. Board side, connector key, cable view, and pin-1 marking require physical verification. All voltages and waveforms are design/code expectations, not bench measurements.
- Raw Allegro pin numbers 01–10 are normalized to 1–10 here. Pin 7 is NC, pin 1 is +3V3, and pins 3/5/9 are GND.
- This follows the v5 debug connectivity. Physical keyed-header orientation remains unverified.

## Electrical pin map

| Pin | Readable net | Allegro net | MCU | Firmware role |
|---|---|---|---|---|
| 1 | +3V3 | 3.3V | U3-19 VDD; U3-32 VDD_2; U3-48 VDD_3; U3-64 VDD_4; U3-13 VDDA/VREF+ | Board supply / debug voltage reference |
| 2 | SWDIO | PA13 TMS | U3-46 PA13 | PA13 debug data |
| 3 | GND | 0 | U3-18 VSS; U3-31 VSS_2; U3-47 VSS_3; U3-63 VSS_4; U3-12 VSSA/VREF- | Common reference |
| 4 | SWCLK | PA14 TCLK | U3-49 PA14 | PA14 debug clock |
| 5 | GND | 0 | U3-18 VSS; U3-31 VSS_2; U3-47 VSS_3; U3-63 VSS_4; U3-12 VSSA/VREF- | Common reference |
| 6 | SWO_TDO | PB3 TBO | U3-55 PB3 | PB3 trace/JTAG output; usable debug mode must be confirmed |
| 7 | NC | NC | No direct MCU pin | No connection in v5 source |
| 8 | TDI | PA15 TDI | U3-50 PA15 | PA15 JTAG input; usable debug mode must be confirmed |
| 9 | GND | 0 | U3-18 VSS; U3-31 VSS_2; U3-47 VSS_3; U3-63 VSS_4; U3-12 VSSA/VREF- | Common reference |
| 10 | NRST | RESET | U3-7 NRST | MCU reset |

## Verification targets — not measured results

### Pin 1 — +3V3

**Domain:** 3.3 V nominal (unmeasured). **Direction:** Board rail; external powering unsupported until reviewed.

Measure rail relative to TP5 with loads disconnected after V1 power defects are reviewed.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:358](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L358); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:322](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L322); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:325](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L325); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:328](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L328); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:331](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L331); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:334](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L334); [docs/atlas/evidence/v1-netmap.json:2](../../docs/atlas/evidence/v1-netmap.json#L2).

### Pin 2 — SWDIO

**Domain:** Target +3V3 logic domain. **Direction:** Bidirectional debugger ↔ MCU.

Verify cable numbering against actual header view before debug attachment.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:421](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L421); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:418](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L418); [docs/atlas/evidence/v1-netmap.json:27](../../docs/atlas/evidence/v1-netmap.json#L27); [firmware/BoatTHISTIMEITSDIFFERENT.ioc:58](../../firmware/BoatTHISTIMEITSDIFFERENT.ioc#L58).

### Pin 3 — GND

**Domain:** 0 V reference (expected). **Direction:** Reference.

Unpowered continuity to GND1/TP5; resistance/continuity has not been measured.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:205](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L205); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:169](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L169); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:172](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L172); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:175](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L175); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:178](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L178); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:181](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L181); [docs/atlas/evidence/v1-netmap.json:3](../../docs/atlas/evidence/v1-netmap.json#L3).

### Pin 4 — SWCLK

**Domain:** Target +3V3 logic domain. **Direction:** Debugger → MCU.

Verify continuity pin 4 → U3-49; no successful programming session recorded here.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:431](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L431); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:428](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L428); [docs/atlas/evidence/v1-netmap.json:26](../../docs/atlas/evidence/v1-netmap.json#L26); [firmware/BoatTHISTIMEITSDIFFERENT.ioc:61](../../firmware/BoatTHISTIMEITSDIFFERENT.ioc#L61).

### Pin 5 — GND

**Domain:** 0 V reference (expected). **Direction:** Reference.

Unpowered continuity to GND1/TP5; resistance/continuity has not been measured.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:202](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L202); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:169](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L169); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:172](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L172); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:175](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L175); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:178](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L178); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:181](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L181); [docs/atlas/evidence/v1-netmap.json:3](../../docs/atlas/evidence/v1-netmap.json#L3).

### Pin 6 — SWO_TDO

**Domain:** Target +3V3 logic domain. **Direction:** MCU → debugger.

Verify trace/debug configuration before expecting SWO output.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:411](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L411); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:408](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L408); [docs/atlas/evidence/v1-netmap.json:28](../../docs/atlas/evidence/v1-netmap.json#L28).

### Pin 7 — NC

**Domain:** No defined voltage. **Direction:** None.

Do not treat NC as a common net; JTAG pin 7 is an individually unconnected pin.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:648](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L648).

### Pin 8 — TDI

**Domain:** Target +3V3 logic domain. **Direction:** Debugger → MCU.

Confirm chosen debug mode; SWD normally uses SWDIO/SWCLK instead.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:464](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L464); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:461](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L461); [docs/atlas/evidence/v1-netmap.json:30](../../docs/atlas/evidence/v1-netmap.json#L30).

### Pin 9 — GND

**Domain:** 0 V reference (expected). **Direction:** Reference.

Unpowered continuity to GND1/TP5; resistance/continuity has not been measured.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:199](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L199); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:169](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L169); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:172](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L172); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:175](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L175); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:178](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L178); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:181](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L181); [docs/atlas/evidence/v1-netmap.json:3](../../docs/atlas/evidence/v1-netmap.json#L3).

### Pin 10 — NRST

**Domain:** Reset domain; pull-up and waveform unmeasured. **Direction:** Debugger → MCU reset.

Verify reset pull network and observe reset release waveform.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:474](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L474); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:471](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L471); [docs/atlas/evidence/v1-netmap.json:23](../../docs/atlas/evidence/v1-netmap.json#L23).

[Atlas index and snapshot provenance](README.md) · [Schematic PDF](../img/v1_schematic.pdf) · [PCB top](../img/v1_pcb_top.png) · [PCB bottom](../img/v1_pcb_bottom.png)
