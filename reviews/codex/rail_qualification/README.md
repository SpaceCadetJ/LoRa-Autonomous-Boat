# ACT-05: rail supervision selection review

The first fixed-window supervisor proposal does **not** fit the present converter bounds. ACT-05 records the conflict before any CAD insertion, provides an interactive voltage-window screen, and defines the remaining detector, reset and signal-edge requirements. **ACT-04 remains the latest native schematic candidate.** Its qualification and acknowledge inputs remain undriven and default low.

Open the [interactive voltage-window explorer](index.html), [exportable comparison figure](v2_rail_qualification.svg), or [qualification boundary guide](QUALIFICATION.md). The [ACT-04 latch and complete signal path](../actuator_latch/README.md) remain available in the [engineering workspace](../../../pm/index.html). These plots show calculated screening intervals; they are not measured waveforms or new schematics.

## What the review changes

The screened TPS3702CX33DDCR and TPS3702CX50DDCR use selectable nominal +/-4% or +/-9% windows. Assuming a nominal +/-5% window would conceal the tight-setting conflict. The source review distinguishes threshold accuracy, hysteresis and rounded nominal tables; the model encompasses both nominal representations. Section 6.3.3 and the Table 7-1 example motivate different accuracy-basis readings, so the report includes a separate trip-relative sensitivity. These are conditional screens, not guaranteed silicon bounds; no TI erratum is asserted.

- Tight settings can assert overvoltage within the recorded converter upper corners. Recovery is a separate condition: hysteresis can prevent a previous fault from clearing even where a new fault would not occur.
- The wide 3V3 setting can allow voltages outside the 3.0–3.6 V range used for ACT-04's logic timing analysis. It is not an acceptable blanket remedy.
- The wide 5 V setting has only a small static margin to the proposed 4.5–5.5 V performance comparison (not the full TXU operating range or a receiver limit). Dynamic response and complete converter behavior remain unqualified.
- The detector's published nominal response times cannot be used as guaranteed maximum shutdown delays. A bounded reset-release delay cannot recover a fault missed by the detector.
- An illustrative 10 kΩ/10 pF open-drain edge fails the latch's specified input slew screen. Neither that capacitance nor the resulting waveform is a board measurement. A suitable conditioning stage still needs review.

Exact calculated values, assumptions and feasibility margins are in [analysis.json](analysis.json). The 3V3 and 5 V converter records already exclude complete temperature, aging, ripple and transient limits; the 5 V PFM upper bound is unknown. A typical no-load offset is not added as though it were a guaranteed limit.

## Evidence and boundaries

[Source facts and citations](source_review.json) identify document revisions, part identities, pinouts and which timing values have actual bounds. The [input manifest](input_manifest.json) preserves 174 prior artifact/input hashes, including ACT-04, both converters, MCU and the ACT-01 population contract. [Preservation evidence](preservation.json) checks the actual captured QUAL_OK, ACK and OE memberships; no hidden permission driver was added.

The [model](model.py) and 21 [numeric/mutation tests](test_model.py) check voltage arithmetic, recovery direction, assumptions and source/input freshness. The [viewer record](viewer_check.json) records desktop/phone controls, plots, source links and overflow. [Packet hashes](packet_manifest.json) bind the exact artifacts. Native export commands were not rerun because the electrical and copper delta is zero. No parts were selected, purchasing exports changed, firmware altered, or physical qualification established.

For V2 boat or rover adaptation, retain the [receiver acceptance worksheet](../actuator_interlock/RECEIVER_ACCEPTANCE.md). Local rail validity cannot establish a remote ESC or servo is ready. Stage A is still a diagnostic, and V1 inspection/build procedures remain separate. The voice/text/location handheld continues to require measured voice/RC coexistence before hardware choice.

Read-only restart checks from the repository root:

```text
python -B reviews/codex/rail_qualification/model.py --check
python -B reviews/codex/rail_qualification/test_model.py
python -B reviews/codex/rail_qualification/build_view.py --check
python -B reviews/codex/rail_qualification/check_packet.py --check
python -B tools/quality/check_publication.py
node pm/tools/validate.mjs
```

The viewer embeds its data and opens directly from a repository copy. Refresh only this page with `python -B reviews/codex/rail_qualification/build_view.py`. The exportable figure was rendered with matplotlib 3.10.7 using [export_figure.py](export_figure.py); this optional plotting dependency is not needed for viewing or portable CI. [Review notes](review_notes.json) record the source review and input-range fix.

## Next smallest task

Screen one adjustable window implementation against an integrated window/reset alternative, using the demonstrated threshold and recovery requirements. TPS3700 and TPS3703 are investigation families, not selected replacements; timing bounds apply only under their stated conditions. Include open-drain edge conditioning, fault retention, monitor-supply startup/collapse and ACK ordering before declaring a native subcell delta. Keep remote-ready, watchdog and other unfinished permissions disabled.

Preserve ACT-04, R40 at OE, both converter sheets, source populations and corrected copper. Still open: receiver identities/readiness and watchdog deadlines, C11 identity and VSERVO reservoir/regeneration/transients, full 6S simultaneous-load feed, negative leakage/damping, ADC/sense and combined IMU2. No ordering, flashing or powered-use release follows from this screen.
