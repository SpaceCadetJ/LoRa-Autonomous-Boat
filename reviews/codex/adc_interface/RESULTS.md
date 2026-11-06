# SENSE-04 — necessary interface calculations

[Guide](README.md) | [Interactive explorer](index.html) | [Functional boundary](interface_boundary.svg) | [Evidence](evidence.json)

All actual numerical inputs and qualifications remain unavailable. These allocated examples do not choose a device, implement control or establish hardware acceptance.

## Reference-loss window

For the interval before physical isolation, let H0 = Vrelease,min − Vsignal,max − reserve. With a bounded linear fall S and total delay T = Tdetect + Topen, Hafter = H0 − S×T. Require strictly positive margin in this screen. For S > 0 the strict delay limit is H0/S. The equation does not cover subsequent residual-charge discharge or an unbounded/step collapse.

| Allocated fall | Total delay | Margin at opening | Strict delay limit |
|---|---|---|---|
| 100 V/s | 200.000 µs | 38.799955 mV | < 587.999551 µs |
| 10000 V/s | 200.000 µs | -1941.200045 mV | < 5.879996 µs |

Both cases allocate release 3.35 V, signal 3.241200045 V and reserve 50 mV. The signal is the prior conditional 25.2 V divider corner, not a qualified transient maximum. A 3.35 V release level may be unavailable on the converter low corner; no threshold is selected.

## Discharge with leakage

Ideal V(t) = I×R + (V0−I×R)exp(−t/RC). The leakage floor is I×R. For a descending trajectory, a target at or below that floor is not reached in finite time. Being initially below the target does not imply it stays there if the equilibrium is higher; the model records attainment and retention separately.

| Allocated capacitance / leakage | Floor | Time to allocated 0.3 V |
|---|---|---|
| 100 nF / 1.000 µA | 0.006800 V | 1632.505758 µs |
| 100 nF / 100.000 µA | 0.680000 V | No finite crossing |
| 1 nF / 1.000 µA | 0.006800 V | 16.325058 µs |

All cases allocate 6.8 kΩ and initial 3.241200045 V. The 0.3 V target is not a PA2 rating. C36 is 100 nF nominal, not a qualified maximum; 1 nF is a hypothetical downstream capacitance. No downstream capacitor or discharge resistor is selected.

## Permanent pulldown tradeoff

With unloaded-divider Thévenin resistance Rth and switch Ron, added attenuation = (Rth+Ron)/(Rp+Rth+Ron). An allocated loading error ε requires Rp ≥ (Rth+Ron)(1−ε)/ε. Positive leakage requires Rp ≤ Vpark/Ileak. A nonempty interval is necessary only; settling, tolerances and all power states still need review.

| Allocated positive leakage | Minimum Rp for loading | Maximum Rp for parking | Necessary interval |
|---|---|---|---|
| 1.000 µA | 5.944570 MΩ | 0.300000 MΩ | None |
| 0.001 µA | 5.944570 MΩ | 300.000000 MΩ | Exists conditionally |

This uses nominal Rth=47k∥6.8k, allocated Ron 10 Ω, error 0.1% and park 0.3 V. It supplies no component tolerance or temperature guarantee. Switched discharge changes the tradeoff but adds default-state and transition obligations.

## Charge and qualification

The ideal |Q|/Cmin step for allocated 1 pC and hypothetical 1 nF is 1.000 mV. Exact signed charge, feedthrough and minimum capacitance remain unqualified; maximum capacitance is separately needed for discharge.

All seven qualification inputs are null and proposed permission is disabled. The HOLD/QUALIFY/SETTLE/ACQUIRE/TRIP/REARM table is a requirements artifact, not an implemented or tested state controller. Physical isolation, parking and sample validity cannot be inferred from a displayed command.

675 prior hashes and the four-member sensing net remain preserved. No native tool or hardware action occurred. Next screen exact device/arrangement limits against every state before selecting parts or amending an isolated SENSE-02 copy.
