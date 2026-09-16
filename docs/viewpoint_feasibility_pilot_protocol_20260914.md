# Redundant viewpoints and independent route feasibility

This local development pilot addresses the low unconditional completion rate in
the frozen confirmation. That confirmation had 7/50 test and 21/30 shifted cases
with a required item absent from every available view; its original data and
manuscript figures are preserved. The pilot is a new experiment, not a revised
denominator or a substitute for the earlier results.

## Frozen design

The YAML is `src/orbinspect_guidance/config/viewpoint_feasibility_pilot.yaml`.
All source hashes and geometry-generation parameters are frozen before new
viewpoints are generated. Three fixed seeds sample distinct graphs on the same
ISS geometry; this does not establish generalization to different spacecraft.
The original nine required identities and 90 mesh-sample coordinates are checked
against the archived confirmation. The 41-item background denominator remains
fixed and does not affect the required-only completion predicate.

Each graph has three newly sampled, separated, geometry-valid viewpoints for
each required item and six additional views anchored to other observable samples.
Camera positions lie in a 35-degree cone around a source target's surface normal,
26--42 m from that target; the camera aims at the source target. Each source gets
64 candidate attempts. Selection uses a deterministic first-valid seed followed
by farthest-point spacing, with 4 m minimum separation. Connector source targets
are selected by geometric farthest-point sampling, without route outcomes.
All rejected candidate attempts are retained. Range, FOV, incidence, full-mesh
line of sight and viewpoint clearance are checked with the existing implementation.

Every directed initial/observation transfer is regenerated under the original
90-s HCW model, 3-s integration step, 0.06 m/s² input limit, 2 m safety margin,
0.8 m vehicle radius and original terminal tolerances. Existing speed and swept
clearance checks apply. Passive-drift auditing remains disabled as in the study.
All methods receive the identical stored graph and scenario availability mask.

Each graph gets one unperturbed reference case, 10 nominal cases with independent
node dropout probability sampled from [0, 0.10], and 10 shifted cases from
[0.15, 0.25]. All 63 cases are kept. The nine-item requirement never shrinks.
Background weights are held fixed because the required-only goal and graph cost
do not depend on the previous campaign's randomized priority multipliers.

## Independent certificates and comparison

The independent formulation chooses binary directed arcs and node-selection
variables. Source and sink each have one selected arc; each selected observation
has one incoming and one outgoing arc. Every mandatory target must be visible
from at least one selected node. The selected-node count is at most 14.
Continuous ranks increase along every selected inter-observation arc, excluding
cycles and disconnected selected components. The objective is the sum of enabled
edge stage costs plus the same 0.05 per-observation action charge used by ADP.

The solver never calls ADP and receives no ADP seed. Missing required visibility
or source-unreachable required visibility proves impossibility in that library.
A SciPy/HiGHS infeasibility result is also a certificate. A feasible integer
incumbent is checked against every model constraint and independently reconstructed
through the original graph. A time/iteration limit without such a witness is
unresolved. Optimality is claimed only when the MILP terminates with an optimum.
Tests compare solutions and infeasibility with all permutations of small directed
graphs and exercise required zero-gain connectors, budget limits, unsafe shortcuts,
disconnected cycles and timeout interpretation.

MILP feasibility/cost results are frozen before ADP evaluation. The benchmark
then runs the original greedy incumbent, one-step ADP and depth-three ADP from
scratch; neither ADP depth receives the MILP route. All methods have a common
15-s budget including initialization/model construction and excluding shared
geometry/edge generation. Planner order is shuffled deterministically within
each scenario. SciPy's native implementation and Python ADP are distinct software
implementations; timing is a desktop implementation measurement, not a complexity
comparison. Every case-method pair is timed once in this pilot.

