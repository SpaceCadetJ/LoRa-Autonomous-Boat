# VSERVO-01 - C11 identity and reservoir candidate

**This isolated ACT-04-derived amendment replaces C11's unconfirmed identity with a documented candidate and an explicit manufacturer land pattern.** It preserves every electrical pin membership. The live board and purchasing package are unchanged; reservoir, assembly and actuator acceptance remain held.

[Annotated review](v2_vservo_reservoir.svg) | [Reservoir explorer](index.html) | [Calculated limits](RESULTS.md) | [Native candidate](source/hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_pro) | [Native checks](validation.json) | [Change contract](expected_contract.json)

## Exact part and package correction

The source `EEE-FK1A101P` / `EEEFK1A101P` could not be confirmed in current Panasonic evidence. This does not prove that it never existed or is discontinued. The explicit alternative is **EEEFK1C101P**, listed by [Panasonic](https://industrial.panasonic.com/ww/products/pt/aluminum-cap-smd/models/EEEFK1C101P): 100 uF, 16 V, standard FK, 6.3 mm diameter and 5.8 mm nominal body length. It is a held candidate, not a silent spelling correction or approved substitute.

The [dated FK catalog, pages 1-3](https://industrial.panasonic.com/cdbs/www-data/pdf/RDE0000/ABA0000C1181.pdf) defines size-D lands: 3.2 x 1.6 mm pads, 1.8 mm inner gap, derived pad centers at +/-2.5 mm and 8.2 mm overall span. Existing C11 lands use 3.5 x 1.6 mm pads at +/-2.7 mm, with a 1.9 mm gap and 8.9 mm span. Both stock KiCad 6.3x7.7 and 6.3x5.8 footprints retain those different lands; merely renaming the stock footprint would not implement the recommendation.

The candidate therefore uses a new local `CP_Panasonic_FK_D_6.3x5.8` footprint. Pad 1 remains positive / VSERVO; pad 2 remains negative / GND. Selected native pad dimensions are checked separately from the schematic. Courtyard, mask, paste, placement, vibration, soldering and board fit remain review items. The candidate follows catalog reflow profile (1), not the AP variant; see the [source ledger](source_review.json) and [soldering document](https://industrial.panasonic.com/cdbs/www-data/pdf/RDE0000/DME0000COL48.pdf).

## Explicit amendment and preservation

| Item | Source ACT-04 | Isolated VSERVO-01 |
|---|---|---|
| C11 value / identity | 100uF 10V / EEE-FK1A101P | 100uF 16V / EEEFK1C101P |
| C11 footprint | Stock CP_Elec_6.3x7.7 | Explicit Panasonic standard-D land |
| C11 pins | 1 = VSERVO; 2 = GND | Unchanged |
| Electrical memberships | 429 physical pins | All preserved |
| Other components | 127 identities | All preserved |
| Source populations | BEC_ONLY D9; ONBOARD D4; exclusive | Unchanged |
| Live PCB, BOM and firmware | Existing review snapshot | Unchanged |

**Expected delta: one candidate identity/footprint amendment; zero pin/net changes; zero live electrical or copper changes.** The expected contract was recorded before the copy was amended. Native export/ERC, exact comparison and footprint inspection are recorded on this captured revision. These checks establish only their stated scope. The new candidate retains ACT-04's default-disabled unimplemented permissions and both converter sheets. It does not integrate the separate IMU2 candidate.

## What the reservoir must do

VSERVO still contains C11, C12, D4/D9 cathodes, J3.2 and TP4.1. A source diode supplies forward current but does not establish a controlled energy sink. Actual reverse leakage cannot be treated as a guaranteed clamp. A returning actuator can therefore charge the local rail unless another qualified path absorbs the energy. No sink/clamp is added here.

Three limits need independent closure: voltage droop while the capacitor supplies a current deficit, voltage rise from net returned energy, and ripple heating/lifetime. Source/BEC contribution, wiring inductance, effective capacitance, receiver limits and regeneration waveforms are not yet known. Raising C11's voltage rating does not raise the permitted VSERVO or receiver voltage. The [ACT-12 connector contract](../connector_fault_contract/README.md) remains open.

The explorer uses **allocated examples**, not servo requirements: a 5 V starting rail, 4.5 V floor, 5.5 V ceiling, 0.5 A deficit for 100 us, and 0.2 ohm series resistance. That resistance is not inferred from the catalog's impedance entry. Source-conditioned 80 uF initial and 56 uF post-endurance arithmetic are shown alongside 100 uF nominal; none is a guaranteed all-condition effective-capacitance bound. C12 receives no effective-capacitance credit until its actual bias/temperature/frequency behavior is bounded.

## Read the calculation correctly

`delta_V = I_deficit * R + I_deficit * time / C` is a simple load-step screen. It omits converter dynamics and inductive spikes. A depleted or negative modeled voltage is outside its useful positive-rail domain, not a physical waveform prediction.

`V_after = sqrt(V_start^2 + 2 * E_net / C)` accounts for net energy retained in an ideal capacitor. It omits instantaneous ESR/inductive rise; those need additional peak-voltage margin. Source energy, load absorption and clamp dissipation must be accounted for before defining E_net. The required capacitance values in [RESULTS](RESULTS.md) are equality thresholds, so positive margin requires larger capacitance and valid assumptions.

The [manufacturer precautions](https://industrial.panasonic.com/cdbs/www-data/pdf/RDE0000/DME0000COL75.pdf) constrain reverse voltage and repeated charge/discharge. This amendment adds no reverse protection, verified energy sink or lifetime result. Missing data cannot be replaced with the capacitor's voltage rating.

## Ordering, assembly and next task

Do not replace the live BOM line or remove its purchasing hold based on this study. This candidate is reviewable through its own source/contract; neither a cart nor an assembler file is released. The reviewed land and correct part identity are necessary inputs, but physical fit, stencil/reflow, temperature, ripple and load/energy evidence remain required.

**Next smallest circuit task: define the VSERVO energy sink and reverse-voltage boundary for both source populations.** Build a symbolic transient budget using explicit allowed receiver voltage, BEC/source envelope, net return energy/current, repetition and harness inductance. Keep unknowns unavailable. Compare a dissipative clamp/sink and source-return approach under those boundaries before selecting a device or inserting another circuit. Do not assume the 16 V capacitor or diode leakage protects an unidentified servo.

Retain the 6S requirement. Full input-feed, leakage/damping, ADC, combined IMU2, receiver/watchdog/stop/ACK and observer power gates remain open. V1 inspection, V2 vehicle applications and the future voice/text/location handheld remain separate; measured voice/RC coexistence precedes handheld selection.

[Review record](review_notes.json), [source ledger](source_review.json), [input hashes](input_manifest.json), [native capture](native_manifest.json) and [packet manifest](packet_manifest.json) support restart. Inspect Git/FILE_OWNERSHIP and preserve unrelated v1_design.py/route_v2.py edits.

```text
python -B reviews/codex/vservo_reservoir/test_candidate.py
python -B reviews/codex/vservo_reservoir/test_model.py
python -B reviews/codex/vservo_reservoir/verify_candidate.py --check
python -B reviews/codex/vservo_reservoir/build_packet.py --check
python -B tools/quality/check_publication.py
node pm/tools/validate.mjs
```
