# Datasheet research notes — STM32 boat-controller PCB review

Compiled 2026-09-16 from the current manufacturer documents (or the newest copy that could actually be retrieved; where a newer revision exists but could not be downloaded, that is stated). Page numbers are PDF page numbers of the cited document. "NOT FOUND" means the fact is not in the cited document(s), not that it is false.

Retrieval notes that affect trust:
- st.com, toshiba.semicon-storage.com (Akamai) and product.tdk.com refuse non-browser downloads; where a mirror was used it is named, and the manufacturer's current revision/date is recorded from the manufacturer's product page.
- All PDFs were text-extracted with pypdf and drawings were rendered and read visually (PyMuPDF), so pin numbers/land patterns below come from the drawings, not from distributor summaries.

---

## 1. Nisshinbo (ex-Ricoh) R1240N001B-TR-FE — 1.2 A / 30 V asynchronous step-down DC/DC, SOT-23-6W

- Manufacturer: Nisshinbo Micro Devices Inc. (the former Ricoh Electronic Devices "R" product line; DigiKey lists the part under Nisshinbo).
- Exact MPN: R1240N001B-TR-FE.
- Datasheet: "R1240x Series 1.2 A, 30 V Step-Down DC/DC Converter", document NO.EA-190-240903 (2024-09-03; PDF created 2024-09-11), 22 pp. URL: https://www.nisshinbo-microdevices.co.jp/en/pdf/datasheet/r1240-ea.pdf (linked from https://www.nisshinbo-microdevices.co.jp/en/products/dc-dc-switching-regulator/spec/?product=r1240).

Facts:
- Topology: ASYNCHRONOUS. Only an internal N-ch high-side switch (RON 0.35 Ω typ); the converter is built "with the following external components: an inductor, resistors, a diode, and capacitors" (p.1 OUTLINE). The basic-circuit figure shows an external freewheel diode (p.6) and the recommended-parts table lists D = CMS06 or CMS11 (Toshiba) (p.7, p.11). There is no synchronous low-side FET. A catch Schottky from Lx to GND is mandatory.
- Note on the series description: switching frequency is 1.25 MHz typ (1.0–1.5 MHz min/max), not 1.5 MHz (p.1, p.5 "fosc"). Fold-back (B version) frequency 310 kHz when VFB < 0.56 V (p.5).
- Input voltage: 4.5–30 V operating (p.1 FEATURES; p.4 Recommended Operating Conditions); VIN abs max −0.3 to 32 V (p.4).
- Max output current: 1.2 A (p.1). Peak current limit 2.0 A typ; ILX abs max 2 A (p.4, p.5). Min on-time 100 ns typ (p.5, p.10).
- Feedback reference: VFB = 0.800 V ±1.5 % (0.788–0.812 V), ±150 ppm/°C (p.5). Output formula: VOUT = VFB × (R1 + R2) / R2; recommended R2 ≈ 1.2–16 kΩ (p.9). Recommended-values table: R1 = (VOUT/0.8 − 1) × 1.2 kΩ with R2 = 1.20 kΩ; for 3.3 V the typical circuit uses R1 = 3.75 kΩ, R2 = 1.2 kΩ, CSPD = 470 pF (+ optional 5.1 kΩ) (p.7, p.11).
- Recommended externals (p.7 typical circuit, p.11 table): CBST = 0.1 µF/50 V (Murata GRM21BB11H104KA01L) in series with RBST = 51 Ω between BST and Lx; L = 4.7 µH for 1.8 V ≤ VOUT < 5 V (TDK SLF7045T-4R7M2R0-PF; 2.2 µH below 1.8 V, 4.7–10 µH ≥ 5 V, p.9); CIN ≥ 10 µF ceramic (10 µF/50 V: Taiyo Yuden UMK325BJ106MM-P, TDK CGA6P3X7S1H106K, or Nippon Chemi-Con KTS500B106M55N0T00); COUT ≥ 10 µF for VOUT ≥ 1.8 V (10 µF/25 V Murata GRM31CR71E106K), ≥ 20 µF below 1.8 V (p.9, p.11); D = CMS06 (30 V/2 A, 0.32 V) or CMS11 (40 V/2 A) (p.11). Diode guidance: Schottky with total capacitance ≤ 100 pF at VR = 10 V; if VF > 0.7 V at 4–5 A the Lx pin can exceed its negative rating on an output short (p.9).
- SOT-23-6W pinout (p.3, "R1240N001x Pin Description"): 1 = CE (chip enable, active "H"), 2 = VIN, 3 = Lx, 4 = BST, 5 = GND, 6 = VFB. Pin 1 is at the dot; pins 1-2-3 down the left side, 6-5-4 down the right side (top view).
- CE thresholds: VCEH ≥ 1.6 V, VCEL ≤ 0.3 V; ICEH/ICEL = ±1 µA (p.5) — i.e. NO internal pull-up/down; CE must be driven or tied. An ESD diode exists from CE to VIN; if CE can exceed VIN add ~5 kΩ in series (p.11 "RCE").
- UVLO: detect (falling) 3.8 V typ (3.6–4.0), release (rising) VUVLO1 + 0.2 V typ, 4.2 V max (p.5). Thermal shutdown 160 °C typ, 30 °C hysteresis (p.5). Standby current 0 typ / 5 µA max (p.5).
- Package thermal: SOT-23-6W PD = 430 mW on the standard land pattern, θja ≈ 233 °C/W (p.4, p.16). Tj −40..125 °C, Ta −40..85 °C (p.4).
- Part-number decoding (Selection Guide p.2 and marking p.18): R1240 = series; N = SOT-23-6W package (K = DFN(PL)2527-10); 001 = product/version code for the SOT-23-6W version (003 for the DFN); trailing letter = short-protection option, A = latch (2 ms delay), B = fold-back → "001B" = fold-back version, and it is NOT a fixed-output code — every R1240 is adjustable 0.8–15 V via R1/R2 (p.1). Marking on SOT-23-6W: R1240N001B = product code "8B" (p.18). "-TR" = tape & reel, 3000 pcs (p.2). "-FE" is not decoded in the datasheet (NOT FOUND; the selection guide only lists the full string "R1240N001x-TR-FE" as Pb-free/halogen-free "Yes").

