# Repository-dependent paper tools

These working copies were moved out of `OrbInspectLatex/scripts/` to keep the
manuscript portable. This folder has the same depth below the repository root,
so the experiment runners' root discovery is unchanged. Original script bytes
are retained in `OrbInspectLatex/archive/preorganization_20260908/scripts/`.

None of these tools is needed to compile or share the LaTeX paper. Use
`make -C OrbInspectLatex package` for the current standalone source ZIP.

## Current workflows

- Required-target ROS evidence: after the existing full-mesh audit, run
  `python3 tools/paper/audit_required_target_ros.py <execution-directory>` in
  the sourced Jazzy environment. It checks both event topics against the frozen
  per-view target IDs, retains rejected observations, and integrates stamped
  safe-control commands to the final verification event. A failed mission
  produces an audit file and exits with status 1; this is not an accepted run.
  `python3 -m pytest -q tools/paper/tests/test_required_target_ros_audit.py`
  checks rejection/duplicate handling and the timestamped integration boundary.
- Experiment execution: `run_required_target_study.py`,
  `run_required_target_confirmation.py`, `run_required_target_depth_diagnostic.py`.
  These still require the full repository, frozen inputs and recorded environment.
- Tables and results: `write_required_target_tables.py`,
  `generate_required_target_figures.py`, `generate_required_target_details.py`,
  `generate_required_target_depth_figures.py`. Output paths now match the
  numbered figure folders and `OrbInspectLatex/tables/`.
- Current Figure 3 typography: `OrbInspectLatex/scripts/generate_depth_figure.py`
  draws the three panels at final column size with approximately 7-point text.
  It verifies the included frozen diagnostic CSV and all plotted statistics,
  stages editable SVG/PDF/PNG exports, and does not rewrite tables or evidence.
  The legacy depth figure/table generator does not preserve this typography.
- Current Figures 4 and 5: use the optional standalone
  `OrbInspectLatex/scripts/generate_result_figures.py` from the repository root
  with the review Python environment. It exports independent panels and the
  Figure 5 legend for LaTeX's single-column 2-by-2 assembly, verifies frozen statistics, and does not
  rerun experiments. The older general generator above creates the historical
  separate-panel files, not the current final-size panel exports.
- Current Figure 3--6 palette: use the optional standalone
  `OrbInspectLatex/scripts/recolor_result_figures.py` to stage the shared
  teal/purple colors while verifying unchanged geometry and data. It preserves
  finalized Figure 3/6 vector paths and calls the current Figure 4/5 generator.
  See `OrbInspectLatex/docs/FIGURE_PALETTE_20260908.md`. Historical generators
  retain their original palettes; do not run them over the approved artwork.
- Current Figure 2 development: `compact_figure2_vertical.py` imports the
  preceding layout and checked graph helpers. Its historical comparison inputs
  remain under the repository's `output/`. For ordinary edits, use the current
  self-contained draw.io file in `OrbInspectLatex/figures/fig02_rollout_example/`.
- Current Figure 1 development: `romanize_figure1_panels.py` and its earlier
  refinement chain use historical input packages under `output/`. The current
  draw.io source and embedded imagery are in `OrbInspectLatex/figures/fig01_framework/`.
- Current Figure 7: `OrbInspectLatex/scripts/generate_ros_camera_figure.py`
  uses the included frozen camera/trajectory snapshot and stages a compact
  double-column SVG/PDF/PNG. The one-time `prepare_compact_ros_camera_figure.py`
  prepared that snapshot from verified archived evidence and the approved
  composite PDF, retaining the exact embedded camera pixels. Do not rerun this
  preparation over the current snapshot or archive.
- Historical ROS camera figure/video: `generate_ros_key_camera_views_figure.py`
  and `compose_rviz_planning_demo_video.py`; full archived recordings are required.
  The former produces the old single-column layout and writes evidence outputs;
  do not run it over the current Figure 7.
- Native diagram QA: `verify_drawio_export.cjs`; requires Node, Playwright,
  Chrome and access to the diagrams.net embed service.