The primary planner benchmark is materialized by
`tools/paper/materialize_solvable_benchmark.py` after certification and route
auditing. It selects only cases whose independent certificate has status
`feasible`, before using any planner outcome. For this run it contains 59 cases:
three reference, 30 nominal and 26 shifted. The four shifted cases that fail the
visibility certificate remain in `visibility_stress_cases.json` and are reported
as a separate stress test. Completion rates in the primary comparison therefore
answer whether a planner succeeds when a valid finite-graph route exists; they do
not measure viewpoint-library availability. Gap means can have different
completion denominators; paired rows must be inspected before a comparative
saving is claimed. No significance or population-level generalization is inferred
from three graphs.

## Scaling rule and commands

The predeclared geometry/feasibility gate requires at least three views per
mandatory item, at least 80% nominal and 60% shifted independently feasible cases,
at most 10% unresolved cases overall, and at most 1,200 s graph construction time
per graph. This gate deliberately does not require ADP to beat another method.
Any later confirmation needs fresh graph/scenario seeds and a separately frozen
protocol. Pilot-driven changes must be disclosed before that confirmation.

From the repository root, choose a new timestamped directory and run:

```bash
python3 tools/paper/run_viewpoint_feasibility_pilot.py prepare --output data/results/<timestamp>_viewpoint_feasibility_pilot
python3 tools/paper/run_viewpoint_feasibility_pilot.py certify --output data/results/<timestamp>_viewpoint_feasibility_pilot
python3 tools/paper/run_viewpoint_feasibility_pilot.py benchmark --output data/results/<timestamp>_viewpoint_feasibility_pilot
python3 tools/paper/run_viewpoint_feasibility_pilot.py summarize --output data/results/<timestamp>_viewpoint_feasibility_pilot
python3 tools/paper/audit_viewpoint_feasibility_pilot.py data/results/<timestamp>_viewpoint_feasibility_pilot
python3 tools/paper/materialize_solvable_benchmark.py data/results/<timestamp>_viewpoint_feasibility_pilot
```

The optional dependencies are NumPy, PyYAML and SciPy >= 1.9. The runner resolves
the repository's existing pure Python packages. ROS is not launched. `rosbag/`
and `videos/` contain notes explaining why those artifacts are absent. Raw graph
state/control arrays and per-edge audits are retained; the six standard CSVs
materialize complete offline routes. The existing stabilized-view exposure
assumption is preserved. These are not measured flight or ROS execution records.

Solver interface and status definitions:
[SciPy 1.11.4 MILP documentation](https://docs.scipy.org/doc/scipy-1.11.4/reference/generated/scipy.optimize.milp.html).

## Completed pilot, 2026-09-14

The retained run is
`data/results/20260914_073800_viewpoint_feasibility_pilot/`.
Its [review](../data/results/20260914_073800_viewpoint_feasibility_pilot/review.md)
gives the interpretation, paired comparisons and limitations. Independent
certification resolved all 63 cases: 59 feasible, four visibility-infeasible.
Depth-three ADP completed all 59 feasible cases. The mean gap to the 27 proven
optima was 0.9601%. The geometry/feasibility gate passed without any protocol
or planner changes during the run.

The post-run auditor reconstructs the source/scenario/graph identities, numeric
edge metrics, route costs, coverage, applicable base-policy bounds and independent
MILP lower bounds. It also adds `review.md`, explicit gap denominators and solver
limit counts to the derived reports. MILP reached its nominal 15-s limit in 32
cases, all with a validated feasible route; these were not proven optimal.
The native solver can return slightly after the requested limit. Its timing was
recorded during the preceding certification phase; only greedy/ADP evaluation
order was shuffled. No repeated timing or significance claims are made.

Validation: 57 relevant Python tests passed, all 12 ROS packages built, and the
manuscript asset check passed (one active TeX source, eight figure groups and 68
verified figure assets). Restrict the ROS build to active packages using
`colcon build --symlink-install --base-paths src`; unrestricted discovery also
finds the archived source bundles under `output/supplementary/`.
