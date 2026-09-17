# V2 requirements — LoRa Autonomous Boat Controller

Written 2026-09-16. Each requirement is numbered, testable, and traces to a finding in `V1_DESIGN_REVIEW.md` (F-xxx) or to the mission (M). "Verify" says how the requirement is checked. Values marked **[default]** are the assumptions used to proceed while the decisions in §7 are open; they change if Jay decides otherwise.

Mission (M): an RC-scale autonomous surface vessel that takes thrust/rudder commands from a handheld over a 915 MHz LoRa link, reports position, and can hold heading / follow waypoints; a future handheld adds voice + text + location (see `reviews/codex/PLATFORM_CONCEPT.md`).

## 1. Radio link (REQ-RF)

| ID | Requirement | Trace | Verify |
|---|---|---|---|
| REQ-RF-01 | The LoRa module model and firmware version shall be identified at boot (`AT+VER`), every configuration command shall be acknowledged, and the resulting parameters read back (`AT+PARAMETER?`) and logged before the link is declared up. | F-RF-03, F-RF-06 | Bench: swap module, inject `+ERR`, confirm the node refuses to arm with wrong parameters |
| REQ-RF-02 | Operating point: SF7 or SF8, BW 125 kHz, CR 4/5 **[default SF7]**, with automatic fallback to SF9/SF10 when the handset RSSI < −110 dBm for > 5 s, and recovery when > −100 dBm for > 10 s. Both ends switch together via a signalled profile change. | F-RF-02, §2.2 | Range test with attenuator; log SF transitions |
| REQ-RF-03 | One command packet carries thrust, rudder, arm flag, 8-bit sequence number and CRC-8 in ≤ 8 payload bytes; handset sends it at ≥ 5 Hz **[default 10 Hz at SF7]**; telemetry ≤ 1 Hz and never longer than 120 ms on air at the current SF. | F-RF-02, F-RF-05 | Logic analyser on the module UART: command period and telemetry duration |
| REQ-RF-04 | The board provides a 50 Ω antenna port (SMA or u.FL bulkhead) with a controlled-impedance feed ≤ 20 mm long and a copper/component keep-out of ≥ 5 mm around the feed and connector; no antenna sits on the module header. **[default: RYLR998_M4 (I-PEX) on the existing 1×5 pinout, u.FL-to-SMA pigtail to a 2 dBi whip]** | F-RF-04, §2.1 | Impedance by TDR/VNA or by stack-up calculation record; range test ≥ 1.5 km over water at SF7 with 12 dB margin |
| REQ-RF-05 | The buck converter, ESC cabling and servo cabling shall be ≥ 25 mm from the antenna feed; the copper pour is voided under the module on both layers. | F-RF-04 | Layout review; DRC keep-out rule areas |
| REQ-RF-06 | Every received command shall be rejected unless it has the expected sender address, a valid CRC, and a sequence number newer than the last accepted one (modulo 256); rejected packets are counted and reported in telemetry. | F-RF-05 | Fuzz the UART with corrupted frames; count rejects, confirm no actuator change |
| REQ-RF-07 | Link statistics (RSSI, SNR, reject count, command age) are available in telemetry and on the console. | F-RF-05 | Read telemetry |

## 2. Control and safety (REQ-CTL)

