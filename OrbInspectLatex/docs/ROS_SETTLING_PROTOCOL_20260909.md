# Required-target completion: execution settling protocol

The user requested a case with full observation of the prescribed targets after
reviewing the failed median-effect execution. Full completion means the same nine
required mesh-sample IDs used in the frozen confirmation study. It does not mean
100% of the 41 inspectable samples or all 90 full-mesh samples.

## Search and decision

The frozen held-out ADP inventory contains 80 rows: 52 successful plans and 28
planning failures. The successful plans contain eight distinct route sequences.
Each sequence was exported using the first-listed matching scenario, preserving
its archived route and metrics. Synchronous 20-Hz screening called the production
HCW, LQR and projection-filter functions with the unchanged ROS verification YAML.
None of the eight sequences accepted every observation. This is a diagnostic
screen, not an 80-run ROS campaign or an execution success-rate estimate.

The original median-effect scenario, `required09_test_000`, was therefore retained.
A derived execution schedule adds a uniform 60-s stationary settling period after
each original 90-s transfer, before evaluating the observation. The nine positions,
route order, boresights, visibility masks, required IDs and acceptance tolerances
remain fixed. All original transfer state and control samples are preserved;
only their execution times are shifted. Stationary hold references have zero
velocity and HCW feedforward acceleration `[-3*n*n*x, 0, n*n*z]`, with
`n = 0.00113137 rad/s`. No runtime ROS node or global YAML parameter was changed.
Only one nonzero dwell duration, 60 s, was screened. It accepted all nine
observations synchronously; the worst terminal position error was 0.0501 m.

The resulting schedule lasts 1,350 s, compared with the archived 810-s plan.
Its stationary reference adds 0.070756 m/s to the archived 13.768885 m/s transfer
commands, giving 13.839641 m/s of scheduled reference effort. These are planned
quantities. Feedback effort must be integrated from the normal-speed run's
recorded safe-control messages. The archived graph cost still describes the
original transfers and does not price the added settling time or feedback.

This was a post-hoc execution adaptation following a failure. It does not alter
the offline cohort, median-effect selection, ADP theorem, or 11.05% aggregate
result, and it cannot support a paired ROS saving or robustness claim.

## Completed accelerated check

`20260909_035724_required09_dwell60_headless5x` used the derived schedule at 5x
simulation-clock speed. It accepted all nine observations and required targets
at 1,350.015 s. The full transformed mesh audit passed all eight gates over
27,944 trajectory samples and connecting segments, with 5.3551 m minimum
finite-body clearance above the required 2-m margin. Target identities were
also reconstructed from its recorded verification events. This run is a
preliminary check; the manuscript's measured effort and camera evidence must
come from the separate normal-speed graphical run.

The probe passed reference-count completion, but its maximum 0.150150-s
reference gap exceeded the separate 0.075-s nominal-gap diagnostic. The
normal-speed graphical run passed that diagnostic with a 0.055441-s maximum gap.

## Graphical recording protocol

The separate normal-speed run is `20260909_040344_required09_dwell60_visual`.
Its camera capture is `20260909_040344_required09_camera`. Both are retained
under `data/results/`. The recording includes original RGB camera messages,
ROS odometry, attitude references, verification events, Gazebo clock, and scene
pose messages. A supplemental raw Gazebo JSONL stream preserves named chaser
poses and simulator timestamps because the ROS TF bridge omits those fields.

For each accepted observation, choose the nearest camera message by MCAP wall
receipt time with an absolute mismatch no greater than 0.2 s. Missing evidence
must fail rather than select the first or last frame. Check the nearest named
Gazebo chaser pose at the camera's simulator timestamp (within 0.041 s), and
require agreement with recorded event-time odometry within 0.1 m and 0.5 degrees.
These visual alignment checks are additional to the unchanged mission gates.
Receipt matching includes transport delay; camera imagery does not establish
fresh visibility credit or perform target/defect detection.

## Preserved evidence and presentation

The failed 810-s execution remains retained and reported. The complete search
inventory and screening outcomes are in
`data/results/20260909_035331_required09_route_screen/selection_protocol.json`
and `synchronous_screen.json`; the derived schedule is in
`data/results/20260909_035637_required09_dwell60_inputs/`.

Figure 7 retains the approved 170-by-74-mm layout, Arial family, numbered color
mapping, gray dashed reference, blue executed path, neutral mesh and uncropped
camera images. Five observations appear on the left and four on the right.
Axis ranges may expand to contain the new trajectory, while the two projections
retain identical physical scale. Required completion and weighted background
coverage have separate labels. Historical artwork and its caption are retained
under `data/historical_ros/figure7/artwork/`.

The graphical run and all per-view camera checks subsequently passed. See
[the completed report](ROS_FULL_COMPLETION_20260909.md) for final values, timestamp
diagnostics and the reviewed PDF.
