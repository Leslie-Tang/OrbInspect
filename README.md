# OrbInspect

OrbInspect is a ROS 2 Jazzy simulation, planning, and evaluation framework for autonomous orbital structure inspection. The repository focuses on a ROS-native baseline first: HCW/CW relative dynamics provide the source of truth for spacecraft state, while RViz2 and Gazebo Harmonic are used for visualization and experiment playback.

The project is organized as a research workspace for safety-constrained external inspection of large orbital structures. It includes baseline dynamics, control, safety monitoring/filtering, inspection target coverage, waypoint and greedy next-best-view planning, experiment logging, Monte Carlo comparison utilities, and optional Basilisk integration scaffolding.

## Target Platform

- Ubuntu 24.04.4 LTS
- ROS 2 Jazzy
- Gazebo Harmonic
- RViz2
- Python 3.12
- colcon + ament

The project intentionally avoids ROS 1, ROS 2 Humble, Gazebo Classic, and catkin.

## Current Status

The workspace has progressed beyond the initial skeleton through the baseline research demo stack:

- ROS-native HCW dynamics node
- RViz2 research visualization
- CSV trajectory, control, safety, coverage, planner, and mission-event logging
- Gazebo Harmonic ISS proxy and visual model support
- Inspection target generation and coverage tracking
- Fixed waypoint inspection demo
- Safety monitor and projection-based safety filter
- Greedy next-best-view inspection planner
- Paper experiment launch workflow
- Deterministic Monte Carlo comparison utility
- Optional Basilisk backend adapter and availability check
- Placeholder scaffold for future advanced safe planners

Advanced MPC, CBF-QP, HJI, ADP, or other research solvers are not implemented yet. The active baseline remains the ROS-native HCW workflow.

## Repository Layout

```text
src/
  orbinspect_interfaces/   Custom inspection and coverage messages
  orbinspect_description/  RViz config and Gazebo model assets
  orbinspect_dynamics/     HCW dynamics node and optional Basilisk adapter
  orbinspect_control/      Baseline LQR-style controller and reference publisher
  orbinspect_safety/       Keepout model, safety monitor, and command filter
  orbinspect_guidance/     Waypoints, offline trajectories, NBV planner, offline coverage planner
  orbinspect_perception/   Inspection targets, visibility checks, and coverage tracking
  orbinspect_mission/      Mission state machine and fixed-waypoint manager
  orbinspect_eval/         CSV logger, metrics, figures, rosbag helpers, Monte Carlo runner
  orbinspect_gazebo/       Gazebo Harmonic launches, bridge config, visual helpers
  orbinspect_bringup/      Top-level demos and experiment launch files
  orbinspect_utils/        Shared utility package placeholder
data/results/              Experiment outputs
docs/                      Research and implementation notes
OrbInspectLatex/           Paper draft material
```

## Build

From the workspace root:

```bash
cd /home/rugang/robotics/projects/OrbInspect
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 pkg list | grep orbinspect
```

If your local workspace is symlinked or moved, use the new workspace path in place of `/home/rugang/robotics/projects/OrbInspect`.

## Tests

Run all Python tests:

```bash
pytest
```

Run selected package tests through colcon:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
colcon test --packages-select orbinspect_dynamics orbinspect_control orbinspect_safety orbinspect_guidance orbinspect_perception orbinspect_eval orbinspect_bringup --event-handlers console_direct+
colcon test-result --verbose
```

After modifying mathematical modules, run the relevant package tests. For example:

```bash
pytest src/orbinspect_dynamics/test
pytest src/orbinspect_control/test
pytest src/orbinspect_safety/test
pytest src/orbinspect_guidance/test
```

## Main Demos

Always build and source the workspace before launching:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
```

RViz visualization:

```bash
ros2 launch orbinspect_bringup demo_rviz.launch.py record:=false
```

Coverage demo:

```bash
ros2 launch orbinspect_bringup demo_coverage.launch.py record:=true
```

Fixed waypoint inspection:

```bash
ros2 launch orbinspect_bringup demo_fixed_waypoints.launch.py record:=true
```

