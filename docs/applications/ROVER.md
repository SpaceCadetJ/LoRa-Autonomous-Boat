# Rover: one ESC and a steering servo

**Current use: adaptation specification.** The V2 vehicle interface is a candidate for an Ackermann-style rover using one motor controller and one steering servo. It has not been tested in a rover. The preserved V1 image is unsuitable for powered driving because it retains commands after link loss.

## Choose a compatible drivetrain

Prepare the V2 controller and radio peer, selected reversible or forward-only ESC, matched motor, steering servo/linkage, rated actuator power, chassis, independent propulsion isolation and instruments. Use the [V2 assembly/BOM process](../build/ASSEMBLY_V2.md), then record the ESC model, its manufacturer-defined pulse map, brake/reverse sequence and behavior with signal loss. A centered reversible ESC may use a different neutral from the boat's proposed minimum pulse.

Reuse **J2 pin 1 / PC6** for the ESC signal and **J3 pin 1 / PA8** for steering only after verifying the current [V2 connection contract](../build/FLASHING_V2.md). Confirm physical orientation, signal levels and common reference; qualify servo/BEC power separately. Review steering travel before linking it to a rack or horn.

Two independently driven motors require a different profile and a reviewed second motor interface. The current two channels do not automatically create a differential-drive design: they are assigned motor and steering, with distinct safe values and application meaning. No encoder, wheel-speed, obstacle-avoidance or dedicated motor-driver capability is established by this design.

## Startup and use after release

1. Select the rover profile while disarmed. Confirm the displayed unit/peer, ESC type, calibrated neutral and forward/reverse policy.
2. Keep wheels unloaded and propulsion isolated for initial connection and signal checks. Power the logic using the approved sequence; require disarmed startup and valid diagnostics.
3. Verify full steering travel without mechanical binding and measure the ESC output at neutral. A requested reverse direction must follow the selected ESC's actual state sequence, not merely reverse a number.
4. Perform the accepted restrained-drive check, then explicitly arm for the defined test area. Start at the released speed limit. Motor mixing and navigation remain unavailable until separately implemented and tested.
5. On a control or power fault, apply the tested rover stop policy locally. Radio loss must not leave the last speed command active.

## Shutdown after release

Request the configured neutral/brake state, disarm and confirm it. Isolate propulsion, then logic and controller power. Keep a faulted unit disarmed until its cause and restart behavior are understood; reconnecting a peer must not recover an old speed command.

## Troubleshooting and release evidence

| Symptom | Check |
|---|---|
| Vehicle moves at “zero” | ESC neutral/profile mismatch; verify pulse map unloaded before changing anything |
| Reverse command brakes or does nothing | The ESC may require a documented brake/neutral/reverse sequence |
| Steering binds or reverses | Endpoint/direction calibration and mechanical travel |
| Telemetry works but driving fails | Control authority, profile compatibility and arming conditions are separate from message reception |

Acceptance requires measured neutral, boot/reset/link-loss stop behavior, controlled forward/reverse transitions, steering limits, low-supply response and reconnect with nonzero input. Record stopping behavior for the actual mass, surface and speed; firmware timeout alone is not stopping distance.

**Next task:** select one ESC/servo pair and write its pulse/neutral/brake requirements into a rover profile before any powered demonstration. Reuse the [V2 boat development stages](V2_BOAT.md), replacing boat assumptions with that profile's measured acceptance criteria and [record](ACCEPTANCE_RECORD.md).
