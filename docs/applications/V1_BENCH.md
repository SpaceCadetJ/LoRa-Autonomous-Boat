# V1: characterize the existing boat controller

**Scope: existing-source, instrument-only bench work.** This guide explains the legacy RC behavior and how to establish evidence before adapting it. Keep the ESC, servo and propulsion harnesses disconnected throughout. The preserved image retains the last command after radio silence and has no arming state or watchdog supervision.

## Parts and connections

Use the identified V1 assembly, its documented electrical corrections, a current-limited supply approved for that assembly, ST-LINK and the correctly mapped adapter, a scope/logic analyzer, and a computer for logs. A radio demonstration additionally needs an identified compatible radio, matching antenna/profile and a separately controlled peer. A wired parser demonstration needs a verified 3.3 V UART source with the radio removed from the driven receive line.

| Bench connection | Electrical destination | Purpose |
|---|---|---|
| Analyzer channel A | TP3 / STEERINGSERVO1 pin 2 / PC6 | Thrust waveform |
| Analyzer channel B | TP1 / SPEEDCONTROLLER1 pin 2 / PA8 | Rudder waveform |
| Instrument ground | TP5 / verified GND | Common reference |
| Optional UART injection, radio disconnected | LORAMODULE1 pin 3 / PA1 | Emulate module receive lines at 115200 8N1 |
| Optional high-impedance debug receiver | GPSMODULE1 pin 5 / PC10 | Read legacy debug at 9600 8N1; GPS remains unplugged |

Do not connect two TX drivers together or drive an unpowered MCU input. Verify signal levels, ground and pin orientation before power. Neither actuator header pin 1 is a servo/BEC power inlet: both are connected to +3V3 in V1. Leave GPSMODULE1 pin 3 disconnected until its module function is established; firmware drives PB0 LOW. See the [atlas](../atlas/README.md) and [assembly prerequisites](../build/ASSEMBLY_V1.md).

## Startup

1. Identify and photograph the board, rework and fitted modules. Complete the VCAP, boot and power review in the assembly guide before powering.
2. Follow [V1 flashing](../build/FLASHING_V1.md) to preserve two matching main-Flash backups, reproduce the candidate build and verify any deliberate programming. This image is `boat_v1_unqualified`; no hardware qualification is implied.
3. Attach instruments before deliberate reset. Confirm source-expected startup pulses: PC6 approximately 1000 microseconds and PA8 approximately 1500 microseconds, both on nominal 20 ms frames. Record the first pulse as well as steady operation.
4. Observe radio setup on PA0 if needed. Source emits address 1, network 18, 915000000 Hz and `AT+PARAMETER=12,7,1,4`; it does not verify acknowledgements. These are legacy requests, not a recommended or accepted radio profile. Identify the module and its accepted configuration before an RF test.

## Demonstrate the legacy protocol without loads

These are **module-to-MCU UART test lines**, not handset console commands. With the radio removed and a single verified UART transmitter on PA1, send each line terminated by CR/LF:

```text
+RCV=2,8,THRUST,0,-50,10
+RCV=2,9,RUDDER,50,-50,10
```

The payload byte counts are 8 and 9. Address 2 models the intended peer; RSSI −50 and SNR 10 are synthetic parser fields, not RF measurements. The legacy parser skips the first two comma fields rather than enforcing sender or payload length. It accepts `THRUST,<integer>` and `RUDDER,<integer>`, clamps values into 0–100, and applies each independently.

| Source mapping | Formula | Selected expectations |
|---|---|---|
| Thrust → PC6 | `1000 + 10 × value` microseconds | 0 → 1000; 50 → 1500; 100 → 2000 |
| Rudder → PA8 | `1100 + 8 × value` microseconds | 0 → 1100; 50 → 1500; 100 → 1900 |

Use instruments to compare these values. A nonzero-thrust/link-loss demonstration is permissible here only with every actuator physically absent: stop input and record that the pulse persists. That is confirmation of a defect, not acceptance of the control system. `GPS,<lat>,<lon>` arriving through the radio is printed to debug; it does not steer toward that position.

No `ARM`, `DISARM`, mode-selection, heading-hold or waypoint command exists in this preserved source. Address/network matching is not authorization, and CRC/checksum, replay rejection and atomic control updates are absent from this application parser.

## Shutdown and recovery

Send the zero-thrust/center lines and observe their waveforms while instruments remain attached. Disable or disconnect external UART/programmer signal drivers first while keeping the common ground connected. Then remove target supply and disconnect the remaining connections. Stop the peer and archive logs. This order prevents external drivers from powering an unpowered MCU through its inputs. Radio silence is not a shutdown method for this image.

If execution fails, keep loads absent and follow the under-reset recovery in the flashing guide. Restore only a verified image for this identified board. Do not erase or alter read protection to work around a failed connection.

## Troubleshooting and exit checks

| Symptom | Check / interpretation |
|---|---|
| No command response | Correct PA1 path, 115200 8N1, CR/LF, module disconnected during injection; inspect UART errors |
| Radio startup text but no link | Capture module replies and accepted profile; legacy setup ignores errors |
| Apparent swapped controls | Compare actual headers to PC6/thrust and PA8/rudder; do not trust header names |
| Last pulse remains after peer off | Expected legacy defect; no command-age supervisor exists |
| Bad or stale position | Follow [telemetry](TELEMETRY.md); UART sharing, receive-buffer races and validity handling remain defects |

Save startup and command traces, board/image identities and one link-loss trace in an [acceptance record](ACCEPTANCE_RECORD.md). Mark these as **characterization**. The next task is to integrate a reviewed control supervisor and receive parser into a board-specific candidate, then pass unloaded fault/timeout tests before defining any powered RC operating procedure. Keep the preserved V1 image as an evidence baseline.

Source: [main.c](../../firmware/Core/Src/main.c), especially `parse_lora_line`, `set_thrust`, `set_rudder`, `main` and `HAL_UART_RxCpltCallback`; [firmware review](../research/FIRMWARE_REVIEW_NOTES.md); [build evidence](../build/FIRMWARE_HANDOFF.md).
