# OrbInspect corrected reproducibility package

This archive supports the manuscript *Viability-Preserving Rollout
Approximate Dynamic Programming for Dynamics-Aware Orbital Inspection*.
It was assembled on 2026-09-05 from repository revision
`1743eb6083e09b17f1612bd451978f1117f1b101`.

## Evidence boundary

The primary evidence is a deterministic offline paired comparison on a frozen
candidate graph and incumbent-feasible scenario set. The corrected test split
was not used to tune the corrected graph or policy, but the same seed identities
appeared in superseded pre-correction analyses. It is therefore a frozen
corrected benchmark, not a prospectively untouched external test sample.

Some byte-preserved primary metadata still use the earlier terms
`held-out`, `predeclared`, or `before test access`. Those design labels are
superseded by `EVIDENCE_CORRECTIONS.json`; the archived graph, scenario,
method-row, and primary numerical results remain unchanged.

The ROS evidence is one corrected, media-backed closed-loop execution of
`validation_002`. It verifies the interface, reference execution, logging,
sampled terminal gates, and a post-run full-mesh finite-body audit. It is not a
corrected paired ROS campaign or an additional offline comparison observation.

This package excludes every 2026-08-10 depth-sensitivity bundle and every
result derived from the obsolete translation-only mesh interpretation. It
instead includes a new depth-one-to-six sweep run entirely after the primary
analysis on the corrected graph and validation scenarios. That sweep is
post-selection diagnostic evidence and did not select or justify depth three.

The high-coverage and mandatory-target experiment is likewise included only as
post-selection exploratory evidence. Its sentinels were selected using the
frozen test and shifted scenario inventories, and its coverage-only and
sentinel-constrained variants returned identical routes in the archived cases.
It does not alter the frozen 80% paired comparison.

## Contents

- `data/results/adp_future_full_transform_radius080_20260812/`: corrected
  primary offline bundle. It contains the 24-node/41-inspectable-target graph,
  frozen scenarios, all method--scenario rows, paired statistics, summaries,
  figure data, and legacy provenance manifests interpreted together with
  `EVIDENCE_CORRECTIONS.json`.
- `data/results/adp_depth_corrected_postselection_d{1..6}_20260905/`:
  six corrected-graph validation runs used by the post-selection depth
  diagnostic. Each run uses the same graph and 12 validation scenarios and
  changes only the adaptive rollout depth.
- `data/results/ros_verification_inputs_full_transform_radius080_20260812/`:
  hash-checked ROS reference export for 124 ADP/local-search routes over the
  validation, test, and shifted splits. These routes were exported but were
  not executed as a new 124-run ROS campaign.
- `data/results/ros_rviz_full_planning_demo_corrected_validation002_radius080_20260812/`:
  accepted graphical closed-loop ROS task used for the manuscript camera-view
  figure and video. It contains the six CSV streams, configuration and route
  manifests, launch log, summary, version-2 mesh audit, raw RViz/camera media,
  annotated H.264 video, figure sources, and media provenance.
- `data/results/high_coverage_key_targets_20260904/`: post-selection
  exploratory stress test at 95% and 98% inspectable coverage, including the
  six spatial-sentinel definitions, scenario-level rows, and structural
  feasibility summaries.
- `src/`: the current twelve-package ROS 2 source snapshot and tests. Python
  caches are excluded. The NASA ISS GLB is excluded as a third-party asset;
  see below.
- `OrbInspectLatex/`: IEEE Transactions manuscript sources, publication
  figures, corrected depth source table and manifest, and the scripts used for
  the offline and ROS figure/video artifacts.
- `EVIDENCE_CORRECTIONS.json`: machine-readable correction of obsolete
  evidence-design labels and the legacy depth-figure provenance.
- `pytest.ini` and `project/`: root test configuration and
  repository-level build/test notes.

## Evidence-to-claim map

