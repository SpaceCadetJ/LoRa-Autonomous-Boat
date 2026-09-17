# Firmware work handoff — 2026-09-17

Outcome: **preserved V1 sources compile and link through a new non-flashing recipe; no qualified V2 image exists.** No functional firmware, `.ioc`, hardware, shared coordination file or Git state was changed by this work. No probe enumeration, connection, reset, erase, program, option-byte write or hardware test was executed.

## Added files

- [FIRMWARE_BUILD.md](FIRMWARE_BUILD.md): actual inputs/toolchain, reproducible commands, artifacts, known limitations, CI/release boundary.
- [FLASHING_V1.md](FLASHING_V1.md): assembly gate, verified electrical debug pin map, two backups, option-byte record, program/verify/readback, first instrument-only execution and rollback.
- [FLASHING_V2.md](FLASHING_V2.md): current J7 map, no-image status, V1 incompatibility, firmware/hardware contract gaps, staged implementation and future programming acceptance.
- [build_v1.py](../../firmware/tools/build_v1.py): Python standard-library preflight/build; hashes inputs, captures commands, exports ELF/HEX/BIN/map, checks vectors and records success/failure. Output is confined to subdirectories of the already ignored `firmware/Debug/` tree.
- This handoff.

## Actual software checks

Executed from the repository root on Windows using Python **3.12.14** at:

```text
C:/Users/Jay/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe
```

The host's `py -3 --version` reported `No installed Python found`; `python`, GNU Arm tools and CubeProgrammer were not on PATH. The helper discovered these existing tools without an installation/download:

```text
C:/ST/STM32CubeIDE_1.19.0/STM32CubeIDE/plugins/com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.13.3.rel1.win32_1.0.0.202411081344/tools/bin
```

Compiler banner: `arm-none-eabi-gcc.exe (GNU Tools for STM32 13.3.rel1.20240926-1715) 13.3.1 20240614`.

| Command (using the Python executable above) | Observed result |
|---|---|
| `firmware/tools/build_v1.py preflight` | Exit 0; `software_preflight_pass`, 23 compilation sources, 95 hashed inputs |
| `firmware/tools/build_v1.py build` | Exit 0; `build_pass_unqualified`; generated default outputs |
| `firmware/tools/build_v1.py build --out firmware/Debug/reproducible_v1_repeat` | Exit 0; independent second output directory |
| SHA-256 comparison of two builds' BIN, HEX and ELF | All three identical on this host/toolchain/source snapshot |
| `firmware/tools/build_v1.py preflight --toolchain firmware/tools/nonexistent-toolchain` | Expected exit 1 with clear missing-toolchain error |
| `firmware/tools/build_v1.py build --out firmware/Core/rejected-build-output` | Expected exit 1; forbidden source-directory output rejected before creation |
| Installed `STM32_Programmer_CLI.exe --help` | Exit 0, version 2.20.0; syntax for connect, read/upload, write, verify, halt and option-byte display inspected |
| Static documentation checks | Five PowerShell blocks parsed without executing them; all relative document links resolve |

Both builds reported these same existing HAL warnings: unused `Banks` argument at `stm32f4xx_hal_flash_ex.c:948`, `:1027`, `:1063`. No build errors. Each build's before/after source hashes matched, so the preserved inputs were stable through compilation.

## Generated result

Default output directory: `firmware/Debug/reproducible_v1/`. Repeat: `firmware/Debug/reproducible_v1_repeat/`. These are ignored local artifacts, not a committed firmware release.

| Measurement | Result |
|---|---|
| Flash region used / BIN length | 36,528 bytes |
| RAM region used | 4,496 bytes, including static data and linker heap/stack reservation |
| GNU size text / data / bss | 36,044 / 472 / 4,024 bytes |
| Initial stack | `0x20020000` |
| Reset vector | `0x08003569` (Thumb) |
| BIN SHA-256 | `9b90f0322089d997f1498ee634d4880005bd85fd5337d7a013a5609954239e17` |
| ELF SHA-256 | `612c82d7c2d4994003d509526d382328300dd505e0a6ef9520c9de8cd2939b0c` |
| HEX SHA-256 | `70efa56de33629a070fdc6c5b65b1a7b6e0b9aad8ebc2e5a84e30c1791957ff6` |

`manifest.json` contains individual input hashes and artifact hashes; `build.log` contains exact tool argument arrays. Map/log/manifest paths or timestamps can differ between directories; no cross-machine or cross-compiler bit-identical claim is made. The same-machine ELF/HEX/BIN repeat is the verified scope.

## Limits that remain

1. The historical deployed image and original IDE build metadata are absent. This recipe is a new reproducible reconstruction, not proof of the exact original binary.
2. V1 retains no link-loss failsafe or explicit arming, mirrored actuator-header naming, parser/GPS problems, and PB0 driven low at the GPS header. The build does not correct them. V1 power/VCAP/BOOT0 findings must be resolved on the actual assembly before power is applied.
3. Current C starts TIM3 at 1000 microseconds; `.ioc` says 1500. In-place regeneration is not part of this workflow.
4. V2 has a design plan but no firmware project/image. Its plan needs reconciliation against actual V2 nets (battery divider, USB VBUS sense, BOOT0 access, CRC/protocol decisions). It must not inherit a release claim from the V1 build.
5. All backup, flash, readback, waveforms, boot, UART, radio, USB, sensor, actuator and recovery instructions are hardware procedures awaiting execution. Programmer `--help` is not an ST-LINK connectivity test.

## Next small work packages

**Software-only next step:** integrate `preflight` and `build` in CI with a pinned GNU Arm 13.3.rel1 toolchain and Python version, uploading the unqualified artifacts plus manifest/log. It needs no hardware, IDE regeneration or programmer. The coordinating agent owns CI integration.

**V1 bench next step:** after documented assembly/power corrections, photograph and continuity-check JTAG1, then connect under reset and capture two matching 512 KiB backups plus option-byte display. Do not skip directly to programming.

**V2 development next step:** freeze a reviewed pin/protocol contract, then create a separate stage-A `firmware_v2/` diagnostic project with actuator outputs inactive. Prove build, SWD/identity and measured rails before adding PWM/supervisor, radio, sensors or handheld profiles.

## Primary references consulted

- [ST STM32CubeProgrammer MCU CLI](https://dev.st.com/stm32cube-docs/prog/2.23.0/en/docs/markup/CubeProg_Command_Lines.html), backed by installed 2.20.0 CLI help for the used syntax.
- [ST STM32F446xC/E datasheet DS10693](https://www.st.com/resource/en/datasheet/stm32f446re.pdf), device family/memory/debug reference.
- Repository sources: `firmware/Core`, `firmware/Drivers`, both linker scripts, `.ioc`, V1 pin atlas/evidence, V1 review, V2 requirements/firmware plan and `hardware/kicad_v2/tools/v2_design.py`.
