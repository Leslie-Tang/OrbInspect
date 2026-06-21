# AGENTS.md

## Project Name

OrbInspect

## Project Goal

This repository implements OrbInspect, a ROS 2-based simulation and planning framework for autonomous orbital structure inspection.

The target system is:

- Ubuntu 24.04.4 LTS
- ROS 2 Jazzy
- Gazebo Harmonic
- RViz2
- Python 3.12
- colcon + ament
- ROS-native HCW dynamics first
- Optional Basilisk backend later

## Hard Constraints

1. Do not introduce ROS 1.
2. Do not introduce ROS 2 Humble.
3. Do not introduce Gazebo Classic.
4. Do not use catkin.
5. Do not make Basilisk required for the main demo.
6. Do not use Gazebo physics as the source of truth during early phases.
7. The ROS dynamics node is the source of truth for spacecraft state.
8. Keep interfaces stable once created.
9. Use YAML files for parameters.
10. Use `colcon build --symlink-install` after major changes.
11. Run relevant Python tests after modifying mathematical modules.
12. Do not hard-code absolute paths except under the workspace root.
13. Save paper experiment data under `data/results/<timestamp>/`.
14. Do not implement advanced algorithms before the baseline demo works.
15. Do not rewrite the entire repository unless explicitly requested.

## Required Build Command

```bash
cd ~/orbinspect_ros2
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
```

## Required Test Commands

For pure Python modules:

```bash
pytest
```

For ROS package build validation:

```bash
colcon build --symlink-install
```

For package discovery:

```bash
ros2 pkg list | grep orbinspect
```

## Implementation Style

- Prefer small, verifiable changes.
- Implement one phase at a time.
- Add docstrings to mathematical functions.
- Use Python type hints where reasonable.
- Keep launch files simple and reproducible.
- Add README notes for every package.
- Every demo must have a clear launch command.
- Every experiment must produce logs or explain why logging is not yet implemented.

## Paper-Grade Output Requirement

The final system must support:

```text
data/results/<timestamp>/
├── config_snapshot/
├── raw/
├── rosbag/
├── figures/
├── videos/
├── summary.json
└── summary.md
```

The key CSV files are:

```text
trajectory.csv
control.csv
coverage.csv
safety.csv
planner.csv
mission_events.csv
```

## Development Order

Follow this order strictly:

1. Workspace skeleton.
2. ROS-only HCW dynamics.
3. RViz visualization.
4. CSV trajectory/control logger.
5. Gazebo ISS proxy visualization.
6. Inspection targets and coverage.
7. Fixed waypoint inspection.
8. Safety monitor and safety filter.
9. Greedy NBV planner.
10. Paper experiment launch.
11. Monte Carlo comparison.
12. Optional Basilisk backend.
13. Advanced safe planner.
