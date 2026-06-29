# SOOA Revision Report

## Code Map

- planner entry point: `src/orbinspect_guidance/orbinspect_guidance/offline_coverage_planner.py`
- visibility code: `OfflineCoveragePlanner.compute_visibility_matrix()` and `_target_visible()`
- HCW transfer code: `OfflineCoveragePlanner.estimate_transfer()`
- experiment runner: `src/orbinspect_guidance/orbinspect_guidance/offline_planning_experiment.py`
- figure scripts: offline planner and experiment plotting methods in the same guidance modules
- ROS/replay scripts: `src/orbinspect_guidance/orbinspect_guidance/planned_trajectory_replay_node.py`

## Code Modifications

- Added `SafeObservableOrbitalArc` as the exported SOOA schema for selected inspection actions.
- Added SOOA aliases to planner summaries: `selected_sooa_count`, `selected_sooa_ids`, `rho_min`, `passive_safe`, `input_feasible`, `clearance_feasible`, and `trajectory_feasible`.
- Added `raw/selected_sooas.csv` for both the standalone offline planner and the comparison experiment.
- Kept legacy outputs such as `selected_viewpoints.csv`, `viewpoints.csv`, `planner.csv`, `trajectory.csv`, and `attitude.csv` intact for backward compatibility.
- Updated figure labels from selected viewpoints / CW-feasible trajectory to SOOA terminal poses / SOOA HCW trajectory where the plotted object is the selected inspection action.

## Simulation Modifications

- No ROS topic names, replay input filenames, launch files, or Gazebo pose-flow code were changed.
- The simulation-to-ROS data flow remains:
  offline planner CSV outputs -> replay node -> ROS state/attitude/path/frustum markers -> RViz/Gazebo visual replay.
- Gazebo remains a visual replay layer; HCW planner logs remain the quantitative source for trajectory, coverage, and safety metrics.

## New SOOA Data Schema

Each selected SOOA records:

- `arc_id`
- `seed_view_id`
- `t_samples`
- `x_samples`
- `u_samples`
- `q_samples`
- `visible_target_ids`
- `delta_v`
- `min_clearance`
- `peak_input`
- `max_speed`
- `terminal_error`
- `passive_margin`
- `passive_safe`
- `feasible`
- `rejection_reason`

## Passive-Safety Audit Status

- Implemented as a lightweight HCW drift audit over selected arc samples.
- Default horizon: `passive_safety_horizon: 300.0`.
- Default passive distance: `passive_safety_distance: 0.0`, meaning the planner uses the configured keep-out `safety_margin`.
- The audit is reported in outputs and summaries but is not fed back into selection or ROS replay, preserving existing numerical planning behavior and replay flow.

## Benchmark Rerun Status

- Full configured offline comparison rerun completed with run id `data/results/sooa_publication_check`.
- The rerun produced `raw/selected_sooas.csv`, SOOA summary aliases, and passive-drift audit metrics for all compared methods.
- Core proposed-tour trajectory metrics match the manuscript result: 98.33% coverage, 21 selected SOOAs, 21.5921 m/s cumulative Delta-v, and 9.9107 m minimum clearance.
- The proposed sequence passed the passive-drift audit with `rho_min = 1.5091 m` over a 300 s horizon.

## Changed Numerical Results

- No intended changes to trajectory selection, transfer generation, ROS replay, or existing CSV consumers.
- Wall-clock planning times were refreshed from the rerun and may differ from earlier cached manuscript values.
- Passive audit metrics are additional reported quantities.

## Unchanged Numerical Results

- HCW transfer generation.
- Visibility matrix construction.
- Candidate selection scoring.
- Baseline method scoring.
- ROS/RViz/Gazebo replay input flow.

## Tests/Sanity Checks

- `python3 -m py_compile src/orbinspect_guidance/orbinspect_guidance/offline_coverage_planner.py src/orbinspect_guidance/orbinspect_guidance/offline_planning_experiment.py src/orbinspect_guidance/test/test_offline_coverage_planner.py src/orbinspect_guidance/test/test_offline_planning_experiment.py`
- Standalone planner smoke run: passed and produced `raw/selected_sooas.csv`.
- Comparison experiment smoke run: passed and produced `raw/selected_sooas.csv`.
- Full configured offline comparison run: passed and produced `data/results/sooa_publication_check`.
- `pytest` was not available in this environment (`No module named pytest`), so the full pytest suite was not run here.
- `colcon` and `ros2` were not available in this macOS environment, so ROS package discovery/build validation was not run here.

## Known Code Limitations

- SOOA visibility currently uses the existing stabilized terminal camera-pose visibility model. The exported SOOA is therefore a transfer-to-stabilized-dwell inspection action, not a newly introduced along-arc visibility integrator.
- Passive safety is audited for selected arcs and reported; it does not yet reject candidate arcs during planning.
- Legacy `viewpoint` terminology remains in filenames and compatibility fields to avoid breaking ROS replay and existing analysis scripts.