| Manuscript evidence | Source of record |
|---|---|
| Corrected graph, target masks, transfers, and scenarios | `data/results/adp_future_full_transform_radius080_20260812/raw/hcw_graph.json` and `raw/scenarios.json` |
| Frozen test and shifted method results | `data/results/adp_future_full_transform_radius080_20260812/raw/heldout_results.csv` |
| Paired confidence intervals and multiplicity checks | `data/results/adp_future_full_transform_radius080_20260812/statistical_validation.json` |
| Current evidence-design interpretation and legacy-metadata correction | `EVIDENCE_CORRECTIONS.json` |
| Primary figure/table transformations, except the current depth diagnostic | `data/results/adp_future_full_transform_radius080_20260812/figure_table_trace.json`, read with `EVIDENCE_CORRECTIONS.json` |
| Post-selection corrected depth diagnostic | `data/results/adp_depth_corrected_postselection_d1_20260905/` through `data/results/adp_depth_corrected_postselection_d6_20260905/`, `OrbInspectLatex/data/adp_depth_sensitivity_corrected_20260905.csv`, and `OrbInspectLatex/figures/adp_future/adp_depth_tradeoff_manifest.json` |
| Corrected ROS route provenance | `data/results/ros_verification_inputs_full_transform_radius080_20260812/manifest.json` |
| One accepted ROS execution | `data/results/ros_rviz_full_planning_demo_corrected_validation002_radius080_20260812/summary.json` |
| Full-mesh finite-body ROS audit | `data/results/ros_rviz_full_planning_demo_corrected_validation002_radius080_20260812/mesh_execution_audit.json` |
| Camera-view figure provenance | `data/results/ros_rviz_full_planning_demo_corrected_validation002_radius080_20260812/figures/ros_key_camera_views_trajectory_manifest.json` |
| Annotated video provenance | `data/results/ros_rviz_full_planning_demo_corrected_validation002_radius080_20260812/videos/video_manifest.json` |
| Exploratory high-coverage and sentinel stress test | `data/results/high_coverage_key_targets_20260904/raw/scenario_results.csv` and `summary.json` |

## Critical source hashes

```text
e90f40f0aaf87464ad5b5ef6b39979aa3c5f0b7049fe0ec17ad5e5b1a19b0af2  corrected hcw_graph.json
3f59a5e2e8dab0c2dddb9538321ab5f8890d15b8bfc9fcf5933096e2d5a5b920  corrected scenarios.json
d5696d4075feb0a0d50cd5cd6fb79e9cdb2545720d1d14a004c20b415a0d4f14  corrected heldout_results.csv
602d690828877c21a05e64592af54866ae648443e0a809c6e796d28356f5b4bf  accepted ROS summary.json
9ac1b2365d0c61a512059877c8770bce3c1110460e7c3e91182619787a8544e3  accepted ROS mesh_execution_audit.json
0b954553816c2a4bb1a398c111958e75bf8ed944d7550b39e82897766182b1a7  accepted annotated ROS video
```

The archive-level `SHA256SUMS.txt` is the transfer-integrity source of record.
Run the following command from the archive root after extraction:

```bash
shasum -a 256 -c SHA256SUMS.txt
```

## Deterministic offline rerun

Use Python 3.12 with NumPy, Matplotlib, scikit-learn, PyYAML, and pytest. From
the archive root, place the guidance package on `PYTHONPATH` and run:

```bash
export PYTHONPATH="$PWD/src/orbinspect_guidance${PYTHONPATH:+:$PYTHONPATH}"
python3 -m orbinspect_guidance.offline_adp_superiority_study \
  --config src/orbinspect_guidance/config/adp_future_study.yaml \
  --graph-cache data/results/adp_future_full_transform_radius080_20260812/raw/hcw_graph.json \
  --candidate-limit 24 --goal-coverage 0.80 --max-steps 14 \
  --branch-width 8 --candidate-pool-width 18 --lookahead-depth 2 \
  --training-scenarios 24 --validation-scenarios 12 \
  --test-scenarios 30 --ood-scenarios 20 --episodes-per-scenario 12 \
  --critic-backend ridge --training-target rollout \
  --adaptive-rollout-depth 3 --splits test,ood \
  --run-id adp_future_full_transform_radius080_independent_rerun
```

Recompute the statistical outputs and compare all non-timing fields with:

