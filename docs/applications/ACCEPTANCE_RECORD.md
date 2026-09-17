# Application acceptance record — copy per physical unit

Leave unperformed values blank and mark them **NOT RUN**. A test script, source expectation or simulation result is not a physical measurement. Keep the completed copy and its linked traces with the corresponding release packet.

## Identity and configuration

| Field | Recorded value |
|---|---|
| Date / operator / reviewer | |
| Application / requested release stage | |
| Board revision / serial / assembly or rework record | |
| PCB and schematic revision / hashes | |
| Selected BOM / population / approved substitutions | |
| Harness drawing / electrical pin map / photographs | |
| Firmware commit / image SHA-256 / build manifest | |
| Protocol / application profile / peer software revision | |
| Radio model / firmware / accepted settings / antenna | |
| GNSS / ESC / servo / audio device identities, as applicable | |
| Supply arrangement / current limits / calibration revision | |
| Programmer / probe / backup and rollback hashes | |
| Instrument models / settings / time reference | |

## Measured cases

Write the numerical limit or explicit expected behavior **before** each test. Record PASS, FAIL, NOT RUN or NOT APPLICABLE with a reason; link raw evidence rather than only a screenshot of a green status.

| Case | Limit / expected behavior | Measured result / evidence | Status |
|---|---|---|---|
| Unpowered continuity / orientation / rail isolation | | | NOT RUN |
| Startup rails / current / first output pulse | | | NOT RUN |
| Program verify / readback / deliberate reset | | | NOT RUN |
| Profile / peer identity and wrong-peer rejection | | | NOT RUN |
| Explicit arm / disarm / non-idle arm rejection | | | NOT RUN |
| Valid command input to measured output | | | NOT RUN |
| Silence, corrupt, duplicate and stale control traffic | | | NOT RUN |
| Reconnect / mode change with nonzero input | | | NOT RUN |
| Watchdog / reset / brownout / power-source interaction | | | NOT RUN |
| GNSS invalid / stale / disconnected | | | NOT RUN |
| Text delivery / duplicate / expiry / offline UI | | | NOT RUN |
| Voice quality / delay / expired audio | | | NOT RUN |
| Maximum control age during voice + telemetry | | | NOT RUN |
| Application-specific motion/navigation test | | | NOT RUN |
| Shutdown / backup recovery / restart | | | NOT RUN |

## Disposition

- Released use and operating limits:
- Remaining failures / restricted features:
- Hardware versus source-only or simulated evidence:
- Exact files to retain:
- Smallest next task / owner:
- Reviewer / date / accepted revision:

Default disposition: **development; powered operation not released**. Change that statement only after the selected application's required evidence is complete and reviewed. An instrument-only V1 characterization can pass its characterization cases while still failing the operational release gate.
