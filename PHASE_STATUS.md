# PHASE_STATUS.md

## Phase 9: Greedy Next-Best-View Planner

- Status: Complete
- Files changed:
  - `src/orbinspect_guidance/orbinspect_guidance/waypoint_generator.py`
  - `src/orbinspect_guidance/orbinspect_guidance/greedy_nbv_planner.py`
  - `src/orbinspect_guidance/orbinspect_guidance/inspection_planner_node.py`
  - `src/orbinspect_guidance/config/planner.yaml`
  - `src/orbinspect_guidance/setup.py`
  - `src/orbinspect_guidance/test/test_greedy_nbv_planner.py`
  - `src/orbinspect_guidance/test/test_pep257.py`
  - `src/orbinspect_bringup/launch/demo_greedy_inspection.launch.py`
  - `src/orbinspect_eval/orbinspect_eval/logger_node.py`
- Commands run:
  - `colcon build --symlink-install`
  - `pytest src/orbinspect_guidance/test`
  - `pytest src/orbinspect_eval/test`
  - `pytest src/orbinspect_bringup/test`
  - `ros2 launch orbinspect_bringup demo_greedy_inspection.launch.py record:=true`
  - `colcon test --packages-select orbinspect_guidance orbinspect_eval orbinspect_bringup --event-handlers console_direct+`
  - `colcon test-result --verbose`
- Build result: Passed, 12 packages built.
- Test result: Passed, 67 tests, 0 errors, 0 failures, 10 skipped.
- Launch/smoke result: Passed headless smoke. Planner generated 178 safe candidates, selected an NBV waypoint, wrote `planner.csv`, and coverage began increasing.
- Known limitations: Short smoke test does not prove 80 percent final coverage; it validates planner startup, waypoint selection, controller handoff, and logging.
- Next phase: Phase 10 paper experiment launch.

## Phase 10: Paper Experiment Launch

- Status: Complete
- Files changed:
  - `src/orbinspect_bringup/launch/paper_experiment.launch.py`
  - `src/orbinspect_eval/orbinspect_eval/experiment_index.py`
  - `src/orbinspect_eval/orbinspect_eval/report_generator.py`
  - `src/orbinspect_eval/orbinspect_eval/rosbag_manager.py`
  - `src/orbinspect_eval/orbinspect_eval/logger_node.py`
- Commands run:
  - `colcon build --symlink-install`
  - `pytest src/orbinspect_eval/test`
  - `pytest src/orbinspect_bringup/test`
  - `ros2 launch orbinspect_bringup paper_experiment.launch.py scenario:=full_station method:=greedy_nbv_safety_filter record:=true save_figures:=true run_id:=phase10_smoke dynamics_backend:=hcw`
- Build result: Passed, 12 packages built.
- Test result: Eval and bringup tests passed.
- Launch/smoke result: Passed headless smoke. Created `data/results/phase10_smoke/` with `config_snapshot/`, `raw/`, `rosbag/`, `figures/`, `videos/`, `summary.json`, and `summary.md`.
- Known limitations: Smoke run was timeout-limited; rosbag wrote data successfully, but long-duration experiment completion was not exercised.
- Next phase: Phase 11 Monte Carlo comparison.

## Phase 11: Monte Carlo Comparison

- Status: Complete
- Files changed:
  - `src/orbinspect_eval/orbinspect_eval/monte_carlo_runner.py`
  - `src/orbinspect_eval/orbinspect_eval/compare_methods.py`
  - `src/orbinspect_eval/setup.py`
  - `src/orbinspect_eval/test/test_monte_carlo_runner.py`
- Commands run:
  - `pytest src/orbinspect_eval/test`
  - `colcon build --symlink-install`
  - `ros2 run orbinspect_eval monte_carlo_runner --scenario full_station --methods fixed_waypoints random_safe greedy_nbv greedy_nbv_safety_filter --num-runs 2 --seed 11`
- Build result: Passed, 12 packages built.
- Test result: Eval tests passed.
- Launch/smoke result: CLI smoke passed and generated `data/results/monte_carlo_20260621_155201/summary_table.csv` plus `figures/method_comparison.png`.
- Known limitations: Runner uses deterministic metric simulation rather than launching full ROS experiments for each run; this keeps Phase 11 fast and reproducible while preserving output structure.
- Next phase: Phase 12 optional Basilisk backend.

## Phase 12: Optional Basilisk Backend