Safety filter demo:

```bash
ros2 launch orbinspect_bringup demo_safety_filter.launch.py record:=true
```

Greedy next-best-view inspection:

```bash
ros2 launch orbinspect_bringup demo_greedy_inspection.launch.py record:=true
```

Gazebo ISS proxy visualization:

```bash
ros2 launch orbinspect_bringup demo_gazebo.launch.py
```

Real ISS visual trajectory demo:

```bash
ros2 launch orbinspect_bringup demo_real_iss_trajectory.launch.py
```

Optional Basilisk backend check and launch:

```bash
ros2 run orbinspect_dynamics validate_basilisk_backend
ros2 launch orbinspect_bringup demo_basilisk_backend.launch.py dynamics_backend:=hcw
ros2 launch orbinspect_bringup demo_basilisk_backend.launch.py dynamics_backend:=basilisk
```

The Basilisk backend is optional. If Basilisk is not installed, the adapter reports that cleanly and the default HCW backend remains available.

## Paper Experiment

Run the paper-style experiment launcher:

```bash
ros2 launch orbinspect_bringup paper_experiment.launch.py \
  scenario:=full_station \
  method:=greedy_nbv_safety_filter \
  record:=true \
  save_figures:=true \
  run_id:=exp001 \
  dynamics_backend:=hcw
```

Expected output:

```text
data/results/<timestamp-or-run-id>/
  config_snapshot/
  raw/
  rosbag/
  figures/
  videos/
  summary.json
  summary.md
```

Key CSV files produced by the logging and experiment workflow include:

```text
trajectory.csv
control.csv
coverage.csv
safety.csv
planner.csv
mission_events.csv
```

## Monte Carlo Comparison

The Monte Carlo runner provides a fast deterministic comparison utility for paper-table and figure scaffolding:

```bash
ros2 run orbinspect_eval monte_carlo_runner \
  --scenario full_station \
  --methods fixed_waypoints random_safe greedy_nbv greedy_nbv_safety_filter \
  --num-runs 2 \
  --seed 11
```

It writes a result directory under `data/results/` with a summary table and comparison figure. The current runner simulates deterministic metrics rather than launching a full ROS experiment for every trial.

## Offline Coverage Planner

The offline coverage planner can generate paper-style artifacts without running the full ROS launch stack:

```bash
ros2 run orbinspect_guidance offline_coverage_planner \
  --config src/orbinspect_guidance/config/offline_coverage_planner.yaml
```

The planner loads YAML configuration, generates viewpoints and selected inspection poses, and writes raw CSV, figures, and summary files to the configured result directory.

## Core ROS Nodes

Important executable entry points include:

- `orbinspect_dynamics`: `dynamics_node`, `basilisk_adapter_node`, `validate_basilisk_backend`
- `orbinspect_control`: `controller_node`, `reference_publisher_node`
- `orbinspect_safety`: `safety_monitor_node`, `safety_filter_node`
- `orbinspect_perception`: `coverage_node`, `target_marker_node`
- `orbinspect_guidance`: `inspection_planner_node`, `offline_trajectory_node`, `offline_coverage_planner`, `advanced_safe_planner_node`
- `orbinspect_mission`: `mission_manager_node`
- `orbinspect_eval`: `logger_node`, `monte_carlo_runner`
- `orbinspect_gazebo`: `chaser_pose_follower`, `follow_camera_pose_node`, `image_video_recorder`

## Design Notes

- The ROS dynamics node is the source of truth for spacecraft state.
- Gazebo physics is not used as the truth model in the baseline workflow.
- YAML files are used for package parameters and experiment configuration.
- Interfaces should remain stable once created.
- Basilisk is optional and must not be required for the main demo.
- Paper experiment data belongs under `data/results/<timestamp>/`.

## Git Hygiene

Do not commit generated ROS build artifacts:

```text
build/
install/
log/
```

Large rosbag files, videos, and raw experiment data should generally stay out of normal Git history unless they are intentionally curated artifacts. Prefer GitHub Releases, external storage, or Git LFS for large binary outputs.
