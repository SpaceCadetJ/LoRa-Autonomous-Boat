# TP3 — PC6 PWM

Test point on the source servo header signal, currently firmware thrust output.

Allegro reference **TP3** → KiCad reference **TP3**.

BOM: TP; MPN `not applicable (bare pad)`; no purchased component; confidence: TBD.
Footprint: `LoRa_Boat_Controller:amv_test_point`. [Full BOM](../BOM.csv).

## Read before wiring

- Electrical pin numbers below come from v5 pstxnet.dat, not a physical left-to-right view. Board side, connector key, cable view, and pin-1 marking require physical verification. All voltages and waveforms are design/code expectations, not bench measurements.
- V1 connector names conflict with firmware roles: SPEEDCONTROLLER pin 2 carries the firmware rudder waveform; STEERINGSERVO pin 2 carries the firmware thrust waveform. Treat both as electrical identities until harness labels and physical continuity are verified.

## Electrical pin map

| Pin | Readable net | Allegro net | MCU | Firmware role |
|---|---|---|---|---|
| 1 | PWM_PC6_SERVOHDR | N04395 | U3-37 PC6 | TIM3_CH1 / set_thrust(): 1000–2000 us; C startup 1000 us |

## Verification targets — not measured results

### Pin 1 — PWM_PC6_SERVOHDR

**Domain:** 3.3 V logic; load compatibility unverified. **Direction:** MCU → header / TP3.

Expected 50 Hz, 1000 us after C startup. CubeMX .ioc instead specifies 1500 us. Scope with actuators disconnected.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:270](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L270); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:276](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L276); [docs/atlas/evidence/v1-netmap.json:25](../../docs/atlas/evidence/v1-netmap.json#L25); [firmware/Core/Src/main.c:391](../../firmware/Core/Src/main.c#L391); [firmware/Core/Src/stm32f4xx_hal_msp.c:146](../../firmware/Core/Src/stm32f4xx_hal_msp.c#L146); [firmware/Core/Src/main.c:621](../../firmware/Core/Src/main.c#L621); [firmware/BoatTHISTIMEITSDIFFERENT.ioc:150](../../firmware/BoatTHISTIMEITSDIFFERENT.ioc#L150).

[Atlas index and snapshot provenance](README.md) · [Schematic PDF](../img/v1_schematic.pdf) · [PCB top](../img/v1_pcb_top.png) · [PCB bottom](../img/v1_pcb_bottom.png)
