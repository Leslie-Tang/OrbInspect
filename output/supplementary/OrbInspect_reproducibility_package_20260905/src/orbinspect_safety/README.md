# orbinspect_safety

Build type: `ament_python`.

Purpose: Safety monitor, keep-out checking, collision checking, and safety filtering package.

Phase 8 status: provides an approximate ISS-proxy keep-out model, a passive safety monitor, and a projection-based command filter. The active demo is:

```bash
ros2 launch orbinspect_bringup demo_safety_filter.launch.py record:=true
```
