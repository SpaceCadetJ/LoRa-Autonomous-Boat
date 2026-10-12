# Nonpolar reservoir and local buck bypass — 2026-10-12

**The next power revision has a concrete capacitor-network proposal and a dimension-checked footprint. Effective capacitance and source damping remain qualification gates.** Open the [annotated connection drawing](v2_input_capacitors.svg) and [interactive design review](index.html). This packet changes no live or candidate schematic, PCB, BOM or firmware. INPUT-A1 and IMU2 remain separate preserved evidence; no new ERC/DRC result is claimed.

## Selected screening configuration

Use two **TDK C5750X7S2A106K230KB** devices as the nonpolar reservoir candidate, and a separate pair beside the first **LMR36520ADDAR**. Each is nominally 10 µF / 100 V, ±10%, X7S, 2220. The manufacturer lists production status; no stock, price or procurement approval is inferred. These are commercial parts, not AEC-Q200-qualified. [Exact TDK part](https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C5750X7S2A106K230KB).

| Proposed site / purpose | Connection contract | Qualification status |
|---|---|---|
| CBULK-A/B: 2 × 10 µF nonpolar | Each terminal 1 to VIN_RAW, terminal 2 to GND; replace polarized C1 only in a future amendment | 20 µF nominal is not 20 µF effective or an equivalent 47 µF reservoir |
| Existing C2: 1 µF / 100 V | Preserve VIN_RAW–GND | Remote from converter; no automatic local-bypass credit |
| CIN-A/B: separate 2 × 10 µF | Each terminal 1 to /Power/VIN_BUCK after R33, terminal 2 to converter PGND | Combined effective capacitance must be ≥4.7 µF over the accepted operating/fault envelope |
| CHF: 220 nF / 100 V, GRM21AR72A224KAC5L screening part | Parallel with CIN, closest to future VIN pin 2 and PGND pin 1 | TI EVM reference identity; exact-part electrical, footprint and placement acceptance remain open |
| Future 5 V converter | Its own local CIN and CHF, independently sized | Not included in this first-cell four-site area or ripple budget |

These names describe functions, not allocated CAD reference designators. C43 belongs to IMU2; choose unused C44+ references only after checking the then-current schematic. The proposed C1 replacement, new capacitor pins, D12 identity/leakage correction and converter replacement must have an explicit delta before native export. Actual electrical/copper delta in this packet is **zero**.

