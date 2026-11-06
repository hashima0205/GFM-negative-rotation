# Physical fault paths and conditional initial-state sections

The main figures follow the operating sequence from the pre-fault state. They use the layout of the historical `vsm_basin_slack_rotation_recovery_D1_10_20` figure, identified in the source materials as `studies/h2p5_bus5_basins/basins_slack.png`. That reference used mp=10% and D1=10/20. Current A/B/C parameters remain mp=5%; neither old labels nor physical trajectories are reused.

## Start with the pre-fault state

All main cases start at the same equilibrium: mean remote internal angle −0.323414657 rad relative to fixed Bus6, internal frequency deviation zero, Bus5 voltage 0.996594324 pu. Absolute time 0–1 s collapses to this point in the phase plane; the blue triangle represents it.

The Bus4 fault is applied at 1 s. Purple shows the fault-on path through 1.15 s. Removing the shunt and opening L7 at 1.15 s defines clearing and post-fault time zero. The white circle is the continuous internal-angle/frequency clearing state. Black shows the first 30 post-fault seconds. A recovers toward the stable point (mean angle −1.669678513 rad, zero frequency deviation); B/C continue in the negative-angle direction. Their 1000 s classifications are unchanged.

Full saved observations are in `results/A,B,C/`. Plot-specific stage-labeled data are in `results/fault_basins/<case>/physical_fault_projection.csv`; `anchors.csv` identifies the operating, switching and equilibrium coordinates. Angles are unwrapped, with no origin subtraction. Frequency means the internal frequency deviation of Bus2/3/7. Its kinematic relation to the mean angle is checked against the model RHS.

## Why the first publication looked different

| Feature | Initial publication: now local diagnostics | Revised main / historical prescription |
|---|---|---|
| Displayed angle | Stable angle ±0.087 rad | −2.25 to −0.2 rad, including pre-fault point |
| Displayed frequency | ±0.045 Hz | −1.25 to 0.08 Hz |
| Samples per case | 49 | 43 |
| Remote internal angles/frequency | Uniformly changed | Uniformly changed |
| Initial Vc/If/Ig | Rotated with internal angle | **Held at the post-fault root** |
| Other initial states | Root values; VSM z=0 | Root values, including VSM z=0 to root precision |
| Main curves | Section-launched representatives | **Actual pre/fault/post trajectory** |
| Background | Classified scatter | Scatter and homogeneous/mixed-vertex triangles |

Changing electrical states changes the high-dimensional initial-state section even at identical plotted coordinates. The local plot is therefore not a zoom of the new background. Neither physical-fault simulations nor controller parameters were changed in this revision.

## Revised section and interpretation

Start at each case's post-fault stable root. Uniformly shift only the three remote internal angles and set only their frequency coordinates: Pf=P*−Δf/(60mp) for Droop, ν=Δf/60 for VSM. Relative remote angles are retained. All other differential states initially remain at the root: Vc/If/Ig, dq PI integrators, Qf, Bus1 and all VSM washout states. Algebraic voltages are reconstructed with the post-fault network. **All differential states evolve after initialization.**

The 43 coordinates reproduce the historical sampling positions: seven angles × five frequencies, plus four angles × two small frequency deviations. [Exact input](../inputs/fault_basin.toml), [integration](../scripts/fault_basins.jl), [checks](../scripts/check_fault_basins.jl), [plotting](../scripts/plot_fault_basins.py). Every point is newly integrated for 1000 s with the current classifier; historical labels and 30/100/300 s stopping decisions are not imported.

Each point retains full native initial/final states, reconstructed voltages, requested/actual coordinates, per-machine labels/metrics and a saved projection trajectory. Homogeneous triangles summarize only three vertices; their interiors are not independently classified. Mixed/unresolved vertex triangles are hatched. This is not an exact boundary.

The actual fault path generally lies **outside the initial-state section** because its other states have evolved. Background color at its projected coordinates cannot determine its outcome. The saddle is also a full-state projection, not a proved section-boundary intersection. A is a recovery fault-response example; a negative-running background point is not required.

## Historical D1=10 and current C are dynamically equivalent

The historical D1=10 side used mp=0.10, giving nominal damping 1/mp+D1=10+10=20. Current C uses mp=0.05 and D1=0, giving 20+0=20. With H=2.5 s, D2=100, ωD=50 and the same remaining model, these yield the same VSM differential equations. A change in the names of the coefficients does not change these trajectories.

All **43 C labels agree** with the historical side: 19 recover and 24 run negatively. Full native initial states agree within 1.56×10⁻¹⁵; evaluating both parameterizations at the same states gives identical RHS values. The physical trajectories agree at 1903 common saved timestamps through 30 s, with angle error below 1.5×10⁻¹¹ rad and frequency error below 5×10⁻¹² Hz. No interpolation is used for this check. [Recorded checks](../results/validation/basin_view_trajectory_checks.json), [historical compact initial-state reference](../provenance/reference_results/historical_D1_10_section.csv), [historical projected-path reference](../provenance/reference_results/historical_D1_10_fault_projection.csv).

A's revised section has 43 recovery points; B has 13 recovery / 30 negative-running points. These are independent integrations with the A/B controllers, rather than transferred VSM labels.

## Data and provenance

- Main data: [A](../results/fault_basins/A/), [B](../results/fault_basins/B/), [C](../results/fault_basins/C/).
- Verification: [state/constraint checks](../results/validation/fault_basin_checks.toml), [coordinate/display summary](../results/validation/fault_basin_plot_checks.json).
- Historical source identities and hashes: [basin_view_revision.json](../provenance/basin_view_revision.json).
- Local diagnostic data remain in [results/basins](../results/basins/); see [detailed figures](DETAILS.md#phase-plane-details).

```bash
JULIA_NUM_THREADS=8 OPENBLAS_NUM_THREADS=1 julia --project=. scripts/fault_basins.jl
julia --project=. scripts/check_fault_basins.jl
python scripts/plot.py --only basins
python scripts/verify_basin_views.py
python scripts/plot.py --only local-basins  # Separate diagnostic section.
```
