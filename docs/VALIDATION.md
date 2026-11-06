# Verification and source migration

## Sources and the confirmed C case

VSM source: [VSM_decelaration](https://github.com/hashima0205/VSM_decelaration), executable-code base `584b7519d67adb135404b9b319445ca428ded413`. The remote head inspected for this publication was `e8fe0e535bee84b824f58cd89139467f027c14dc`; comparison with the local base showed only README.md changes.

The confirmed C input is `check_mp0p05_H2p5_D1_0_B1_20261106`: H=2.5 s, mp=0.05, D1=0, D2=100, ωD=50, τq=0.02 s. That side-case CSV and its generated run were not committed in the source repository. This publication therefore identifies the code commit **and** the input/result SHA-256 values, rather than inventing an execution commit for an uncommitted input. The original configuration signature and source response/settings are in [reference_results](../provenance/reference_results/). C_D1_10 is separately identified there.

Droop handoff: workspace-relative `droop_transfer/`, verified against its README_TRANSFER_JA.md, FILE_MANIFEST.csv and SHA256SUMS. **1932 files, 686336010 bytes**, passed checksum verification. The original execution tree was not a Git repository. The related public repository `hashima0205/gfm-deceleration-simulation` had head `22a1581b7e3807ab7edcd332e9210e1301597258`, but it is not asserted to be the execution source of study13/study15.

[Import audit](../provenance/import_audit.json) · [Selected source file hashes](../provenance/selected_sources.csv) · [Reference waveform selection and original hashes](../provenance/reference_selection.json). These provenance paths identify the source; the executable environment does not read the original workspace or transfer.

## Common-system adjustment versus implementation cleanup

| Setting | Transferred original Droop A/B | Shared paper system A/B/C |
|---|---|---|
| τp candidates | 0.02 / 1.00 s | Same two values for A/B |
| mp | 2% | 5% |
| P* Bus1/2/3/7 | 0.7049006414424951 / 0.10025606988910452 / 0.10014224804119214 / 0.10010511385855865 | 0.5 / 0.4 / 0.4 / 0.4 |
| Bus5 conductance G | 0.921385146865719 | 2.268230115233306 |
| Bus5 capacitive B | 0 | 1 |
| L2/L3 grid factor k | 1.02994 | 0.6812730259441179 |
| Fault interval | 1.00–1.10 s | 1.00–1.15 s |
| τq, Q*, inner PI, LCL, limiter, network connectivity and clearing line | Source values | Preserved |

The Q commands are exactly the values listed in the parameter table, not rounded estimates. The transferred B observation extended to 3000 s; migration comparison uses its first 1000 s. This is a comparison-window selection, not a changed physical scenario. Both new A/B cases use the same 0.15 s fault; neither fault duration nor network condition is varied to create their different outcomes.

The original saved `t_clear_p=1.2` was dormant under explicit fault-enable flags. The actual transferred execution segments clear at **1.1 s**. Original replay uses that segment schedule, not the dormant timer. The full 219-parameter comparison and numeric NetworkDynamics edge-index/original-line-ID mapping are in [parameter_alignment.csv](../provenance/parameter_alignment.csv) and [notes](../provenance/parameter_alignment_notes.json).

The inherited component and base-model source hashes were compared. The common runtime is now a typed, explicit equation implementation. It does not slice exploration files or evaluate strings. The 14 bus-voltage constraints are solved exactly for the constant-admittance network. All 52 original differential states remain. VSM replaces the four Pf coordinates with ν and adds four z states; Droop retains the actual P filters.

Implementation cleanup was checked at the original Droop parameters **before** evaluating the changed common-system conditions. Therefore the change in common-system waveforms is not described as an implementation error. The stored original-condition A/B reproductions agree with their source waveforms. Inactive legacy Kp/τp duplicates were subsequently removed from machine metadata; active canonical equations were rechecked after that cleanup.

## Waveform comparisons

| Comparison | Largest absolute difference across audited channels |
|---|---:|
| A_accuracy | 3.127386128e-10 |
| B_accuracy | 6.782101991e-09 |
| C_D1_10_source_reproduction | 3.052655906e-10 |
| C_accuracy | 3.829063644e-08 |
| C_source_reproduction | 4.632338513e-09 |
| original_droop_A_migration | 4.441562673e-10 |
| original_droop_B_migration | 6.533582564e-10 |

There are **230 per-channel comparisons**, all passing a 10⁻⁵ absolute threshold in the channel’s own unit. The cross-channel maxima above are numerical summaries, not a sum of unlike physical units. The [CSV](../results/validation/waveform_comparisons.csv) preserves the channel identity, sample count, threshold and result. Angles, frequencies, voltages, currents and P/Q were compared on matching saved timestamps with matching event stages.

The C source reference defines remote Pcap and terminal Q as **sums**, while remote current is a **mean**. The compatibility comparison preserves those definitions. Main figures/data retain individual machine values.

The original Droop classifier distinguishes synchronized/transient-negative recovery and resynchronization after slip. Here the first two map to `recovery`, and the last to `recovery_after_slip`; `sustained_negative_rotation` maps to `negative_running` to avoid implying infinite-time proof. Recovery thresholds and late negative-progress tests are documented in the README. The common root separation makes the old adaptive phase tolerance equal to the retained 0.002 rad threshold. Labels of the checked original A/B and C cases did not change. Tail mean frequency is the arithmetic mean on the uniformly saved tail grid; the source Droop report used trapezoidal averaging. This reporting distinction does not enter the classification decision.

Validation-only tables select audited channels without changing saved time samples. Source magnitudes are calculated as hypot(real, imaginary). No temporal resampling or smoothing is used. Full native states and full observations remain for all four main/additional cases.

## Equations, events and constraints

At the 150 sampled legacy VSM states (75 each for C and C_D1_10), the largest shared-model differential-vector-field difference was below 6×10⁻¹¹, and reconstructed legacy-state differences were below 4×10⁻¹⁵. The maximum additional-damping-free Droop/VSM coordinate-equivalence residual was below 2×10⁻¹⁸. See [equations.log](../results/validation/equations.log) and [equivalence.toml](../results/validation/equivalence.toml). The equivalence check is an algebraic relationship, not independent physical validation.

| Case | Max network-constraint residual | Differential event jump | Washout event jump |
|---|---:|---:|---:|
| A | 7.016e-15 | 0 | 0 |
| B | 8.762e-15 | 0 | 0 |
| C | 8.031e-15 | 0 | 0 |
| C_D1_10 | 7.272e-15 | 0 | 0 |

Standard Rodas5P tolerances are rtol=10⁻⁹, atol=10⁻¹¹, dtmax=0.005 s; stricter main-case runs use 10⁻¹⁰, 10⁻¹², 0.0025 s. All main-case machine classifications are unchanged. Internal accepted/rejected step counts are in each `events.csv`; saved output intervals are separately specified.

## Equilibria and conditional sections

| Case | Stable mean internal angle [rad] | Saddle projected mean angle [rad] | Saddle unstable eigenvalue [s⁻¹] | Recovery / negative / unresolved points |
|---|---:|---:|---:|---|
| A | -1.66967851283 | -1.70121520285 | 0.08372299719 | 49 / 0 / 0 |
| B | -1.66967851283 | -1.70121520285 | 0.07780256094 | 30 / 19 / 0 |
| C | -1.66967851283 | -1.70121520285 | 0.08153438673 | 33 / 16 / 0 |

All three full-state saddles have exactly one positive-real-part eigenvalue. Their projections are not asserted to lie on the initial-state section. Each grid point has a full native initial/final state and all bus-voltage values, with requested/actual mean angle/frequency checked. VSM z is explicitly zero initially on the section, not set to the imposed ν. Other coordinates are prescribed in `section.toml` and in the README. The 147 classification points were freshly integrated using the shared paper parameters; no transferred basin labels were reused.

No negative-running example was found among the 49 A-section points, so an A negative-running representative is not fabricated. A wider section or a different choice of other initial states has not been searched here. These finite-time local maps do not establish an exact attraction boundary or explain the fault outcome from two projected coordinates alone.

## Network power flows

The [power-flow directories](../results/power_flow/) contain complex bus voltages, every line’s R/X/status, signed P/Q at both ends, bus injections and balance audits. The snapshots use the saved post-switch state at tpost=0, then tpost=1 and 5 s, consistently for A/B/C. The shared pre/post roots are separately labeled equilibrium data.

Pfrom/Qfrom and Pto/Qto are positive **from their respective buses into the line**. Their sum is line absorption. Bus powers are positive device injection into the network. Fixed-slack terminal voltage angles are principal radian values; these are not the unwrapped internal controller angles used for rotation classification. The checked whole-system boundary is at inverter terminals, so LCL/internal stored energy is not mistaken for a network-power imbalance.

## Limits of this release

- Main and additional physical-fault trajectories cover 1000 s after clearing. This is finite-time evidence.
- Section maps cover only the 49 declared points per case at 1000 s. A has no negative-running representative on this grid; unsampled regions and alternative hidden-state prescriptions remain untested.
- The inverter model is balanced and averaged, with the inherited current-command limiter. No switching, DC-source/SoC dynamics or additional PI-energy mechanism has been introduced.
- No physical MVA ratings are assigned. The model bases and parameter units must be retained when transferring the coefficients to a different installation.
- The source case CSV was uncommitted; its checksum and code commit are both retained rather than assigning an unsupported source execution commit.
- No manuscript, original source repository or transfer file was edited, and no Drive copy or ZIP bundle was made.
