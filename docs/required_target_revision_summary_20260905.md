# IEEE TAES required-target revision — 5 September 2026

## Completed manuscript changes

The title, abstract, introduction, contribution list, problem formulation,
algorithm, theory, experimental protocol, results, discussion, and conclusion
now center on **viability-preserving rollout approximate dynamic programming**.
This is model-based ADP, not a newly trained DRL policy. DRL is discussed only
as a possible learned approximation requiring independent completion checks.

Mission success now requires every identity in a fixed required target set.
Camera viewpoints remain decision variables; required physical sample IDs are
not prescribed camera poses. The whole-sample denominator, priority-weighted
background score, and required-target completion are distinguished. Full mesh
occlusion and collision geometry remain unchanged.

The required items are synthetic, geometry-distributed sample requirements,
not verified mission-critical ISS components. Their selection uses geometry
and nominal candidate observability, not successful routes. Completion means
acceptance of every prescribed sample under the deterministic camera model;
it does not establish full-region imaging, defect detection, or full ISS
inspection.

## ADP implementation and evidence

Required and hybrid goals use a shared exact completion predicate. All safe
unvisited viewpoints remain eligible, including zero-immediate-gain
connections. A finite-horizon recursion guard was corrected. The manuscript
states exhaustive-prefix, deterministic-base, finite-completion, and
no-revisit assumptions and the empty-action-set convention explicitly.

The successful-base cost guarantee is conditional: the greedy base fails
every primary confirmation scenario, so an empirical check of that bound
there would be vacuous. Synthetic finite-graph tests cover implementation of
the bound and exact recursion. No new full-mesh exact-optimality result is
claimed. Empirical comparisons against other policies are not consequences
of the base-policy theorem.

## Honest development and confirmation history

The original geometry-prescribed campaign retains all 276 scenarios across
6/9/12-item profiles. The primary nine-item profile was chosen before its
results. Greedy-initialized comparators did not finish that primary task;
those outcomes remain disclosed as development evidence.

A second campaign froze unchanged nine-item requirements, the unchanged
depth-three policy, fresh seeds, and a stronger comparator before new
evaluation. The comparator applies audited local search to a completed
one-step ADP route. It is explicitly ADP-seeded, not an independent non-ADP
method. The fresh campaign has 12 validation, 50 test, and 30 shifted
scenarios; no scenario is rejected or resampled for infeasibility.

Depth-three ADP completes 43/50 test and 9/30 shifted missions. Those counts
equal the scenarios retaining any available view of each mandatory item;
all other primary tasks are impossible in the fixed candidate library.
Every completed mission credits all nine items. This observed agreement
does not make the visibility-union test a general route-feasibility theorem.

The seeded local comparator completes 43/50 and 8/30. The predeclared
all-test penalized-cost difference is −12.256, with a percentile 95% interval
[−14.155, −10.212]. The fixed 500-unit penalties are evaluation scores, not
physical maneuver costs.

On 43 jointly complete test pairs, mean physical delta-v falls from
15.777 to 14.033 m/s, an 11.05% ratio-of-means reduction. The paired reduction
is 1.744 m/s, with a 95% interval of 1.525–1.923 m/s. ADP wins 40 pairs and
loses three. The eight jointly complete shifted pairs are reported
separately; their two-sided sign-test p value is 0.0703. The bootstrap uses
the frozen seed 60935 and 10,000 replicates.

Of the 43 completed ADP test missions, 41 finish below 80% weighted background
coverage. Mean background coverage over those 43 successes is 72.32%.
This directly supports the new task definition without relabeling partial
whole-mesh coverage as complete station inspection.

## Figures and execution

The established Python palette, fonts, line/marker encodings, panel
dimensions, and manuscript arrangements are retained. The route panel
remains above the two progress panels. Necessary changes update target
markers, completion curves, comparator labels, captions, and measured
values. Small annotation-placement adjustments prevent overlap.

The illustrative route is selected by the declared median-effect rule from
jointly complete test pairs. Repropagated trajectories match both archived
graph costs and delta-v values. The prepared ADP replay has nine actions,
9/9 required targets, and 77.22% planned weighted background coverage.

Accepted-target bookkeeping now unions identities from accepted observations
only; a later accepted view cannot import credit from an earlier rejected
view. All six core replay CSV streams are available and labeled as planned
records. Existing ROS message fields and legacy defaults are preserved.

No new ROS execution occurred. The retained camera-view figure is explicitly
historical survey evidence. ROS 2 Jazzy and colcon are unavailable on this
macOS host; the required build command was attempted and could not run.

## Verification and remaining author decisions

- 50 focused planner, execution-credit, route-export, and protocol tests pass.
- The broader runnable offline guidance suite passed 70 tests earlier in the
  revision. ROS/ament-dependent collection requires the intended deployment.
- Independent audits reconstruct all 1,200 development and 400 confirmation
  evaluation rows, plus the confirmation depth rows, from archived graph
  records. Frozen input/source hashes and unchanged target IDs match.
- All 124 historical exported routes retain their all-accepted coverage.
- The IEEE manuscript compiles and is visually inspected in the two-column
  template. Current figures are generated from the new source rows.
- Previous final PDF, Overleaf archive, and reproducibility archive are kept.

Before submission, the authors should confirm the correspondence email and
funding text, choose the public code/data repository and licenses, and obtain
a persistent release identifier. No DOI, license, or new ROS/flight result
has been invented. A fresh required-target ROS campaign remains necessary
for execution-level claims under the revised objective.
