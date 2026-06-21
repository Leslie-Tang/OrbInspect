# Advanced Safe Planner Placeholder

Phase 13 adds a lightweight scaffold for future MPC, CBF-QP, HJI, or ADP-based safe planners.

The active research baseline remains:

```bash
ros2 launch orbinspect_bringup demo_greedy_inspection.launch.py record:=true
```

The placeholder node publishes `/advanced_planner/status` and intentionally does not alter `/chaser/reference` or `/chaser/safe_control_command`.

Future work should plug into the stable topics:

- Subscribe: `/chaser/odom`, `/inspection/coverage_map`, `/chaser/safety_status`
- Publish: `/chaser/reference`, `/inspection/planned_path`, `/planner/status`, `/planner/event`

No advanced optimizer dependency is required by this phase.
