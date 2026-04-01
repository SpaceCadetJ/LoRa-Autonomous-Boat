# Netlist Reference — LoRa Autonomous Boat Controller

Extracted from Allegro Specctra DSN (`senior design v2.dsn`). Net names in parentheses are the original OrCAD auto-generated names.

---

## Power Nets

### GND (Allegro net: `0`)
Ground plane — connects to every IC ground pin, decoupling cap, connector ground, and test points.

**Pins:** C1-1, C2-1, C3-1, C4-2, C5-1, C6-1, C7-1, C8-1, C9-1, C10-1, C21-1, C22-1, C23-1, COUT1-1, GND-1 (Battery−), U3-12 (VSSA), U3-18 (VSS), U3-31 (VCAP_1), U3-47 (VSS), U3-63 (VSS), U1-1, U5-2, U6-5, R2-2, R6-1, L4-1, SPEEDCONTROLLER-3, STEERINGSERVO-3, CANHEADER-1, JTAG-1, TP5-1, LORAMODULE-5, GPSMODULE-2

### +3V3 (Allegro net: `3.3V`)
Regulated 3.3V rail from the R1240N buck converter.

**Pins:** U3-13 (VDDA), U3-19 (VDD), U3-32 (VDD), U3-48 (VDD), U3-64 (VDD), C2-2, C3-2, C4-1, C5-2, C6-2, C7-2, C8-2, C9-2, C10-2, C14-1, C20-2, CEXT-2, COUT-2, L1-2, R1-1, L3-2, SPEEDCONTROLLER-1, STEERINGSERVO-1, GPSMODULE-1, JTAG-3, JTAG-5, JTAG-9, TP4-1

### VIN_RAW (Allegro net: `N088060`)
Battery input voltage — feeds the buck converter and ADC voltage divider.

**Pins:** VIN-1 (Battery+), CIN-2, U6-2, R4-1, R5-1

### GND_BAT (Allegro net: `GND`)
Battery ground terminal.

**Pins:** CIN-1

---

## Power Supply (R1240N Buck Converter)

### EN (Allegro net: `N055670`)
Enable pin for the R1240N regulator.

**Pins:** U6-1, R4-2

### SW_NODE (Allegro net: `N18028`)
Switching node — inductor/diode connection.

**Pins:** U6-3, U1-3, C12-1, L1-1

### BST (Allegro net: `N17942`)
Bootstrap capacitor node.

**Pins:** U6-4, R3-2

### FB_DIV (Allegro net: `N17576`)
Feedback voltage divider node.

**Pins:** U6-6, C14-2, R1-2, R2-1

### COIL_SENSE (Allegro net: `N061071`)
Current sense / inductor-side filter.

**Pins:** R3-1, C12-2

### VREG_OUT (Allegro net: `N068040`)
Regulator output before the output caps.

**Pins:** COUT-1, COUT1-2

### ADC_VBAT (Allegro net: `ADC`)
Battery voltage ADC measurement via resistor divider (R5/R6).

**Pins:** U3-16 (PA2), R5-2, R6-2, TP2-1

### VCAP1 (Allegro net: `N27791`)
Internal voltage regulator capacitor for STM32.

**Pins:** U3-30 (PB11 — Note: This is actually VCAP_1 on pin 31), CEXT-1

---

## LoRa Module Interface

### LORA_TX (Allegro net: `N04477`)
MCU UART4_TX → LoRa module RX.

**Pins:** U3-14 (PA0), LORAMODULE-2

### LORA_RX (Allegro net: `N04485`)
LoRa module TX → MCU UART4_RX.

**Pins:** U3-15 (PA1), LORAMODULE-3

### LORA_RST (Allegro net: `N24517`)
LoRa module reset.

**Pins:** U3-17 (PA3), LORAMODULE-4

### LORA_VCC (Allegro net: `N04429`)
Filtered 3.3V supply for LoRa module (through ferrite beads L3/L4 with decoupling).

**Pins:** LORAMODULE-1, L3-1, C21-2, C22-2, C23-2

### LORA_FILT (Allegro net: `N27410`)
Intermediate node between ferrite beads and bulk cap.

**Pins:** L4-2, C20-1

---

## GPS Module Interface

### GPS_RX (Allegro net: `N04277`)
MCU PB0 → GPS module (data to GPS). Note: firmware uses USART3 on PC10/PC11.

**Pins:** U3-26 (PB0), GPSMODULE-3

### GPS_TX_PC11 (Allegro net: `N04281`)
GPS TX → MCU USART3_RX.

**Pins:** U3-52 (PC11), GPSMODULE-4

### GPS_TX_PC10 (Allegro net: `N04285`)
MCU USART3_TX → GPS module.

**Pins:** U3-51 (PC10), GPSMODULE-5

---

## CAN Bus (TCAN1042H)

### CAN_TX (Allegro net: `N04755`)
MCU CAN_TX → TCAN1042H TXD.

**Pins:** U3-44 (PA11), U5-8 (Note: pin 8 = STB on TCAN1042; verify pinout)

### CAN_RX (Allegro net: `N04759`)
TCAN1042H RXD → MCU CAN_RX.

**Pins:** U3-43 (PA10), U5-4

### CAN_STB (Allegro net: `N04763`)
TCAN1042H standby pin.

**Pins:** U3-45 (PA12), U5-1

### CANH (Allegro net: `N04855`)
CAN High bus line.

**Pins:** U5-6, CANHEADER-4

### CANL (Allegro net: `N24691`)
CAN Low bus line.

**Pins:** U5-7, CANHEADER-3

### CAN_VCC (Allegro net: `N24886`)
CAN transceiver VCC.

**Pins:** U5-3, C1-2, CANHEADER-2

---

## PWM Outputs

### PWM_MOTOR (Allegro net: `N04355`)
Motor ESC PWM signal (TIM3_CH1, 50 Hz, 1000–2000 µs).

**Pins:** U3-41 (PA8 — Note: firmware uses PC6/TIM3_CH1), SPEEDCONTROLLER-2, TP1-1

### PWM_RUDDER (Allegro net: `N04395`)
Rudder servo PWM signal (TIM1_CH1, 50 Hz, 1100–1900 µs).

**Pins:** U3-37 (PC6 — Note: firmware uses PA8/TIM1_CH1), STEERINGSERVO-2, TP3-1

> **Note:** The schematic pin assignments for motor/rudder appear swapped relative to the firmware. The firmware assigns TIM3_CH1/PC6 to motor and TIM1_CH1/PA8 to rudder. Verify against the actual board routing.

---

## Debug / JTAG

### SWDIO (Allegro net: `'PA13`)
SWD data.

**Pins:** U3-46 (PA13), JTAG-10

### SWCLK (Allegro net: `'PA14`)
SWD clock.

**Pins:** U3-49 (PA14)

### JTDI (Allegro net: `'PA15`)
JTAG TDI.

**Pins:** U3-50 (PA15), JTAG-4

### JTDO_SWO (Allegro net: `'PB3`)
JTAG TDO / SWO trace output.

**Pins:** U3-55 (PB3), JTAG-6

### JTAG_TCK (Allegro net: `PA14TCLK`)
JTAG TCK routed to header.

**Pins:** JTAG-8

### NRST (Allegro net: `RESET`)
MCU reset.

**Pins:** U3-7, JTAG-2

### VBAT (Allegro net: `VBAT`)
Battery backup for RTC.

**Pins:** U3-1
