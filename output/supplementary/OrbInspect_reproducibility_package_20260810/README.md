# OrbInspect rollout-ADP reproducibility package

This archive accompanies the manuscript *Viability-Preserving Rollout
Approximate Dynamic Programming for Dynamics-Aware Orbital Inspection*.
It contains the frozen held-out graph and scenarios, all method rows,
statistical outputs, development-split records, figure artifacts and trace
metadata, the deterministic rerun comparison, the planning source and tests,
the frozen YAML configuration, and the figure-generation source.

## Evidence boundary

The archived results are deterministic, offline, and simulator-only. They do
not contain ROS 2 execution measurements. ROS 2 Jazzy replay is intentionally
deferred until the Ubuntu 24.04 target environment is available.

## Key directories

- `data/results/adp_future_physical_heldout_20260810/`: primary held-out bundle.
- `data/results/adp_future_physical_heldout_repro_20260810/`: exact non-timing rerun audit.
- `data/results/adp_dev_adaptive_depth{1,2,3}_fullmesh_20260810/`: validation-only depth selection.
- `src/orbinspect_guidance/`: planner, experiment, analysis, and tests.
- `OrbInspectLatex/scripts/generate_adp_future_figures.py`: manuscript figure generator.
- `docs/adp_future_experiment_protocol.md`: frozen study protocol.
- `manuscript/`: LaTeX source and bibliography corresponding to the supplied PDF.

## Environment and public mesh dependency

The target environment is Python 3.12 with NumPy, Matplotlib, scikit-learn,
PyYAML, and pytest. The ISS geometry is the public NASA International Space
Station 3D model. It is not duplicated in this archive. Place
`ISS_stationary.glb` at
`src/orbinspect_description/models/iss_real/meshes/ISS_stationary.glb`.
The file used for the reported graph has SHA-256
`26DBA905B4B7555EDBCB0C5F5A61B5C18659F5166076AB27DBB0E64025759FCA` and is
available from <https://science.nasa.gov/resource/international-space-station-3d-model/>.

## Deterministic held-out rerun

From the archive root, put `src/orbinspect_guidance` on `PYTHONPATH` (or install
that package), then run:

```text
python -m orbinspect_guidance.offline_adp_superiority_study \
  --config src/orbinspect_guidance/config/adp_future_study.yaml \
  --graph-cache data/results/adp_future_physical_heldout_20260810/raw/hcw_graph.json \
  --candidate-limit 24 --goal-coverage 0.80 --max-steps 14 \
  --branch-width 8 --candidate-pool-width 18 --lookahead-depth 2 \
  --training-scenarios 24 --validation-scenarios 12 \
  --test-scenarios 30 --ood-scenarios 20 --episodes-per-scenario 12 \
  --critic-backend ridge --training-target rollout \
  --adaptive-rollout-depth 3 --splits test,ood \
  --run-id adp_future_physical_heldout_independent_rerun
```

Analyze and compare the rerun with:

```text
python -m orbinspect_guidance.offline_adp_future_analysis \
  --result-dir data/results/adp_future_physical_heldout_independent_rerun \
  --bootstrap-draws 10000 \
  --original-dir data/results/adp_future_physical_heldout_20260810
```

The supplied rerun audit reports exact agreement for every non-timing field in
all 350 method--scenario rows. Wall-clock fields are deliberately excluded.

## Figure regeneration

```text
python OrbInspectLatex/scripts/generate_adp_future_figures.py \
  --result-dir data/results/adp_future_physical_heldout_20260810 \
  --dev-depth1 data/results/adp_dev_adaptive_depth1_fullmesh_20260810 \
  --dev-depth2 data/results/adp_dev_adaptive_depth2_fullmesh_20260810 \
  --dev-depth3 data/results/adp_dev_adaptive_depth3_fullmesh_20260810 \
  --config src/orbinspect_guidance/config/adp_future_study.yaml \
  --paper-dir OrbInspectLatex
```

The machine-readable `figure_table_trace.json` records source files,
transformations, hashes, and the completed visual-verification iterations.