| ID | Requirement | Trace | Verify |
|---|---|---|---|
| REQ-CTL-01 | If no valid command is accepted for `T_loss` **[default 1.0 s]**, thrust goes to idle (1000 µs) and rudder to neutral (1500 µs) within 20 ms of the timeout and stays there until a fresh arm sequence. | F-RF-01 | Logic analyser on both PWM pins while the handset is switched off; measure time from last packet to idle pulse |
| REQ-CTL-02 | The independent watchdog (IWDG) runs from the LSI with a ≤ 500 ms window; a watchdog or fault reset drives both PWM outputs to idle/neutral before any radio traffic is processed; fault handlers set outputs safe and reset within 100 ms. | F-MCU-06 | Force a fault (stack overflow test), verify outputs and reset cause in the boot log |
| REQ-CTL-03 | At power-on, reset and brown-out the PWM pins are held so that the ESC sees ≤ 1000 µs or no pulse (pull-down on the ESC signal line) and the servo sees no pulse until firmware is running. | F-CTL-03, F-CTL-04 | Scope both pins through 20 power cycles and 10 resets |
| REQ-CTL-04 | The vehicle has states Disarmed / Armed / Failsafe (`reviews/codex/PLATFORM_CONCEPT.md`); arming requires an explicit handset command with the throttle at zero; reconnect after link loss does not re-arm. | F-CTL-03 | State-machine test vectors |
| REQ-CTL-05 | ESC and servo signal outputs pass through a 100 Ω series resistor and a TVS (working voltage 5 V); the outputs are 5 V-capable (level shifter or open-drain with pull-up to the actuator rail) so the ESC's 5 V logic threshold is met. | F-CTL-02 | ESD gun ±8 kV contact on the header; ESC arms reliably |
| REQ-CTL-06 | Net names, header silkscreen and firmware pin defines use the same function names (ESC, SERVO) derived from one pin table (`firmware/V2_FIRMWARE_PLAN.md`); the schematic, board and `.ioc` are generated/checked from that table. | F-CTL-04 | `check_netlist.py` equivalent for V2 + a pin-table diff in CI |
| REQ-CTL-07 | Rudder and thrust limits, trim and the failsafe values are configuration parameters stored in flash, changeable only while disarmed. | M | Console test |

## 3. Power (REQ-PWR)

| ID | Requirement | Trace | Verify |
|---|---|---|---|
| REQ-PWR-01 | Battery input: reverse-polarity protection (P-FET), fuse **[default 3 A blade or PTC on the logic feed]**, 33 V TVS, ≥ 47 µF bulk capacitance; input range 7-25.2 V **[default 2S-6S LiPo; decision 2]**. | F-PWR-01, F-PWR-03 | Reverse the battery for 10 s; surge test; Vin sweep |
| REQ-PWR-02 | Battery terminal rated for the ESC current if the ESC is fed through the board **[default: ESC fed directly from the battery; the board takes ≤ 1 A through an XT30 or 5.08 mm screw terminal]**. | F-PWR-01 | Connector rating vs measured current |
| REQ-PWR-03 | Actuator power rail (servo/ESC BEC, 5-6 V) is a separate net from the 3.3 V logic rail with no DC path between them; the actuator header power pin is that rail, never +3V3. | F-CTL-01 | Continuity/ohmmeter test; back-feed test with 5 V on the header pin while the board is off |
| REQ-PWR-04 | The servo rail is sourced either from the ESC BEC through the SERVO header **[default]** or from an on-board 5 V/2 A buck (populate option); a Schottky OR-ing prevents BEC/board contention. | F-CTL-01 | Power-tree review; both sources connected |
| REQ-PWR-05 | Battery voltage is measured with ≥ 1 % accuracy over 6-26 V through a filtered divider (≤ 10 kΩ source impedance, 100 nF), and the firmware acts on two thresholds (warning, failsafe) with hysteresis. | F-PWR-04 | Calibrated supply sweep |
| REQ-PWR-06 | Board current sense (≤ 3 A, 1 % shunt + amplifier) on the logic feed **[default: fitted]**; ESC current via ESC telemetry UART if the ESC supports it (optional). | F-CTL-05 | Compare with a bench meter |
| REQ-PWR-07 | The 3.3 V rail delivers ≥ 600 mA with ≤ 50 mV ripple at the LoRa module pins during a 145 mA TX burst; LoRa supply keeps the V1 pi-filter with all capacitors returned to GND. | F-PWR-06 | Scope at LORAMODULE pin 1 during `AT+SEND` |
| REQ-PWR-08 | Status LEDs: power, link (blinks on accepted command), GNSS fix, fault/failsafe. | F-PWR-05 | Visual |

## 4. Navigation and sensing (REQ-NAV)

