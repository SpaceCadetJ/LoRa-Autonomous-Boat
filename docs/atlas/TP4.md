# TP4 — +3V3

Test point on the main 3.3 V rail.

Allegro reference **TP4** → KiCad reference **TP4**.

BOM: TP; MPN `not applicable (bare pad)`; no purchased component; confidence: TBD.
Footprint: `LoRa_Boat_Controller:amv_test_point`. [Full BOM](../BOM.csv).

## Read before wiring

- Electrical pin numbers below come from v5 pstxnet.dat, not a physical left-to-right view. Board side, connector key, cable view, and pin-1 marking require physical verification. All voltages and waveforms are design/code expectations, not bench measurements.
- Use TP5 as the source-defined reference. Bench rail tolerance/ripple has not been measured.

## Electrical pin map

| Pin | Readable net | Allegro net | MCU | Firmware role |
|---|---|---|---|---|
| 1 | +3V3 | 3.3V | U3-19 VDD; U3-32 VDD_2; U3-48 VDD_3; U3-64 VDD_4; U3-13 VDDA/VREF+ | Board supply / debug voltage reference |

## Verification targets — not measured results

### Pin 1 — +3V3

**Domain:** 3.3 V nominal (unmeasured). **Direction:** Board rail; external powering unsupported until reviewed.

Measure rail relative to TP5 with loads disconnected after V1 power defects are reviewed.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:313](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L313); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:322](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L322); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:325](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L325); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:328](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L328); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:331](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L331); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:334](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L334); [hardware/kicad/_build/netmap.json:2](../../hardware/kicad/_build/netmap.json#L2).

[Atlas index and snapshot provenance](README.md) · [Schematic PDF](../img/v1_schematic.pdf) · [PCB top](../img/v1_pcb_top.png) · [PCB bottom](../img/v1_pcb_bottom.png)
