# V2 firmware plan (boat node)

Written 2026-09-16. `firmware/` (V1, `main.c`) is not modified beyond comments. V2 firmware lives in `firmware_v2/` as a new STM32CubeIDE project when Phase C hardware is frozen; until then this plan is the specification. Requirement IDs refer to `docs/V2_REQUIREMENTS.md`; defect IDs to `docs/research/FIRMWARE_REVIEW_NOTES.md` §10 (S/F/R/N) and `docs/V1_DESIGN_REVIEW.md`.

## 1. Pin map (STM32F446RET6, LQFP-64) — V2 default

Derived from the V2 schematic defaults (decisions 1-8 in `docs/V2_REQUIREMENTS.md` §7 change rows marked *opt*). One table drives the `.ioc`, the schematic net names and this file (REQ-CTL-06).

| Function | Pin | AF / peripheral | Direction, level | Notes |
|---|---|---|---|---|
| ESC PWM | PC6 | TIM3_CH1 | out, 3.3 V → 5 V level shifter | net `PWM_ESC`; header "ESC" (V1 used PA8 for this header) |
| SERVO PWM | PA8 | TIM1_CH1 | out, 3.3 V → 5 V | net `PWM_SERVO`; header "SERVO" |
| LoRa UART | PA0 TX / PA1 RX | UART4, 115200 8N1, DMA RX circular | 3.3 V | series 100 Ω; `LORA_NRST` = PA3 (out, open-drain, 100 kΩ pull-up in module) |
| GNSS UART | PC10 TX / PC11 RX | USART3, 115200, DMA RX circular | 3.3 V | dedicated to the GNSS (REQ-NAV-04) |
| GNSS PPS | PB0 | TIM3_CH3 input capture (or EXTI0) | in | replaces V1's GPIO output on this header pin |
| Console | PA11/PA12 USB OTG_FS D−/D+ (opt: USART1 PA9/PA10 header) | USB CDC | — | needs HSE (REQ-MCU-03) |
| IMU | PB6 SCL / PB7 SDA | I2C1 400 kHz; INT on PB5 | 3.3 V | ICM-20948 default |
| Battery V | PA2 | ADC1_IN2 | analog | 30 k/10 k → 1 %; scale for ≤ 26 V (REQ-PWR-05) |
| Board current | PA4 | ADC1_IN4 | analog | shunt amplifier (REQ-PWR-06) |
| LEDs | PC0 PWR (hardware), PC1 LINK, PC2 FIX, PC3 FAULT | GPIO out | — | |
| User button | PC13 | EXTI13, pull-up | in | |
| HSE | PH0/PH1 | 8 MHz crystal | — | SYSCLK 84-180 MHz via PLL; `RCC_CSS` on |
| LSE | PC14/PC15 | 32.768 kHz (opt) | — | RTC timestamps |
| SWD | PA13 SWDIO, PA14 SWCLK, PB3 SWO | | | 10-pin Cortex; PA15 freed (SWD only) |
| CAN (opt) | PA11 CAN1_RX / PA12 CAN1_TX, STB on PB1 | CAN1 | | mutually exclusive with USB; default dropped (decision 4) |
| VBAT, BOOT0 | — | | | VBAT → VDD; BOOT0 10 kΩ to GND |

## 2. Failsafe and watchdog behaviour (REQ-CTL-01..04)

State machine: `DISARMED` (outputs: ESC 1000 µs, servo 1500 µs) → `ARMED` on an accepted `ARM` command with thrust = 0 and link age < 200 ms → `FAILSAFE` when command age > `T_loss` (default 1000 ms), battery below the failsafe threshold, IMU/GNSS fault while in an autonomous mode, or watchdog-reset flag → back to `DISARMED` only by explicit disarm after the fault clears. In `FAILSAFE`: ESC 1000 µs within 20 ms, servo 1500 µs, LINK LED off, FAULT LED on, telemetry every 1 s with the reason.

- Command age is measured from the last packet that passed sender, CRC and sequence checks (REQ-RF-06); packets that fail are counted, never applied.
- IWDG: LSI 32 kHz, prescaler 32, reload 500 → ~500 ms; kicked only from the main loop when the 50 Hz scheduler, the UART DMA and the ADC have all run in the last 100 ms.
- Boot: PWM pins configured as outputs LOW before the clock tree; the ESC pull-down keeps the line at 0 V through reset. Startup CCR values come from the same header the setpoint code uses (fixes R2/R5 in the V1 review); `.ioc` pulse fields set to the same values and `main()` fully inside USER CODE blocks (REQ-FW-02).
- Reset cause (`RCC->CSR`) is logged and sent in the first telemetry frame.