## 2. Texas Instruments TCAN1042H-Q1 (orderable TCAN1042HDRQ1, SOIC-8 "D")

- Manufacturer: Texas Instruments. Exact MPN: TCAN1042HDRQ1 (Active, SOIC D, 2500/reel, -55 to 125 °C, per orderable addendum at the end of the datasheet).
- Datasheet: "TCAN1042-Q1 Automotive Fault Protected CAN Transceiver with CAN FD", SLLSES9D, February 2016 – revised October 2021 (Rev. D; TI product page shows "Rev. D, Oct 28 2021"). Covers TCAN1042-Q1/V/H/HV/G/GV/HG/HGV-Q1. URL: https://www.ti.com/lit/ds/symlink/tcan1042h-q1.pdf. (Note: the family datasheet number is SLLSES9, not SLLSER7.)

Facts:
- SOIC-8 pin table (Table 6-1, p.5; Figure 6-1 top view): 1 TXD (digital in, LOW = dominant), 2 GND, 3 VCC (5 V transceiver supply), 4 RXD (digital out, LOW = dominant), 5 NC on Base/H/G/HG devices — VIO only on "V"-suffix devices, 6 CANL, 7 CANH, 8 STB (standby control input, active high). Block-diagram note A (p.1): "Terminal 5 function is device dependent; NC on devices without the 'V' suffix".
- VCC range: 4.5–5.5 V (Recommended Operating Conditions §7.4, p.8). 3.3 V on VCC is NOT allowed; UVCC falling threshold 3.8–4.25 V puts the part in protected mode (p.9, Table 9-1 p.20). VIO 3–5.5 V exists only on V variants; the H variant has no VIO (pin 5 = NC).
- RXD output level on the H (non-V) part: referenced to VCC — VOH 4.0 V min / 4.6 V typ at IO = −2 mA, VOL 0.2/0.4 V (§7.7 RXD terminal, p.10); block-diagram note B: "RXD logic output is driven to VCC on devices without the 'V' suffix". So RXD is a 5 V output; the MCU RXD pin must be 5 V tolerant (STM32 PA11 is FT, see §5).
- TXD input thresholds (non-V devices): VIH ≥ 2 V, VIL ≤ 0.8 V (§7.7 TXD terminal, p.9). 3.3 V CMOS drive is therefore acceptable on TXD (and STB, same thresholds). TXD has an internal pull-up to VCC (§9.3.5 p.20; footnote 2 to the mode table p.22; §11 p.29). IIL at TXD = 0 V is −100 to −7 µA (p.9).
- STB polarity: HIGH = Standby (driver and receiver off, bus biased to GND); LOW = Normal (Table 9-3 p.22; §9.4.2/9.4.3 p.23). STB is INTERNALLY PULLED UP to VCC "to force the device into low power Standby mode if the terminal floats" (§9.3.5 p.20) — STB must be actively driven low (or tied to GND) to communicate. IIL(STB) at 0 V = −20 to −2 µA (p.9).
- Temperature: AEC-Q100 grade 1 (p.1); electrical characteristics over TA = −55 to 125 °C (p.9); TJ −55 to 150 °C (p.6, p.1); orderable TCAN1042HDRQ1 marked −55 to 125 (addendum).
- Bus fault protection ±70 V for H variants (p.1, p.6). Feature bullet "I/O Voltage range supports 3.3 V and 5 V MCUs" (p.1) refers to the family (V variants supply the level shift); for the H part the practical 3.3 V compatibility is TXD/STB thresholds (TTL) plus a 5 V-tolerant RXD input on the MCU.

## 3. Toshiba CMS06(TE12L,Q,M) — 30 V / 2 A Schottky barrier rectifier, M-FLAT

- Manufacturer: Toshiba Electronic Devices & Storage Corp. Orderable: CMS06(TE12L,Q,M) (Toshiba page lists "CMS06(TE12L,Q" MOQ 3000; TE12L = 12 mm embossed tape, 3000/reel per the M-FLAT package page; the ",Q" and ",M" suffix letters are not decoded on the pages retrieved — NOT FOUND).
- Current datasheet: "CMS06 Data sheet/English", Nov 2013, 155 KB, URL https://toshiba.semicon-storage.com/info/CMS06_datasheet_en_20131101.pdf?did=3138&prodName=CMS06 (product page https://toshiba.semicon-storage.com/us/semiconductor/product/diodes/detail.CMS06.html). Toshiba's server forces a file download and blocks scripted access, so the outline/marking/pad drawings below were read from the 2003-02-17 edition mirrored at https://media.digikey.com/pdf/Data%20Sheets/Toshiba%20PDFs/CMS06.pdf and the ratings were cross-checked against Toshiba's current product page (identical values). Package data also from Toshiba's M-FLAT package page https://toshiba.semicon-storage.com/us/semiconductor/design-development/package/detail.M-FLAT.html.

