# Remote position and telemetry

**Current use: source review and unloaded demonstration planning.** V1 implements a basic position broadcast; it is not a qualified tracker. V2 is intended to add bounded telemetry with identity, fix age, power and fault state. A standalone telemetry profile must leave actuator outputs inactive even if control-looking traffic is received.

## Parts and connection plan

Use an electrically reviewed V1 or accepted V2 assembly, an identified GNSS module and antenna, compatible radio endpoints and antennas, a validated supply, and a computer/receiver that logs payloads with reception time. Keep actuator harnesses absent. The controller BOM identifies module connectors; it does not identify a fitted radio/GNSS system.

For V1, the [GPS atlas](../atlas/GPSMODULE.md) gives pin 1 supply, pin 2 ground, pin 3 PB0 driven LOW, pin 4 GNSS TX → PC11, and pin 5 PC10 → GNSS RX/debug. Leave pin 3 open until the actual module function is resolved, and assess debug traffic on pin 5 before connection. V1 expects 9600 8N1 GNSS input. V2 instead requires dedicated GNSS serial reception and PB0 configured as a PPS input; use the frozen module configuration rather than inheriting V1's baud.

## What the V1 source actually does

`gps_parse_rmc` recognizes `$GPRMC` and `$GNRMC` with an NMEA checksum and reads latitude/longitude. If its `gps_valid` flag is set, `main` formats `GPS,<latitude>,<longitude>` to six decimal places and requests transmission to radio address **2** every **5000 ms**. The generated radio command is `AT+SEND=2,<payload byte count>,<payload>`. Incoming remote `GPS,...` messages are printed to debug and do not change the vehicle's navigation.

This payload contains no fix time/age, message sequence, unit identity, altitude, satellite count, power or fault state. A repeated coordinate may be stale: V1 has no fix timeout, empty RMC fields can bypass invalidation, and its shared receive buffer can lose sentences. Formatting to six decimals does not establish that position accuracy. Refer to [the source](../../firmware/Core/Src/main.c) and [review](../research/FIRMWARE_REVIEW_NOTES.md).

## Startup and unloaded demonstration

1. Follow the board's assembly and [programming guide](../build/README.md), then record the image hash and selected GNSS/radio identities. Preserve any existing firmware before changing it.
2. Verify GNSS serial levels and the allowed connection map with loads absent. Log raw RMC traffic and its reception times separately from radio reception.
3. Identify/read back both radios' accepted settings using their documented tools. V1 startup requests are not proof of accepted settings. Capture both module UARTs if diagnosing a link.
4. Compare received coordinates with the actual accepted RMC inputs. Record the payload's arrival time explicitly as **received time**, not fix time.
5. Stop GNSS input after a valid sample while keeping radio reception running. A continuing V1 position message demonstrates the stale-data defect; label it accordingly. Do not present the point as a current asset location.

For this demonstration, preserve raw records before building a map or dashboard. Mark synthetic/replayed NMEA as test data and keep it separate from measured locations. No command for a finished map application or receiver is supplied because that application is not released.

## Operation after a telemetry-profile release

Start the node and receiver, verify the expected unit/profile, then confirm fresh fix status and power health. The receiver must show **no fix**, **fresh**, **stale** and **offline** distinctly; a map pin alone is insufficient. Use bounded reporting that cannot starve control if the same endpoint also supports RC. Disable control acceptance in a dedicated tracker profile; enable application changes only while disarmed.

To shut down, stop the session, save the last received and fix times, then remove node power using the accepted sequence. The receiver must age the unit to offline rather than leaving a permanent “live” marker.

| Symptom | Diagnose |
|---|---|
| No coordinates | GNSS baud/pin map, valid RMC with checksum, selected image float formatting, module replies and receiver address |
| Coordinates repeat indefinitely | Compare fix age and raw input; legacy behavior can preserve an old fix |
| Missing RMC but other NMEA visible | Legacy receive-buffer race or parser rejection; raw serial presence is not parsing success |
| Position current but map offline | Receiver arrival-time/session handling or transport delivery; distinguish fix from link state |

**Acceptance / next task:** implement a receive parser that preserves empty fields and invalidates stale/void fixes, with replay tests for silence, invalid status, malformed checksums and back-to-back sentences. Then define a versioned telemetry payload and receiver display with identity, fix age, sequence, units and explicit offline behavior. Record results in the [acceptance template](ACCEPTANCE_RECORD.md).
