# 6S power envelope and package review — 2026-10-12

**6S remains required. The present input circuit is not qualified for it.** This packet captures nine boundary nets and 24 references, adds three assembly findings and widens the ordering holds. It changes no electrical connections, copper, original BOM, V1 hardware or firmware. [Evidence](evidence.json) records hashes and reproducible calculations; [power map](v2_power_envelope.svg) shows existing courtyard bounds and explicitly proposed planning allowances. The previous [IMU2 circuit](../imu_bias_filter/README.md) remains the latest isolated IMU schematic.

## Envelope to design against

| Case | Requirement or assumption | Status / acceptance needed |
|---|---|---|
| Normal connector input | Existing REQ-PWR-01: 7–25.2 V, 2S–6S LiPo. 6 × 4.2 V = 25.2 V full-charge assumption. | Requirement retained; exact pack, charger tolerance and minimum loaded voltage unqualified. Do not use the older 7–25 V connector description as the maximum. |
| Current and output power | REQ-PWR-06 monitors up to 3 A; requirements decision 2 also says board ≤1 A. Existing 3.3 V/1.2 A and 5 V/2 A labels describe converter goals. ESC motor feed bypasses this board. | Resolve simultaneous radio/GNSS/IMU/servo demand and fuse derating. These are not three interchangeable continuous-current guarantees. |
| Hot plug, cable inductance, ESC regeneration and repetitive ripple | Positive pulse amplitude, duration, impedance, repetition and temperature have not been measured or specified. | No invented surge rating. Bound energy, local overshoot and every exposed pin before selecting a protection threshold. |
| Reverse input / disconnect | Existing requirement calls for 10 s reverse battery. Include charged downstream capacitors and USB/BEC connections. | Evaluate differential MOSFET stress, current paths and recovery. Do not perform this on an unqualified assembly. |
| Temperature / enclosure | Maximum ambient, PCB temperature and cooling remain unspecified. | Use worst-case component tolerances; no room-temperature calculation constitutes qualification. |

## Voltage boundary and limiting parts

Actual captured path: J1 → F1 → Q1 drain; Q1 source → VIN_RAW → R33 (20 mΩ) → VIN_BUCK. D1, C1/C2, R31 and U8 IN+ attach to VIN_RAW. U8 IN−, both converters, their enable pull-ups and C10 attach to VIN_BUCK. A cutoff only after the shunt leaves IN+ exposed. D1 is downstream of Q1 and cannot independently bound the connector-side voltage.

