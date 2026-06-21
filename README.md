# OrbInspect

OrbInspect is a ROS 2 Jazzy simulation and planning framework for autonomous orbital structure inspection.

This workspace targets:

- Ubuntu 24.04.4 LTS
- ROS 2 Jazzy
- Gazebo Harmonic
- RViz2
- Python 3.12
- colcon + ament

## Phase 1 Status

Phase 1 creates the ROS 2 workspace skeleton only. The packages, configuration directories, documentation directories, scripts directory, and paper-result output layout are present. Algorithms, nodes, message definitions, launch behavior, and Gazebo/RViz assets are deferred to later phases.

## Packages

- `orbinspect_interfaces`
- `orbinspect_description`
- `orbinspect_gazebo`
- `orbinspect_dynamics`
- `orbinspect_control`
- `orbinspect_safety`
- `orbinspect_guidance`
- `orbinspect_perception`
- `orbinspect_mission`
- `orbinspect_eval`
- `orbinspect_bringup`
- `orbinspect_utils`

## Build

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 pkg list | grep orbinspect
```

## Paper Output Layout

Experiment outputs should be saved under `data/results/<timestamp>/` in later phases:

```text
config_snapshot/
raw/
rosbag/
figures/
videos/
summary.json
summary.md
```
