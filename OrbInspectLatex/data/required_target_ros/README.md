# Required-target ROS evidence

## Current supplemental twelve-observation execution

`20260909_093200_hybrid12_visual/` contains the normal-speed graphical run with 12/12 accepted observations,
9/9 required targets and 95.8577156% weighted background coverage (39/41 samples).
The 1,800-s schedule retains the same nine required IDs, weights and physical
gates as the earlier run, with two explicit viewpoint/aim refinements and
recomputed transfers and visibility. The original twelve-view tracking failure,
refinement search, actual execution and camera evidence are retained separately.

Execution, full-mesh and per-view camera alignment audits passed. The publisher
reported a 0.248723-s maximum reference interval, above the 0.075-s nominal
diagnostic; the count-completion gate passed. Three empty startup scene messages
are retained and diagnosed without synthesizing poses. The snapshot includes
12 original RGB frames, complete CSV logs, event/control audits, portable figure
arrays, execution inputs and search provenance. Original large MCAPs and scene
poses remain local with hash-identified paths and metadata.

See [the twelve-observation report](../../docs/ROS_TWELVE_OBSERVATIONS_20260909.md).
The earlier executions below remain distinct historical evidence.

## Original failed execution

`20260909_031355_required09_adp_closed_loop/` preserves an unsuccessful headless
execution of the frozen median-effect representative ADP route. Seven of nine
observations and seven of nine required targets were accepted. Weighted
background coverage was 65.916233%; two required IDs remained missing.

The full-mesh geometric, finite-body, acceleration, and reference-stream checks
passed. Overall execution failed because terminal tracking and required-target
completion did not pass. This failed snapshot has no camera figure; it remains separate from the subsequent successful graphical execution.

The snapshot contains the six original CSV streams, extracted JSON messages
from both event topics, stamped safe-command norms, configuration and frozen
replay inputs, execution logs, preflight checks, summaries, and two audits.
`snapshot_manifest.json` hashes each copied evidence file. Original manifest
paths and revision IDs are preserved as provenance.

The `rosbag/` folder contains metadata and a location note. The 1.7 GiB MCAP
remains in the original repository execution directory; its SHA-256 is recorded
in `required_target_execution_audit.json`. This is not a bag-complete portable
snapshot. No camera frames or video were captured. `planner.csv` is header-only
because the sequence was fixed offline.

From the repository root with Jazzy sourced, the full original run can be
re-audited with:

```bash
python3 tools/paper/audit_required_target_ros.py \
  data/results/20260909_031355_required09_adp_closed_loop
```

The expected exit status is 1 for the retained mission failure. The generated
audit records which gates passed and failed. Its control integral can also be
reproduced without ROS from `raw/safe_control_integral_samples.csv`, using the
terminal event receipt time recorded in the audit JSON.

See [the full report](../../docs/ROS_EXECUTION_CHECK_20260909.md) for exact planned
and executed metrics, failure diagnostics, versions, commands, and validation
limits. The current Figure 7 uses the twelve-observation supplemental execution described above.


## Successful execution with terminal settling

`20260909_040344_required09_dwell60_visual/` contains the normal-speed graphical execution that
accepted all nine observations and required targets at 1,350.038 s, with 77.22%
weighted background coverage. The original route includes a declared 60-s
stationary settling period after each transfer. The original 810-s failure and
the eight-route synchronous screening inventory remain recorded; no offline
scenario, required target or acceptance tolerance was changed.

The `figure7/` subdirectory contains nine original RGB images, exact planned and
executed coordinates, camera/scene-pose alignment records, timing diagnostics,
and the portable plotting snapshot. All nine selected frames are within 0.036 s
of their events. The full recording contains two equal receipt-time pairs and
four receipt gaps above 0.2 s; sensor timestamps strictly increase. These full
stream diagnostics do not affect the selected views and are retained without
silently dropping images. The initial all-stream timestamp assertion and its
failure log remain in the workspace run directory; the final audit applies the
predeclared per-view timing and pose gates.

The snapshot also contains all six executed CSVs, both event streams,
stamped safe-control norms, runtime and derived schedule configuration,
full-mesh and target audits, source/tool hashes, accelerated-probe summaries,
and the complete held-out route-screening inventory. `planner.csv` is
header-only because there is no online replanning. Large MCAPs and the full
named scene-pose JSONL remain under the timestamped workspace result directories;
metadata, hashes and selected pose records are included here. No re-encoded
video is used as timing evidence.

See [the completion report](../../docs/ROS_FULL_COMPLETION_20260909.md) and
[the execution adjustment protocol](../../docs/ROS_SETTLING_PROTOCOL_20260909.md).