| References / exposure | Operating or component rating | Absolute limit / consequence |
|---|---|---|
| U8 IN+/IN− | INA180 common mode −0.2…26 V | −0.3…26 V absolute; only **0.8 V** above 25.2 V for all charge tolerance and overshoot. The 5 mA limited-input exception has no supporting circuit here. [TI SBOS741H, p. 7](https://www.ti.com/lit/ds/symlink/ina180.pdf#page=7). |
| U3 VIN / EN | TPS54202 VIN 4.5…28 V, EN −0.1…5.5 V | VIN 30 V, EN 7 V absolute. R6 alone does not bound EN. [TI SLVSD26C, p. 4](https://www.ti.com/lit/ds/symlink/tps54202.pdf#page=4). |
| U2 VIN / CE | R1240 VIN 4.5…30 V | VIN 32 V; CE −0.3…VIN+0.3 V absolute. R2 is a VIN pull-up. [Nisshinbo EA-190-240903, p. 4](https://www.nisshinbo-microdevices.co.jp/en/pdf/datasheet/r1240-ea.pdf#page=4). |
| Q1 drain/source/gate | AO3401A needs case-specific SOA/thermal review | VDS −30 V, VGS ±12 V. Normal conducting VDS is not battery voltage. Reverse battery with stored charge can be more severe than the pack alone. [AOS rev 3.1, pp. 1–4](https://www.aosmd.com/pdfs/datasheet/AO3401A.pdf). |
| D1 | SMAJ33A stand-off 33 V; breakdown 36.7–40.6 V | Rated clamp 53.3 V at 7.5 A, not an unconditional rail ceiling. The 400 W specification uses a 10/1000 µs pulse with temperature/mounting conditions. No fuse/pulse-energy coordination is established. [Littelfuse, rev 12/02/25, pp. 1–2](https://www.littelfuse.com/assetdocs/littelfuse_tvs_diode_smaj_datasheet?assetguid=13c2a823-03b8-4d1f-9ddc-9b44670aed9d). |
| D3 switch-node catch diode | CMS06 2 A subject to waveform/thermal conditions | 30 V repetitive reverse rating leaves switching overshoot unresolved. Include its low-temperature rating change and forward/reverse thermal losses. [Toshiba, 2026-04-07 pp. 1–2](https://toshiba.semicon-storage.com/info/docget.jsp?did=3138&prodName=CMS06). |
| C1 / C2 / C10 | Design specifies 50 V capacitors | A 53.3 V clamp point already exceeds this rating. C1's exact rating is manufacturer-confirmed; C2/C10 effective capacitance and exact-part qualification remain open. Hold all three pending the protection envelope. |
| D2 / R1 | Schematic: BZT52C10, 100 kΩ gate pull-down | D2's 9.4–10.6 V range is characterized at 5 mA; nominal gate-clamp current here is only 0.152 mA at 25.2 V. Establish actual static/dynamic bounds. [Diodes DS18004 p. 2](https://www.diodes.com/_files/datasheets/ds18004.pdf#page=2). |
| R31 / R32 / C36 / U1 PA2 | 47 kΩ / 6.8 kΩ divider | Assuming 1% resistors, maximum ratio produces 3.2412 V at 25.2 V and 3.3441 V at 26 V. Minimum VDDA, input injection during shutdown and transient protection remain unqualified. |
| R33 / L1 / L2 / C3 / remaining passives | Inventory records exact MPNs, pads and courtyards | At 3 A, nominal shunt drop 60 mV / loss 0.18 W. This does not qualify pulse energy, resistor working voltage, bootstrap differential voltage, effective capacitance, magnetic saturation or temperature. E-06 remains open. |
| J1 / F1 / TP5 | Connector, fuse and accessible raw rail | J1 mating/current derating and harness fault current unresolved; TP5 is raw battery, not a regulated test point. F1 findings below. |

Each table row is a component-limit comparison or an explicitly open review, not a complete validated input model. The [original six blockers](../design_completion/electrical/README.md) remain open.

## New assembly and ordering findings

- **PE-01, C1:** EEE-FK1H470P is 47 µF/50 V, **8.0 mm diameter × 6.2 mm body**, while schematic and PCB select `CP_Elec_6.3x7.7`. A matching-diameter study footprint is not yet a qualified solder land pattern. [Panasonic exact-part page](https://industrial.panasonic.com/jp/products/pt/aluminum-cap-smd/models/EEEFK1H470P).
- **PE-02, F1:** 0468003.NR belongs to the **1206 slow-blow** 468 series, not the stated fast-acting 1812 part. The 3 A row is **32 V**, with **50 A** interrupt rating at that voltage and nominal melting I²t **1.27 A²s**. Its 200% opening interval is 1–120 s. The manufacturer adds continuous-current and temperature derating; pack fault-current compatibility is not established. [Littelfuse 468, rev 11/24/22, pp. 1–3](https://www.littelfuse.com/assetdocs/fuse-468-datasheet?assetguid=6b7857dc-f79c-4aae-8bcc-a9ef11ddef09).
- **PE-03, D2:** native schematic value **10 V**, PCB value **12 V**. Resolve the MPN, value and assembly annotation together in a later explicit revision. This is recorded parity drift, not evidence of an installed diode.

D1 also embeds A1/A2 labels and bidirectional drawing semantics despite unidirectional SMAJ33A identity and a description assigning cathode to pad 1. Resolve symbol, actual diode polarity and assembly marking; do not infer reverse behavior from its positive clamp number.

Procurement policy now holds C1, C2, C10, F1, D2 and R1 for this review, in addition to earlier holds. Generated candidate exports remain partial review lists. No source BOM or component value is silently repaired, and no order is placed.

## Space budget before routing

Coordinates are global KiCad millimetres, board outline x=50…130 / y=50…96. Existing U2 courtyard is 3.860 × 2.509 mm, U3 4.150 × 3.450 mm, and each L1/L2 courtyard 7.050 × 6.550 mm. See [all 24 inventories](evidence.json) for pads, nets, locations and exact bounds.

The installed KiCad `CP_Elec_8x6.2` candidate has a **10.6 × 8.8 mm courtyard bounding box (93.28 mm²)** at C1=(57,80), versus 9.45 × 7.15 mm (67.5675 mm²) currently. Its bounding box overlaps no current courtyard. That says nothing about new pad routing, actual component tolerances, enclosure height or reflow suitability; C1 is still held and no footprint was changed.

For a concrete larger-converter comparison, TI's LMR36520 has 4.2–65 V operation, 70 V input absolute maximum and an **HSOIC-8 DDA 4.9 × 6 mm package including leads**. It is an exploration candidate, not a drop-in part or a selected power architecture. Its thermal pad, local bypass/inductor/feedback geometry and operating-mode choice require a new layout. [TI SNVSBF0C, pp. 1, 3–5, 27–29](https://www.ti.com/lit/ds/symlink/lmr36520.pdf).

The map therefore marks **proposed 10 × 10 mm planning boxes**, not manufacturer footprints, at each current buck centre. U2's box intersects R4/R2/D3/C1; U3's intersects L2/C36/C10/C7/R16/C24/R8/R6. These conservative bounding-box intersections demonstrate that converter expansion needs coordinated placement. They neither establish minimum required area nor reserve clear routing space. Old IMU-study obstacles still apply; do not spend the shared space twice.

## Decision and next smallest task

The present passive clamp plus low-voltage parts has no demonstrated 6S protection margin. Keep two architectures under consideration: a wider-voltage raw-side converter/sense/protection set, or an active cutoff with every vulnerable node inside its protected boundary. Retaining INA180 narrows cutoff tolerance plus delay/overshoot to the 0.8 V window; replacing or relocating sensing deserves evaluation. A cascaded 5 V-to-3.3 V arrangement also needs the combined load and startup budget, not reuse of the 5 V/2 A label.

**Next packet:** compare two complete power topologies with exact input/sense/enable/divider boundaries, candidate part limits and simultaneous load budget. Start from 7–25.2 V normal operation; explicitly parameterize unresolved surge/pack/environment conditions. Produce a proposed pin-delta contract and actual package/thermal placement budget before selecting one. Correct C1/F1/D2/D1 identity issues within that captured candidate, then native-export and compare it. Do not route final IMU2 against an undecided power region. Physical pack/BEC/radio identities and measured surge waveforms remain separate acceptance inputs; missing identities do not authorize a reduced cell count.

## Reproduce and review

Run `python reviews/codex/power_envelope/capture.py --check` from a checkout of this packet. It uses only the captured native netlist, hashed current CAD and existing geometry; no KiCad runtime or new ERC/DRC is required because the electrical delta is zero. `render_map.py` rebuilds the explanatory SVG. `tools/quality/check_publication.py` checks packet provenance and current ordering holds. New CAD revisions require a new capture rather than overwriting this evidence.

An independent read-only audit reconfirmed the five primary device limits and topology; root independently checked C1/F1/D2 identities and package constraints. No simulation or hardware measurement occurred. Hosted CI execution is not inferred from local checks. Live board SHA-256 remains `49a8aa88cf61e8b6272ce13a0d5a5a6a3c6b81aeba057ebcd4ca15a6262c37b2`. Preserve unrelated local `v1_design.py` and `route_v2.py` edits.
