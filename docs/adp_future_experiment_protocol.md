# ADP Future-Version Experiment Protocol

## Material Passport

- Origin skill: experiment-agent
- Origin mode: plan
- Origin date: 2026-08-10
- Verification status: protocol frozen before new result inspection
- Version: `adp_future_protocol_v1`

## Objective and claim gate

The study tests whether a safety-shielded approximate dynamic-programming
policy can be the main algorithmic contribution of OrbInspect.  The learned or
rollout ADP policy must control the returned inspection sequence on unseen
missions; a deterministic reversal-search or incumbent fallback cannot by
itself support the claim.

The primary endpoint is paired penalized graph cost, defined as audited graph
cost plus a fixed coverage-shortfall and mission-failure penalty.  This prevents
an incomplete low-cost trajectory from being counted as an improvement.

## Split discipline

- Training scenarios may fit critic parameters only.
- Validation scenarios select the ADP structure and its hyperparameters.
- Test scenarios remain unopened until one structure is frozen.
- OOD scenarios assess robustness after the held-out test evaluation.
- Scenario seeds are deterministic and disjoint across all splits.
- Every method receives the same scenario graph, target weights, coverage goal,
  action budget, and audited edge archive.

The legacy 2026-08-01 validation is treated only as motivation.  Its negative
outcomes are not pooled with the new full-mesh experiment.

## Candidate structures

1. Frozen linear fitted-Q critic with shielded finite look-ahead.
2. Frozen nonlinear fitted-Q critic with shielded finite look-ahead.
3. Exact-action-advantage distillation on exhaustible training subgraphs.
4. Graph-structured rollout/beam ADP that uses a frozen value approximation at
   the search frontier.

Architecture development may stop early for a route that fails the validation
success gate.  Changes prompted by validation produce a new version label and
must not use test outcomes.

## Frozen development decision (recorded before test access)

The 24-node, 12-scenario full-mesh validation screen selected depth-3
viability-preserving rollout ADP.  All three rollout depths achieved 12/12
success.  Mean graph costs were 101.424 (depth 1), 97.388 (depth 2), and 93.586
(depth 3), compared with 109.299 for audited local search.  Depth 3 won all 12
paired cost comparisons; its median online time was 1.685 s within a 90 s
decision interval.  The frozen held-out configuration is:

- candidate graph: 24 nodes and 41 inspectable weighted mesh targets;
- goal: 0.80 weighted inspectable coverage within 14 actions;
- adaptive rollout depth: 3;
- safety: common archived HCW/input/clearance/terminal shield; passive drift is
  disabled in this study and is not claimed;
- test scenarios: 30 deterministic, disjoint seeds;
- OOD scenarios: 20 deterministic seeds with greater node dropout and target
  priority shift.

No test or OOD method rows were evaluated during this selection.

## Post-selection validation sensitivity extension

After the depth-3 configuration had been frozen and the held-out study had
been completed, depths 4--6 were evaluated on the same 24-node graph and the
same 12 validation scenarios.  These runs are a computational sensitivity
extension, not a new hyperparameter-selection screen: they did not open test
or OOD rows for the alternative depths and they do not alter the confirmatory
depth-3 comparison.

All three added depths achieved 12/12 validation success.  Their mean graph
costs, median online times, and mean safe-action evaluations were:

| Depth | Mean graph cost | Median online time (s) | Mean safe-action evaluations |
|---:|---:|---:|---:|
| 4 | 92.431 | 3.847 | 1,203,706 |
| 5 | 92.369 | 14.966 | 4,243,492 |
| 6 | 91.564 | 38.421 | 11,730,359 |

Relative to depth 3, depths 4, 5, and 6 reduce mean cost by 1.23%, 1.30%, and
2.16%, respectively, while their median runtimes are 2.28, 8.88, and 22.81
times larger.  Thus depth 3 remains the selected cost--computation compromise,
not the minimum-cost configuration when planning time is unconstrained.

## Predeclared selection rule

Rank candidates on the validation split by:

1. success rate (higher is better);
2. mean paired penalized-cost difference from audited local search (lower is
   better), with its paired-bootstrap 95% confidence interval;
3. median online planning latency (lower is better).

Freeze the highest-ranked candidate only if its success rate is no lower than
local search and its mean paired penalized cost is lower.  The stronger paper
claim requires the upper 95% confidence bound to be below zero on the unopened
test split.  If no candidate passes validation, do not open the test split and
do not make ADP the empirical main contribution.

## Held-out analysis

- Primary comparison: proposed ADP versus audited reversal local search.
- Secondary comparisons: incumbent, one-step rollout, and search-only ablation.
- Report paired mean and median differences, paired-bootstrap 95% confidence
  intervals, exact two-sided sign tests, success rates, online latency, shield
  rejections, and selected-action counts.
- Apply Holm correction to secondary hypothesis tests; the primary comparison
  is tested once at alpha 0.05.
- Perform the complete 11-item statistical-fallacy scan and a deterministic
  rerun/hash comparison.

## Execution environment and outputs

- Python 3.12 target; current offline development run on Windows/Anaconda.
- ROS 2 execution remains a documented Ubuntu/Jazzy integration placeholder.
- Base config: `src/orbinspect_guidance/config/adp_future_study.yaml`.
- Results: `data/results/<run-id>/` with `config_snapshot/`, `raw/`,
  `figures/`, `rosbag/`, `videos/`, `summary.json`, and `summary.md`.
- The graph archive records full-mesh visibility and HCW-audited directed
  transfers and is reused byte-for-byte across candidate structures.
