# ACT-05 qualification boundary: selection remains held

ACT-05 screens a possible local-rail qualification circuit and leaves ACT-04 intact. No part is selected, no schematic or copper changes, and no new native or hardware acceptance follows. QUAL_OK and ACK retain their existing default-low, undriven state.

## Why the proposed fixed windows do not close the design

The [TPS3702 source record](source_review.json) identifies two selectable **C-family** windows: tight and wide. The tight window is not a nominal +/-5% choice. Read [TI section 6.3.3](https://www.ti.com/document-viewer/TPS3702/datasheet) with the naming and released-device tables.

Use [analysis.json](analysis.json) for computed bounds and comparisons against the captured converter records. Tight trip corners overlap the present converter envelopes, so nominally compliant parts can still cause unwanted fault assertion or prevent recovery. The wide 3V3 choice extends beyond the selected logic timing range. The wide 5V result depends on the accuracy interpretation; neither screen closes dynamic protection. Widening both windows is therefore not an acceptable blanket fix.

[TPS3702 SBVS251A](https://www.ti.com/lit/ds/symlink/tps3702.pdf) presents accuracy differently in section 6.3.3 and Table 7-1. The former adds accuracy percentage to the nominal rail window; the latter's CX33 example is consistent with trip-relative error. The main calculation follows section 6.3.3; a separate sensitivity calculation follows the example. Neither is asserted as a definitive guaranteed silicon bound. Each also encompasses rounded-table and percentage-defined nominal trips. That rounding union does not resolve the accuracy-basis difference. No published TI erratum is asserted. Release checks use specified hysteresis limits.

The **4.5-5.5 V comparison is a proposed signal-performance corridor**, not the TXU recommended operating range, an absolute maximum range or an established board limit. Keep that proposal separate from the 3.0-3.6 V interval used for the chosen logic timing tables.

The existing converter results are engineering screens, not complete operating envelopes. Temperature/aging, load transitions, ripple, wiring drops and light-load behavior remain incomplete. In particular, a typical PFM offset cannot be promoted into a guaranteed worst-case allowance.

## What a delayed release can establish

[TPS3808](https://www.ti.com/lit/ds/symlink/tps3808.pdf) offers a bounded reset-release interval with CT open. Its short-pulse and assertion-delay entries are typical-only. The source JSON keeps those categories separate. A detected, sustained fault may be retained through recovery; that does not prove every short input fault was detected or that inhibit arrived before the logic rail left its valid range.

Both reviewed devices have an undefined output region below their power-on-reset voltage. Their low-voltage reset conditions include stated output loading, and the TPS3808 power-up note adds a rail-rise condition. Neither source establishes unrestricted zero-supply isolation or all possible ramp behavior.

## Required architecture before a native amendment

A future local window detector may feed a fault-retention/release block, followed by a suitable edge conditioner. Only a reviewed combination of local permission, remote ESC readiness, remote servo readiness, stop continuity and fresh-command supervision may drive QUAL_OK. Unimplemented permissions must remain disabled; local rails alone cannot authorize actuator signals.

The next candidate must demonstrate all of the following:

- Earliest fault thresholds leave room for normal converter operation, including release hysteresis. Latest thresholds leave enough rail margin to inhibit before downstream limits.
- Detection, retention, conditioning and final inhibit delays have applicable bounds. Compare their sum with the available time during the declared rail slope or fault waveform; do not extrapolate an overdrive step test to arbitrary collapse.
- Every detected fault holds ACT-04 clear long enough despite distribution uncertainty. Qualification recovery requires stable acceptable inputs and a defined release process.
- Open-drain pullups and total node capacitance meet the receiving interface, or a characterized Schmitt stage restores the edge. A millisecond release delay does not by itself create a sufficiently fast edge.
- ACK has a deliberate source and conditioning. ACK, ARM and clear release obey ACT-04's independent setup/hold/recovery requirements. A rail supervisor alone does not enforce event ordering.
- Missing/collapsing monitor supply, externally powered sense inputs, broken grounds, output leakage and stuck-high fault lines are considered. A single permission wire has no automatic failure detection.

Preserve the explicit distinction between **observation**, **local power permission** and **complete actuator permission**. A converter's PG signal, local VSERVO or a BEC pin is not a substitute for observing actual receiver readiness.

## Alternatives to investigate, not selected parts

| Candidate | Source-backed opportunity | Limit that remains open |
| --- | --- | --- |
| [TPS3703A4330DSER / TPS3703A5500DSER](https://www.ti.com/lit/ds/symlink/tps3703.pdf), SBVS249B | Detection maximum 30 us at **5% threshold overdrive**, VDD 1.7-5.5 V, -40 to 125 C, 10k/10pF output load; A-family CT-open release 7-13 ms. | Startup 300 us and MR assertion delay 500 ns are nominal-only; MR pulse minimum is 1 us. These do not establish arbitrary near-threshold or collapse protection. Window and recovery compatibility remain unreviewed. |
| [TPS3700DDCR](https://www.ti.com/lit/ds/symlink/tps3700.pdf), SBVS187G | Adjustable divider windows; rising threshold 396-404 mV, falling threshold 387-400 mV. Startup maximum 450 us after VDD exceeds 1.8 V. | Sense high-to-low/low-to-high delays 18/29 us are nominal-only at VDD 5 V, 10 mV overdrive and 10k pullup. They are not universal fault/release bounds. Divider bias, tolerances and retention need review. |
| [SN74LVC1G17DBVR](https://www.ti.com/lit/ds/symlink/sn74lvc1g17.pdf), SCES351Y | Schmitt input offers an edge-conditioning option; operation specified at 1.65-5.5 V. | Output slew/loading and behavior below the operating supply remain gates. Conditioning cannot repair missed faults or enforce ACK/ARM ordering. |

Exact package pin maps, ordering-page links and numerical source conditions are in [source_review.json](source_review.json). Availability does not establish suitability.

## Next smallest task

Screen one adjustable window and one integrated window/reset alternative against complete assertion **and recovery** margins. Resolve the declared detector fault waveforms, downstream timing budget and missing-supply behavior before native insertion. Specify a compatible conditioner and ACK source; leave every unimplemented permission disabled.

The deliverable should be one bounded local-qualification subcell with its complete limits and default-disabled external permissions. Declare the exact part/pin delta before native capture. Keep both converters, source populations, R40 at OE, the existing PWM/output path and corrected live copper preserved.
