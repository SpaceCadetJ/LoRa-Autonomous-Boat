# V1 connector atlas

This atlas connects the authoritative v5 electrical netlist to preserved V1 KiCad net evidence and the repository BOM and firmware. It is a wiring/review aid for the faithful V1 reconstruction, not a corrected V2 hardware release or a bench sign-off.

Electrical pin numbers below come from v5 pstxnet.dat, not a physical left-to-right view. Board side, connector key, cable view, and pin-1 marking require physical verification. All voltages and waveforms are design/code expectations, not bench measurements.

## Navigate

| Connector / test point | Allegro reference | KiCad reference | Pins |
|---|---|---|---|
| [LoRa module](LORAMODULE.md) | LORAMODULE | LORAMODULE1 | 5 |
| [GPS module](GPSMODULE.md) | GPSMODULE | GPSMODULE1 | 5 |
| [SPEEDCONTROLLER header / firmware rudder](SPEEDCONTROLLER.md) | SPEEDCONTROLLER | SPEEDCONTROLLER1 | 3 |
| [STEERINGSERVO header / firmware thrust](STEERINGSERVO.md) | STEERINGSERVO | STEERINGSERVO1 | 3 |
| [CAN bus](CANHEADER.md) | CANHEADER | CANHEADER1 | 4 |
| [Debug / JTAG](JTAG.md) | JTAG | JTAG1 | 10 |
| [Battery positive](VIN.md) | VIN | VIN1 | 1 |
| [Battery ground](GND.md) | GND | GND1 | 1 |
| [TP1 — PA8 PWM](TP1.md) | TP1 | TP1 | 1 |
| [TP3 — PC6 PWM](TP3.md) | TP3 | TP3 | 1 |
| [TP4 — +3V3](TP4.md) | TP4 | TP4 | 1 |
| [TP5 — ground](TP5.md) | TP5 | TP5 | 1 |

[Full BOM](../BOM.csv) · [Schematic PDF](../img/v1_schematic.pdf) · [PCB top](../img/v1_pcb_top.png) · [PCB bottom](../img/v1_pcb_bottom.png) · [Viewer JSON](../../pm/data/connectors.json)

## Known V1 issues that affect connection decisions