## 3. Protocol (REQ-RF-03/06/07)

Command packet, 8 bytes payload, handset → boat at 10 Hz (SF7) / 5 Hz (SF9):

| Byte | Field |
|---|---|
| 0 | version (0x01) / flags: bit0 ARM, bit1 DISARM, bit2 MODE (0 manual, 1 heading hold), bit3 profile change request |
| 1 | thrust 0..200 (0.5 % steps) |
| 2 | rudder 0..200 (0.5 %) |
| 3 | heading setpoint / 2 (0..179 → 0..358°) or aux |
| 4 | sequence 0..255 |
| 5 | reserved (SF profile index when bit3 set) |
| 6-7 | CRC-16/CCITT over bytes 0-5 |

Telemetry, boat → handset at 1 Hz, ≤ 20 bytes: state, command age (10 ms units), battery (0.1 V), board current (10 mA), fix status/age, lat/lon (int32 1e-7°), heading (0.5°), RSSI/SNR of the last command, reject count, reset cause. Everything binary; the RYLR carries it as the `AT+SEND` payload (the module's own framing adds 8 bytes).

## 4. Drivers

| Driver | Hardware | Key requirements |
|---|---|---|
| `lora_rylr` | UART4 DMA, NRST GPIO | boot: pulse NRST, wait `+READY` (timeout 2 s), `AT+VER`, set ADDRESS/NETWORKID/BAND/PARAMETER/CRFOP, read back `AT+PARAMETER?` and compare; every command waits for `+OK`/`+ERR` with timeout; `+RCV` frames parsed with length field, address check, CRC (REQ-RF-01/06); RSSI/SNR captured |
| `gnss_nmea` | USART3 DMA ring buffer, PPS capture | RMC+GGA (+ UBX-NAV-PVT if u-blox), checksum, field-count independent of empty fields (fixes V1 defect A), fix age, PPS timestamping (REQ-NAV-01..03) |
| `imu` | I2C1, INT | accel+gyro+mag at 100 Hz, tilt-compensated heading, hard/soft-iron calibration stored in flash |
| `actuators` | TIM1/TIM3 | 50 Hz, 1 µs resolution from a PLL-derived timer clock, limits/trim from config, safe values at init |
| `power` | ADC1 (DMA, 100 Hz), LEDs | battery/current with 1 s moving average, thresholds with hysteresis |
| `console` | USB CDC (or USART1) | line-based shell: `stat`, `cfg`, `arm`, `log`, `loraat` passthrough while disarmed |
| `supervisor` | IWDG, state machine | §2 |

## 5. Link-loss test procedure (acceptance for REQ-CTL-01/02/03)

1. Bench: boat board on a lab supply, ESC replaced by a logic analyser on the ESC and SERVO signal lines (or a real ESC with the motor removed), handset sending 10 Hz commands with thrust 50 %, rudder 30 %.
2. Switch the handset off. Expected: ESC line returns to a 1000 µs pulse and the servo to 1500 µs between `T_loss` and `T_loss` + 20 ms after the last packet's end-of-air; FAULT LED on; telemetry reports state = FAILSAFE, reason = LINK. Record the measured interval for 10 trials.
3. Switch the handset back on with thrust still at 50 %. Expected: outputs stay at idle/neutral; the boat reports DISARMED; only an ARM command with thrust 0 re-arms.
4. Repeat with (a) the handset transmitting corrupted frames (wrong CRC), (b) a second handset on the same network ID with a different address, (c) the LoRa module held in reset — outputs must go/stay safe in every case, and the reject counter must increment for (a) and (b).
5. Pull the IWDG kick (debug command) — outputs go safe within 500 ms + boot time, and the reset cause is logged.
6. Brown-out: ramp the supply down to 2.5 V and back up 20 times — no ESC pulse > 1000 µs at any point (scope with persistence).

## 6. Order of work

1. `.ioc` from the pin table above; HAL project with USER CODE discipline; console + LEDs (day 1).
2. Actuators + supervisor + IWDG + failsafe test (day 2) — this alone would have prevented the V1 safety defects.
3. LoRa driver with readback and the binary protocol; handset firmware update (day 3-4).
4. GNSS DMA parser + PPS; IMU; heading hold (week 2).
5. Telemetry/logging, configuration in flash, waypoint following (week 3).