Facts:
- VRRM = 30 V; IF(AV) = 2.0 A (note: Tℓ = 82.8 °C, rectangular wave 180°, VR = 15 V); IFSM = 40 A (50 Hz, one cycle); Tj −40..125 °C; Tstg −40..150 °C (DS p.1 Maximum Ratings; product page).
- VF: VFM = 0.37 V max / 0.32 V typ at IFM = 2.0 A; 0.28 V typ at 1.0 A; 0.26 V typ at 0.5 A (DS p.1 Electrical Characteristics; product page "VFM (max) 0.37 V").
- IR: IRRM = 3.0 mA max / 1.4 mA typ at VRRM = 30 V; 0.09 mA typ at 5 V (DS p.1; product page "IRRM(MAX) 3 mA @ 30 V"). Junction capacitance Cj = 130 pF typ at VR = 10 V, 1 MHz (DS p.1) — larger than the ≤ 100 pF at 10 V that the R1240 datasheet asks for, even though Nisshinbo lists CMS06 as a recommended diode.
- Rth(j-a) 60 °C/W on ceramic with 2 × 2 mm lands, 135 °C/W on glass-epoxy with 6 × 6 mm lands; Rth(j-l) 16 °C/W (DS p.1).
- Package: Toshiba name "M-FLAT" (Toshiba code 3-4E1A in the datasheet, 3-4E1S on the package page; no JEDEC/JEITA equivalent listed). Overall 2.4 (+0.2/−0.1) wide × 4.7 ± 0.2 long × 0.98 ± 0.1 high; body 3.8 ± 0.1 long; each terminal 1.75 ± 0.1 wide, 0.65 ± 0.2 long, 0.16 thick (DS p.1 outline; package page "2.4×4.7×0.98 mm, 2 pins, surface mount"). Weight 0.023 g.
- Land pattern: datasheet "Standard Soldering Pad" (p.2): two pads 1.4 mm (along the part) × 2.1 mm (across), 3.0 mm gap → 4.4 mm centre-to-centre, 5.8 mm outer extent. Toshiba package page reference land pattern (JEITA ET-7501 level 3): pads 2.1 × 1.4 mm, 4.4 mm centre-to-centre (same geometry).
- Polarity/pin numbering: DS p.1 outline labels ① ANODE and ② CATHODE, i.e. pin 1 = anode, pin 2 = cathode. The cathode is the end carrying the printed CATHODE BAND ("Cathode mark", DS p.2 marking drawing; the band is at the pin-2 end). Marking type code "S6".
- Application: switching-mode power supplies, portable battery equipment (DS p.1).

## 4. onsemi (ex-SANYO) SB007-03Q-TL-E — 30 V / 70 mA Schottky barrier diode, SOT-323 (SC-70), NOT an ESD/TVS device

- Manufacturer: onsemi (Semiconductor Components Industries, LLC; legacy SANYO part, ordering number EN2939B). Exact MPN: SB007-03Q-TL-E.
- Datasheet: "SB007-03Q Schottky Barrier Diode 30V, 70mA, Low IR, Single MCP", September 2013, 5 pp., URL https://www.onsemi.com/download/data-sheet/pdf/sb007-03q-d.pdf (product page https://www.onsemi.com/products/discrete-power-modules/schottky-diodes-schottky-rectifiers/sb007-03q). The datasheet is in English on onsemi.com — not a Japanese-only page.

Facts:
- What it is: a single small-signal Schottky rectifier ("Schottky Barrier Diode ... Single MCP"), applications "High frequency rectification (switching regulators, converters, choppers)" (p.1). It is not a TVS/ESD diode array, so "working voltage / clamping voltage / peak pulse power" are NOT FOUND (not applicable). If the schematic uses it as ESD protection, that is a mis-application: it only has VRRM 30 V, 2 A single-cycle surge, no specified ESD clamp.
- Ratings (p.1 Absolute Maximum, p.2 Electrical, Ta = 25 °C): VRRM 30 V; VRSM 35 V; IO 70 mA; IFSM 2 A (50 Hz, 1 cycle); Tj/Tstg −55..125 °C. VR ≥ 30 V at IR = 20 µA; VF ≤ 0.55 V at IF = 70 mA; IR ≤ 5 µA at VR = 15 V; C = 3.0 pF typ at VR = 10 V, 1 MHz; trr ≤ 10 ns.
- Package: "MCP" = JEITA SC-70 / JEDEC SOT-323 (p.1). Body 2.0 ± 0.2 × 1.25 ± 0.1 mm, 0.9 ± 0.1 high, lead pitch 0.65 mm, overall lead span 2.1 ± 0.1 (p.1, p.4 outline 7023A-005).
- SOT-323 pinout (p.1 "Electrical Connection" and outline): pin 1 = Anode, pin 2 = No Contact (NC), pin 3 = Cathode. Pins 1 and 2 are on one side (0.65 mm apart), pin 3 alone on the opposite side. Marking "G".
- Land pattern example (p.4): three pads 0.7 × 1.0 mm; pins 1/2 pads on 0.65 mm pitch; pin-3 pad centred 2.1 mm from the pin-1/2 pad row (centre-to-centre).

## 5. STMicroelectronics STM32F446RE (DS10693), LQFP64

