# Required-target evidence audit

## Confirmation campaign

Audited bundle: `data/results/20260905_101500_required_target_confirmation`.
The new confirmation follows the first required-target campaign and fixes an
ADP-seeded local comparator before evaluating fresh scenarios. The nine
required target IDs, graph, greedy base policy, and depth-three ADP remain
unchanged. The comparator performs three audited local-search passes starting
from a complete depth-one ADP route; it is therefore an ADP-based comparator.

Independent reconstruction checked all 400 evaluation rows and 36 validation
depth rows. No discrepancies were found in the six frozen input hashes, four
source hashes, 92 unique fresh seeds, unchanged required IDs, node availability,
route budget, no-revisit condition, selected-edge safety, graph cost, velocity
increment, credited masks, required completion, weighted coverage, unweighted
sample coverage, visibility upper bound, or fixed penalized cost. Seeded-local
reference routes matched their separately recorded one-step ADP routes, local
search never increased the cost of a successful seed, and its timing included
seed generation. Original frozen source files were not modified.

| Endpoint | Test | Shifted |
|---|---:|---:|
| Unconditional ADP3 completion | 43/50 | 9/30 |
| ADP1-seeded local completion | 43/50 | 8/30 |
| Required items jointly available in retained views | 43/50 | 9/30 |
| Mean all-scenario penalized ADP3-minus-local cost | -12.255743 | -31.999060 |
| 95% bootstrap interval for that mean | [-14.154833, -10.212206] | [-91.494203, -1.240598] |
| Jointly complete cost pairs | 43 | 8 |
| Mean jointly complete graph-cost difference | -14.250863 | -9.890342 |
| Mean jointly complete velocity-increment difference (m/s) | -1.743769 | -1.207499 |
| Joint graph-cost wins/ties/losses | 40/0/3 | 7/0/1 |
| Two-sided sign-test p-value | 3.0213e-9 | 0.0703125 |

In this confirmation, every ADP3 failure has a required item absent from all
retained observation masks. Such absence proves impossibility in that fixed
observation library. Every availability-passing scenario has an actual ADP3
completion witness; this observation does not establish that the visibility
condition generally implies route feasibility. Shifted scenario 020 is a
specific witness where depth-three ADP completes but depth-one ADP and its
seeded-local successor do not.

## Interpretation boundaries

- Always present unconditional success denominators alongside the 43/43 and
  9/9 completion figures conditional on available required observations.
- All original greedy bases fail in this confirmation. Consequently the
  theoretical cost bound against a successful greedy completion is not
  empirically exercised here. It does not guarantee a bound against the
  ADP1-seeded local comparator; that comparison is empirical.
- The principal frozen endpoint is the paired penalized score over all 50
  test scenarios. The score uses fixed penalties of 500 and is not a physical
  maneuver cost. Joint-success resource comparisons are secondary.
- Test mean velocity increment is 14.033367 m/s for ADP3 and 15.777136 m/s for
  the comparator, an 11.0525% reduction in the ratio of means. Mean graph cost
  is 115.640839 versus 129.891702, a 10.9713% reduction. Do not mix these two
  percentages or confuse a ratio of means with a mean of pairwise ratios.
- The shifted sign test is not below 0.05, although its bootstrap mean-effect
  interval excludes zero. Do not claim every inferential test is significant.
- Whole-sample coverage is the unweighted credited count divided by 90. It
  is not complete-mesh geometric area coverage or a defect-detection metric.
- The source graph and geometry are unchanged. New perturbation seeds do not
  establish generalization to independent geometries or flight conditions.
- Runtime includes the common greedy-base construction; non-incumbent
  `safe_action_evaluations` counts the selected planner only. Seeded-local
  runtime also includes its one-step seed, recorded separately as
  `seed_time_s`. These scopes should accompany workload comparisons.

## Display and theoretical checks

The original plotting/table drafts pooled profiles 6/9/12 despite a frozen
nine-item primary profile. This was reported and the main agent changed the
headline filtering to `required09`. The first campaign also had no successful
primary greedy seeds, leaving fixed-suffix and unseeded-local comparisons
without jointly complete cost pairs. Its results must remain development
evidence, with the fresh campaign identified as the stronger-comparator
confirmation. Different profile seed ranges do not support paired causal
comparisons of profile difficulty.

The confirmation freezes bootstrap seed 60935 and 10,000 replicates. Figure
and table generators must use these values or the archived intervals; their
original default seed 60905 was reported to the main agent for correction.
Representative-case selection must use only primary-confirmation pairs and
remain explicitly illustrative. Required-target curves need all nine IDs
credited, irrespective of optional background coverage.

The required-goal Bellman recursion, deterministic base-policy ranking, safe
zero-gain transit action set, viability proof, and telescoping cost proof agree
with the implementation. Empty-action minimization must explicitly equal
infinity. The implementation's finite-budget guard was tested, including a
lookahead depth exceeding the remaining horizon. The bound requires exhaustive
prefix evaluation and the same deterministic Markov base policy. It does not
apply to pruned learned-policy search and does not imply monotonic realized
cost across depths. Exact-solver evidence currently includes meaningful small
unit-test graphs; no full confirmation graph has been exhausted, so no
full-graph optimality claim is supported.

The focused planner suite passed 31 cases; the runnable offline guidance suite
passed 70 tests. ROS/ament-dependent tests were unavailable in this macOS
runtime. Offline route reconstruction is not a new ROS execution result.
