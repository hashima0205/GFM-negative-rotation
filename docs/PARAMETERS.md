# Complete common parameter definitions

Canonical inputs are [common.toml](../inputs/common.toml) and [cases.csv](../inputs/cases.csv). Only the case-level outer-control settings differ between the main cases. The quantities below use the shared model per-unit bases.

## Network

| Line | From–to bus | R [pu] | X [pu] | Post-fault status |
|---|---|---:|---:|---|
| L1 | 1–4 | 0.1209434790198695 | 0.45136720854629359 | connected |
| L2 | 4–6 | 0.051407123623603911 | 0.19185399723426411 | connected |
| L3 | 5–6 | 0.259303579454355 | 0.96773413310812628 | connected |
| L4 | 3–5 | 0.11711269009163834 | 0.4370705096330626 | connected |
| L5 | 2–3 | 0.13550735345681714 | 0.50572032790003574 | connected |
| L6 | 2–5 | 0.1209434790198695 | 0.45136720854629359 | connected |
| L7 | 4–5 | 0.14378835839028931 | 0.53662545904948245 | open |
| L8 | 2–8 | 0.11927144935600034 | 0.44512710888897156 | connected |
| L9 | 2–7 | 0.04050376292684206 | 0.15116210114069928 | connected |
| L10 | 7–8 | 0.1531473639659886 | 0.57155374336631259 | connected |
| L11 | 5–8 | 0.02888605414090633 | 0.1078042216840478 | connected |

The impedance angle is 75°. L2 and L3 use the verified C grid-strength factor k=0.6812730259441179. All line-end shunt conductances/susceptances are zero, transformer ratios are 1, and every line is connected before/during the fault. L7 opens at clearing. Lines are static admittances, not dynamic line-inductor models.

Bus5 has G=2.268230115233306, B=1 pu and load admittance G+jB. The capacitor supplies positive Q. Bus4 has a consuming shunt conductance 20 pu only during 1.00–1.15 s. Bus8 has no load. Bus6 is an ideal fixed 1∠0 pu, 60 Hz slack.

## Machine parameters

The same values apply to all four machines except their P/Q commands. The input keys retain the source component names; the executable code uses the typed `Machine` fields. Kp and τp are set at case level and are not duplicated in the machine table.

| Input parameter | Bus1 | Bus2 | Bus3 | Bus7 |
|---|---:|---:|---:|---:|
| droop₊Kq | 0.050000000000000003 | 0.050000000000000003 | 0.050000000000000003 | 0.050000000000000003 |
| droop₊Pset | 0.5 | 0.40000000000000002 | 0.40000000000000002 | 0.40000000000000002 |
| droop₊Qset | 0.16370094127236381 | 0.19769004039190199 | 0.11248584940369824 | 0.052320804785790848 |
| droop₊Vset | 1 | 1 | 1 | 1 |
| droop₊τ_q | 0.02 | 0.02 | 0.02 | 0.02 |
| droop₊ω0 | 376.99111843077515 | 376.99111843077515 | 376.99111843077515 | 376.99111843077515 |
| vsrc₊C | 0.1086 | 0.1086 | 0.1086 | 0.1086 |
| vsrc₊CC1_F | 1 | 1 | 1 | 1 |
| vsrc₊CC1_Fcoupl | 1 | 1 | 1 | 1 |
| vsrc₊CC1_KI | 0.0018 | 0.0018 | 0.0018 | 0.0018 |
| vsrc₊CC1_KP | 0.98170000000000002 | 0.98170000000000002 | 0.98170000000000002 | 0.98170000000000002 |
| vsrc₊I_max | 1.2 | 1.2 | 1.2 | 1.2 |
| vsrc₊Lf | 0.019599999999999999 | 0.019599999999999999 | 0.019599999999999999 | 0.019599999999999999 |
| vsrc₊Lg | 0.020899999999999998 | 0.020899999999999998 | 0.020899999999999998 | 0.020899999999999998 |
| vsrc₊R_virt | 0 | 0 | 0 | 0 |
| vsrc₊Rf | 0.013899999999999999 | 0.013899999999999999 | 0.013899999999999999 | 0.013899999999999999 |
| vsrc₊Rg | 0.01 | 0.01 | 0.01 | 0.01 |
| vsrc₊VC_F | 1 | 1 | 1 | 1 |
| vsrc₊VC_Fcoupl | 1 | 1 | 1 | 1 |
| vsrc₊VC_KI | 0.027300000000000001 | 0.027300000000000001 | 0.027300000000000001 | 0.027300000000000001 |
| vsrc₊VC_KP | 1.4476 | 1.4476 | 1.4476 | 1.4476 |
| vsrc₊X_virt | 0 | 0 | 0 | 0 |
| vsrc₊filter₊connected | 1 | 1 | 1 | 1 |
| vsrc₊ω0 | 376.99111843077515 | 376.99111843077515 | 376.99111843077515 | 376.99111843077515 |

