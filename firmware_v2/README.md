# V2 Stage A: board identity diagnostic

This is the first separate V2 executable, built for STM32F446RET6. It is a **development diagnostic**, not RC, navigation or handheld firmware. The current board has unresolved electrical issues; resolve the [electrical review](../reviews/codex/design_completion/electrical/README.md) before powering an assembly. Keep actuator loads disconnected throughout Stage A.

## Build on your computer

From the repository root, using Python 3.10+ and GNU Arm GCC (the existing STM32CubeIDE installation is auto-detected on Windows):

```text
python firmware_v2/tools/build.py check
python firmware_v2/tools/build.py build
```

If the compiler is elsewhere, add `--toolchain` with its `bin` directory. Outputs are confined to a new, empty directory under `firmware_v2/build/`; use `--out firmware_v2/build/stage_a_repeat` for a second build. Existing output directories are not overwritten. No compiler download, probe discovery or programmer command is performed.

The default build creates `firmware_v2/build/stage_a/v2_stage_a_unqualified.elf`, `.hex`, `.bin`, `.map` and `manifest.json`. The manifest records compiler, exact inputs, command output, load address, image size and hashes. A failed build has `status: build_failed`; never use artifacts from it. Compare the manifest with the exact image before any later programming.

This target reuses ST's preserved CMSIS headers, system/startup files and F446RE linker script from `firmware/`. It does not compile V1's application, change V1 sources or require CubeMX. There is no V2 `.ioc` yet. The [pin contract](board_contract.json) verifies seven MCU pin functions, net names and peer pads against the recorded native schematic export and checks that current V2 schematic inputs still match that export. That check covers electrical membership, not footprint/cable orientation.

## Expected behavior after approved bench programming

First complete the power and SWD prerequisites in the [V2 programming guide](../docs/build/FLASHING_V2.md), including backups, image identity and readback verification. This diagnostic is not permission to power the present circuit. Start from a hardware reset, not a debugger jump into `main` after running another image.

| Item | Expected observation; not yet measured on hardware |
| --- | --- |
| ESC PC6 / U1-37 and SERVO PA8 / U1-41 | Output latch set low before GPIO output mode. No timer/PWM initialization or pulse generation. Check both MCU and header signals with loads disconnected. |
| D6 / PC1 | Toggles every nominal 500 ms, one complete on/off cycle per second; this is a diagnostic heartbeat, not radio-link status. |
| D7 / PC2 | Off; no GNSS driver or fix is claimed. |
| D8 / PC3 | On to identify the diagnostic edition; it does not mean the vehicle is ready to arm. |
| SWD PA13 / PA14 | Reset configuration retained; inspect `v2_diagnostic` with the matching ELF symbols. |
| Radio, IMU, USB, ADC, GNSS and other GPIO | No drivers initialized; those pins retain reset state. A connected module may still have its own power-on behavior. |

In CubeIDE's debugger Expressions view, add `v2_diagnostic`. The structure is volatile RAM and contains:

| Field | Interpretation |
| --- | --- |
| `magic` | `0x3252564C`, identifying this V2 diagnostic record |
| `version` | `1`, the record format |
| `stage` | `2` after initialization; `0xE1` unexpected clock, `0xE2` SysTick setup failure; `0xF1`–`0xF5` processor fault/NMI |
| `reset_flags`, `device_id` | Raw RCC reset flags and DBGMCU IDCODE for the bench record |
| `core_clock_hz` | Nominal 16,000,000 from the internal HSI; no external-crystal or USB-clock qualification |
| `milliseconds`, `heartbeat_edges` | SysTick count and LED edge count; sampling while halted will stop progress |

Fault handlers attempt to hold the MCU actuator pins low and stop for diagnosis. A corrupted stack or bus fault can prevent a C handler from completing. They do **not** implement the later watchdog/recovery requirements. This stage is not evidence of a safe control supervisor, controlled startup at the external buffer, brownout performance or an operational link-loss failsafe.

## Troubleshooting and next stage

If the builder rejects the pin contract, compare the changed schematic with its native export and review the mapping before updating evidence. Do not disable the guard. If SWD cannot attach, use the power/reset/cable checks in the programming guide; the diagnostic does not provide USB DFU, a serial console or radio commands. If the heartbeat does not appear, inspect the RAM record and PC1 waveform before assuming the LED polarity, population or MCU clock is correct. Stop if a rail or actuator waveform is unexpected.

Record board/rework identity, firmware hash, power rails/current, SWD ID, reset flags, LED/PC1 period, and both actuator signals across reset. Stage B adds the control supervisor, timers and watchdog only after the electrical design and output behavior are accepted. Application-specific use and release gates are in the [application handbook](../docs/applications/README.md).

The register behavior is based on [ST RM0390](https://www.st.com/st-web-ui/static/active/en/resource/technical/document/reference_manual/DM00135183.pdf), the local ST CMSIS definitions and [Arm's SysTick API](https://arm-software.github.io/CMSIS_6/main/Core/group__SysTick__gr.html). Compilation is software evidence; none of the expected physical observations above has been performed.