| ID | Requirement | Trace | Verify |
|---|---|---|---|
| REQ-NAV-01 | GNSS module with ≥ 5 Hz update, PPS output, backup power input, on a 1×6 header **[default: u-blox NEO-M8N/M9N-class breakout pinout VCC/GND/TX/RX/PPS/VBAT]** at 115200 baud. | F-NAV-03 | Log rate and PPS with a counter |
| REQ-NAV-02 | PPS is wired to a timer input-capture pin; no GPIO output drives any GNSS header pin. | F-NAV-01 | Pin table review; scope |
| REQ-NAV-03 | GNSS parsing is DMA/ring-buffer based; a fix older than `T_fix` **[default 2 s]** is invalid for control and reported as stale in telemetry. | F-NAV-02 | Replay NMEA with gaps and `V` sentences |
| REQ-NAV-04 | The debug console is a separate UART (see REQ-DBG-01); nothing but GNSS traffic is on the GNSS UART. | F-NAV-02 | Sniff the GNSS RX line |
| REQ-NAV-05 | A 6/9-axis IMU with magnetometer **[default: ICM-20948 or BMI270+BMM150 on I²C/SPI, decision 5]** provides heading at ≥ 50 Hz; magnetometer placed ≥ 15 mm from the buck inductor and ESC cables. | F-NAV-03 | Heading error < 3° after calibration on a turntable |
| REQ-NAV-06 | Heading hold and waypoint following run at 20 Hz with configurable gains; loss of heading source degrades to manual rudder, never to "hold last output". | M | HIL test with logged commands |

## 5. MCU, debug and firmware (REQ-MCU, REQ-DBG, REQ-FW)

| ID | Requirement | Trace | Verify |
|---|---|---|---|
| REQ-MCU-01 | VCAP_1: 4.7 µF X5R/X7R (ESR < 1 Ω) between pin 30 and VSS, within 5 mm of the pin. | F-MCU-01 | Schematic/layout review; 1.2 V ripple scope |
| REQ-MCU-02 | VBAT tied to VDD (100 nF); BOOT0 pulled to GND with 10 kΩ and jumper-able to VDD. | F-MCU-02 | Continuity |
| REQ-MCU-03 | 8 MHz (or 25 MHz) HSE crystal with load capacitors per DS10693; USB and UART timing derive from it; HSI remains as fallback with a logged clock-security event. | F-MCU-03 | Measure MCO; UART error < 0.2 % |
| REQ-MCU-04 | 32.768 kHz LSE footprint (populate option) for RTC timestamps **[default: fitted]**. | F-MCU-03 | RTC drift |
| REQ-MCU-05 | NRST has 100 nF to GND and is available on the debug header and a push-button. | F-MCU-04 | — |
| REQ-DBG-01 | A dedicated console: USB-C (USB FS, device) **[default]** or a 3-pin 3.3 V UART header; SWD via the same 10-pin Cortex connector as V1. | F-MCU-05 | Enumerates as CDC; SWD attach |
| REQ-DBG-02 | Four status LEDs (REQ-PWR-08) and one user button. | F-PWR-05 | — |
| REQ-DBG-03 | Test points on: ESC signal, SERVO signal, 3V3, actuator rail, VIN, GND, PPS — labelled on silkscreen. | F-MECH-04 | — |
| REQ-DBG-04 | LoRa NRST is driven by the MCU; the driver waits for `+READY`, checks every reply, and reports failures on the console. | F-RF-06 | Hold the module in reset; watch the recovery |
| REQ-FW-01 | Firmware plan (`firmware/V2_FIRMWARE_PLAN.md`): DMA UARTs with error callbacks, command timeout, IWDG, arm state machine, GNSS fix age, ADC battery, link-loss test procedure. `main.c` of V1 is not modified. | F-MCU-06, F-RF-01 | Plan reviewed; V2 firmware project separate |
| REQ-FW-02 | A regenerated CubeMX project must not change startup pulse values or NVIC settings (all user code inside USER CODE blocks; `.ioc` and code agree). | F-CTL-04 | Regenerate and diff |

