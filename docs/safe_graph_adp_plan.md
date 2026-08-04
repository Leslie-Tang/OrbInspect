# Safety-Shielded Candidate-Graph Policy-Improvement Plan

## Objective

Replace the myopic high-level SOOA selector with safety-shielded candidate-graph
policy improvement while preserving:

- ROS 2 Jazzy and the existing stable topics;
- the ROS-native HCW dynamics node as the state source of truth;
- finite-duration continuous-maneuver SOOA transfers;
- the existing visibility, input, speed, terminal-error, clearance, and
  passive-drift audits;
- YAML configuration;
- the timestamped paper-result directory and CSV interfaces; and
- the simulation-first, plot-second paper workflow.

The implementation is model-based and offline. It learns an action-value
approximation from safe graph rollouts, uses the approximation as the terminal
value in truncated Bellman look-ahead, evaluates a shield-feasible base-policy
completion, and retains the base tour as a no-degradation safeguard. It does
not replace the HCW transfer controller and does not allow a learned value to
override a failed safety audit.

## Decision Model

Each accepted camera candidate is a decision node. The Markov state is

```text
(current node, covered-target mask, selected-node mask, remaining action budget)
```

The covered-target mask is required because the reward of a candidate depends
on which targets were covered by earlier actions. An action selects the next
candidate node. Its transition is the archived rest-to-rest HCW transfer.

The terminal set contains states meeting the requested weighted coverage. The
stage cost combines the existing HCW dynamic cost and a small action cost.
Unsafe edges are removed by the model-based shield before value evaluation.

## Implementation Stages

1. Activate `advanced_safe_planner.py` as a ROS-independent graph planner.
2. Add immutable graph node, edge, state, decision, and result records.
3. Add exact dynamic programming for reduced-graph verification.
4. Add a linear action-value critic trained by deterministic Monte Carlo
   policy evaluation with reproducible exploration.
5. Add truncated Bellman look-ahead using the learned critic as its terminal
   value.
6. Integrate the method into `offline_planning_experiment.py` as
   `safe_graph_adp`.
7. Build a coverage-preserving candidate pool and evaluate transfer edges
   lazily through the existing HCW cache.
8. Apply input, speed, terminal, clearance, and passive-drift checks before an
   edge can enter the action set.
9. Log critic weights, training error, safe-action evaluations, shield
   rejections, estimated decision values, and reduced-graph optimality gaps.
10. Expose all planner settings through YAML without changing existing
    defaults for other methods.
11. Add a deterministic base policy, shielded rollout, audited reversal
    improvement, and an explicit policy-source diagnostic.
12. Run every study case independently, clear transfer caches between methods,
    and aggregate the saved rows only after each case is complete.

## Theory to Support

The manuscript will state and prove only claims supported by the
implementation:

1. **Markov sufficiency.** The graph state contains all variables used by the
   deterministic transition, coverage update, termination rule, and cost.
2. **Compositional safety.** If every selected rest-to-rest edge passes the
   shield, concatenating selected edges preserves the modeled sampled
   constraints.
3. **Incumbent no-degradation.** The returned successful policy is no worse
   than a supplied successful shield-feasible base policy on the same graph.
4. **Reduced-graph optimality.** Exact Bellman recursion returns the graph
   optimum when the finite reduced state space is exhausted.
5. **Approximate-policy bound.** For a finite horizon, a policy greedy with
   respect to an action-value approximation with uniform error `epsilon` has a
   suboptimality bound proportional to `2 H epsilon` over the shielded action
   set.

The implementation does not claim neural-network convergence, continuous-space
optimality, or flight safety.

## Verification

- Unit tests for state updates, unsafe-edge masking, long-horizon selection,
  deterministic training, and exact-oracle agreement.
- Regression tests for the existing experiment outputs.
- Reduced-graph optimality-gap experiments.
- Full deterministic ISS comparison.
- Three deterministic initial-state stress cases with a common passive audit.
- Compute cases for critic training and look-ahead depth.
- Matched cold-cache component cases for critic/lookahead (C), rollout (R),
  incumbent safeguard (S), and local sequence search (L).
- Python-only PDF/SVG/PNG figures loaded from archived result files.
- LaTeX compilation and page-level visual QA.

## Paper Evidence Contract

Core conclusion:

> Safety-shielded graph policy improvement can improve a feasible incumbent or
> replace an unsafe one without allowing approximate values to bypass HCW
> transfer feasibility.

Required evidence:

- optimality gap on graphs small enough for exact DP;
- matched coverage, delta-v, feasibility, and decision latency on the full
  graph;
- matched performance under explicitly defined initial-condition stresses;
- zero shielded-policy violations under the modeled audits;
- critic and look-ahead compute cases; and
- explicit failure cases when the candidate pool or control authority is
  insufficient.

## Conducted Findings

- The 180-target primary policy reaches 98.33% coverage with 18 actions and
  19.47 m/s delta-v, versus 21 actions and 21.59 m/s for the base tour.
- The learned-only primary candidate is not the winner; the result is correctly
  attributed to audited incumbent improvement.
- The seven-way component ablation shows that L+S alone reproduces the complete
  method's 18-action, 19.47 m/s route in 52.81 s. The complete C+R+S+L method
  takes 339.92 s, or 6.44 times longer, without a primary-case improvement.
- Critic-only planning reaches the same 98.33% coverage but requires 26 actions
  and 42.86 m/s. C+S returns the incumbent unchanged, while R+S provides the
  smaller 20-action, 20.92 m/s improvement.
- All nine reduced 8-, 10-, and 12-node cases match the exact Bellman
  objective. The exhaustive recursion expands 23, 97, and 439 states,
  respectively.
- IC-1 exposes a passive-unsafe low-effort base tour and a higher-effort safe
  replacement. IC-2 shows a smaller rollout improvement when both policies
  are safe.
- Twenty critic-training episodes reach the 95% compute-case goal, whereas
  zero and 80 episodes do not. Increasing look-ahead from depth 2 to 3 also
  fails to recover the goal, so no empirical convergence claim is made.
- The complete 17-case archive is saved under
  `data/results/adp_paper_study_20260731_final/`; its plotting step is separate
  from simulation and exposes one function per manuscript result figure.
- The independent seven-variant archive is saved under
  `data/results/adp_component_ablation_20260801/`. These results support local
  safeguarded graph improvement on the primary case, not ADP superiority.
