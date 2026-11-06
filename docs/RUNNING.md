# Purpose-specific execution

Run from the repository root. Python 3.11+ is required (`tomllib`); the recorded environment used Python 3.13.9. Install the pinned packages:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Julia calculations/checks use Julia 1.12.5 and the committed Project/Manifest:

```bash
julia +1.12.5 --project=. -e 'using Pkg; Pkg.instantiate()'
export OPENBLAS_NUM_THREADS=1
```

Select that Julia version, or use `julia +1.12.5` for every Julia command below. `gzip` must be available. The workflows below are alternatives; replotting does not require running the simulations or Julia setup.

## 1. Draw from the committed saved data

```bash
# Individual-machine responses, section plots and local diagnostic plots.
python scripts/plot.py
# System diagram and all saved network-flow views.
python scripts/power_flow.py
```

Both write under `outputs/figures/`, preserving the `paper/` and `details/` subdirectories. They read committed numeric datasets and leave `results/` and `figures/` untouched. Every newly drawn figure has PNG/PDF files and a `.sources.json` sidecar listing datasets, input hashes, plotting code and axis metadata.

Choose only the figures needed:

```bash
python scripts/plot.py --only time
python scripts/plot.py --only basins
python scripts/plot.py --only local-basins
python scripts/plot_flow_comparison.py
python scripts/network_figure.py --input results/power_flow/C_post_1s
```

Use `--output /path/to/new/figures` to choose a figure output directory. The standalone network renderer takes the same directory convention. Plotting reads the result's archived settings and rejects a mismatch with the current canonical inputs or computational code. It never refreshes classification CSVs, triangles, numeric snapshots or validation reports.

## 2. Recompute physical-fault cases

```bash
# One main case; the complete pre/fault/post schedule is integrated.
julia --project=. scripts/run.jl cases.csv C
# All main and additional cases in cases.csv.
julia --project=. scripts/run.jl cases.csv
# Select cases and an explicit output root.
julia --project=. scripts/run.jl cases.csv A,B,C --output outputs/abc-rerun
```

Outputs default to `outputs/runs/<case>/`. The entry point selects the controller from the case's `control` field. It preserves all differential states across events, including VSM z. Each output contains `run_record.toml`, input snapshots/hashes, code hashes, states, observations, roots, machine classifications and event/constraint checks. The record is finalized with data hashes. A nonempty existing physical-run directory is rejected; select a new output directory rather than overwriting a baseline.

For a short implementation check, `--horizon 5` changes only the post-clearing duration. This short run is not a substitute for the committed 1000 s classification. Strict integration uses `--strict`; its output tag has `_strict` appended.

Solver tolerances, maximum internal step and saved intervals come from [study.toml](../inputs/study.toml). The adaptive internal step is not the saved output interval.

## 3. Recompute conditional sections

```bash
# Main, frozen-electrical-state initial section.
JULIA_NUM_THREADS=8 julia --project=. scripts/fault_basins.jl
# Separate local diagnostic section with rotated electrical states.
JULIA_NUM_THREADS=8 julia --project=. scripts/basins.jl
```

Outputs are `outputs/fault_basins/<case>/` and `outputs/local_basins/<case>/`. The default target roots are the verified committed physical-case roots. `--results <run-root>` selects freshly computed case roots; that directory must contain the required A/B/C runs and valid identities. `--output` selects the section output root.

Only matching section checkpoints are resumed: the case row, physical input, numerical/classification settings, section input, computational source and exact target-root file must match. Missing identities or a mismatch stop the run. Changing a section creates a different initial-state experiment; do not relabel it as a zoom. See [section definitions](BASIN_VIEWS.md).

The entry points integrate and save new point states/projections. Prepare plotting tables with an explicit export step, which leaves source points unchanged:

```bash
python scripts/export_section_views.py --sections outputs/fault_basins --output outputs/section-views
python scripts/plot.py --only basins --section-results outputs/section-views
```

For a recalculated local section, add `--local` to the exporter, select `outputs/local_basins`, and use the plotter's `--local-results` with `--only local-basins`. `--results` selects physical-case runs and the exporter's `--roots` selects verified section-root results; defaults are the committed common-condition datasets. Input/code mismatches reject inappropriate root reuse. Plotting committed section figures needs none of these calculation/export commands.

## 4. Numerical verification and source comparisons

```bash
# Reference regression and full saved-waveform classification, no integration.
julia --project=. scripts/check_refactor.jl
# Legacy equations, state conversion, and undamped Droop/VSM equivalence.
julia --project=. scripts/check_equations.jl
# Common conditions and both section definitions.
julia --project=. scripts/check_conditions.jl
julia --project=. scripts/check_fault_basins.jl
julia --project=. scripts/check_basins.jl
# Existing strict/source waveform comparisons.
python scripts/validate.py
# Physical-path projections and network-flow balances.
python scripts/verify_basin_views.py
python scripts/check_flows.py
```

Reports go to `outputs/checks/`, or a directory selected with `--output`. They do not replace the committed validation baseline. `check_refactor.jl` evaluates the archived RHS/voltage fixtures and reclassifies every saved post-fault sample of the four adopted cases. It performs no new long integration.

When new strict integrations are needed, use a separate output root:

```bash
julia --project=. scripts/run.jl cases.csv A,B,C --strict --output outputs/strict-check
# Source-condition replay is a distinct validation task.
julia --project=. scripts/run.jl original_cases.csv --output outputs/source-replay
```

Full source/strict tables and adopted main tables must be present together when pointing the saved-waveform validator at a different `--results` root. The original-condition inputs are migration evidence, not additional paper cases.

## 5. Optional derived-data exports

`python scripts/power_flow.py --export --output outputs/new-flow-data` reconstructs fresh bus/line tables and balance audits from the selected saved case states. It does not run Julia. Existing export directories are rejected. This is an explicit data-export operation, separate from drawing saved flows.

`python scripts/compact_validation.py source.csv.gz outputs/check-view.csv.gz` selects validation columns into a new file. It never removes native states, edits reference tables or modifies the source file.

## Identity and provenance

Committed datasets have `record.toml` pointers to [reproduction.toml](../provenance/reproduction.toml), which records case rows, archived input text, input/code hashes and data hashes. Original generation provenance is retained; the refactor's equivalence binding is identified separately. Presentation settings in `inputs/figures.toml` are separate from numerical result identities; changing colors or display ranges does not require another integration. A numerical-input/code/data hash mismatch is an error, not permission to regenerate a catalog or silently bless stale results. New runs generate their own complete records automatically. [Architecture and verification](REPRODUCIBILITY.md).
