# Data dictionary

Unless stated otherwise, CSV files use a header row, comma delimiters, decimal
points, UTF-8 text, SI units, and an empty field for a quantity that is not
applicable. Boolean fields are serialized as `True` or `False`. Scenario and
candidate identifiers are stable strings and should not be interpreted as
ordinal measurements.

## Corrected offline study

Directory: `data/results/adp_future_full_transform_radius080_20260812/raw/`

### `heldout_results.csv`

One row per method--scenario evaluation.

| Field | Meaning | Unit |
|---|---|---|
| `split` | `test` or distribution-shift (`ood`) partition | categorical |
| `scenario_id`, `scenario_seed` | Frozen scenario identifier and random seed | identifier |
| `method` | Evaluated planner variant | categorical |
| `success` | Whether the inspectable-coverage goal was reached within budget | Boolean |
| `coverage` | Final weighted coverage over candidate-observable targets | fraction |
| `graph_cost` | Sum of archived directed-edge stage costs | study cost unit |
| `penalized_cost` | Graph cost with the predefined failure/shortfall penalty | study cost unit |
| `selected_count` | Number of selected SOOA transfers | count |
| `online_time_s` | Recorded planner wall-clock time | s |
| `safe_action_evaluations` | Historical field name for candidate-action safety checks; it includes candidates subsequently rejected by the shield | count |
| `shield_rejections` | Candidate actions rejected by the safety/viability shield | count |
| `policy_source` | Planner component that supplied the returned route | categorical |
| `total_delta_v` | Sum of impulse-equivalent control magnitude over the route | m/s |
| `min_clearance` | Minimum finite-body clearance above the required mesh margin | m |
| `peak_input` | Maximum commanded acceleration magnitude | m/s^2 |

### `heldout_summary.csv`

Aggregates `heldout_results.csv` by split and method. Fields prefixed with
`mean_`, `median_`, or `p95_` are the indicated sample summaries. Cost,
coverage, time, clearance, acceleration, and evaluation-count units match the
row-level definitions above.

### `paired_comparisons.csv`

Paired proposed-versus-baseline summaries. Differences are proposed minus
baseline; a negative cost or delta-v difference favors the proposed method.
Confidence intervals are paired bootstrap 95% intervals. `cohen_dz` is the
paired standardized mean difference. `exact_sign_test_p` is two-sided, and
`holm_adjusted_sign_test_p` records the multiplicity-adjusted secondary test
where applicable.

### `representative_case_progress.csv`

`action` is the selected-transfer index; `candidate_id` is the reached
observation node; `weighted_coverage` is a fraction; `cumulative_delta_v` is in
m/s; and `cumulative_graph_cost` is in study cost units.

### `representative_case_trajectory.csv`

`time_s` is mission time in seconds. Position (`rx`, `ry`, `rz`) is in metres,
velocity (`vx`, `vy`, `vz`) is in m/s, and acceleration (`ux`, `uy`, `uz`) is
in m/s^2 in the LVLH frame.

### JSON files

- `hcw_graph.json`: node identifiers, camera-valid target bitmasks, target
  weights, node positions, and one archived record per directed HCW transfer.
- `scenarios.json`: split, seed, available nodes, target weights, reference
  route, goal, and action budget for each frozen scenario.
- `critic_checkpoint.json`: fitted-critic negative-ablation parameters and
  training metadata; the proposed rollout policy does not require this critic.
- `representative_case_manifest.json`: post-hoc illustrative-case selection
  and source-row checks.

## Post-selection corrected depth diagnostic

Directories:
`data/results/adp_depth_corrected_postselection_d1_20260905/` through
`data/results/adp_depth_corrected_postselection_d6_20260905/`.

All six directories use the same corrected graph, frozen scenarios, 80%
weighted inspectable-coverage goal, 14-action budget, branch settings, and
shield. Only `adaptive_rollout_depth` differs. Only the 12 validation
scenarios were evaluated; the entire sweep was conducted after the primary
analysis and is diagnostic rather than confirmatory.

- `raw/heldout_results.csv`: one row per validation scenario and method.
  The manuscript depth diagnostic uses rows with
  `method=adaptive_rollout_adp`. Field meanings and units match the
  corrected offline-study table above.