Run the depth-one-to-six figure/table generator after the general detail/table
generators, whose earlier three-depth behavior is retained. Work on a copied
result bundle for reruns; do not overwrite frozen evidence. New experiments
still belong under `data/results/<timestamp>/`.

The figure integrity manifest is a snapshot, not an automatic approval mechanism.
After an intentional regeneration, visually review the changes and update
`OrbInspectLatex/figures/manifest.json`; `make check` will otherwise flag them.

## Historical tools

Other figure-option, color-test, initial-framework, old-study and packaging
scripts are retained as historical workflows, not current entry points. Their
original input/output layouts and notes are preserved in the archive. In
particular, `package_required_target_revision.py` describes an older figure
layout and root-level PDF; use the current Makefile's `package` target instead.
Do not run a historical generator over the active manuscript without reviewing
its inputs and destination paths.

## Tests

From the repository root, with the existing review environment and repository
Python packages available:

```sh
pytest tools/paper/tests/test_figure2_example.py test/test_required_target_depth_summary.py src/orbinspect_guidance/test/test_required_target_study.py
```

The folder organization changes paths and output routing only. No dynamics,
planner mathematics, experiment configuration or recorded results changed.

## Required-target completion and camera evidence

- `screen_required_target_routes.py` runs a synchronous diagnostic with the
  production HCW/LQR/filter functions and the unchanged ROS verification YAML.
  It is not ROS execution evidence. The complete search inventory is retained.
- `add_ros_terminal_dwell.py SOURCE DESTINATION` derives an execution-only
  schedule using `config/required_target_settling.yaml`. It preserves every
  archived transfer sample and target identity, appends stationary HCW holds,
  and evaluates observations after the holds. The input manifest distinguishes
  archived transfer metrics from the extended schedule; existing destinations
  are rejected.
- `record_gazebo_pose.py OUTPUT.jsonl` records the named Gazebo chaser pose with
  simulator stamps and wall receipt times. Set the same `GZ_PARTITION` as the
  graphical launch. Stop it cleanly after the mission.
- `audit_required_target_ros.py RUN` reconstructs target unions from both event
  topics and integrates stamped safe-control commands. Its receipt-based
  control integral requires an unaccelerated wall-clock run. Run the independent
  `ros_evidence_audit` first. Per-action intervals come from the actual exported
  observation times, including any declared settling periods.
- `prepare_required_target_camera_snapshot.py RUN CAPTURE OUTPUT` selects
  uncropped camera messages within 0.2 s of accepted observations. It requires
  matching event streams, checks named Gazebo pose alignment, matches recorded
  odometry to the executed CSV, and retains hashes, timing diagnostics and
  portable figure arrays. Failed camera or execution checks prevent output.
- `OrbInspectLatex/scripts/generate_ros_camera_figure.py --snapshot-dir SNAPSHOT
  --output-dir OUTPUT [--font-dir ARIAL_DIRECTORY]` supports nine or ten views
  in the approved compact style. It verifies source pixels and coordinates,
  label bounds, and equal physical scaling between both trajectory projections.
  The optional font directory supplies the same Arial family on hosts where it
  is not installed; it does not change global font settings.

The execution adaptation is described in
`OrbInspectLatex/docs/ROS_SETTLING_PROTOCOL_20260909.md`. It does not change the
frozen planning study or establish a paired ROS maneuver saving.


## Supplemental twelve-observation hybrid execution

`prepare_higher_coverage_ros_inputs.py` freezes the selected 95%-goal hybrid ADP
plan from the unchanged parent scenario. `refine_ros_viewpoints.py`, configured
by `config/hybrid12_viewpoint_refinements.yaml`, materializes the two declared
position/aim refinements with recomputed HCW transfers and visibility, then adds
the uniform 60-s settling periods. Both create inputs, not execution evidence.
`audit_required_target_ros.py` checks required and hybrid goals, including the
background threshold when every required target has already been accepted.
`prepare_required_target_camera_snapshot.py` retains empty startup scenes as
diagnostics and rejects duplicate named chaser poses; selected-frame timing and
pose gates are unchanged. The current source/inputs, search inventories, retained
failure and audited recordings are documented in
`OrbInspectLatex/docs/ROS_TWELVE_OBSERVATIONS_20260909.md`.