## Equations, signs and units

Complex stationary-frame variables rotate at nominal ω0=2π60 rad/s. The current directions If and Ig point from the inverter to the network; Vc is the LCL capacitor voltage, Vi is the commanded internal converter voltage and U is terminal bus voltage. In each inverter:

```math
\frac{L_f}{\omega_0}\dot I_f=V_I-V_C-(R_f+jL_f)I_f,
\qquad \frac{C}{\omega_0}\dot V_C=I_f-I_g-jCV_C,
\qquad \frac{L_g}{\omega_0}\dot I_g=V_C-U-(R_g+jL_g)I_g.
```

The supplied `connected` flag is 1 for every inverter. The implementation retains its multiplication on terminal voltage. No inverter disconnection occurs.

The controller dq transformation is d+jq=(r+ji)exp(−jδ). Define W=[[0,1],[-1,0]] and eV=Vref,dq−Vc,dq. The virtual impedance is zero here; generally Vref,d=V*−Rv Ig,d+Xv Ig,q, Vref,q=−Rv Ig,q−Xv Ig,d.

```math
\dot\gamma_V=e_V,\qquad r_I=-F_{V,c}CW V_{C,dq}+K_{PV}e_V+K_{IV}\gamma_V+F_V I_{g,dq},
\alpha=\min\!\left(1,\frac{I_{\max}}{\sqrt{r_{I,d}^2+r_{I,q}^2+10^{-6}}}\right),\qquad I^*_{f,dq}=\alpha r_I,
\dot\gamma_I=I^*_{f,dq}-I_{f,dq},
V_{I,dq}=-F_{I,c}L_fW I_{f,dq}+K_{PI}(I^*_{f,dq}-I_{f,dq})+K_{II}\gamma_I+F_I V_{C,dq}.
```

Voltage PI gains have units pu current/pu voltage and pu current/(pu voltage·s). Current PI gains have units pu voltage/pu current and pu voltage/(pu current·s). Integrator states retain the corresponding error×seconds units. Feedforward and cross-coupling flags are all 1. No extra anti-windup loop or instantaneous actual-current clamp has been added.

The Droop and VSM outer equations are in the [README](../README.md#model-and-parameters). `mp` has units pu frequency/pu power; Kp=ω0 mp is the equivalent dimensional P–f gain in (rad/s)/pu power. H is in seconds; D=1/mp, D1 and D2 are pu power/pu frequency. The washout pole ωD is in s⁻¹, with a 0.02 s time constant in C. H is not a Droop input. τp is not an independent VSM measurement-filter time constant.

The equations use one common model power base. Physical MVA/kV ratings are not inferred. In particular, a P command is not the device rating. The stated H and droop are on this model base.

## Native state order

Each inverter contributes 13 states, in Bus1, Bus2, Bus3, Bus7 order. The CSV fields x1,… have this ordering:

| Offset within each 13-state block | State | Unit / frame |
|---|---|---|
| 1,2 | Current PI γq, γd | pu current·s; local dq |
| 3,4 | Ig,i, Ig,r | pu current; stationary frame |
| 5,6 | Vc,i, Vc,r | pu voltage; stationary frame |
| 7,8 | If,i, If,r | pu current; stationary frame |
| 9,10 | Voltage PI γq, γd | pu voltage·s; local dq |
| 11 | Filtered reactive power Qf | pu power |
| 12 | Droop: Pf; VSM: ν | pu power; pu frequency, respectively |
| 13 | Internal δ | unwrapped rad, fixed Bus6 reference |

For VSM only, x53…x56 are washout z for Bus1/2/3/7, in pu frequency. `states.csv.gz` stores every differential state. The seven non-slack complex bus voltages are algebraic functions of Ig and the stage network. The slack is fixed. Section files retain the complete initial/final native vectors and all eight reconstructed complex bus voltages.

The [legacy 66-state ordering](../provenance/legacy_states.csv) is provided only for source comparison. In legacy-coordinate VSM reference files, the old Pf slot is an auxiliary P*−ν/mp coordinate. This does not mean a P-filter state exists in the VSM integrator.

## Observations

`observations.csv.gz` contains individual internal angle/frequency, Vc, terminal U, If/Ig magnitudes, P/Q at the measurement and terminal positions, pre/post-limit dq current commands, limiter scale/active flag, Qf, native ν and VSM z. `Pfilter_pu` is NaN for VSM by design. Complex terminal U and Ig are also saved for independent network-power reconstruction. NaN in inactive, explicitly named fields is not a solver failure.

The pre-fault stable state initializes every physical/PI/filter state; VSM z starts at ν=0. At fault application/clearing, all differential states are inherited exactly. The algebraic bus voltages may jump. The fault is applied in three explicit integration segments, with no time smoothing or shift of either switch.