```bash
python3 -m orbinspect_guidance.offline_adp_future_analysis \
  --result-dir data/results/adp_future_full_transform_radius080_independent_rerun \
  --bootstrap-draws 10000 \
  --original-dir data/results/adp_future_full_transform_radius080_20260812
```

Wall-clock fields are environment-sensitive and are excluded from the exact
deterministic comparison.

## Post-selection diagnostic reproduction

The six corrected depth runs are retained as source data. Regenerate the
three-panel depth figure, corrected CSV source table, and provenance manifest
from the archive root with:

```bash
python3 OrbInspectLatex/scripts/generate_depth_tradeoff_figure.py
```

To rerun the exploratory high-coverage and six-sentinel analysis under a new
identifier, use:

```bash
python3 OrbInspectLatex/scripts/evaluate_high_coverage_key_targets.py \
  --study-root data/results/adp_future_full_transform_radius080_20260812 \
  --output-root data/results \
  --run-id high_coverage_key_targets_independent_rerun \
  --goals 0.95,0.98 --splits test \
  --sentinel-selection-splits test,ood \
  --max-steps 14 --adaptive-rollout-depth 3
```

These analyses are explicitly post-selection. Regeneration does not turn them
into independent or confirmatory evidence.

## ROS 2 reproduction boundary

The ROS target is Ubuntu 24.04.4, ROS 2 Jazzy, Gazebo Harmonic, RViz2, and
Python 3.12. Gazebo is a visual and camera renderer; the ROS-native HCW node is
the spacecraft-state source of truth. After restoring the ISS mesh described
below, build and launch from the archive root:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 launch orbinspect_bringup demo_corrected_rviz.launch.py
```

Always use a new result identifier. Do not overwrite the accepted evidence
directory. The retained run was accelerated by a factor of five for graphical
capture; it is an execution/interface demonstration, not timing evidence.

## Third-party geometry

The NASA International Space Station GLB is not redistributed in this archive.
Obtain `ISS_stationary.glb` from the
[NASA International Space Station 3D model page](https://science.nasa.gov/resource/international-space-station-3d-model/)
and place it at:

```text
src/orbinspect_description/models/iss_real/meshes/ISS_stationary.glb
```

The required file SHA-256 is:

```text
26dba905b4b7555edbcb0c5f5a61b5c18659f5166076ab27dbb0e64025759fca
```

The corrected pipeline applies the complete glTF node hierarchy, followed by
the recorded SDF pose and scale. Do not substitute the earlier
translation-only interpretation.

The small `CubeSat_1RU_Generic.glb` visual is included because the Gazebo
camera demonstration references it. Its `model.config` records NASA 3D
Resources as the origin; the source collection is the
[NASA 3D Resources hub](https://science.nasa.gov/3d-resources/) and its
[public mirror](https://github.com/nasa/NASA-3D-Resources). The included file
SHA-256 is
`bae308ea2e33778c93675909f7dc2e0d5d6916cd685668a463566c61224b1e85`.
Reuse remains subject to the NASA media usage guidelines linked from those
pages.

## Deliberate omissions

- The separate rosbag-complete confirmation task is not duplicated because its
  MCAP alone is 2,121,127,166 bytes (approximately 2.0 GiB), which would make
  the submission supplement impractically large. Its MCAP SHA-256 is
  `81f962360fd845b68608fb4b6d2daa970273a0c0392cb07a84bf02b0574744f6`.
  The paper-facing numerical ROS result and all inputs to its figure/video are
  retained in the media-backed task included here.
- Provenance JSON files are preserved byte-for-byte. Some record absolute paths
  from the execution host; the relative archive locations and hashes above are
  portable.

## Licence and persistent access

The ROS package metadata declare `Apache-2.0` for the source code, but the
source repository does not yet contain a repository-level licence file. The
authors must confirm that licence before public deposition and assign an
explicit data/media licence compatible with the NASA assets and recorded
videos. Deposit the finalized archive in a durable repository that supplies a
DOI or other persistent identifier; do not use a temporary personal or
cloud-storage link as the sole access route.
