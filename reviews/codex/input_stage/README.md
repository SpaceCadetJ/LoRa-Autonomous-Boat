# INPUT-A1: isolated 6S input-stage schematic — 2026-10-12

**A concrete, wired input-stage candidate is available for review.** It replaces the old P-channel MOSFET/gate-zener circuit with a fuse, a bidirectional TVS and a 100 V series Schottky diode. Open the [native schematic drawing](v2_input_stage.svg), [editable project](source/hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_pro), [pin-delta evidence](validation.json) and [candidate part inventory](candidate_parts.json).

This is an isolated copy of the published live design at `8f58ae6d8939e483d45b89631e2a3b1c01771291`, with the corrected PCB preserved outside the candidate. It is **not a power-ready or fabrication-ready board**. The old downstream buck, sense/ADC, buffer and IMU circuits remain in the copy for a precise comparison. They must be corrected before powered bring-up. The separate [IMU2 candidate](../imu_bias_filter/README.md) has not been merged into this input-stage copy. Live CAD, PCB copper, purchasing, firmware and V1/Allegro evidence remain unchanged.

## Circuit and intended delta

The new PowerInput sheet shows an explicit wired path:

`J1.1 → F1 → VBAT_FUSED → D12 anode → D12 cathode → VIN_RAW → existing shunt / future converters`

D1 clamps VBAT_FUSED to GND **before** the reverse diode. C1 and C2 sit after D12. Bidirectional D1 does not intentionally short a reversed 25.2 V pack; D12 blocks the reversed input subject to its leakage and voltage/thermal qualification. Its cathode band must face VIN_RAW. J1.2 is return; the motor feed stays external.

| Change | Expected and native-verified result |
|---|---|
| Remove Q1, D2 and R1 | Seven physical pins removed; old PGATE net disappears |
| Add D12 | Pin 1 = K / VIN_RAW; pin 2 = A / fused input |
| Move D1.1 | VIN_RAW → `/PowerInput/VBAT_FUSED`; D1.2 remains GND |
| Move J1/F1 to new sheet | Three local-name changes on J1.1, F1.1 and F1.2; physical path intent retained |
| Replace F1/D1/C1/C2 identities | Exact candidate values, MPNs, symbols and footprints enforced by the verifier |
| Preserve the rest | All 344 outside-boundary pin memberships unchanged; 350 retained memberships unchanged in total |

Native totals change from **114 components / 361 pins to 112 / 356**. ERC reports **zero errors and the original AD0 warning**, with no new finding. The verifier checks actual exported pin memberships and rejects reversed D12, misplaced D1, identity drift, missing/duplicate pins and unrelated rewiring. Fourteen acceptance/rejection tests pass. These results establish the schematic delta, not device-rating or physical acceptance.

The old 49-object input panel is removed from the copied Power sheet. Its downstream objects and the five other subsystem sheets are retained; the root gains sheet 8. No primary CAD generator or router runs. The [build manifest](build_manifest.json) records the expected delta before export; [native manifest](native_manifest.json) records captured inputs, commands, KiCad version and output hashes.

## Exact candidate parts — every selection remains held

