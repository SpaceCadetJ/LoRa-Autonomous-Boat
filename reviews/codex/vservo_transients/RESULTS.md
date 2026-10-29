# VSERVO-02 - conditional clamp and sink calculations

[Guide](README.md) | [Explorer](index.html) | [Annotated boundary](v2_vservo_transients.svg)

## Captured topology, unchanged

Verified 14 explicit pin memberships and the complete six-member VSERVO net against VSERVO-01 XML. U3 is LM76003RNPR; SYNC/MODE pin 17 is GND. The existing automatic mode is not credited as a regenerative sink. D4/D9 remain exclusive forward sources. No native command was rerun and no circuit changed.

## Actual envelopes remain unavailable

| Model | Missing actual inputs | Actual result |
|---|---|---|
| clamp_window | normal_max_V, turnon_min_V, turnon_max_V, overshoot_V, allowed_max_V | Unavailable |
| delay_rise | C_F, return_current_A, delay_s | Unavailable |
| sink_budget | C_F, start_V, ceiling_V, net_event_energy_J, events_per_s | Unavailable |
| negative_boundary | cap_terminal_min_V, receiver_terminal_min_V, receiver_allowed_min_V | Unavailable |

Examples below are allocations only. Unknowns are not replaced by C11 voltage ratings or arbitrary receiver limits.

## Necessary clamp window

Turn-on minimum must exceed the maximum normal rail. Turn-on maximum plus all remaining full-current/dynamic/local-path rise must remain below the allowed local maximum. The rise term is not delay alone; a breakdown number is not a loaded clamp voltage.

| Example | Off-state margin (V) | Protection margin (V) | Meaning |
|---|---:|---:|---|
| Allocated positive window; physically unqualified | 0.1 | 0.1 | Positive arithmetic only |
| Allocated overshoot consumes the protection window | 0.1 | 0.0 | No accepted window |
| Actual envelope unavailable | Unavailable | Unavailable | No accepted window |

Allocated normal maximum 5.1 V, turn-on range 5.2-5.3 V, allowed ceiling 5.5 V. Combined remaining rise of 0.1 V leaves 0.1 V protection margin; 0.2 V consumes it exactly. Neither case qualifies the actual receiver, clamp or remote node.

## Delay and energy are separate constraints

For 80 uF, 0.5 A constant net return current and 10 us delay, the capacitive rise is **0.062500 V**. This omits ESR/inductive peaks. The 80 uF value is only the inherited initial 120 Hz/20 C illustration, not an all-condition effective minimum.

| Positive residual burst (mJ) | Finite storage to 5.5 V (mJ) | Minimum event sink, endpoint lower bound (mJ) | Full sink energy to restore same start (mJ) | Conditional mean at 10 events/s (mW) |
|---|---:|---:|---:|---:|
| 1 | 0.210 | 0.790 | 1.000 | 10.000 |
| 0.1 | 0.210 | 0.000 | 0.100 | 1.000 |

The energy window assumes 80 uF initially at 5 V. Residual burst energy is after other paths, with no later offset inside the burst. The endpoint lower bound does not bound an earlier peak. Repeated-event values assume that the sole remaining local sink restores the same starting rail with no other later absorption credit. An event fitting the capacitor still needs a reset path before identical repetition.

Actual peak closure needs the maximum cumulative energy excursion and the time waveform. Do not double-count harness energy already present at the chosen port. Mean watts alone do not establish pulse current, hot-start SOA, thermal recovery or continuous-fault handling.

## Separate negative-terminal boundary

At the illustrative C11/receiver terminal minima of zero volts and receiver minimum allowance of zero, both equality boundaries are met with **zero positive margin**. No physical acceptance is inferred. Actual lower bounds remain unavailable. A local positive clamp does not establish remote overshoot, negative ringing, ground-loss or connector-sequencing behavior.

Next specify one independent local shunt cell with full-current voltage/current limits, startup/control-power behavior, maximum delay, recovery, SOA/thermal and failed-open/short behavior for both exclusive source populations. Keep missing actuator permissions disabled and all device/procurement/hardware decisions held.
