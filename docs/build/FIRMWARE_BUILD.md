# Firmware build and artifact provenance

Status: **V1 software build verified; V1 hardware qualification unrun; V2 firmware not implemented.** Last checked 2026-09-17. Start here before [V1 flashing](FLASHING_V1.md) or [V2 bring-up](FLASHING_V2.md).

## What exists

The preserved `firmware/` tree contains STM32F446RE HAL/CMSIS sources, startup assembly, a Flash linker script, a RAM linker script, and `BoatTHISTIMEITSDIFFERENT.ioc`. It does not contain a retained CubeIDE `.project`/`.cproject`, original Makefile, or a known deployed firmware image. Those IDE files and build outputs are ignored by the repository. The new [build helper](../../firmware/tools/build_v1.py) reconstructs an explicit GCC recipe around the existing files; it does **not** establish bit-for-bit equivalence to firmware previously used on a boat.

| Item | Reconstructed V1 build |
|---|---|
| Device | STM32F446RET6, Cortex-M4F |
| Application Flash | `0x08000000`, 512 KiB; no application bootloader offset |
| SRAM | `0x20000000`, 128 KiB |
| Linker | `firmware/STM32F446RETX_FLASH.ld` |
| Startup | `Core/Startup/startup_stm32f446retx.s` |
| ABI | Thumb, Cortex-M4, FPv4-SP-D16, hard float |
| Defines | `USE_HAL_DRIVER`, `STM32F446xx` |
| C / optimization | GNU11, `-Og`, debug information, section garbage collection |
| C library | newlib nano; `_printf_float` **and** `_scanf_float` linked explicitly for existing GPS formatting/parsing |
| Included code | All current `Core/Src/*.c`, vendored HAL `Src/*.c`, startup assembly |
| Original Cube package declaration | STM32Cube FW_F4 V1.28.3 in `.ioc`; vendored files are the actual build inputs |

Memory sizes and device family are consistent with the [ST STM32F446xC/E datasheet](https://www.st.com/resource/en/datasheet/stm32f446re.pdf). The Flash linker is authoritative for this recipe. Do not substitute the RAM linker for a persistent flash image.

## Tools and commands

Required: Python 3.9+ standard library and GNU Arm `arm-none-eabi-gcc`, `arm-none-eabi-objcopy`, `arm-none-eabi-size`. GCC 11 or later is needed for this linker's `READONLY` syntax. The tested compiler was **GNU Tools for STM32 13.3.rel1**, bundled with STM32CubeIDE 1.19.0. No packages are downloaded by the helper.

From the repository root:

```text
python firmware/tools/build_v1.py preflight
python firmware/tools/build_v1.py build
```

The helper uses `--toolchain BIN_DIRECTORY`, then `ARM_GCC_BIN`, then PATH, then installed CubeIDE tools under `C:/ST` on Windows. Set `--toolchain` explicitly in CI to pin the intended compiler; automatic discovery is convenient locally and is not a version lock.

On the verified Windows host, `python` was absent from PATH and `py -3` reported no installed Python. The working commands were:

```powershell
$Python = 'C:\Users\Jay\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $Python firmware/tools/build_v1.py preflight
& $Python firmware/tools/build_v1.py build
if ($LASTEXITCODE -ne 0) { throw 'Firmware build failed' }
```

`preflight` prints JSON with tool paths, compiler version, source list, SHA-256 hashes and known warnings. It writes no files and accesses no hardware. `build` always recompiles, invokes only compiler/binutils, and writes below `firmware/Debug/`, an already ignored folder. It neither runs CubeMX nor changes the C, headers, startup or `.ioc`. It rejects an output path outside a subdirectory of `firmware/Debug/`. Do not run it concurrently against the same output directory.

## Outputs and interpretation

Default output: `firmware/Debug/reproducible_v1/`.

| File | Purpose |
|---|---|
| `boat_v1_unqualified.elf` | Address-bearing executable and debug information; preferred programming input after hardware gates |
| `boat_v1_unqualified.hex` | Address-bearing Intel HEX |
| `boat_v1_unqualified.bin` | Raw Flash image; requires address `0x08000000` when programming |
| `boat_v1_unqualified.map` | Link placement and memory review |
| `manifest.json` | Compiler, source hashes, artifact hashes, vectors, build state and warnings |
| `build.log` | Exact argument arrays and all compiler/linker output |
| `size.txt` | GNU size summary |

Use artifacts only from a manifest whose status is `build_pass_unqualified`. A failed attempt records `build_failed`; earlier files may remain in its output directory and must not be mistaken for a successful current build. Archive the manifest and log with every candidate image.

The helper checks binary length, SRAM stack bounds/alignment, Thumb reset vector within the image, and unchanged inputs before/after compilation. These are software sanity checks, not peripheral tests or a safety qualification.

The verified build used 36,528 bytes of the Flash region and 4,496 bytes of the RAM region. GNU size reported text/data/bss = 36,044 / 472 / 4,024 bytes. The RAM figure includes reserved heap/stack space; it is **not** a measured worst-case runtime stack/heap usage. Three warnings came from unused `Banks` parameters in the existing ST `stm32f4xx_hal_flash_ex.c`; the build completed without errors.

## Preserve behavior and review known drift

Do not regenerate the V1 project in place. Current C initializes TIM3 to 1000 microseconds, while `.ioc` specifies 1500. Main-loop application code and IRQ setup also differ from generator assumptions. A regenerated project may lose behavior even if it compiles. If CubeIDE integration is needed, import the sources into a separate project, reproduce this recipe, compare generated diffs, and preserve these hashes before accepting changes.

The compiled image retains the documented V1 issues: no link-loss stop, no explicit arm/disarm, PWM/header naming mismatch, GPS freshness/parser limits, and PB0 configured as an output on the GPS connector. Compilation does not fix them. Follow the [V1 design review](../V1_DESIGN_REVIEW.md) and [firmware review](../research/FIRMWARE_REVIEW_NOTES.md).

## CI and release boundary

CI should run preflight and build on every firmware/tooling change, retain `manifest.json`, `build.log`, `size.txt`, ELF/HEX/BIN/map, and display `UNQUALIFIED V1` in the artifact name. Pin Python and GNU Arm versions in the CI environment. On a runner with both on PATH the two commands above are sufficient; no IDE or programmer is needed. Hardware flashing must not occur on an ordinary pull-request runner.

Before distribution as a qualified release, record the source revision and manifest hash, exact target board revision, assembly rework, radio model/firmware, build recipe/toolchain, hardware acceptance results, operator and rollback image. A green compile is only a build result. V2 requires a separate target, pin contract and qualification record; renaming this V1 binary does not provide them.

See [firmware handoff](FIRMWARE_HANDOFF.md) for actual runs, reproducibility results and the smallest next step.
