# Frozen-ADP Superiority Evaluation

## Claim Under Test

A critic trained once on related orbital-inspection graphs should improve
held-out mission quality at lower online latency than matched search and local
improvement, while the common HCW shield preserves modeled feasibility.

This claim is stronger than showing that a safeguarded stack returns a good
route on one deterministic mission. It requires a frozen checkpoint, disjoint
mission splits, strong baselines, paired statistics, and a decision rule fixed
before test evaluation.

## Hypotheses

The frozen critic must satisfy all three hypotheses on the same held-out test
scenarios:

1. **Feasibility and success:** its coverage-success rate is no lower than
   safeguarded local search (L+S), with every selected edge passing the same HCW,
   input, clearance, terminal, and passive-drift audits.
2. **Mission quality:** the upper bound of the paired-bootstrap 95% confidence
   interval for `penalized_cost(ADP) - penalized_cost(L+S)` is below zero.
3. **Online computation:** its median online planning time is below that of L+S.

The penalized cost adds a fixed coverage-shortfall and failure penalty to the
same graph objective used by every method. It prevents a cheap incomplete route
from being reported as an improvement.

## Experimental Design

### Common graph and dynamics

- One 24-node candidate library and 180 weighted ISS surface targets.
- Every directed/start edge is generated once with finite-duration continuous
  HCW transfer simulation and archived in `raw/hcw_graph.json`.
- Every method receives the same scenario-specific node subset, target weights,
  action budget, coverage goal, and edge archive.
- The learned critic can rank only edges accepted by the model-based shield.

### Data separation

- Training scenarios fit critic parameters only.
- Validation scenarios select the target type, critic width, regularization,
  decision horizon, and task regime.
- Test and out-of-distribution (OOD) scenarios remain unopened unless a frozen
  candidate passes the complete validation gate.
- Scenario identifiers and random seeds are disjoint between splits.

### Compared methods

- Frozen ADP without an incumbent safeguard.
- Search-only planning with the unfitted heuristic value.
- The dynamics-aware incumbent.
- One-step safeguarded rollout.
- Audited reversal local search (L+S).
- Frozen ADP with the incumbent safeguard.

The standalone frozen policy tests critic quality. The safeguarded variant tests
deployment behavior but cannot establish that the critic itself is superior
when the incumbent is selected instead.

### Critic variants

1. Rollout-return distillation with a two-layer MLP.
2. Exact Bellman action-value regression on exhaustible 12-node graphs.
3. Exact Bellman-advantage regression using
   `Q(s,a) - min_a Q(s,a)` to remove state-level return offsets.
4. Exact-advantage regression under a harder 70% coverage goal and eight-action
   budget, where exact DP confirms that the incumbent and rollout leave
   meaningful optimality headroom.

The critic features include coverage and budget state, action cost and gain,
safety margins, residual coverage structure, regional target-weight summaries,
and safe outgoing-graph cost and degree statistics.

## Execution Plan and Status

1. **Archive the HCW graph.** Complete. The graph has 24 nodes, 180 targets, and
   576 directed/start edges.
2. **Implement frozen checkpoints.** Complete. Test-time fitting and parameter
   updates are disabled and verified by unit tests.
3. **Add disjoint scenario generation.** Complete. Train, validation, test, and
   OOD seeds are reproducible and disjoint.
4. **Add graph-aware critic features.** Complete. Scenario-specific safe
   outgoing cost and degree features are populated from the archived graph.
5. **Add exact policy targets.** Complete. Both absolute Bellman values and
   within-state Bellman advantages are available on reduced graphs.
6. **Tune on validation only.** Complete. Rollout targets, exact values, exact
   advantages, and a harder coverage regime were evaluated.
7. **Apply the validation gate.** Complete. No candidate qualified.
8. **Run test and OOD evaluation.** Withheld by design because stage 7 failed.
9. **Generate result figures.** Complete. A separate read-only plotting module
   provides one function per standalone figure and exports PDF, SVG, and PNG.
10. **Revise the manuscript if superiority is demonstrated.** Not triggered.

## Validation Results

Each row contains eight disjoint validation scenarios. Cost differences are
paired within scenario; positive values favor L+S.

| Critic | Regime | Success (ADP/L+S) | Mean paired penalized-cost difference [95% CI] | ADP/L+S median-latency ratio | Pass |
|---|---|---:|---:|---:|---:|
| Rollout targets | 90% goal, full graph | 0.875/1.000 | 104.64 [54.21, 187.96] | 0.42 | No |
| Exact value targets | 55% goal, 12 nodes | 0.750/1.000 | 94.21 [22.20, 196.41] | 9.43 | No |
| Exact advantage targets | 55% goal, 12 nodes | 0.875/1.000 | 53.02 [16.49, 120.54] | 9.03 | No |
| Exact advantage, harder goal | 70% goal, 12 nodes | 0.625/1.000 | 118.85 [47.90, 212.13] | 1.89 | No |

The rollout-distilled critic reduced median full-graph latency relative to L+S,
but it lost one success case and lost all eight paired cost comparisons. Exact
advantage targets improved over absolute exact values, yet still lost one
success case and every paired cost comparison. The harder regime increased the
available optimality headroom but reduced frozen-critic success to 62.5%.

## Decision

The current experiments do **not** demonstrate superiority of the proposed
frozen ADP. Opening the test or OOD splits after every validation candidate
failed would convert the test set into another tuning set, so those evaluations
were not run. The manuscript must retain its bounded conclusion: the evidence
supports safety-shielded graph policy improvement and incumbent safeguarding,
while the demonstrated primary gain is attributable to audited local sequence
search rather than the learned critic.

The next technically justified critic is graph-structured rather than a wider
MLP on compressed hand features. It should encode the full uncovered-target set
and candidate-edge neighborhood, train with a ranking-aware objective, and pass
the same validation gate before test evaluation. Until then, an ADP-superiority
claim would not be evidence-supported.

## Reproducible Outputs

- Validation decision archive:
  `data/results/adp_superiority_validation_decision_20260801/`
- Aggregation command:
  `offline_adp_validation_decision`
- Plot command:
  `offline_adp_superiority_plots`
- Plotting source:
  `src/orbinspect_guidance/orbinspect_guidance/offline_adp_superiority_plots.py`
- Focused tests:
  `test_advanced_safe_planner.py`,
  `test_offline_adp_superiority_study.py`, and
  `test_offline_adp_validation_decision.py`
