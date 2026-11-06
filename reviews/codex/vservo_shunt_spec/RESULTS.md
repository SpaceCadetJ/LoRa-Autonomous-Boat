# VSERVO-03 — conditional shunt bounds

**All values below are illustrative allocations. Actual source/receiver/device inputs remain unavailable. No nominal resistance, component, circuit or operating limit is selected.**

[Specification](README.md) | [Interactive explorer](index.html) | [Proposed cell](v2_shunt_spec.svg)

## Threshold margins

Normal maximum 5.0 V; falling threshold 5.10–5.15 V; rising threshold 5.25–5.30 V; disturbance 40 mV peak-to-peak; local ceiling 5.5 V. Normal maximum includes the worst sensed normal feed/ripple/disturbance.

| Necessary margin | Allocated result |
|---|---:|
| Release above normal | 0.100 V |
| Hysteresis after disturbance | 0.060 V |
| Protection with 0.1 V further rise | 0.100 V |
| Protection with 0.2 V further rise | 0 V; no positive margin |

The complete response delay to useful sink current and loaded/parasitic rise must fit the allocation. Turn-off delay and lower-rail excursion remain separate and uncalculated; these numbers do not qualify receiver undervoltage.

## Necessary nominal resistance interval

`Rnom > max(0, (rail_max / Ipath_allocation - Ron_min) / (1 - tolerance))`

`Rnom < (off_min / Iexcess - Ron_max) / (1 + tolerance)`

The upper bound ensures positive current margin at the lowest falling threshold, not just at the ceiling. Excess current includes all simultaneous source and return paths after justified load credits. The branch-current allocation is not a device rating.

| Excess allocation | Strict lower bound | Strict upper bound | Result |
|---|---:|---:|---|
| 0.5 A | 5.789474 ohm | 9.619048 ohm | Positive necessary interval only |
| 1.0 A | 5.789474 ohm | 4.761905 ohm | No interval |

Both cases allocate 5.1 V falling minimum, 5.5 V rail maximum, 1 A branch-current ceiling, 0–0.1 ohm Ron and 5% resistor tolerance. An assumed rail bound must be established independently of this unimplemented clamp.

## Fixed 8.2 ohm illustration

| Bound | Conditional result |
|---|---:|
| Minimum fully-on sink current | 0.585534 A |
| Maximum branch current | 0.706033 A |
| Sink margin above 0.5 A | 0.085534 A |
| Conservative resistor instantaneous power | 3.883184 W |
| Fully-on FET conduction-only bound | 49.848313 mW |

Resistor power is bounded by Vmax^2/Rmin. The FET figure uses Imax^2*Ronmax; it excludes transitions, partial gate drive, startup and linear-region SOA. Neither number is a component wattage or thermal rating. Pulse duration, hot-start temperature, repetition and continuous fault operation remain unknown.

Finite capacitor storage cannot be reused every event without restoration. No repeated-energy reset path or continuous-fault clearing time is inferred. A resistor nearly dissipating 3.9 W instantaneously cannot be chosen from mean event watts alone.

## Actual evidence

The threshold, resistance and branch models all remain unavailable because their actual inputs are null. Device selection, full-current startup/turn-off behavior, reverse voltage, remote receiver limits and source fault interruption are held. No native tools or hardware were run.

Next independent task: full 6S sensing/ADC range and protection review, preserving the latest native Power presentation and all existing electrical evidence.
