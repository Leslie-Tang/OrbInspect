# RViz full planning demo

This directory contains the complete `validation_002` rollout-ADP planned task at 5x mission time. The main view is the recorded RViz2 window; the inset is the live Gazebo chaser-camera topic. The task credited all 10 views, reached 81.33% coverage, and passed every post-run full-mesh finite-body execution-audit gate with 5.69 m minimum safety clearance. Gazebo remains visual-only; the ROS HCW dynamics node is the state source of truth.

Regenerate the video, milestone preview, and provenance manifest from the retained raw captures with:

```bash
python3 OrbInspectLatex/scripts/compose_rviz_planning_demo_video.py --run-dir data/results/ros_rviz_full_planning_demo_corrected_validation002_radius080_20260812
```