TI requires effective capacitance after voltage, temperature and tolerance, plus the small high-frequency bypass. Its VIN/PGND connections must be physically close: the reservoir upstream of the 20 mΩ R33 is a different loop. The first 1.2 A output gives a 0.6 A input-capacitor RMS screening value; the optional 2 A rail needs its own 1 A screen. These approximate values are not ripple/thermal acceptance. At a 7 V battery, only 2.8 V remains above the 4.2 V operating floor before all feed losses and sag; regulation still needs verification. [TI SNVSBF0C §§8.1, 8.2.1.2.5, 8.4–8.5](https://www.ti.com/lit/ds/symlink/lmr36520.pdf).

## Capacitance evidence must answer the actual question

For two nominal 10 µF local parts, **each must contribute at least 2.35 µF effective** if the devices share an equal lower bound. This is a requirement, not a measured result. The [model](analysis.json) compares one through four sites without fabricating a DC-bias value. Its optional retention factors are hypothetical and never clear the acceptance gate.

The exact [TDK characterization sheet](https://product.tdk.com/info/en/documents/chara_sheet/C5750X7S2A106K230KB.pdf) contains reference curves for DC bias, combined temperature/50 V bias and ripple heating. Numerical curve values could not be obtained in this review; no 25.2 V or 44 V capacitance is asserted. Moreover, the curves are not guaranteed limits. The X7S ±22% specification is measured without applied voltage; multiplying it by a typical room-temperature bias curve does not establish a guaranteed combined minimum. [TDK GC11010030, September 2026, printed pp. 7, 16–18](https://product.tdk.com/system/files/dam/doc/product/capacitor/ceramic/mlcc/specification/mlccspec_commercial_general_midvoltage_en.pdf).

The compact EVM alternative uses two **CGA6M3X7S2A475K200AB**, 4.7 µF / 100 V, 1210 parts locally. Each must still supply 2.35 µF effective: half its nominal value. Its two additional filter capacitors are upstream and must not be counted as local CIN. The EVM's polarized bulk capacitor is unsuitable as an automatic substitute within our unresolved negative-voltage boundary. [TI SNVU677, schematic p. 7 and BOM p. 10](https://www.ti.com/lit/ug/snvu677/snvu677.pdf). The larger 2220 proposal trades area for a lower fractional-retention requirement; this is a design choice, not proof of margin.

## A usable footprint proposal, with a measured library mismatch

Native KiCad 9.0.7 reads the installed generic C_2220_5750Metric as a 3.3 mm land gap and 1.8 × 5.4 mm pads. Those dimensions fall outside this TDK part's recommended reflow ranges: gap 4.1–4.8 mm, pad length 1.2–1.4 mm, width 4.0–5.0 mm. This does not declare the generic footprint universally invalid; it prevents silently treating its package name as exact-part matching.

The [isolated footprint](footprints/LoRa_Power_Study.pretty/C_TDK_C5750X7S2A106K230KB.kicad_mod) uses **4.4 mm gap, 1.3 × 4.6 mm pads**, centers ±2.85 mm. Its proposed courtyard is 7.5 × 5.9 mm; four sites consume 177 mm² of courtyard rectangles before routing, high-frequency bypass and the second converter. It accommodates the specified maximum 6.1 × 5.4 mm body in this geometric sense. Stencil, soldering, board flex, clearances, environmental qualification and whole-board fit remain open. [Native dimensions and hashes](native_geometry.json) capture both footprints; the generic source is preserved under inputs. No live library was overwritten.

## Why source-lead damping needs its own decision

Removing a lossy electrolytic changes the input network. A low-ESR ceramic bank can resonate with source wiring. The interactive tool shows an **ideal linear series-RLC step**, using an explicitly assumed effective capacitance; it does not simulate the diode, fuse, TVS, both rail branches, switching converters, harness connector or nonlinear capacitor. A zero-loss 25.2 V step can approach 50.4 V in that model, above the proposed 44 V qualification target. This is a sensitivity finding, not a prediction of the protected board.

Do not add the displayed critical-damping resistance in series with the board feed without a loss and regulation review. First determine cable/source impedance, effective capacitance and allowed inrush, then evaluate a separate damped RC branch, a qualified bulk technology or another controlled approach. Retain the TVS/diode energy and reverse-current review. A 2 A fuse marking does not bound hot-plug current. No damping resistor value or complete negative-rail solution is selected here.

## Acceptance record to complete before powered use

Record the exact part/lot, source revision and instrument conditions. Establish a lower effective-capacitance bound at 7, 25.2 and 44 V, across the selected temperature and service-life envelope, including tolerance, aging and AC amplitude/frequency. Accept local CIN only if the combined bound is ≥4.7 µF. Capture individual and bank ripple heating and actual converter waveforms; use the manufacturer temperature limits, including self-heating. No component samples were tested during this review.

Capture the real cable length, source inductance/resistance, connector bounce and plug-in waveform. Check peak VIN_RAW and VIN_BUCK, inrush, damping, fuse pulse survival, TVS energy, diode junction conditions and startup at 7 V. Repeat the powered/unpowered and positive-then-negative boundary cases from the [leakage handoff](../reverse_leakage/README.md), including external USB/BEC and falling VDDA. A nonpolar reservoir removes the polarized-capacitor objection; it does not protect semiconductor pins from negative voltage.

## Efficient restart

Next bounded task: **design the complete first 3.3 V LMR36520 cell in an isolated editable schematic**, using this separate local-bank contract and explicit capacitance holds. Select its inductor, output bank, feedback, EN/UVLO, VCC/BOOT and thermal/placement boundaries; record exact old/new pin membership before native checks. Do not replace the old converter on the corrected live PCB yet. Keep complete leakage/negative-rail closure, ADC sequencing and capacitor/damping qualification as named integration gates, rather than repeatedly redoing the nominal capacitor search.

Retain the 6S and optional on-board-actuator requirements. V1 inspection, V2 vehicle-node work and the future voice/text/location handheld stay distinct; measured voice/RC coexistence precedes handheld selection. Existing ordering and flashing holds remain. Preserve all earlier packets and both unrelated dirty tools.

Reproduce the numerical/footprint checks with `python -B reviews/codex/input_capacitors/model.py --check`, `test_model.py`, `check_geometry.py` and `build_view.py --check`. Native inspection additionally requires the recorded KiCad Python and runs `native_geometry.py`; it is footprint parsing only. [Review notes](review_notes.json) and [packet manifest](packet_manifest.json) record scope, hashes and limitations.
