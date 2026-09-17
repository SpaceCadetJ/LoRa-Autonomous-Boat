# TP5 — ground

Test point on common ground.

Allegro reference **TP5** → KiCad reference **TP5**.

BOM: TP; MPN `not applicable (bare pad)`; no purchased component; confidence: TBD.
Footprint: `LoRa_Boat_Controller:amv_test_point`. [Full BOM](../BOM.csv).

## Read before wiring

- Electrical pin numbers below come from v5 pstxnet.dat, not a physical left-to-right view. Board side, connector key, cable view, and pin-1 marking require physical verification. All voltages and waveforms are design/code expectations, not bench measurements.
- TP2 is absent from the v5 netlist and current BOM. Do not reuse the older documentation's ADC test-point claim.

## Electrical pin map

| Pin | Readable net | Allegro net | MCU | Firmware role |
|---|---|---|---|---|
| 1 | GND | 0 | U3-18 VSS; U3-31 VSS_2; U3-47 VSS_3; U3-63 VSS_4; U3-12 VSSA/VREF- | Common reference |

## Verification targets — not measured results

### Pin 1 — GND

**Domain:** 0 V reference (expected). **Direction:** Reference.

Unpowered continuity to GND1/TP5; resistance/continuity has not been measured.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:163](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L163); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:169](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L169); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:172](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L172); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:175](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L175); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:178](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L178); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:181](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L181); [hardware/kicad/_build/netmap.json:3](../../hardware/kicad/_build/netmap.json#L3).

[Atlas index and snapshot provenance](README.md) · [Schematic PDF](../img/v1_schematic.pdf) · [PCB top](../img/v1_pcb_top.png) · [PCB bottom](../img/v1_pcb_bottom.png)
