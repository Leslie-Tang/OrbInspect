# orbinspect_bringup

Build type: `ament_python`.

Purpose: Top-level launch and configuration package for OrbInspect demos,
frozen-route ROS verification, and paper experiments.

## Corrected visual verification

After building and sourcing the workspace, launch a graphical closed-loop
verification run with:

```bash
ros2 launch orbinspect_bringup demo_corrected_rviz.launch.py
```

This zero-required-argument wrapper selects the corrected `validation_002`
route, closed-loop ROS execution, RViz2, Gazebo Harmonic, and the live chaser
camera. It runs the complete 900 s mission at 5x mission time after a 10 s
visual startup delay and creates a collision-safe result-directory name.

The launch starts the frozen planned-route publisher, verification evaluator,
controller, safety filter, ROS-native HCW dynamics, logger, Gazebo Harmonic,
the Gazebo-to-ROS chaser-camera bridge, and RViz2. The RViz configuration shows
the `/chaser/camera/image` topic. Gazebo is visual-only; it is not the state
source of truth.

The relevant visual arguments are:

- `headless:=false` enables Gazebo Harmonic, the camera bridge, and RViz2.
- `gz_partition:=<name>` isolates the Gazebo transport session.
- `visual_startup_delay:=<seconds>` lets the visual windows and recorders start
  before mission nodes; it requires `headless:=false`.
- `allow_accelerated_visualization:=true` explicitly permits a graphical run
  with `time_scale>1`. This is intended for demo capture, not quantitative
  evidence generation.

Override wrapper defaults on the same command line when needed, for example:

```bash
ros2 launch orbinspect_bringup demo_corrected_rviz.launch.py time_scale:=1.0 visual_startup_delay:=20.0
```

The accepted corrected full-task capture used `validation_002`, rollout ADP,
5x mission time, a 30 s visual startup delay, and a 0.80 m chaser bounding
radius. Its final video and provenance manifest are under
`data/results/ros_rviz_full_planning_demo_corrected_validation002_radius080_20260812/videos/`.