- **Actuator mapping:** V1 connector names conflict with firmware roles: SPEEDCONTROLLER pin 2 carries the firmware rudder waveform; STEERINGSERVO pin 2 carries the firmware thrust waveform. Treat both as electrical identities until harness labels and physical continuity are verified. Evidence: [firmware/Core/Src/main.c:15](../../firmware/Core/Src/main.c#L15); both PWM connector tables provide pin-level source links.
- **Link loss:** reviewed C has one HAL_GetTick use, for outgoing telemetry; its main loop has no command-age timeout. Last actuator command is retained. Evidence: [firmware/Core/Src/main.c:487](../../firmware/Core/Src/main.c#L487); [firmware/Core/Src/main.c:384](../../firmware/Core/Src/main.c#L384).
- **Regeneration hazard:** C initializes TIM3 at 1000 us; CubeMX stores 1500 us. Evidence: [firmware/Core/Src/main.c:621](../../firmware/Core/Src/main.c#L621); [firmware/BoatTHISTIMEITSDIFFERENT.ioc:150](../../firmware/BoatTHISTIMEITSDIFFERENT.ioc#L150).
- **GPS pin 3:** PB0 is driven LOW; its attached module function is unidentified. Debug text also uses GPS TX. Evidence: [firmware/Core/Src/main.c:688](../../firmware/Core/Src/main.c#L688); [firmware/Core/Src/main.c:171](../../firmware/Core/Src/main.c#L171).
- **CAN routing:** U5 RXD connects to PA10, which lacks a CAN alternate function; STB connects to PA11. The TCAN1042H requires 4.5–5.5 V on CAN_VCC. Source evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:59](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L59); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:89](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L89); [ST pin/alternate-function tables](https://www.st.com/resource/en/datasheet/stm32f446re.pdf); [TI pin table and operating conditions](https://www.ti.com/lit/ds/symlink/tcan1042h-q1.pdf). No operational CAN stack is present in this firmware snapshot.
- **Power and boot:** CEXT connects VCAP1 to the +3V3 net, not ground. BOOT0 is listed NC; VBAT is a singleton. These source facts need an electrical correction decision before treating a reconstructed board as ready to power. Evidence: [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:337](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L337); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:365](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L365); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:642](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L642); [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat:478](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat#L478); [ST MCU supply requirements](https://www.st.com/resource/en/datasheet/stm32f446re.pdf).
- **External power:** ESC and servo header pin 1 are both on +3V3. Exact loads, BEC wiring, regulator thermal margin, and connector orientation are not verified by this atlas.
- **Historical tables:** older DSN-derived documentation contained incorrect V5 CAN/debug pin tables and TP2. This atlas extracts v5 directly; docs/NETLIST.md is maintained separately by the primary agent and is not an input. TP2 is absent from both v5 source and the current BOM.

## Reproduce and refresh

Run `python docs/atlas/generate_atlas.py` from the repository (or use the installed KiCad Python executable). Run with `--check` to compare outputs with the same source snapshot without writing. Only Python's standard library is required.

The generator parses every v5 net/node, preserves Allegro reference and raw pin identifiers, maps readable nets using the preserved V1 KiCad netmap, obtains KiCad references from the BOM, and compares each connected atlas pin's entire source net membership with the preserved exported KiCad XML. NC is never treated as an electrical net. Reviewed firmware assertions cause generation to stop if key behavior changes. Full source SHA-256 hashes and byte sizes are stored in the JSON; inputs are rehashed before outputs are written to detect concurrent edits.

[Preserved evidence and provenance](evidence/README.md) replace the original ignored build paths. These byte-identical snapshots are the evidence used by the original atlas, not newly generated CAD results. The generator verifies their recorded hashes before parsing and never reads hardware/kicad/_build. Commit the evidence directory along with the atlas so a clean checkout needs only Python and the repository files. Every pin evidence path is checked for existence and a valid line number.

Run `python docs/atlas/check_portability.py` to verify a source-only checkout copy with no ignored build directory or CAD tools. It also checks that altered snapshot bytes are rejected. The temporary copy is created and cleaned inside docs/atlas; original inputs remain untouched.

A successful atlas check proves repeatable extraction and agreement with that exported XML snapshot. It does not independently validate the current CAD copper, a stale XML export, a physical board, firmware build/flash results, or external harnesses. Root S2 validation owns CAD equivalence checks. Manufacturer links were checked on 2026-09-17; local datasheet research remains a separately authored review input.

Before adaptation: identify fitted radio/GPS and actuator hardware, resolve the power/boot/CAN defects, label the actual harness, scope unloaded PWM, add/test command failsafe, then perform documented bench bring-up. Voice, text, and location handheld requirements are a future platform requirement, not implemented on these connectors.

## Input snapshot

| Input | SHA-256 |
|---|---|
| [Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat](../../Allegro/hardware/allegro-original/Allegro%20v5/Allegro/pstxnet.dat) | `b88c36244bb3e3eb4d10712ce8ca39ddb5908e2c3225aa187155f9f4dca6b02c` |
| [docs/atlas/evidence/v1-netmap.json](../../docs/atlas/evidence/v1-netmap.json) | `b9f5502f8c0e06aab989e1558b25aba334c8a6395102dbcc328f358ce43b54e9` |
| [docs/BOM.csv](../../docs/BOM.csv) | `71f589596007465f98d433cfb7af735b766a5905f74390a73a25d3e1aa0b3efb` |
| [docs/atlas/evidence/v1-netlist.xml](../../docs/atlas/evidence/v1-netlist.xml) | `d16588c8f579a2a2324b6d6d940b7e0dc2e861f66a75ea191dab4e3c3811a68a` |
| [firmware/Core/Src/main.c](../../firmware/Core/Src/main.c) | `088bc6e61b8865e1bbf5c8a585cb8524134d418db22926f306627440957d495a` |
| [firmware/Core/Src/stm32f4xx_hal_msp.c](../../firmware/Core/Src/stm32f4xx_hal_msp.c) | `180c6eefe84d1e58d7f01f635faad358ccc64a3848e0ff2e3f9d700e2d45a1c0` |
| [firmware/BoatTHISTIMEITSDIFFERENT.ioc](../../firmware/BoatTHISTIMEITSDIFFERENT.ioc) | `eb9df4055fe4f072996c6a92f7b4fc9039c39f28451d9eefeb3bc702370a0579` |
| [docs/research/DATASHEET_NOTES.md](../../docs/research/DATASHEET_NOTES.md) | `b5171f1d3963c6c293c95935485ca9cab86cb0385e6a2174726a99ca3bb73a3d` |
| [docs/atlas/evidence/provenance.json](../../docs/atlas/evidence/provenance.json) | `54ffc1f10921b790befc9e86b5634882c468f675fbe0695ad17591fa26e164f1` |
| [docs/atlas/generate_atlas.py](../../docs/atlas/generate_atlas.py) | `56ff3a3e144c72c134bfc5ebf2e7c1f22bdb9079686aab257e96825e47701158` |
