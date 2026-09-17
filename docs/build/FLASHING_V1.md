# V1: preserve, program and verify firmware

**Bench procedure; hardware steps have not been run.** The standalone V1 software build passes. The resulting image is named `boat_v1_unqualified` because there is no known original image for comparison and no measured hardware qualification. Do not connect motors, propellers, a servo or an ESC during these steps.

Read [firmware build](FIRMWARE_BUILD.md), [V1 design review](../V1_DESIGN_REVIEW.md), and the [debug pin atlas](../atlas/JTAG.md) first. This procedure does not make the original V1 board safe to power: the documented VCAP, power-return/filter, VBAT and BOOT0 findings need assembly-specific review and rework evidence before applying power. Record what the physical board actually contains.

## 1. Identify the board and isolate loads

1. Photograph both sides and the MCU marking. Record board revision, serial/label, any wire modifications, LoRa/GPS model and existing harness connections.
2. Remove battery and USB/debug connections. Disconnect all external modules and all actuator harnesses for first MCU bring-up. An ESC's BEC can power the board through a harness, so disconnect the whole harness.
3. Check the power/VCAP fixes and unpowered continuity against the schematic and atlas. Confirm BOOT0 is held low for Flash boot; V1 source shows it unconnected. Do not improvise a drive voltage onto an unknown pad.
4. Verify supply rails separately using the assembly procedure and a current-limited supply. Record input voltage, current limit, measured +3V3 and current draw. The limit depends on the actual board/rework and is not inferred here.

## 2. Connect ST-LINK by electrical pin number

Use a genuine, supported ST-LINK and the correct adapter for this **10-pin, 1.27 mm** connector. A probe's 20-pin, STDC14 or differently wired 10-pin connector must be mapped by signal, not by matching pin numbers. The table below is the **target-board connector**, not the probe connector.

| V1 JTAG1 pin | Board signal | MCU package pin | Connection for SWD |
|---|---|---|---|
| 1 | +3V3 | VDD rail | Probe target-voltage reference; do not treat it as an automatic power source |
| 2 | SWDIO | U3-46 / PA13 | Probe SWDIO |
| 3 | GND | Ground | Probe ground |
| 4 | SWCLK | U3-49 / PA14 | Probe SWCLK |
| 5 | GND | Ground | Ground |
| 6 | SWO/TDO | U3-55 / PB3 | Optional; unnecessary for basic programming |
| 7 | NC | — | Leave unconnected |
| 8 | TDI | U3-50 / PA15 | Leave unconnected for SWD |
| 9 | GND | Ground | Ground |
| 10 | NRST | U3-7 | Probe reset; required for the under-reset procedure |

With power removed, verify pin 1 orientation and continuity; the cable view and board view are mirrored. Connect ground, voltage reference, SWDIO, SWCLK and NRST. Power the target from the previously validated supply; verify +3V3 at pin 1 relative to ground. Do not join independent 3.3 V sources. Keep actuator power physically disconnected even while the CPU is halted: timers and attached electronics cannot be assumed safe from the debugger state alone.

## 3. Prepare the programmer and records

ST's [STM32CubeProgrammer CLI reference](https://dev.st.com/stm32cube-docs/prog/2.23.0/en/docs/markup/CubeProg_Command_Lines.html) documents connect, upload, write, verify and option-byte display. Command options below were additionally checked against the installed **2.20.0 `--help`**. Help is the only programmer operation executed during this documentation work.

Use PowerShell from the repository root. Set the installed path; this host has:

```powershell
$Programmer = 'C:\ST\STM32CubeIDE_1.19.0\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32_2.2.200.202503041107\tools\bin\STM32_Programmer_CLI.exe'
& $Programmer --help
& $Programmer -l st-link-only
$ProbeSerial = 'REPLACE_WITH_THE_LISTED_PROBE_SERIAL'
$Session = Join-Path (Get-Location) ('firmware/Debug/bench_v1_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $Session -ErrorAction Stop | Out-Null
```

Select the probe serial explicitly, particularly if more than one probe is connected. Close IDE debugging sessions that own it. The enumeration command and every command below remain **unrun on hardware**. If using the GUI, choose ST-LINK/SWD, 1000 kHz, **Under Reset**, Hardware Reset; verify the matching probe serial and target voltage.

## 4. Connect and make two backups before writing

Connection under reset uses the NRST wire to catch the device before application execution. It changes/reset-halts the target's execution state; this is not a passive observation.

```powershell
$BackupA = Join-Path $Session 'before_flash_a.bin'
$BackupB = Join-Path $Session 'before_flash_b.bin'
& $Programmer -c port=SWD "sn=$ProbeSerial" freq=1000 mode=UR reset=HWrst -ob displ -r 0x08000000 0x80000 $BackupA -r 0x08000000 0x80000 $BackupB -halt -log (Join-Path $Session 'backup.log')
if ($LASTEXITCODE -ne 0) { throw 'Backup failed; do not program' }
if ((Get-Item -LiteralPath $BackupA).Length -ne 524288 -or (Get-Item -LiteralPath $BackupB).Length -ne 524288) { throw 'Unexpected backup size' }
$HashA = (Get-FileHash -Algorithm SHA256 -LiteralPath $BackupA).Hash
$HashB = (Get-FileHash -Algorithm SHA256 -LiteralPath $BackupB).Hash
if ($HashA -ne $HashB) { throw 'Backups differ; stop and investigate' }
Get-FileHash -Algorithm SHA256 -LiteralPath $BackupA,$BackupB | Format-List | Out-File (Join-Path $Session 'backup_hashes.txt')
```

Inspect the log and confirm STM32F446, **512 KiB** Flash, expected target voltage and readable memory before proceeding. Do not force this memory size onto a different MCU. Save the option-byte display, probe details and board identity with the backups. These files contain main Flash only: they are not a backup of option bytes, OTP, radio settings or other devices. Copy the session folder to durable storage.

