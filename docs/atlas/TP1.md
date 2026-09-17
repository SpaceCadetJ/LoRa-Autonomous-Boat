# TP1 — PA8 PWM

Test point on the source ESC header signal, currently firmware rudder output.

Allegro reference **TP1** → KiCad reference **TP1**.

BOM: TP; MPN `not applicable (bare pad)`; no purchased component; confidence: TBD.
Footprint: `LoRa_Boat_Controller:amv_test_point`. [Full BOM](../BOM.csv).

## Read before wiring

- Electrical pin numbers below come from v5 pstxnet.dat, not a physical left-to-right view. Board side, connector key, cable view, and pin-1 marking require physical verification. All voltages and waveforms are design/code expectations, not bench measurements.
- V1 connector names conflict with firmware roles: SPEEDCONTROLLER pin 2 carries the firmware rudder waveform; STEERINGSERVO pin 2 carries the firmware thrust waveform. Treat both as electrical identities until harness labels and physical continuity are verified.

## Electrical pin map

| Pin | Readable net | Allegro net | MCU | Firmware role |
|---|---|---|---|---|
| 1 | PWM_PA8_ESCHDR | N04355 | U3-41 PA8 | TIM1_CH1 / set_rudder(): 1100–1900 us; startup 1500 us |

## Verification targets — not measured results

### Pin 1 — PWM_PA8_ESCHDR

**Domain:** 3.3 V logic; load compatibility unverified. **Direction:** MCU → header / TP1.

Expected 50 Hz, 1500 us after startup; source name says ESC but firmware role is rudder. Scope with actuators disconnected.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:241](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L241); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:244](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L244); [docs/atlas/evidence/v1-netmap.json:24](../../docs/atlas/evidence/v1-netmap.json#L24); [firmware/Core/Src/main.c:407](../../firmware/Core/Src/main.c#L407); [firmware/Core/Src/stm32f4xx_hal_msp.c:125](../../firmware/Core/Src/stm32f4xx_hal_msp.c#L125); [firmware/Core/Src/main.c:570](../../firmware/Core/Src/main.c#L570).

[Atlas index and snapshot provenance](README.md) · [Schematic PDF](../img/v1_schematic.pdf) · [PCB top](../img/v1_pcb_top.png) · [PCB bottom](../img/v1_pcb_bottom.png)