- `raw/heldout_summary.csv`: aggregate validation results. The figure
  generator reads success rate, mean penalized cost, median online time, and
  mean safe-action evaluations from this file.
- `summary.json` and `summary.md`: run configuration, graph and
  split counts, and method summaries.
- `OrbInspectLatex/data/adp_depth_sensitivity_corrected_20260905.csv`:
  compact source table used by the manuscript.
- `OrbInspectLatex/figures/adp_future/adp_depth_tradeoff_manifest.json`:
  source paths, script hash, generated-file list, and interpretive limits for
  the current depth figure.

## ROS route export

Directory:
`data/results/ros_verification_inputs_full_transform_radius080_20260812/raw/`

- `trajectory.csv`: one row per archived transfer sample; `time` is seconds,
  position (`rx`, `ry`, `rz`) is metres, velocity (`vx`, `vy`, `vz`) is m/s,
  and acceleration (`ax`, `ay`, `az`) is m/s^2 in LVLH coordinates.
- `attitude.csv`: normalized camera boresight components at each trajectory
  sample.
- `viewpoints.csv`: terminal observation positions in metres, normalized
  boresight, weighted inspectable coverage as a fraction, target counts, and a
  semicolon-separated target-identifier list.

The accompanying `manifest.json` maps every route to the corrected graph and
scenario hashes. `metrics_archived: false` means a route was exported for
possible ROS replay, not that a ROS execution metric was recorded.

## Accepted ROS execution

Directory:
`data/results/ros_rviz_full_planning_demo_corrected_validation002_radius080_20260812/raw/`

- `trajectory.csv`: mission time (s); executed LVLH position (m), velocity
  (m/s), quaternion, tracking-error norms, planned position/velocity/control,
  and normalized camera boresight.
- `control.csv`: nominal and filtered acceleration components (m/s^2), control
  magnitude (m/s^2), incremental and cumulative delta-v (m/s), and saturation
  flag.
- `coverage.csv`: mission time (s), target counts, weighted inspectable
  coverage fraction, newly credited target count, and current visible-target
  count.
- `safety.csv`: proxy-geometry center distance (m), required margin (m),
  finite-body clearance above that margin (m), safety/caution flags, nearest
  primitive, filter state/reason, and nominal/filtered acceleration (m/s^2).
- `mission_events.csv`: terminal-observation and completion events, waypoint
  identifiers, coverage fraction, position error (m), terminal speed (m/s),
  counters, decision flags, and reason strings.
- `planner.csv`: header-only by design because planning was completed offline
  and the ROS task replayed a frozen route.
- `launch.log`: retained process output for the accepted task.

`mesh_execution_audit.json` is the independent full transformed-mesh audit and
is authoritative for the continuous segment lower bound, finite-body margin,
and swept-crossing decision. The online `safety.csv` uses conservative proxy
geometry and should not be substituted for that post-run mesh audit.

## Exploratory high-coverage stress test

Directory: `data/results/high_coverage_key_targets_20260904/`

This dataset is post-selection exploratory evidence, not part of the frozen
primary comparison. Its stopping ratios are weighted over the 41
candidate-observable targets; `whole_mesh_coverage` uses all 90 sampled mesh
targets and is reported separately.

- `raw/key_targets.csv`: the six spatial-sentinel target identifiers, their
  coordinate-extreme selection criterion, LVLH coordinates in metres, and the
  number of graph nodes from which each target is observable.
- `raw/scenario_results.csv`: one row per requested coverage ratio,
  requirement variant, and test scenario. `structural_feasible` checks whether
  the union of available candidate masks can satisfy the stopping condition
  before route search. Coverage fields are fractions, `total_delta_v` is m/s,
  `graph_cost` uses the study cost unit, and selected/action/evaluation fields
  are counts.
- `summary.json` and `summary.md`: aggregate success conditional on structural
  feasibility, achieved inspectable and whole-mesh coverage, sentinel
  satisfaction, action count, and delta-v.

The sentinel set was selected using target observability across the frozen
test and distribution-shift scenario inventories. Accordingly, these rows
must not be described as an independent mandatory-target evaluation. In this
archive, the coverage-only and sentinel-constrained variants have identical
route identifiers and outcomes because every successful coverage-only route
already covers all six sentinels.
