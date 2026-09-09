# OrbInspect Run Summary

- Trajectory samples: 16391
- Control samples: 16391
- Coverage samples: 9
- Mission events: 10
- Safety samples: 16391
- Planner samples: 0
- Cumulative delta-v: 15.431224 m/s
- Mean position tracking error: 0.481070 m
- Max position tracking error: 5.671294 m
- Final coverage ratio: 0.659162
- Verification success: False
- Verification reason: terminal_tracking_or_coverage_gate_failed

## Full-mesh execution audit

- Audit passed: False
- Vehicle bounding radius: 0.800000 m
- Swept mesh crossings: 0
- Minimum finite-body clearance above the required margin: 5.352142 m

## Required-target evidence accounting

This is a retained unsuccessful closed-loop attempt, not a successful replay or camera validation. Both recorded event topics agree. Observations 2 and 8 were rejected; required IDs mesh_00007 and mesh_00079 remain missing. Accepted required completion is 7/9 and weighted background coverage is 65.916233%.

The safe-command zero-order-hold integral through the final event is 15.319716 m/s. The logger's 15.431224 m/s covers the whole 819.6-second recording, including the post-mission buffer, and uses receipt-time integration. These have different endpoints and integration conventions. Neither supports a ROS planner-saving claim for this failed mission.

The six required CSV streams are present. planner.csv is header-only because the sequencer executes a frozen offline route; there was no online replanning. No video or camera capture was made. The final-event receipt-to-mission-epoch spread is 0.263 ms, maximum safe-command stamp gap is 51.969 ms, and the reference-publisher maximum gap is 51.348 ms. These are observed diagnostics, not a real-time guarantee.

The full-mesh audit passes its geometric and acceleration checks but fails overall because terminal verification is false. The ROS processes exited cleanly; the evaluator emitted a shutdown coroutine warning, retained in launch.log.
