# Battery positive

Single solder pad for raw input supply.

Allegro reference **VIN** → KiCad reference **VIN1**.

BOM: Battery+; MPN `not applicable (bare pad)`; no purchased component; confidence: n/a.
Footprint: `LoRa_Boat_Controller:amv_con1`. [Full BOM](../BOM.csv).

## Read before wiring

- Electrical pin numbers below come from v5 pstxnet.dat, not a physical left-to-right view. Board side, connector key, cable view, and pin-1 marking require physical verification. All voltages and waveforms are design/code expectations, not bench measurements.
- The input voltage/current envelope is not established by this source reconstruction. Identify battery and protection first.

## Electrical pin map

| Pin | Readable net | Allegro net | MCU | Firmware role |
|---|---|---|---|---|
| 1 | VIN_RAW | N088060 | No direct MCU pin | Battery input to buck converter and R5/R6 divider; ADC not initialized |

## Verification targets — not measured results

### Pin 1 — VIN_RAW

**Domain:** Battery specification and safe board operating envelope unresolved. **Direction:** Battery/external supply → board.

Identify battery and input protection; regulator rating alone does not establish safe board input voltage.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:251](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L251); [docs/atlas/evidence/v1-netmap.json:33](../../docs/atlas/evidence/v1-netmap.json#L33); [firmware/Core/Src/main.c:428](../../firmware/Core/Src/main.c#L428).

[Atlas index and snapshot provenance](README.md) · [Schematic PDF](../img/v1_schematic.pdf) · [PCB top](../img/v1_pcb_top.png) · [PCB bottom](../img/v1_pcb_bottom.png)