If read protection blocks backup, stop. Do not invoke read-unprotect, erase-all, protection changes, or option-byte changes as a shortcut; recovery can erase the only copy of existing firmware. Confirm the implications in ST documentation and preserve available board history first.

## 5. Program the reviewed candidate and verify

Run the build procedure, review its manifest and match the intended image hash. Retain the candidate files and manifest in the session record. The write below **erases/programs the affected Flash sectors** and replaces the current application; the backup is mandatory for an existing board.

```powershell
$Image = (Resolve-Path 'firmware/Debug/reproducible_v1/boat_v1_unqualified.elf').Path
$CandidateBin = (Resolve-Path 'firmware/Debug/reproducible_v1/boat_v1_unqualified.bin').Path
Copy-Item -LiteralPath $Image,$CandidateBin,'firmware/Debug/reproducible_v1/manifest.json','firmware/Debug/reproducible_v1/build.log' -Destination $Session
& $Programmer -c port=SWD "sn=$ProbeSerial" freq=1000 mode=UR reset=HWrst -w $Image -v -halt -log (Join-Path $Session 'program.log')
if ($LASTEXITCODE -ne 0) { throw 'Programming/verification failed; keep loads disconnected' }
$Readback = Join-Path $Session 'candidate_readback.bin'
$ImageBytes = (Get-Item -LiteralPath $CandidateBin).Length
& $Programmer -c port=SWD "sn=$ProbeSerial" freq=1000 mode=UR reset=HWrst -r 0x08000000 $ImageBytes $Readback -halt -log (Join-Path $Session 'readback.log')
if ($LASTEXITCODE -ne 0) { throw 'Readback failed' }
if ((Get-FileHash -LiteralPath $CandidateBin).Hash -ne (Get-FileHash -LiteralPath $Readback).Hash) { throw 'Readback mismatch' }
```

Require both the programmer's successful verification message and the readback hash match. ELF/HEX carries its addresses; raw BIN must instead be written with `-w FILE.bin 0x08000000`. Do not use `--skipErase`, an external loader, or a RAM address for this target. Do not add an automatic run/reset to the write operation.

## 6. First execution: measure outputs with no loads

1. Attach an oscilloscope/logic analyzer with a common ground before releasing reset. Use the verified voltage rating of the instrument. Keep ESC, servo, GPS and radio physically disconnected initially.
2. Reset/power-cycle deliberately with the target still on the validated supply. Record supply current and reset behavior. Observe both PWM outputs from power-on, including the first frame.
3. Compare measurements to these **source expectations**, not presumed acceptance results:

| Physical V1 point | MCU / firmware role | Expected startup / command range |
|---|---|---|
| TP1 / SPEEDCONTROLLER pin 2 | PA8 / TIM1_CH1 / **rudder** | 1500 microseconds; 1100–1900 microseconds |
| TP3 / STEERINGSERVO pin 2 | PC6 / TIM3_CH1 / **thrust** | 1000 microseconds; 1000–2000 microseconds |

Both expect a nominal 20 ms frame. The header names are reversed relative to this firmware. Pin 1 of both original V1 actuator headers is **+3V3**, not a verified servo/BEC power input. Do not connect an ESC BEC or servo power by color convention.

4. For UART diagnostics, observe PC10 with a high-impedance 3.3 V-compatible receiver at 9600 8N1 while GPS remains unplugged; the existing code sends debug text toward GPS RX. Observe PA0 at 115200 8N1 for LoRa startup commands. A startup debug message proves execution, not successful radio configuration.
5. Only after confirming the installed module pinout, power and radio settings, connect that module for isolated command tests. Keep instruments in place and loads absent. Record both PWM responses to zero/center commands. An optional nonzero command/link-loss demonstration is **instrument-only**: V1 is expected to retain the last command indefinitely, and must not be treated as an operational safety pass.
6. Leave GPS header pin 3 disconnected until its actual function is verified: V1 drives PB0 low and could contend with a module PPS output. No GPS-freshness, watchdog, CAN or arming capability is established by this image.

No powered propulsion test is released by this procedure. A separate firmware correction and hardware acceptance record is needed before operation.

## 7. Recovery and rollback

If connection fails: remove power, recheck connector orientation/ground/target voltage and NRST continuity, close other debug sessions, then retry under reset at a lower supported SWD frequency (for example request `freq=100`; confirm the actual speed reported). Never erase or alter option bytes merely because connection fails. If the application disables debug or faults, under-reset connection is the intended first recovery path.

If a candidate fails after programming, power down and inspect the hardware before retrying. To restore the matching board's verified main-Flash backup, use the same isolated setup and **explicitly reviewed** backup path:

```powershell
& $Programmer -c port=SWD "sn=$ProbeSerial" freq=1000 mode=UR reset=HWrst -w $BackupA 0x08000000 -v -halt -log (Join-Path $Session 'rollback.log')
if ($LASTEXITCODE -ne 0) { throw 'Rollback failed' }
```

Read back 524288 bytes and compare with the saved SHA-256 before first execution. This restores main Flash, not option bytes or hardware changes, and does not qualify the restored application as safe. BOOT0/system-ROM recovery is not documented as a ready V1 cable procedure because BOOT0 is unconnected in the original design and supported bootloader interfaces require their own physical verification.

## Bench record to complete

Record date/operator; board and rework identity; MCU marking; supply/current limit and measurements; probe serial/firmware; programmer version; backup hashes and option bytes; candidate manifest/hash; program and readback logs; first-pulse captures; actual header mapping; UART observations; pass/fail and rollback outcome. **All hardware fields are currently unmeasured/unrun.**