- Manufacturer: STMicroelectronics. Exact MPN family: STM32F446RET6 (LQFP64, 512 KB).
- Datasheet: DS10693 "STM32F446xC/E — Arm Cortex-M4 32-bit MCU+FPU, 225 DMIPS, up to 512 KB Flash/128+4 KB RAM ...". Current revision per ST's product page (https://www.st.com/en/microcontrollers-microprocessors/stm32f446re.html): Rev 11.0, 29 May 2026, URL https://www.st.com/resource/en/datasheet/stm32f446re.pdf. ST's server timed out on every download attempt, so the facts below were verified in DS10693 Rev 10 (January 2021, 198 pp., mirror: https://storage.googleapis.com/media.amperka.com/products/chip-stm32f446ret6/media/stm32f446re-datasheet.pdf). Rev 10's only change from Rev 9 was an HSI footnote (Table 118, p.197); pinout/AF tables are stable across revisions, but re-check Rev 11 if a value below is design-critical.

Facts (Table 10 "STM32F446xx pin and ball descriptions", pp.44–56; Table 11 "Alternate function", pp.57–63):
- LQFP64 pins: 28 = PB2-BOOT1 (p.48); 29 = PB10 (p.49); 30 = VCAP_1 (p.49); 31 = VSS (p.49); 32 = VDD (p.49). Confirmed: pin 30 is VCAP_1 and pin 31 is VSS. Also 47 = VSS, 48 = VDD (p.52), 63 = VSS, 64 = VDD (p.56).
- IMPORTANT: LQFP64 has ONLY ONE VCAP pin. The VCAP_2 row (LQFP100 pin 73 / UFBGA C2 / LQFP144 106) shows "-" in the LQFP64 column (p.55). §6.3.2 (p.76): "For packages supporting only 1 VCAP pin, the two CEXT capacitors are replaced by a single capacitor." Table 18 (p.77): CEXT = 2.2 µF with ESR < 2 Ω per pin for two-VCAP packages; with a single VCAP pin CEXT = 4.7 µF, ESR < 1 Ω. So the LQFP64 board needs 4.7 µF (low-ESR ceramic) on pin 30, not 2.2 µF. Footnote 1: only if the regulator is bypassed can it be 100 nF.
- CAN alternate functions, AF9 column of Table 11: CAN1_RX on PA11 (p.57), PB8 (p.58), PD0 (p.60); CAN1_TX on PA12 (p.57), PB9 (p.58), PD1 (p.60); CAN2_RX on PB5 (p.58), PB12 (p.59); CAN2_TX on PB6 (p.58), PB13 (p.59). (PH13/PH14/PI9 do not exist on STM32F446.)
- PA10: its Table 11 row (p.57) is AF1 TIM1_CH3, AF7 USART1_RX, AF10 OTG_FS_ID, AF13 DCMI_D1, AF15 EVENTOUT — PA10 has NO CAN alternate function on any AF. CAN1_RX must be PA11/PB8/PD0.
- 5 V tolerance (Table 10 "I/O structure"): PA8 FT (p.52), PA10 FT (p.52), PA11 FT (p.52), PA12 FT (p.52), PB0 FT (p.48), PC6 FTf (5 V tolerant, I2C FM+ option) (p.51). All six are 5 V tolerant. (Table 10 legend p.44: FT = 5 V tolerant I/O, TTa = 3.3 V tolerant, connected to ADC.) Note Table 58 footnote (p.117): PA10 and PB12 have a weaker pull-up (OTG ID pins) than the 30–50 kΩ of other pins.
- HSI (Table 41, p.105): fHSI = 16 MHz; accuracy ±1 % at TA = 25 °C (factory calibrated); −8 % / +4.5 % over −40..105 °C; ±4 % over −10..85 °C; ±1 % user-trimmed. Startup 2.2 µs typ / 4 µs max.
- Max SYSCLK: 180 MHz (p.1; Table 43 p.106 fPLL_OUT 12.5–180 MHz, VCO 100–432 MHz, PLL input 0.95–2.10 MHz). The datasheet does not restrict the PLL source; HSI (16 MHz ÷ M) can drive the PLL to 180 MHz (the source selection is in RM0390 §6.2.3, not the DS). Over-drive (scale 1) is required above 168 MHz (Table 17 p.76 area, p.81 notes) — no HSE required for 180 MHz.
- USB OTG FS clock: §3.33 (p.36): "The USB OTG full-speed controller requires a dedicated 48 MHz clock that is generated by a PLL connected to the HSE oscillator." §3.30 (p.35): PLLSAI can also generate the 48 MHz USB/SDIO clock. The DS therefore ties the USB 48 MHz clock to HSE; HSI's −8/+4.5 % tolerance cannot meet USB's ±0.25 % anyway. Practical reading: a crystal is needed for USB FS on this part.
- VBAT when unused: §3.20 (p.30): VBAT may be powered "from VDD when no external battery and an external supercapacitor are present"; §3.16.2 (p.24) and §3.20 (p.30): when PDR_ON is not tied to VDD (internal reset off) "the VBAT pin has to be connected to VDD". Table 10 (p.44): VBAT = LQFP64 pin 1. Tie to VDD (a 100 nF decoupling recommendation is in AN4488, not in the DS).
- BOOT0: LQFP64 pin 60, type I, I/O structure "B — dedicated BOOT0 pin" (Table 10 p.55; legend p.44); §3.14 (p.22) boot modes (user Flash / system memory / SRAM). An explicit "must not float / pull-down" statement is NOT FOUND in DS10693 (it is in RM0390/AN4488); the DS treats BOOT0 as a dedicated input sampled at reset, so it must be driven (normally 10 kΩ to GND).
- NRST: Table 59 (p.121): RPU weak pull-up 30 kΩ min / 40 kΩ typ / 50 kΩ max; filtered pulse < 100 ns; unfiltered pulse ≥ 300 ns (VDD > 2.7 V); internal reset pulse ≥ 20 µs. Figure 33 (p.122) recommends an external RC/capacitor on NRST placed close to the device.

## 6. REYAX RYLR998 and RYLR896 (868/915 MHz LoRa UART modules)

### 6a. RYLR998
- Manufacturer: REYAX Technology Co., Ltd. MPN: RYLR998 (variants: RYLR998_M4 = I-PEX MHF4 connector instead of antenna; _NP = no antenna; datasheet p.17).
- Datasheet: "RYLR998 UART Interface 868/915 MHz LoRa Antenna Transceiver Module Datasheet", 9-FEB-2026, doc 56312E30, 17 pp., https://reyax.com/upload/products_download/download_file/RYLR998_EN.pdf.
- AT guide: "LoRa AT COMMAND GUIDE, apply for RYLR998 / RYLR498", 7-AUG-2025, doc 56312E33, 9 pp., https://reyax.com/upload/products_download/download_file/LoRa_AT_Command_RYLR998_RYLR498_EN.pdf.

Facts:
- Max TX power: 22 dBm (RF output power range 0–22 dBm, DS p.5; "must be set below AT+CRFOP=14 to comply with CE"). Settable with AT+CRFOP=<0..22>, default 22 (AT guide p.7, factory defaults p.8).
- TX current: 140 mA typ at RFOP = +22 dBm (DS p.5); measured table p.6: 144.7 mA at CRFOP=22, 138.1 mA at 20, 94.4 mA at 10, 56.6 mA at 0 dBm.
- RX current: 17.5 mA typ at 3.3 V (DS p.5). Sleep: 10 µA typ (AT+MODE=1); smart-receive average 0.06–2.65 mA depending on duty (DS p.5, p.9).
- Supply: VDD 2.3 V min / 3.3 V typ / 3.6 V max (DS p.5).
- Sensitivity: −129 dBm (DS p.5, no SF/BW condition stated). Per-SF values (SF12/BW125, SF7/BW125): NOT FOUND.
- Frequency 820–960 MHz (default 915 MHz), ±10 ppm (DS p.5).
- 5-pin header (DS p.3 pin description; 2.54 mm pitch per dimension drawing p.13): 1 = VDD, 2 = NRST (active low, 100 kΩ internal pull-up, hold low ≥ 100 ms), 3 = RXD (UART data input), 4 = TXD (UART data output), 5 = GND.
- Logic level (DS p.5): VIH ≥ 0.8·VDD, VIL ≤ 0.1 V, VOH ≥ 0.8·VDD, VOL ≤ 0.1 V → 3.3 V CMOS levels. Absolute-maximum / 5 V tolerance on RXD: NOT FOUND (do not drive from 5 V logic). Timing diagram p.4: keep RXD and NRST low before power-on/off.
- Antenna: "Built-in antenna" (DS p.2); order table p.17 = "90 Degree Angle Antenna"; the dimension drawing p.13 shows a helical (spring/coil) antenna ≈ 16.2 mm long, 5.5 mm wide, mounted at 90° to the board. Gain: NOT FOUND.
- Chipset: DS p.2 "NUVOTON MCU & Semtech LoRa Engine" — the Semtech part number is not named in the datasheet, the AT guide, or Semtech's 12-May-2022 press release. Third-party sources state SX1262 (the 22 dBm / SF5 capability is consistent with SX126x, not SX1276), but that is unverified by REYAX documents.
- AT+PARAMETER=<SF>,<BW>,<CR>,<Preamble> (AT guide p.5): SF 5–11, default 9; allowed combinations "SF7 to SF9 at 125 kHz, SF7 to SF10 at 250 kHz, SF7 to SF11 at 500 kHz". BW index 7 = 125 kHz (default), 8 = 250 kHz, 9 = 500 kHz — only 7..9 accepted. CR 1 = 4/5, 2 = 4/6, 3 = 4/7, 4 = 4/8 (default 1). Preamble default 12; only when NETWORKID = 18 may it be 4–24, otherwise it must be 12 (+ERR=18 otherwise, p.9). Recommended "9,7,1,12"; "8,7,1,12" for payloads > 100 bytes (p.2). NETWORKID 3–15 or 18 (default 18) (p.6).
- AT+SEND max payload: 240 bytes (AT guide p.7; +ERR=13 "TX data exceeds 240 bytes", p.9). The module adds 8 bytes of overhead on air (p.2).
- AT+MODE: 0 transceiver, 1 sleep, 2 smart receiving with <RX time>,<Low speed time> 30–60000 ms (p.3). Default UART 115200 8N1 (p.4).

### 6b. RYLR896
- MPN: RYLR896. Datasheet: "RYLR896 UART Interface 868/915 MHz Lora Antenna Transceiver Module Datasheet", 01-Nov-2021, doc 56312E37, 7 pp. (copy retrieved from https://lemosint.com/wp-content/uploads/2021/11/RYLR896_EN.pdf; REYAX product page https://reyax.com/products/rylr896/). AT guide: "Lora AT COMMAND GUIDE, apply for RYLR405/406/895/896/89H1", 28-Jun-2022, doc 56322E32, 9 pp., https://reyax.com/upload/products_download/download_file/LoRa-AT-Command-RYLR40x_RYLR89x_EN-8.pdf.

Facts:
- Chipset: Semtech SX1276 engine (DS p.2).
- Max TX power: +15 dBm (RF output power range −4 to 15 dBm, DS p.4); AT+CRFOP=<0..15>, default 15 (AT guide p.6, p.8).
- TX current 43 mA typ at +15 dBm; RX 16.5 mA (AT+MODE=0); sleep 0.5 µA (AT+MODE=1) (DS p.4).
- Supply: VDD 2–3.6 V, 3.3 V typ (DS p.4). Sensitivity −148 dBm (no SF/BW condition; per-SF NOT FOUND). Frequency 862–1020 MHz, ±2 ppm.
- Header is SIX pins, not five (DS p.3; 2.54 mm pitch p.5): 1 = VDD, 2 = NRST (active low, 100 kΩ internal pull-up, ≥ 100 ms), 3 = RXD (in), 4 = TXD (out), 5 = NC, 6 = GND. A footprint made for the 5-pin RYLR998 will not match (GND moves from pin 5 to pin 6).
- Logic level (DS p.4): VIH ≥ 0.7·VDD, VIL ≤ 0.3·VDD, VOH ≥ 0.9·VDD (printed "0.9 … VDD"), VOL ≤ 0.1 V → 3.3 V CMOS; 5 V tolerance NOT FOUND.
- Antenna: "Designed with integrated antenna" (DS p.2); drawings p.5–6 show a helical (spring/coil) antenna ≈ 17.5 mm long, 5.5 mm wide, in line with the board. Gain: NOT FOUND. Module 42.5 × 18.4 × 5.5 mm, 7 g (p.4–5).
- AT+PARAMETER (AT guide p.4): SF 7–12, default 12. BW index 0–9: 0 = 7.8 kHz (not recommended), 1 = 10.4, 2 = 15.6, 3 = 20.8, 4 = 31.25, 5 = 41.7, 6 = 62.5, 7 = 125 kHz (default), 8 = 250, 9 = 500. CR 1–4 (default 1). Preamble 4–7 (default 4). Recommended "10,7,1,7" within 3 km, "12,4,1,7" beyond (p.2). NETWORKID 0–16, default 0 (p.5). So BW index 7 = 125 kHz on BOTH modules, but the index table, SF range, preamble rules and CRFOP range differ, so parameter strings are not interchangeable.
- AT+SEND max payload: 240 bytes (AT guide p.7; +ERR=13). AT+MODE only 0/1 (no smart-receive mode) (p.3). UART default 115200.

## 7. TDK SLF7045T-4R7M2R0-PF — 4.7 µH shielded power inductor, 7.0 × 7.0 × 4.5 mm

- Manufacturer: TDK. Exact MPN: SLF7045T-4R7M2R0-PF (4R7 = 4.7 µH, M = ±20 %, 2R0 = 2.0 A rated current, -PF = TDK internal/Pb-free code; product-identification legend on datasheet p.1).
- STATUS: "EOL Announced" — discontinue issue date May 14 2024, last purchase order Mar 31 2026, last shipment Dec 31 2026; recommended alternate VLS5045EX-4R7M (interchangeability not guaranteed) — TDK product page https://product.tdk.com/en/search/inductor/inductor/smd/info?part_no=SLF7045T-4R7M2R0-PF (accessed 2026-09-16).
- Datasheet: "SLF Series SLF7045 Type" — current TDK edition inductor_commercial_power_slf7045_en.pdf (dated 2024-05-27 per TDK search index; https://product.tdk.com/system/files/dam/doc/product/inductor/inductor/smd/catalog/inductor_commercial_power_slf7045_en.pdf) could not be downloaded (server refuses non-browser clients); values below are from the TDK product page (current) and the SLF7045 datasheet edition 531_SLF7045 / 990803 (Aug 1999) mirrored at https://media.digikey.com/pdf/Data%20Sheets/TDK%20PDFs/SLF7045.pdf for the land-pattern drawing.

Facts:
- Inductance 4.7 µH ±20 % at 100 kHz (product page; 1999 DS p.2 tests at 1 kHz).
- Rated current, saturation basis (Isat): 2.0 A max at 10 % inductance drop ("Rated Current (L Change) [Max.] 2A (10 % Down)", product page; DS p.2 "based on inductance change 2").
- Rated current, temperature-rise basis (Irms): 2.1 A typ at 20 °C rise (product page; DS p.2 "based on temperature rise 2.1"). DS footnote: rated current is the smaller of the 20 °C-rise and 10 %-drop values.
- DCR: 30 mΩ typ, 36 mΩ max (product page; 1999 DS 0.03 Ω ±20 %).
- Self-resonant frequency: NOT FOUND (product-page fields "Self Resonant Frequency Min/Typ" are blank; not in the datasheet).
- Operating temperature −40..105 °C including self-heating (product page; the 1999 edition said −20..85).
- Recommended land pattern: product page gives A = 1.50 mm, B = 4.80 mm, C = 2.20 mm nominal; the datasheet drawing (DS p.2 "Shapes and dimensions / recommended PC board pattern") shows two rectangular pads each 2.2 mm wide (C) × 1.5 mm long (A), separated by an inner gap B (4.9 mm in the 1999 drawing, 4.80 mm current) → pad centres ≈ 6.3 mm apart, overall pattern 7.8 × 2.2 mm. Body 7.0 ± 0.2 square, 4.5 ± 0.3 high; terminals 2.0 ± 0.1 wide.

## 8. Samtec FTSH-105-01-L-DV-K — 2 × 5, 1.27 mm SMT micro header (ARM 10-pin Cortex Debug connector)

- Manufacturer: Samtec. Exact MPN: FTSH-105-01-L-DV-K (product page https://www.samtec.com/products/ftsh-105-01-l-dv-k).
- Documents: (a) Footprint: "Recommended PCB layout for FTSH-1XX-XX-XXX-DV-XXX", drawing FTSH-1XX-XX-XXX-DV-XXX-FOOTPRINT, Revision H, 8/27/2019 (ECN-364793), https://suddendocs.samtec.com/prints/ftsh-1xx-xx-xxx-dv-xxx-footprint.pdf. (b) Product print: FTSH-1XX-XX-XXX-DV-XXX-XXX-X-XX-MKT, Revision FX, sheet dated Jan 2026, https://suddendocs.samtec.com/prints/ftsh-1xx-xx-xxx-dv-xxx-xxx-x-xx-mkt.pdf.

Facts:
- Footprint (drawing sheet 1, Fig 1): pad 0.029" × 0.110" (0.74 × 2.79 mm); pitch along the row 0.050" (1.27 mm); the two pad rows span 0.270" (6.86 mm) outer-edge to outer-edge → pad centre-to-centre across rows 0.160" (4.07 mm) with a 0.050" (1.27 mm) inner gap; connector body width 0.135" (3.43 mm); pattern length = (no. of positions per row) × 0.050" = 0.250" (6.35 mm) for -105; "all dimensions symmetric about the centerline". Table 1: option -K has no alignment-pin hole (N/A). Stencil sheet 2: 0.006" (0.152 mm) stencil.
- Pin numbering (drawing Fig 1 and print Fig 1): position 01 and 03 are on one row, 02 on the other — i.e. odd pins on one row, even pins on the other, numbered across the rows (1-2, 3-4, ... 9-10), pin 1 at one end.
- Ordering-code decode (print sheet 1): -105 = 5 positions per row (10 contacts); -01 = lead style .120" (3.05 mm) post; -L = 10 µ" selective gold on contact, matte tin on tail; -DV = double row vertical SMT; -K = keying option (keying notch for mating with FFSD; lead style -01 only). Samtec product page: "Keying Notch". Keil's ULINK2 guide specifies the keyed version FTSH-105-01-L-DV-007-K (-007 = position 7 pin omitted) (https://support.arm.com/documentation/101455 "Target Connectors"); Keil J-Link connector page: "Position 7 has no pin and serves only as a key" (https://www.keil.com/support/man/docs/jlink/jlink_connectors.asp).
- ARM Cortex Debug 10-pin pinout (Arm/Keil "Cortex-M Debug Connectors" overview, https://documentation-service.arm.com/static/5fce6c49e167456a35b36af1, Feb 2011, p.2 diagram, "based on the Samtec 0.05" micro header", ref. FTSH-105): 1 VCC/VTref, 2 SWDIO/TMS, 3 GND, 4 SWDCLK/TCK, 5 GND, 6 SWO/TDO, 7 KEY (no pin), 8 NC/TDI, 9 GNDDetect, 10 nRESET. This matches the list in the question. Keil ULINKpro guide (https://support.arm.com/documentation/101416/0100 "Cortex Debug (10-pin)") gives the same signals with the note that SWDIO/TMS should have a 100 kΩ pull-up, SWCLK a 100 kΩ pull-down, nRESET open-drain with 100 kΩ pull-up.

## 9. "KEMET" KTS500B106M55N0T00 — actually Nippon Chemi-Con, 10 µF 50 V X7R 2220

- Manufacturer: Nippon Chemi-Con Corporation (United Chemi-Con in the Americas) — NOT KEMET. The KTS500B… part number is Chemi-Con's "NTS series" MLCC (Chemi-Con product page https://www.chemi-con.co.jp/en/products/print-condenser.php?part_number=KTS500B106M55N0T00; LCSC lists it as "NCC (Nippon Chemi-Con)"). It is also the exact CIN/COUT capacitor that the R1240 datasheet recommends (R1240 DS p.7, p.11).
- Datasheet: no standalone PDF; specification data and characteristic graphs are on the Chemi-Con page above (graphs served as SVG, e.g. .../capacitor/graph/KTS500B106M55N0T00_1.SVG).

Facts:
- Case size: 2220 EIA = 5750 metric, 5.7 mm L × 5.0 mm W, thickness 2.8 mm; weight 0.46 g (Chemi-Con page).
- Dielectric X7R; 10 µF; ±20 % (M) at 25 °C/1 kHz; 50 Vdc; −55..125 °C; tanδ ≤ 0.05; status "In Production" (Chemi-Con page).
- DC-bias derating: from the Chemi-Con "DC Bias Characteristics" graph (0 % at 0–3 V, ≈ −5 % at 8 V, ≈ −9 % at 12 V, ≈ −20 % at 18 V, ≈ −35 % at 25 V, ≈ −65 % at 50 V) → at 12 V the effective capacitance is ≈ 9.1 µF (≈ −8 to −10 %, read from the graph). Impedance/ESR graph: ESR ≈ 7–10 mΩ from 200 kHz to 1 MHz, SRF ≈ 1 MHz.

## 10. Murata GJM1555C1H220JB01(D) — 22 pF, 0402, C0G — schematic label "47 pF" is wrong

- Manufacturer: Murata Manufacturing Co., Ltd. Exact MPN: GJM1555C1H220JB01# where # = packaging code (D = φ180 mm reel, paper tape, 10 000 pcs; J/V/W other reels). Series: GJM "High Q chip multilayer ceramic capacitors (≤ 100 Vdc) for consumer & industrial equipment". Status: In Production.
- Datasheet/spec: Murata product page https://www.murata.com/en-us/products/productdetail?partno=GJM1555C1H220JB01%23 (redirects to https://pim.murata.com/en-us/pim/details/?partNum=GJM1555C1H220JB01%23), accessed 2026-09-16.

Facts:
- Capacitance encoded by the MPN and confirmed by Murata: 22 pF (code "220" = 22 × 10^0 pF), tolerance J = ±5 %, C1H = 50 Vdc, temperature characteristic C0G (EIA), operating −55..125 °C (Murata page "Specifications").
- Case: chip size code "15" = 1005M / 0402 inch; L 1.0 ± 0.05 × W 0.5 ± 0.05 × T 0.5 ± 0.05 mm; external terminal 0.15–0.35 mm; mass 1.6 mg (Murata page "Appearance & Shape").
- Consequence: the schematic value "47 pF" does not match this MPN; a 47 pF part in the same series would carry code "470" (e.g. GJM1555C1H470JB01D — not verified here). Note the RYLR998 application schematic (RYLR998 DS p.12) uses C4 = 47 pF on the antenna/supply filter, which is likely where the 47 pF intent came from.

---

## Summary of facts that matter for the review

- R1240N sync vs async: ASYNCHRONOUS — internal high-side N-FET only; an external Schottky catch diode (CMS06/CMS11) from Lx to GND is mandatory; fosc is 1.25 MHz (not 1.5), VFB 0.8 V, CBST 0.1 µF + 51 Ω, L 4.7 µH; SOT-23-6W pins 1 CE / 2 VIN / 3 Lx / 4 BST / 5 GND / 6 VFB; CE has no internal pull (VIH 1.6 V) (Nisshinbo R1240x DS NO.EA-190-240903 pp.1,3,5,7,11).
- TCAN1042H VCC range: 4.5–5.5 V only (no 3.3 V option; pin 5 is NC on the H part, VIO exists only on V variants); RXD swings to VCC (VOH 4.0–4.6 V), TXD/STB VIH 2 V so 3.3 V drive is fine; STB is internally pulled up and HIGH = standby, so it must be driven/tied LOW (TI SLLSES9D pp.5,8,9,10,20).
- CAN1 AF pins: CAN1_RX = PA11 / PB8 / PD0 and CAN1_TX = PA12 / PB9 / PD1 on AF9; CAN2_RX = PB5 / PB12, CAN2_TX = PB6 / PB13; PA10 has NO CAN function at all (DS10693 Table 11 pp.57–60).
- STM32 pin 30/31 names: LQFP64 pin 30 = VCAP_1, pin 31 = VSS (pin 29 PB10, 32 VDD); LQFP64 has only one VCAP pin, so CEXT must be 4.7 µF with ESR < 1 Ω, not 2.2 µF (DS10693 Table 10 p.49, §6.3.2 p.76, Table 18 p.77); PA8/PA10/PA11/PA12/PB0 are FT and PC6 is FTf (5 V tolerant); HSI ±1 % at 25 °C, −8/+4.5 % over temp; USB OTG FS 48 MHz is specified from a PLL on HSE; NRST pull-up 30–50 kΩ; current DS is Rev 11 (29 May 2026), facts verified in Rev 10.
- RYLR998 max TX dBm and TX current: 22 dBm (AT+CRFOP 0–22, default 22), 140 mA typ / 144.7 mA measured at +22 dBm, RX 17.5 mA, sleep 10 µA, VDD 2.3–3.6 V, 3.3 V CMOS UART, 5-pin header VDD/NRST/RXD/TXD/GND, helical antenna at 90°, BW index 7 = 125 kHz, SF 5–11, 240-byte max payload; RYLR896 differs: SX1276, 15 dBm max, 43 mA TX, SIX-pin header (pin 5 NC, pin 6 GND), SF 7–12, BW index 0–9 (7 = 125 kHz), preamble 4–7.
- CMS06 ratings: 30 V VRRM, 2.0 A IF(AV), VFM 0.37 V max (0.32 typ) at 2 A, IRRM 3 mA max at 30 V, Cj 130 pF at 10 V (above the ≤ 100 pF the R1240 DS asks for), M-FLAT 2.4 × 4.7 × 0.98 mm, pin 1 anode / pin 2 cathode with the cathode band at the pin-2 end, pads 2.1 × 1.4 mm at 4.4 mm centres (Toshiba CMS06 DS pp.1–2; Toshiba M-FLAT page). Also: SB007-03Q-TL-E is a 30 V/70 mA Schottky diode (pin 1 anode, 2 NC, 3 cathode), not an ESD/TVS part; KTS500B106M55N0T00 is a Nippon Chemi-Con 2220 X7R 10 µF/50 V (≈ −9 % at 12 V), not KEMET; GJM1555C1H220JB01 is 22 pF, not 47 pF; TDK SLF7045T-4R7M2R0-PF is EOL (last shipment 31 Dec 2026).
