# SPEEDCONTROLLER header / firmware rudder

Source-named ESC header carries PA8/TIM1, currently assigned to rudder in firmware.

Allegro reference **SPEEDCONTROLLER** → KiCad reference **SPEEDCONTROLLER1**.

BOM: PPTC031LFBN-RC; MPN `PPTC031LFBN-RC`; Sullins Connector Solutions; confidence: HIGH.
Footprint: `LoRa_Boat_Controller:CONN_PPTC031_SUL`. [Full BOM](../BOM.csv).

## Read before wiring

- Electrical pin numbers below come from v5 pstxnet.dat, not a physical left-to-right view. Board side, connector key, cable view, and pin-1 marking require physical verification. All voltages and waveforms are design/code expectations, not bench measurements.
- V1 connector names conflict with firmware roles: SPEEDCONTROLLER pin 2 carries the firmware rudder waveform; STEERINGSERVO pin 2 carries the firmware thrust waveform. Treat both as electrical identities until harness labels and physical continuity are verified.
- Pin 1 is on the board +3V3 rail. ESC/BEC/servo external power compatibility and current budget are unverified; this is not a certified actuator power port.
- No link-loss failsafe exists in the reviewed C main loop; last command persists.

## Electrical pin map

| Pin | Readable net | Allegro net | MCU | Firmware role |
|---|---|---|---|---|
| 1 | +3V3 | 3.3V | U3-19 VDD; U3-32 VDD_2; U3-48 VDD_3; U3-64 VDD_4; U3-13 VDDA/VREF+ | Board supply / debug voltage reference |
| 2 | PWM_PA8_ESCHDR | N04355 | U3-41 PA8 | TIM1_CH1 / set_rudder(): 1100–1900 us; startup 1500 us |
| 3 | GND | 0 | U3-18 VSS; U3-31 VSS_2; U3-47 VSS_3; U3-63 VSS_4; U3-12 VSSA/VREF- | Common reference |

## Verification targets — not measured results

### Pin 1 — +3V3

**Domain:** 3.3 V nominal (unmeasured). **Direction:** Board rail; external powering unsupported until reviewed.

Measure rail relative to TP5 with loads disconnected after V1 power defects are reviewed.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:295](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L295); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:322](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L322); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:325](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L325); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:328](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L328); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:331](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L331); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:334](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L334); [hardware/kicad/_build/netmap.json:2](../../hardware/kicad/_build/netmap.json#L2).

### Pin 2 — PWM_PA8_ESCHDR

**Domain:** 3.3 V logic; load compatibility unverified. **Direction:** MCU → header / TP1.

Expected 50 Hz, 1500 us after startup; source name says ESC but firmware role is rudder. Scope with actuators disconnected.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:238](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L238); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:244](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L244); [hardware/kicad/_build/netmap.json:24](../../hardware/kicad/_build/netmap.json#L24); [firmware/Core/Src/main.c:407](../../firmware/Core/Src/main.c#L407); [firmware/Core/Src/stm32f4xx_hal_msp.c:125](../../firmware/Core/Src/stm32f4xx_hal_msp.c#L125); [firmware/Core/Src/main.c:570](../../firmware/Core/Src/main.c#L570).

### Pin 3 — GND

**Domain:** 0 V reference (expected). **Direction:** Reference.

Unpowered continuity to GND1/TP5; resistance/continuity has not been measured.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:115](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L115); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:169](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L169); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:172](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L172); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:175](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L175); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:178](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L178); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:181](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L181); [hardware/kicad/_build/netmap.json:3](../../hardware/kicad/_build/netmap.json#L3).

[Atlas index and snapshot provenance](README.md) · [Schematic PDF](../img/v1_schematic.pdf) · [PCB top](../img/v1_pcb_top.png) · [PCB bottom](../img/v1_pcb_bottom.png)
