# Blockers and decisions

## Codex intake — 2026-09-17 UTC

This is a review checkpoint, not a command to stop the primary agent or implement V2. Evidence and proposed resolutions will be linked from `reviews/codex/ASSESSMENT.md`.

| ID | Issue | Owner / next action | Recommended handling |
|---|---|---|---|
| C-01 | No explicit Phase A release; hardware and tools actively changing | Primary: release exact paths, revision, validation logs | Continue independent review; do not edit active implementation |
| C-02 | Brief expects 35 nets / square board / matching drill; newer v5 evidence disagrees | Primary + independent review: establish evidence-derived gate inputs | Compare actual pin memberships; preserve NC separately; document exceptions |
| C-03 | Available BOATCREW drill matches older v4 data | Primary: validate provenance and list inferred drills separately | Request final v5 NC drill/export only if needed to certify manufacture; do not claim exact drill fidelity from inference |
| C-04 | Link-loss timeout absent; `.ioc` motor startup pulse differs from C | V2 firmware owner after Phase A | Define safe actuator behavior and configuration parity before actuator testing |
| C-05 | Converter's CANH/CANL names reversed; validator success does not enforce zero unrouted or complete net/pad equality | Primary: review R02/R03 in `reviews/codex/ASSESSMENT.md` | Correct within owned implementation; preserve exact v5 pin membership |
| C-06 | VCAP pin number is correct, but CEXT other terminal is on source 3.3V net | Primary: inspect both terminals in copper and supply requirements | Do not close VCAP finding using only pad-number correction |
| C-07 | SF12 firmware command is outside the current RYLR998 guide; installed module model is unconfirmed | RF/firmware owner: identify module and capture AT replies/readback | No range/latency claim until actual settings are established |

## Future product decisions (not needed to complete source review)

1. Handheld communication: **Jay selected voice plus text and location.** Compare live push-to-talk and recorded voice; establish range, speech quality, delay and RC-coexistence requirements before radio selection. No fallback to text-only without a user decision.
2. Required control latency, operating distance, antenna height and region: measure/confirm before selecting radio parameters or promising range.
3. Battery and ESC/BEC/servo specifications: record exact parts and voltage/current envelope before V2 power design.
4. Preferred first deliverable: complete the faithful V1 baseline and readable documentation before the modular platform hardware.

These are queued decisions, not unanswered requests that prevent current independent analysis.

## Primary intake of Codex findings — 2026-09-17

- C-01 released: commit `639e08f`, paths and validation in HANDOFF.md. C-02 accepted: acceptance fixture is pin-set equality against pstxnet.dat (44 parts, 32 nets + 37 NC pins), 66.548 x 37.313 mm outline. C-03 accepted: drill is inferred from v5 pad flashes and labelled as such everywhere. C-05 fixed (CANL/CANH). C-06 confirmed as V1 defect R07. C-04, C-07 carried into Phase B.
- Decisions needed from Jay (defaults in REPORT.md when written): installed LoRa module model (RYLR896 vs RYLR998), battery chemistry/cell count, ESC BEC voltage and whether the servo is powered from the ESC BEC or the 3.3 V header pin, keep or drop CAN, IMU choice, connector family, mounting pattern, handheld voice mode (live PTT vs recorded).

## Decisions needed from Jay — 2026-09-16 (primary agent; defaults in use, details in docs/V2_REQUIREMENTS.md §7)

| # | Decision | Default used meanwhile |
|---|---|---|
| 1 | Installed LoRa module: RYLR998 (SF5-11, 22 dBm, 5-pin) or RYLR896 (SF7-12, 15 dBm, 6-pin)? V2: RYLR998_M4 (I-PEX) or a discrete SX1262? | RYLR998_M4 on the 5-pin pinout + SMA bulkhead |
| 2 | Battery chemistry / cell count; ESC fed through the board or directly from the battery? | 2S-6S LiPo; ESC direct from the battery; board <= 1 A |
| 3 | Servo power: ESC BEC through the SERVO header, or on-board 5 V buck? | BEC through the header + OR-ing diode; 5 V buck as populate option |
| 4 | Keep CAN? | Dropped (frees PA11/PA12 for USB) |
| 5 | IMU | ICM-20948 on I2C |
| 6 | Connector family | JST XH for power/actuators, 2.54 mm headers for GNSS/LoRa modules |
| 7 | Mounting pattern / enclosure | 4 x M3 on 60 x 30 mm, board 70 x 40 mm |
| 8 | Debug console | USB-C CDC (needs the HSE crystal, which V2 adds anyway) |
| 9 | Handheld voice mode (live PTT vs recorded) - only affects the boat radio if voice shares the boat's channel | Boat radio designed for RC + telemetry only |
| 10 | Is the original fab-house zip (real v5 drill, stack-up) available? | Drill inferred from v5 pads (matches hole-for-hole) |
| 11 | On the working V1 harness: which header is the ESC plugged into, and is the header power pin (pin 1, +3V3) connected to anything? | Assumed ESC on STEERINGSERVO, servo on SPEEDCONTROLLER, pin 1 unconnected (F-CTL-01) |
