# Final rosbag-complete ROS validation archive

This directory records a corrected graphical `validation_002` closed-loop
execution with the complete glTF scene hierarchy, a 0.80 m chaser bounding
radius, ROS-native HCW state propagation, Gazebo Harmonic visualization, RViz2,
the six paper CSV streams, and a Jazzy MCAP rosbag.

The independent version-2 audit passed every gate: 10/10 observations were
credited, final coverage was 81.331%, no swept mesh crossing was found, and the
minimum finite-body clearance was 5.708 m above the required 2 m margin.

This is an archival confirmation run. It does not replace the media-backed run
at `../ros_rviz_full_planning_demo_corrected_validation002_radius080_20260812/`,
which remains the source of the manuscript's Fig. 7 and annotated H.264 video.
See the repository-root `handover.md` for the evidence boundary and Windows
transfer instructions.

Verify the archive from the repository root with:

```bash
sha256sum -c data/results/20260812_174012_ros_final_validation002_radius080/SHA256SUMS.txt
```
