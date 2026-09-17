# GPS module

Five-pin GPS socket with USART3 and an extra PB0 signal.

Allegro reference **GPSMODULE** → KiCad reference **GPSMODULE1**.

BOM: PPTC051LFBN-RC; MPN `PPTC051LFBN-RC`; Sullins Connector Solutions; confidence: HIGH.
Footprint: `LoRa_Boat_Controller:CONN5_1LFBN-RC_SUL`. [Full BOM](../BOM.csv).

## Read before wiring

- Electrical pin numbers below come from v5 pstxnet.dat, not a physical left-to-right view. Board side, connector key, cable view, and pin-1 marking require physical verification. All voltages and waveforms are design/code expectations, not bench measurements.
- The BOM identifies the socket, not the GPS module. PB0/pin 3 is actively driven LOW by firmware.
- USART3 TX also carries debug output; assess its effect on the selected GPS module.

## Electrical pin map

| Pin | Readable net | Allegro net | MCU | Firmware role |
|---|---|---|---|---|
| 1 | +3V3 | 3.3V | U3-19 VDD; U3-32 VDD_2; U3-48 VDD_3; U3-64 VDD_4; U3-13 VDDA/VREF+ | Board supply / debug voltage reference |
| 2 | GND | 0 | U3-18 VSS; U3-31 VSS_2; U3-47 VSS_3; U3-63 VSS_4; U3-12 VSSA/VREF- | Common reference |
| 3 | GPS_PB0 | N04277 | U3-26 PB0 | PB0 is a push-pull output held LOW, described as debug LED/probe |
| 4 | GPS_RX_PC11 | N04281 | U3-52 PC11 | USART3 RX; $GPRMC/$GNRMC parsing at 9600 baud, 8N1 |
| 5 | GPS_TX_PC10 | N04285 | U3-51 PC10 | USART3 TX; debug strings share the GPS UART |

## Verification targets — not measured results

### Pin 1 — +3V3

**Domain:** 3.3 V nominal (unmeasured). **Direction:** Board rail; external powering unsupported until reviewed.

Measure rail relative to TP5 with loads disconnected after V1 power defects are reviewed.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:286](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L286); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:322](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L322); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:325](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L325); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:328](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L328); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:331](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L331); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:334](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L334); [hardware/kicad/_build/netmap.json:2](../../hardware/kicad/_build/netmap.json#L2).

### Pin 2 — GND

**Domain:** 0 V reference (expected). **Direction:** Reference.

Unpowered continuity to GND1/TP5; resistance/continuity has not been measured.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:109](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L109); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:169](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L169); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:172](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L172); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:175](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L175); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:178](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L178); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:181](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L181); [hardware/kicad/_build/netmap.json:3](../../hardware/kicad/_build/netmap.json#L3).

### Pin 3 — GPS_PB0

**Domain:** 0 V expected after GPIO init (unmeasured). **Direction:** MCU → attached GPS pin 3; external function unknown.

Identify GPS module pin 3 before attachment; possible output contention if that module drives this pin.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:46](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L46); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:49](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L49); [hardware/kicad/_build/netmap.json:15](../../hardware/kicad/_build/netmap.json#L15); [firmware/Core/Src/main.c:688](../../firmware/Core/Src/main.c#L688).

### Pin 4 — GPS_RX_PC11

**Domain:** GPS TX level unverified. **Direction:** GPS TX → MCU.

Capture NMEA lines and verify actual GPS baud rate/logic levels.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:218](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L218); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:221](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L221); [hardware/kicad/_build/netmap.json:16](../../hardware/kicad/_build/netmap.json#L16); [firmware/Core/Src/main.c:660](../../firmware/Core/Src/main.c#L660); [firmware/Core/Src/stm32f4xx_hal_msp.c:241](../../firmware/Core/Src/stm32f4xx_hal_msp.c#L241).

### Pin 5 — GPS_TX_PC10

**Domain:** 3.3 V logic domain; module tolerance unverified. **Direction:** MCU → GPS RX.

Capture transmitted debug text; determine whether the connected GPS interprets or rejects it.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:228](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L228); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:231](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L231); [hardware/kicad/_build/netmap.json:17](../../hardware/kicad/_build/netmap.json#L17); [firmware/Core/Src/main.c:171](../../firmware/Core/Src/main.c#L171); [firmware/Core/Src/stm32f4xx_hal_msp.c:240](../../firmware/Core/Src/stm32f4xx_hal_msp.c#L240).

[Atlas index and snapshot provenance](README.md) · [Schematic PDF](../img/v1_schematic.pdf) · [PCB top](../img/v1_pcb_top.png) · [PCB bottom](../img/v1_pcb_bottom.png)
