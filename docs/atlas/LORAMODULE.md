# LoRa module

Five-pin serial radio interface; the BOM identifies the socket, not the fitted radio module.

Allegro reference **LORAMODULE** → KiCad reference **LORAMODULE1**.

BOM: PPTC051LFBN-RC; MPN `PPTC051LFBN-RC`; Sullins Connector Solutions; confidence: HIGH.
Footprint: `LoRa_Boat_Controller:CONN5_1LFBN-RC_SUL`. [Full BOM](../BOM.csv).

## Read before wiring

- Electrical pin numbers below come from v5 pstxnet.dat, not a physical left-to-right view. Board side, connector key, cable view, and pin-1 marking require physical verification. All voltages and waveforms are design/code expectations, not bench measurements.
- Installed RYLR model remains unconfirmed. Capture identification and accepted AT settings before using performance estimates.
- No LoRa reset GPIO setup appears in the current source. Legacy command reception has no link-loss timeout.

## Electrical pin map

| Pin | Readable net | Allegro net | MCU | Firmware role |
|---|---|---|---|---|
| 1 | LORA_VCC | N04429 | No direct MCU pin | LoRa supply through L3 |
| 2 | LORA_TX_PA0 | N04477 | U3-14 PA0 | UART4 TX; AT commands at 115200 baud, 8N1 |
| 3 | LORA_RX_PA1 | N04485 | U3-15 PA1 | UART4 RX; +RCV line parser |
| 4 | LORA_RST_PA3 | N24517 | U3-17 PA3 | Wired to PA3; no PA3 reset GPIO configuration in this firmware snapshot |
| 5 | GND | 0 | U3-18 VSS; U3-31 VSS_2; U3-47 VSS_3; U3-63 VSS_4; U3-12 VSSA/VREF- | Common reference |

## Verification targets — not measured results

### Pin 1 — LORA_VCC

**Domain:** Derived from +3V3; actual voltage unmeasured. **Direction:** Board → module supply.

Unpowered continuity through L3 to +3V3; identify module before powering.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:27](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L27); [hardware/kicad/_build/netmap.json:22](../../hardware/kicad/_build/netmap.json#L22).

### Pin 2 — LORA_TX_PA0

**Domain:** 3.3 V logic domain; module tolerance unverified. **Direction:** MCU → LoRa RX.

Logic analyzer: expect AT commands at startup. Read module replies to establish accepted settings.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:96](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L96); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:99](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L99); [hardware/kicad/_build/netmap.json:21](../../hardware/kicad/_build/netmap.json#L21); [firmware/Core/Src/main.c:639](../../firmware/Core/Src/main.c#L639); [firmware/Core/Src/stm32f4xx_hal_msp.c:213](../../firmware/Core/Src/stm32f4xx_hal_msp.c#L213).

### Pin 3 — LORA_RX_PA1

**Domain:** Module TX level must be verified. **Direction:** LoRa TX → MCU.

Capture startup replies and +RCV traffic at 115200 baud, 8N1; no capture exists in this atlas.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:17](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L17); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:20](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L20); [hardware/kicad/_build/netmap.json:20](../../hardware/kicad/_build/netmap.json#L20); [firmware/Core/Src/main.c:639](../../firmware/Core/Src/main.c#L639); [firmware/Core/Src/main.c:294](../../firmware/Core/Src/main.c#L294); [firmware/Core/Src/stm32f4xx_hal_msp.c:214](../../firmware/Core/Src/stm32f4xx_hal_msp.c#L214).

### Pin 4 — LORA_RST_PA3

**Domain:** Reset polarity/level needs module identification. **Direction:** Intended MCU → module reset; unconfigured.

Confirm module reset pin and pull network; do not assume this firmware can reset the radio.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:375](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L375); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:378](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L378); [hardware/kicad/_build/netmap.json:19](../../hardware/kicad/_build/netmap.json#L19); [firmware/Core/Src/main.c:678](../../firmware/Core/Src/main.c#L678).

### Pin 5 — GND

**Domain:** 0 V reference (expected). **Direction:** Reference.

Unpowered continuity to GND1/TP5; resistance/continuity has not been measured.

Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:124](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L124); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:169](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L169); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:172](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L172); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:175](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L175); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:178](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L178); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:181](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L181); [hardware/kicad/_build/netmap.json:3](../../hardware/kicad/_build/netmap.json#L3).

[Atlas index and snapshot provenance](README.md) · [Schematic PDF](../img/v1_schematic.pdf) · [PCB top](../img/v1_pcb_top.png) · [PCB bottom](../img/v1_pcb_bottom.png)
