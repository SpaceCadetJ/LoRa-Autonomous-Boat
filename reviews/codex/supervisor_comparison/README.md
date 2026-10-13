# ACT-06: supervisor comparison and local-permission boundary

**Neither reviewed option is ready to connect to the arm latch.** This packet replaces a broad component search with concrete resistor networks, fixed-window variants and numerical limits. ACT-04 remains the latest native schematic; ACT-06 has zero candidate/live electrical or copper delta. QUAL_OK and ACK remain undriven and pulled low.

Use the [comparison results](RESULTS.md), [proposed signal path](v2_supervisor_comparison.svg), [source/calculation contract](contract.json) and [machine-readable analysis](analysis.json). The [engineering workspace](../../../pm/index.html) includes this planning diagram and guide. These artifacts are calculations and a functional proposal, not a native schematic, measured waveform or part release.

## What the comparison resolves

The TPS3703 A4330 variant conflicts with the recorded 3.3 V converter envelope. A5500 can avoid a fresh fault yet fail to release a prior one: its worst screened recovery ceiling is 5.173 V, below the converter's recorded 5.189909 V upper corner. A5330 fits the initial 3.3 V static comparison with only 2.178 mV of upper recovery margin; wider variants trade that margin against later fault thresholds.

The 30 us maximum detection time does not close the inhibit budget. Its specified 5% overdrive is already outside the retained voltage corridor at the latest-trip corners. The main calculation uses the nominal-threshold denominator from TPS3703 section9.1.5 Eq7; actual-trip multiplication appears only as a sensitivity. Neither result predicts a measured failure: neither establishes a guaranteed stop before the rail leaves the corridor. Startup and reset release remain separate.

TPS3700 permits a more tailored window. Two independent dividers per rail avoid sharing sense-node loading. Proposed top/bottom values are 6.90k/1k (3V3 UV), 7.87k/1k (3V3 OV), 10.9k/1k (5V UV), and (12.4k+100ohm)/1k (5V OV). These are preferred values, **not selected resistor order codes**. At assumed independent initial 0.1% tolerance, all four boundaries fit the static screen. Applying 0.35% per resistor as an illustrative initial-plus-temperature budget makes 3V3 OV fail both latest assertion and recovery.

At that 0.35% budget, even an arbitrary continuous 3V3 OV ratio cannot meet both inequalities with the stated 1k bottom resistor and bias assumption. The exact 7.87k proposal reaches zero static guard near 0.257266% per resistor; the best continuous ratio closes near 0.298050%. These are mathematical ceilings, not acceptable purchasing limits. Real margin must remain for the missing converter, bias, aging and dynamic terms.

## Calculation contract

TPS3700 UV asserts at the falling input threshold and releases at the rising threshold. OV does the reverse. Use the published rising/falling bounds directly; subtracting hysteresis again would double-count it. For each independent divider, the model enumerates resistor, threshold and signed bias extrema using:

```text
Vrail = Vthreshold * (1 + Rtop / Rbottom) + Ibias * Rtop
```

The published bias tests occur at sense voltages different from the comparator threshold. Applying those bounds near threshold is an explicit assumption, still requiring confirmation. Likewise, the 0.35% example assumes 0.1% initial tolerance plus 25 ppm/C over 100 C; no actual resistor MPN or operating-temperature budget is accepted. There is no temperature, bias or timing release hidden in a positive table cell.

Both converter inputs remain incomplete engineering envelopes, including an unknown guaranteed 5 V PFM upper limit. The 3.0–3.6 V corridor preserves the ACT-04 logic timing conditions; 4.5–5.5 V is a proposed performance comparison, not the full TXU range or a receiver specification. Raw nominal-trip hysteresis and the separate actual-trip sensitivity remain labeled assumptions for TPS3703.

## Proposed connection contract

1. Observe both local rails through reviewed windows, keeping monitor-supply selection and power-loss behavior explicit. Neither monitor may be connected directly to the 6S battery: both proposed monitor supply limits are below a charged 6S rail.
2. Retain every detected fault long enough to clear the latch. A reset-release timer cannot detect a pulse its input never saw or substitute for a maximum assertion delay. TPS3700's 450 us maximum startup does not bound its nominal-only propagation delay.
3. Condition the output into a valid logic edge. SN74LVC1G17 is an investigation option; loading, low-supply behavior and reset/ACK sequencing still need acceptance.
4. Keep **LOCAL_RAIL_OK** separate from complete actuator permission. No connection to ACT-04 QUAL_OK is made here. Receiver readiness, watchdog/fresh-command service, stop continuity and deliberate ACK remain independent missing inputs.

A direct 10k pull-up against the preserved 10k R42 pulldown yields about 1.65 V from a 3.3 V source, below the chosen 2.0 V logic-high requirement. Removing R42 or bypassing the missing qualifications is not an accepted solution. Drive the eventual permission boundary through a reviewed logic interface while preserving disabled defaults.

## Evidence and restart

The [input manifest](input_manifest.json) preserves 198 exact prior hashes. [Preservation evidence](preservation.json) checks actual unchanged QUAL_OK, ACK and OE memberships. [Model](model.py), [numeric/rejection tests](test_model.py), [review notes](review_notes.json), [viewer checks](viewer_check.json) and [packet manifest](packet_manifest.json) record what was examined. No native export was rerun because no circuitry changed. No hardware, ordering, firmware or fabrication acceptance is implied.

Run from the repository root:

```text
python -B reviews/codex/supervisor_comparison/model.py --check
python -B reviews/codex/supervisor_comparison/test_model.py
python -B reviews/codex/supervisor_comparison/build_results.py --check
python -B reviews/codex/supervisor_comparison/check_packet.py --check
python -B tools/quality/check_publication.py
node pm/tools/validate.mjs
```

## Next smallest circuit task

Close one **3.3 V local-observation subcell** first. Compare a faster comparator/reference or alternative supervisor with an applicable maximum delay at an in-corridor overdrive, and a divider/reference error budget that leaves positive recovery and trip guard. Require exact parts, applicable bias limits, ratio drift, declared fault waveform and total detector-to-OE deadline; include retained clear, supply loss and conditioned output. If these conditions cannot be bounded, document the precise missing parameter instead of inserting another incomplete circuit. The 5 V observation and complete permission chain remain separate follow-ups.

Preserve ACT-04, both converters, MCU, ACT-01 populations, R40/R42 defaults and corrected copper. Keep C11/VSERVO reservoir/regeneration/transients, full 6S feed, leakage/damping, ADC and combined IMU2 gates open. V1 inspection, V2 vehicles and the future voice/text/location handheld remain distinct; measured voice/RC coexistence precedes handheld hardware selection.

Primary references: [TPS3700 SBVS187G](https://www.ti.com/lit/ds/symlink/tps3700.pdf), [TPS3703 SBVS249B](https://www.ti.com/lit/ds/symlink/tps3703.pdf), [Vishay preferred-value table](https://www.vishay.com/docs/28372/e-series.pdf). Exact sections and test conditions are in the contract.