## 6. Mechanical, manufacturing and CAN (REQ-MECH, REQ-CAN)

| ID | Requirement | Trace | Verify |
|---|---|---|---|
| REQ-MECH-01 | Four M3 mounting holes (3.2 mm, 6 mm keep-out) on a rectangular pattern **[default 60 × 30 mm on a 70 × 40 mm board; decision 7]**, board size ≤ 76.2 × 76.2 mm. | F-MECH-01 | Drill check |
| REQ-MECH-02 | All connectors on two opposite edges, keyed (JST XH/PH or locking headers) **[default: JST XH for power/actuators, 2.54 mm headers with polarity marks for modules; decision 6]**; the board accepts conformal coating (no exposed adjustable parts). | F-MECH-05 | Assembly review |
| REQ-MECH-03 | Design rules: 6 mil track / 6 mil clearance minimum, 8 mil pour clearance, 12 mil signal tracks where possible, 20 mil power, 0.3/0.6 mm vias; DRC 0 errors with the project's rule file and no exceptions. | F-MECH-02 | `kicad-cli pcb drc` |
| REQ-MECH-04 | Vias tented or with 1:1 mask; no pour copper of another net inside a via's mask opening. | F-MECH-03 | DRC solder-mask bridge = 0 |
| REQ-MECH-05 | Silkscreen: refdes and function labels for every connector pin 1 and every test point, diode polarity marks, no silk over pads; two fiducials. | F-MECH-04 | DRC silk checks = 0 |
| REQ-CAN-01 | **[default: CAN dropped; decision 4]**. If kept: a 3.3 V-capable transceiver (TCAN334G or TCAN1044AV with VIO) on CAN1_RX = PA11 / CAN1_TX = PA12, STB on a GPIO with pull-down, 120 Ω termination jumper, ESD. | F-CAN-01 | Loopback with a second node |

## 7. Decisions needed from Jay (defaults used meanwhile)

| # | Decision | Default used | What changes if you choose otherwise |
|---|---|---|---|
| 1 | Which LoRa module is installed on V1 and wanted for V2: RYLR998 (SF5-11, 22 dBm, 5-pin), RYLR896 (SF7-12, 15 dBm, 6-pin), or a discrete SX1262 module? | RYLR998_M4 (I-PEX) on the 5-pin header + SMA | RYLR896: header becomes 6-pin, SF12 allowed, 7 dB less power. SX1262: SPI driver, RF layout, best control |
| 2 | Battery chemistry and cell count; is the ESC fed from the board or directly from the battery? | 2S-6S LiPo; ESC direct from battery; board ≤ 1 A | > 6S: input parts change (D21, CIN, R1240N limit 30 V). ESC through the board: terminal ≥ 30 A, fuse sizing |
| 3 | Servo power: from the ESC BEC through the SERVO header, or on-board 5 V buck? | BEC through the header + OR-ing diode | On-board buck adds ~$3 and 200 mm² |
| 4 | Keep CAN? | Drop (frees PA11/PA12, no 5 V needed) | Keep: 3.3 V transceiver, on PA11/PA12, termination |
| 5 | IMU choice | ICM-20948 (9-axis, I²C) | BMI270+BMM150, or an external module header only |
| 6 | Connector family | JST XH (power/actuators), 2.54 mm headers for GNSS/LoRa modules | JST GH/PH for compactness; screw terminals for battery |
| 7 | Mounting pattern / enclosure | 60 × 30 mm M3 pattern, 70 × 40 mm board | Enclosure drawing dictates |
| 8 | Debug console | USB-C CDC | UART header only (no HSE-dependent USB) |
| 9 | Handheld voice mode (live PTT vs recorded messages) — affects V2 radio only if voice must share the boat's channel | Boat V2 radio designed for RC + telemetry; voice on the handheld's own link | Shared channel: RF-02/03 timing changes, second radio study |
| 10 | Do you have the fab-house zip for v5 (real drill file, stack-up)? | Drill inferred from v5 pads | Adds certainty to the V1 baseline only |
