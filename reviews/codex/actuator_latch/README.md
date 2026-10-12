# ACT-04: isolated actuator arm latch

ACT-04 separates PC4's arm request from the TXU0102 output enable on a new **isolated schematic candidate**. The new latch requires a valid acknowledge while arm is low before a later arm request can enable. A qualified fault clears that permission. Receiver observation, the watchdog and the qualification source remain unimplemented; their default-low boundary keeps valid-rail operation disabled.

Open the [annotated latch schematic](v2_actuator_latch.svg), [complete actuator signal path](native/svg/LoRa_Boat_Controller_V2-Actuators.svg), or [editable KiCad project](source/hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_pro). In the [engineering workspace](../../../pm/index.html), choose **Design viewer → V2 draft → ACT-04**; zoom or open the full SVG for individual pins. The preceding [ACT-03 demonstrator](../actuator_interlock/index.html) is a behavior proposal and differs from this circuit as described below.

## What changed

The pre-export [part and pin contract](expected_contract.json) specifies exactly two existing membership changes: U4.6 and R40.1 move from `/ACT_EN_PC4` to `/Actuators/ACT_OE`. U1.24 remains PC4's request. R40 stays directly on translator OE. No existing component identity changes; the PWM paths, connectors and output networks are preserved.

| New reference | Exact candidate identity | Function |
| --- | --- | --- |
| U12 | Texas Instruments SN74LVC1G74DCUR | READY latch; **Q is pad 5**, inverted Q is unused pad 3 |
| U13 | Texas Instruments SN74LVC1G04DBVR | Inverts the PC4 arm request for latch D |
| U14 | Texas Instruments SN74LVC1G11DBVR | Three-input OE gate; **GND is pad 2**, B is pad 3 |
| R41, R42, R43 | Yageo RC0603FR-0710KL, 10k | Default-low ARM, QUAL_OK and ACK respectively |
| C56, C57, C58 | Kyocera AVX KGM15ACG1H104KT, 100nF | Local bypass for U12, U13 and U14 respectively |

All nine parts are held engineering candidates, excluded from the released ordering exports. The [package review](package_review.json) and [native geometry](native_geometry.json) bind local manufacturer-example land patterns for the three ICs. Matching a drawing does not qualify soldering, layout or assembly.

Power, Buck3V3, Buck5V and MCU sheets are byte-identical to ACT-02. The [ACT-01 population contract](population_contract.json) is also byte-identical: BEC_ONLY fits D9 alone; ONBOARD fits D4 alone; the unselected master marks both DNP. Local VSERVO does not prove remote ESC readiness in ONBOARD. Live CAD/copper, V1/Allegro evidence, firmware and purchasing data are unchanged.

## How the proposed control path works

With valid rails, adequate fault duration and settled edges, U12 captures NOT ARM at a new ACK rise. QUAL_OK low clears U12. The final gate implements `OE = QUAL_OK AND ARM_REQUEST AND READY`. A fault destroys READY; restored qualification or held ACK/ARM cannot recreate it under those conditions. Normal arm-low disarm retains READY within a healthy epoch.

**ACT-04 intentionally differs from ACT-03:** ACK rising while arm is high clears READY and disables, whereas the older simulator ignores ACK while armed. Do not present the old simulator as an exact model of this native circuit. The first two-DFF proposal was rejected because clearing READY while leaving ARMED set could cause an OE pulse at a later ARM rise. The one-DFF circuit removes that particular stale-state path; it does not establish glitch-free behavior for arbitrary asynchronous inputs.

Read the [timing and power contract](TIMING.md) before adapting the interface. Short fault pulses can inhibit OE without clearing the latch, allowing recovery; near-coincident reset/ACK/ARM edges are outside the Boolean proof. QUAL_OK eventually needs independently reviewed rail windows, remote receiver readiness, stop continuity and command freshness, with fault retention and safe release. ACK needs conditioning and a defined source. These are functional ports, not assigned harness pins or firmware signals. No tie-high bypass is provided.

For boat and rover applications, complete the [receiver acceptance worksheet](../actuator_interlock/RECEIVER_ACCEPTANCE.md) with the actual ESC/BEC/servo identities and measurable stop/input limits. Stage A remains an identity diagnostic and does not drive this latch. Existing V1 procedures are separate. The future voice/text/location handheld remains a separate design requiring measured voice/RC coexistence before hardware choice.

## Verification and its limits

- KiCad 9.0.7 exports and ERC on the captured candidate: **zero errors, one preserved AD0 warning**. Native capture is recorded in [native_manifest.json](native_manifest.json).
- Independent [native delta verification](validation.json): **128 components, 429 physical pins; 396 existing memberships unchanged**, exactly two changed, 31 added. Existing identities, sheet paths and native pin metadata remain intact. Forty-four contract mutation tests pass.
- [Boolean tests](logic_results.json): 11 tests, including 32 state/input combinations, 32,768 five-event traces and ten contract/claim mutations. This is a zero-delay model with valid-reset and timing assumptions; it is not a circuit simulation or hardware test.
- Three local IC footprints: 19 numbered pads and 42 artwork segments checked in KiCad and portable parsing; nine altered-number/land/pin-1 mutations rejected.
- [Viewer checks](viewer_check.json) cover desktop and phone navigation, source links, SVG loading, 200% zoom and guide overflow. The two source schematic renders were also visually reviewed.

[Input hashes](input_manifest.json), [build provenance](build_manifest.json), [native capture](native_manifest.json) and [packet hashes](packet_manifest.json) support exact review and resumption. Local dirty-tool hashes are preservation metadata, not portable CI inputs. Compilation, ERC or rendering provides no fabrication or physical operating acceptance.

Read-only restart checks from the repository root:

```text
python -B reviews/codex/actuator_latch/verify_candidate.py --check
python -B reviews/codex/actuator_latch/test_candidate.py
python -B reviews/codex/actuator_latch/test_latch.py --check
python -B reviews/codex/actuator_latch/inspect_packages.py --check
python -B tools/quality/check_publication.py
node pm/tools/validate.mjs
```

The isolated builder and export script exist for a declared revision change; ordinary document review does not need to regenerate CAD. Do not run primary generators or the router to refresh this guide.

## Next smallest task

Design the **qualification/reset-release interface** on another isolated ACT-04 copy. Specify exact local supply windows, fault retention, startup/collapse behavior and conditioned ACK timing. Leave remote receiver-ready and command-service permissions disabled until their sources are designed. Preserve R40 at OE, both converters, MCU, the output path and source populations. Define the next part/pin delta before capture.

Still open: actual receiver identities/readiness, hardware watchdog and command deadlines, C11 identity and VSERVO reservoir/regeneration/transients, full 6S simultaneous-load feed, negative leakage/damping, ADC/sense and combined IMU2 integration. The corrected live copper must be preserved during eventual controlled integration.