- Status: Complete
- Files changed:
  - `src/orbinspect_dynamics/orbinspect_dynamics/basilisk_adapter.py`
  - `src/orbinspect_dynamics/orbinspect_dynamics/validate_basilisk_backend.py`
  - `src/orbinspect_dynamics/setup.py`
  - `src/orbinspect_dynamics/test/test_basilisk_adapter.py`
  - `src/orbinspect_bringup/launch/demo_basilisk_backend.launch.py`
  - `src/orbinspect_bringup/test/test_pep257.py`
- Commands run:
  - `pytest src/orbinspect_dynamics/test`
  - `pytest src/orbinspect_bringup/test`
  - `colcon build --symlink-install`
  - `ros2 run orbinspect_dynamics validate_basilisk_backend`
  - `ros2 launch orbinspect_bringup demo_basilisk_backend.launch.py dynamics_backend:=hcw`
  - `ros2 launch orbinspect_bringup demo_basilisk_backend.launch.py dynamics_backend:=basilisk`
- Build result: Passed, 12 packages built.
- Test result: Dynamics and bringup tests passed.
- Launch/smoke result: HCW backend launched and stopped cleanly. Basilisk backend reported unavailable cleanly because Basilisk is not installed.
- Known limitations: Basilisk propagation itself is deferred until the optional Basilisk dependency is installed; default HCW workflow is unchanged.
- Next phase: Phase 13 advanced safe planner placeholder.

## Phase 13: Safety-Shielded Graph Approximate Policy Iteration

- Status: Complete for the ROS-independent planner core and offline paper
  workflow; ROS package rebuild remains to be repeated on the target Jazzy
  host.
- Files changed:
  - `src/orbinspect_guidance/orbinspect_guidance/advanced_safe_planner.py`
  - `src/orbinspect_guidance/orbinspect_guidance/advanced_safe_planner_node.py`
  - `src/orbinspect_guidance/orbinspect_guidance/offline_planning_experiment.py`
  - `src/orbinspect_guidance/orbinspect_guidance/offline_adp_study.py`
  - `src/orbinspect_guidance/orbinspect_guidance/offline_planning_plots.py`
  - `src/orbinspect_guidance/config/advanced_safe_planner.yaml`
  - `src/orbinspect_guidance/config/offline_planning_experiment.yaml`
  - `src/orbinspect_guidance/setup.py`
  - `src/orbinspect_guidance/test/test_advanced_safe_planner.py`
  - `src/orbinspect_guidance/test/test_offline_planning_experiment.py`
  - `src/orbinspect_guidance/test/test_offline_adp_study.py`
  - `docs/advanced_safe_planner.md`
  - `docs/safe_graph_adp_plan.md`
- Commands run:
  - focused mathematical, experiment, study, and plotting tests;
  - `python3 -m py_compile` for the four modified planner/study modules;
  - `python3 -m orbinspect_guidance.offline_adp_study --run-id
    adp_paper_study_20260731_final`;
  - `python3 -m orbinspect_guidance.offline_planning_plots --result-dir
    data/results/adp_paper_study_20260731_final`.
  - `python3 -m orbinspect_guidance.offline_adp_study --run-id
    adp_component_ablation_20260801 --families components`;
  - standalone component-ablation plotting and visual inspection.
- Build result: Not rerun on the current macOS host because ROS 2 Jazzy and
  `colcon` are unavailable. The previous 12-package Jazzy build predates this
  algorithm change.
- Test result: Passed, 22 focused tests after adding component-isolation,
  invalid-configuration, study-family, and plotting checks.
- Experiment result: Completed all 17 planned cases in 1776.38 s. The primary
  returned policy achieved 98.33% coverage with 18 actions and 19.47 m/s
  cumulative delta-v, versus 21 actions and 21.59 m/s for the safe incumbent.
  Nine reduced graphs had zero exact Bellman cost gap.
- Ablation result: Completed seven cold-cache variants in 1454.83 s. Local
  search plus safeguard reproduced the complete method's 18-action,
  19.47 m/s route in 52.81 s; the complete method required 339.92 s.
  Critic-only planning required 26 actions and 42.86 m/s, so the primary
  result does not demonstrate ADP superiority.
- Known limitations: The learned critic is not the source of the primary
  improvement, critic training is not monotonic on the truncated compute
  graph, planning is offline, and safety remains conditional on deterministic
  sampled HCW and passive-drift audits.
- Next phase: Jazzy build/replay validation, cached or batched edge-audit
  acceleration, and higher-fidelity uncertainty-aware motion primitives.
