# Twelve-observation higher-coverage ROS execution, 2026-09-09

The supplemental normal-speed graphical execution **20260909_093200_hybrid12_visual**
accepted all 12 observations, all nine required targets and **95.8577156%** weighted
background coverage. The prior nine-view run reached 77.2174358% with the same
required IDs and weights. This is an 18.6403 percentage-point increase, with
three more observations and a 450-s longer nominal execution schedule.

This is a selected supplemental hybrid task, not a new held-out confirmation
result. The fixed denominator contains the same 41 inspectable target IDs;
39 are accepted. The two missing IDs are `mesh_00009` and `mesh_00088`. Neither
39/41 nor the weighted percentage denotes complete continuous ISS surface coverage.

## Selection and retained diagnostic

The hybrid ADP search on the unchanged parent scenario selected 12 views for a
95% goal. The original 12-view schedule passed 10/12 synchronous tracking checks;
views 5 and 12 stopped 2.868740 and 2.618019 m from their intended positions because
the endpoints lay inside the unchanged proxy caution zone. This failure is retained.
A declared local position-and-aim search moved those endpoints by 8 m and 6 m.
All original visible target IDs were preserved, all visibility masks and HCW
transfers were recomputed, and the 12-view order was retained. The selected
adjustments and full search inventories are included in the evidence snapshot.
The refined schedule passed all 12 synchronous checks before this graphical run.

The original 2-m safety margin, 8-m caution distance, 0.8-m vehicle radius,
0.060-m/s² acceleration limit, 1.5-m/s speed limit and 0.5-m/0.05-m/s acceptance
tolerances were unchanged. The same camera range, incidence, field-of-view and
full-mesh line-of-sight predicates were retained. Each 90-s transfer has a
60-s stationary settling interval, for a nominal 1800-s schedule. No accelerated
probe result is substituted for this normal-speed graphical execution.

## Recorded results

| Quantity | Value |
|---|---:|
| Required targets accepted | 9/9 |
| Observations accepted | 12/12 |
| Weighted background coverage | 95.857715604% |
| Inspectable samples accepted | 39/41 |
| Completion time | 1800.035297363 s |
| Safe-control integral through final event | 20.476704864 m/s |
| Transfer-and-hold reference effort | 18.027014268 m/s |
| Maximum terminal position error | 0.050469711 m |
| Maximum terminal speed | 0.003843660 m/s |
| Filter-active safety messages | 1847 |
| Safe-control messages | 36172 |
| Trajectory samples | 36181 |
| Full transformed mesh triangles | 247525 |
| Minimum swept-body margin above required 2 m | 3.379874828 m |
| Peak acceleration | 0.060000000 m/s² |
| Recorded camera messages | 23722 |
| Maximum selected camera/event receipt mismatch | 0.073427677 s |
| Maximum scene/event position difference | 0.002763542 m |
| Maximum scene/event orientation difference | 0.000001708 degrees |

All execution, full-mesh and selected camera alignment gates passed. Target
credit is the union of pre-execution geometric visibility masks admitted by
terminal tracking; images provide synchronized visual context, not fresh
image-based target recognition or defect detection. The full-mesh audit checks
all connecting trajectory segments with the 0.8-m body radius and subtracts
the required 2-m margin. Control effort uses timestamped safe-command norms
with zero-order holds, clipped at the final event receipt.

Figure 7 retains Arial fonts, the approved path/mesh treatment and the existing
observation palette, extended for views 11 and 12. Twelve uncropped camera
frames appear in two chronological rows of six; odd/even numbered markers are
highlighted in the two equally scaled projections to prevent label collisions.
The new layout is 170 by 47 mm, with 18.1-mm camera panels. It is 3 mm taller
than the approved nine-view 44-mm layout and 34.7% shorter than the earlier
72-mm layout. No source image brightness, color, contrast or crop is changed.
The nine-view layout is archived in
`archive/figure7_nine_view_two_rows_20260909/`; its renderer regression retained
identical PNG pixels before adding the new 12-view branch.

The original 810-s failed run, the successful 1350-s nine-view graphical run,
the original 12-view diagnostic failure and all refinement inventories remain
available. Figures 1–6, the frozen offline study, bibliography and the 11.05%
offline saving are unchanged. This single adjusted execution establishes no
paired ROS maneuver-saving or population success-rate claim.

The compact evidence snapshot is
`data/required_target_ros/20260909_093200_hybrid12_visual/`. Its manifest records
all included file hashes and paths/hashes/sizes of the original local core and
camera MCAPs and named Gazebo pose stream. The reviewed manuscript is exported
to `output/pdf/OrbInspect_IEEE_TAES_ROS_12_observations_20260909.pdf` in the workspace.

## Timing and startup-scene diagnostics

The publisher-reported maximum reference interval was 0.248723052 s, exceeding
the 0.075-s nominal diagnostic. The separate count-completion gate passed with
36,186 published references against a minimum 35,640. The recorded reference
headers have a maximum gap of 0.051313877 s; this does not replace or erase the
publisher diagnostic, which includes publication history beyond the recorded
sample set. Both reports are retained in `reference_timing_diagnostic.json`.

Camera recording began before the chaser was spawned. Scene messages with no
named chaser are retained in the original JSONL and listed separately in the
camera audit; no pose is synthesized. The initial preparation failure is
retained. All selected frames still satisfy the unchanged temporal bracketing,
0.2-s receipt, 0.041-s scene-time, 0.1-m position and 0.5-degree orientation gates.

## Delivery checks

The reviewed PDF has 13 pages, with Figure 7 and the complete conclusion on page 12; references start on page 13. Pages 1–10 render identically to the approved nine-view manuscript. All 67 protected figure files outside the four Figure 7 outputs and overall manifest retain their original hashes. The frozen confirmation data, bibliography and pre-existing root build artifacts are unchanged. The LaTeX build and project integrity check pass, with no overfull boxes, undefined references or oversized floats. Figure 7 has a 7-pt minimum glyph size. Seven evidence-tool tests pass. The earlier complete colcon test record retains two pre-existing guidance lint failures; the ROS build passed all 12 packages, and this follow-up changed no runtime source.