| Ref | Candidate identity | Relevant source facts and unresolved work |
|---|---|---|
| F1 | Littelfuse **0451002.MRL**, 2 A / 125 V, 451 series | Very fast acting; nominal 36.7 mΩ and 0.530 A²s at 8 ms. Interrupt ratings have distinct conditions: 50 A at 125 VAC/DC, 300 A at 32 VDC, 10 kA at 75 VDC. Apply 25% continuous derating plus temperature curve. This fuse does not limit current to 1 A. [Littelfuse, 2025-12-01, pp. 2–4](https://www.littelfuse.com/assetdocs/fuse-451-and-453-datasheet?assetguid=533cd5cc-956c-4243-867f-6ab5a62f6ba1). |
| D1 | Littelfuse **SMBJ26CA**, bidirectional SMB | 26 V standoff; published 42.1 V clamp at 14.3 A for the specified pulse conditions. Temperature, pulse shape, source energy and wiring overshoot are still open. [SMBJ series, electrical table](https://m.littelfuse.com/~/media/electronics/datasheets/tvs_diodes/littelfuse_tvs_diode_smbj_datasheet.pdf.pdf). |
| D12 | ST **STPS3H100U**, SMB | 100 V reverse rating; 3 A average rating depends on lead temperature. The manufacturer loss equation gives 0.627 W at 1 A DC. Its 0.84 V maximum at 3 A/25°C is not a guaranteed cold-temperature drop. Reverse leakage and thermal behavior require review. [ST DS6597 Rev. 3, pp. 2, 6, 9](https://www.st.com/resource/en/datasheet/stps3h100.pdf). |
| C1 | Panasonic **EEEFK1J470P**, 47 µF / 63 V | Polarized, ±20%; 8 mm diameter and 10.2 mm nominal body length; 250 mA ripple rating at 100 kHz. The copied 8 × 10.5 footprint is a library candidate, not a manufacturer land-pattern approval. [Panasonic specifications](https://industrial.panasonic.com/tw/products/pt/aluminum-cap-smd/models/EEEFK1J470P). |
| C2 | Murata **GRM32ER72A105KA01L**, 1 µF / 100 V | X7R, ±10%, 1210. This replaces the old nominal 10 µF / 50 V selection. Effective capacitance and each future converter's local input bypass must be qualified; the nominal value does not settle that design. [Murata reference sheet](https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GRM32ER72A105KA01-01A.pdf). |
| J1 | Existing **XT30PW-M** | Reference, electrical numbering and connector footprint retained. Physical cable orientation and branch current remain unverified. |

The inventory is for review, not supplier import or an approved order. Live V2 purchasing remains **69 candidate / 38 held / 11 feature references**, with 36 candidate order lines. No hold is cleared by this schematic.

## Why use a diode for this first variant?

The [previous comparison](../power_topology/README.md) screened LM74700. A lower-clamping TVS improves the single-pulse arithmetic: 25.2 V stored output plus a −42.1 V pulse gives 67.3 V differential. However, a preceding positive pulse can leave approximately 42.1 V on the output; the following negative pulse then gives **84.2 V**, exceeding the controller's 75 V absolute differential limit. A 100 V MOSFET does not fix the controller. [TI SNOSD17G, pp. 5, 17](https://www.ti.com/lit/ds/symlink/lm74700-q1.pdf).

INPUT-A1 therefore uses the series diode for the first ≤1 A external-BEC study. This trades conduction loss for a simpler reverse-blocking boundary. It is not a waiver of the 6S requirement or optional on-board actuator supply. The high-load variant remains open; an efficient active path can be reconsidered with a complete bidirectional/stored-energy specification.

## Explicit qualification envelope

These are **requirements to demonstrate**, not protection already guaranteed by D1:

- Normal battery: 7–25.2 V. Do not apply sustained overvoltage as if a TVS were a regulator.
- During qualified pulses, VBAT_FUSED must remain within **±44 V**, including temperature and overshoot. Stored VIN_RAW must remain at or below **44 V**, including overshoot/backfeed. Then D12 reverse stress is bounded by 88 V, leaving 12 V below its rating. The gap from the published 42.1 V clamp point to 44 V is only 1.9 V; no hot-clamp guarantee is inferred.
- Define waveform, source impedance, repetition, starting temperatures and output charge before calculating TVS energy or fuse coordination. A fuse's nominal melting integral is not a guaranteed clearing/protection bound.
- Check discharged-output reversal: diode leakage can draw an unloaded output negative. Do not claim a non-negative VIN_RAW or protected downstream pins without a measured/modelled discharge and clamp disposition. Also verify capacitor inrush, hot-plug ringing, minimum-input drop and externally driven output cases.
- Preserve the 1 A board-feed planning goal. The prior calculator excludes this diode's loss; do not treat its earlier values as the revised total input demand. The simultaneous 1.2 A logic / 2 A servo rail goals still cannot be promised at 7 V through a 1 A feed.

## Package and thermal budget

[Captured native footprint data](package_budget.json) lists pad numbers and courtyard rectangles for F1/D1/D12/C1/C2. Their summed library rectangles occupy **221.33 mm²**; this is not occupied board area or a placement proof. J1, clearance between parts, TVS loop geometry, routing, heat-spreading copper and both future converters are excluded. Generic SMB lands differ from ST's example; manufacturer land/stencil reconciliation remains held. Diode pad 1 is the marked cathode; the nonpolar TVS uses the same geometry without functional polarity.

As an explicit planning example, 1 A DC and ST's 0.627 W loss equation, with assumed 60°C ambient and a chosen 125°C junction target, require total thermal resistance no greater than **103.7°C/W**. No measured board thermal resistance is available. Local copper, neighboring converters, enclosure and pulse loading must determine the actual result. No fit or thermal release is claimed.

## Reproduce, then continue

1. `python -B reviews/codex/input_stage/build_candidate.py` copies verified captured inputs and builds only the isolated sheet amendment. Live CAD hashes are guarded.
2. With KiCad 9.0.7 available, run `export_native.py` using its recorded CLI path (adjust for the host); CairoSVG makes the review PNGs. It captures netlist/ERC/SVG only, not routing.
3. `python -B reviews/codex/input_stage/verify_candidate.py --check` verifies the captured native delta. `python -B reviews/codex/input_stage/test_candidate.py` exercises fourteen mutation cases without KiCad.
4. Inspect the root, Power and PowerInput drawings plus [review notes](review_notes.json). The [packet manifest](packet_manifest.json) ties source, drawing, validation and preservation hashes together.

**Next smallest implementation task:** resolve discharged-output reverse leakage with an explicit negative-output clamp or alternative circuit, against the future converter/sense pin limits; record a native amendment and temperature/leakage bound. Then replace the isolated 3.3 V buck cell with the wider-voltage candidate from the topology study, including exact magnetics, enable/feedback/bootstrap/bypass values and an explicit native pin delta. Preserve INPUT-A1 and every unrelated connection. Then implement the 5 V cell, raw-side current sensing/ADC protection and buffer supply; integrate IMU2 only after their package/routing budget is known. Keep pulse-energy and thermal qualification open alongside that work. Leakage is a circuit-design gate, not just a deferred measurement.

V1 inspection, vehicle-node development and future handheld hardware remain distinct. Voice, text and location are still required for the handheld; measure voice/RC coexistence before selecting that hardware. No powering, flashing, ordering or hosted CI success is claimed here.
