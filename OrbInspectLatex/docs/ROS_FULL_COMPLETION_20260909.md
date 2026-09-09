# All-nine required-target ROS execution, 2026-09-09

The normal-speed graphical run **20260909_040344_required09_dwell60_visual** accepted all nine observations and
all nine prescribed targets. It uses the original median-effect route with a
uniform 60-s terminal settling interval after each unchanged 90-s transfer.
This is an explicitly extended execution schedule, selected after the original
810-s execution failed. The offline experiment and all Figures 1–6 are unchanged.

| Quantity | Graphical execution |
|---|---:|
| Required targets accepted | 9/9 |
| Observations accepted | 9/9 |
| Weighted background coverage | 77.2174358% |
| Unweighted inspectable coverage | 30/41 |
| Completion time | 1350.037800792 s |
| Executed safe-control integral through final event | 15.928652166 m/s |
| Scheduled reference effort, including stationary holds | 13.839641061 m/s |
| Maximum terminal position error | 0.050277841 m |
| Maximum terminal speed | 0.003829052 m/s |
| RMS position tracking error over complete recorded run | 0.905878143 m |
| Maximum position tracking error over complete recorded run | 5.668295282 m |
| Filter-active safety messages; safe-control messages | 1402; 27185 |
| Audited trajectory samples | 27188 |
| Full transformed mesh triangles | 247525 |
| Minimum finite-body clearance above required 2 m | 5.352930589 m |
| Peak safe acceleration | 0.060000000 m/s² |
| Camera image messages recorded | 17522 |
| Maximum selected camera/event receipt mismatch | 0.035501719 s |
| Maximum selected scene/event position difference | 0.003567021 m |
| Maximum selected scene/event orientation difference | 0.000000000 degrees |

All execution, full-mesh and camera alignment gates passed. The body-clearance
quantity subtracts the 0.8-m vehicle radius and required 2-m margin from the
continuous segment-distance lower bound. It concerns segments between logged
samples. The safe-control integral uses actual command header timestamps and
zero-order holds, clipped at receipt of the final event. Its definition differs
from the logger's whole-run receipt-time integral, 15.928769772 m/s.
Reference-count completion passed; maximum reference-message gap was
0.055440793000002486 s.
Message-gap diagnostics are separate from that count-based completion gate.

The camera audit retains frame counts, simulator-stamp gaps and estimated missing
nominal sensor slots. It selects original RGB messages by wall receipt time,
checks named Gazebo poses at camera simulator timestamps, and matches recorded
odometry to the executed CSV. Images are uncropped and have no brightness,
contrast, gamma or color adjustment. Rendering into the composite resamples
images for their printed size. Target credit still comes from the unchanged
frozen geometric masks gated by terminal tracking, not image-based detection.

See [the settling and search protocol](ROS_SETTLING_PROTOCOL_20260909.md) and
[the retained failed execution](ROS_EXECUTION_CHECK_20260909.md). The accelerated
probe has its own metrics and audit; none of those measurements are substituted
for this graphical run. This is one post-hoc execution adjustment, not a paired
ROS comparison, population success-rate estimate or change to the offline
11.05% result.

## Evidence and figure

The compact snapshot is `data/required_target_ros/20260909_040344_required09_dwell60_visual/`; its
`snapshot_manifest.json` hashes all included files. Original core/camera MCAPs
and named scene-pose JSONL remain in the corresponding timestamped workspace
result directories, with their hashes and metadata in the compact snapshot.
The original failed run is retained separately. Historical Figure 7 artwork and
caption are preserved under `data/historical_ros/figure7/artwork/`.

Figure 7 keeps the 170-by-74-mm compact layout, Arial family and original sizes,
observation colors, numbered badges, neutral mesh, gray dashed reference and
blue executed path. It has five views left and four right, without an invented
tenth observation. Expanded axis ranges contain the new path and preserve equal
physical scale in both projections. Source RGB arrays and trajectory coordinates
are checked before SVG/PDF/600-dpi PNG export.

## Delivery validation and camera timing diagnostics

The reviewed manuscript is 13 pages. Its LaTeX build has no overfull boxes,
undefined references or oversized floats; all 33 bibliography entries remain.
The project integrity check passes 33 local compilation inputs and 60 approved
figure files across seven groups. All 67 figure-directory files outside the
four replaced Figure 7 outputs and overall manifest retain their original hashes.
The style configuration function is identical to the original; the new Figure 7
PDF has a 7-pt minimum glyph size and passed panel-by-panel visual review.
The ROS build passed all 12 packages. Five new evidence/schedule checks passed.
The earlier 66 focused checks also passed; the complete initial colcon test
record still contains two pre-existing guidance lint failures (flake8 and pep257).
No ROS runtime source or frozen offline data, table or bibliography was changed.

The camera stream contains 17,522 image messages with strictly increasing sensor
timestamps. Two pairs share equal wall receipt timestamps, and four receipt gaps
exceed 0.2 s; the largest is 0.430546 s. An initial preparation attempt rejected
the duplicate receipts with an extra all-stream monotonicity assertion. That
failure log is retained. The final preparation keeps every message and reports
those stream diagnostics while applying the declared per-view gates unchanged:
0.2 s event/frame receipt mismatch, 0.041 s scene/frame simulator-time mismatch,
0.1 m position agreement and 0.5-degree orientation agreement. All selected
views pass; their maximum receipt mismatch is 0.035502 s, scene timestamp
mismatch is zero, position difference is 0.003567 m and orientation difference
is zero to reported numerical precision. No frame was silently dropped or
clamped. No missing nominal sensor slot was estimated from the 15-Hz simulator
stamps; this estimate is not a transport-delivery guarantee.

The reviewed PDF is
`output/pdf/OrbInspect_IEEE_TAES_ROS_full_required_completion_20260909.pdf` in the
repository workspace. Machine-readable delivery checks are in
`ROS_FULL_COMPLETION_QA_20260909.json`. The historical ten-view compact figure,
its caption and the earlier failed-execution PDF remain retained.
