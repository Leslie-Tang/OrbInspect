# Safety-Shielded Graph Approximate Policy Iteration

The advanced planner selects finite-duration safe observable orbital arcs
(SOOAs) as decision nodes. It is implemented as a ROS-independent core in
`orbinspect_guidance.advanced_safe_planner` and is exercised by the offline
paper experiment.

The decision state contains:

- current candidate node;
- covered-target bit mask;
- selected-node bit mask; and
- remaining action budget.

The planner learns a linear action-value approximation from reproducible safe
rollouts. Truncated Bellman look-ahead uses that approximation as its terminal
value. A deterministic two-stage tour is retained as a base policy. Shielded
rollout and audited sequence improvement may improve that base, while the final
selector guarantees that a feasible returned policy is no worse than the base
on the same graph. The saved `policy_source` field states whether the winner was
the learned policy, rollout, the unchanged safeguard, or the improved base.

The HCW transfer evaluator remains responsible for motion generation. An edge
is hidden from training and execution when it violates any enabled input,
speed, terminal, clearance, or passive-drift audit. Learning never overrides
the shield.

The paper study exposes explicit component variants. Disabled components are
not evaluated and cannot influence the returned sequence:

- `safe_graph_adp_critic_only`: learned critic and finite look-ahead only;
- `safe_graph_adp_critic_safeguard`: critic plus the unchanged base tour;
- `safe_graph_adp_rollout`: one-step rollout plus the base safeguard;
- `safe_graph_adp_local_search`: audited reversal search plus the base;
- `safe_graph_adp_no_local`: critic, rollout, and base safeguard; and
- `safe_graph_adp`: all components.

The ROS status node exposes the same switches as YAML parameters:
`enable_critic`, `enable_rollout`, `enable_reference_safeguard`, and
`reference_improvement_passes`. Set the last value to zero to disable local
search. Local search requires the safeguard because it improves the audited
base sequence.

Run the offline comparison:

```bash
ros2 run orbinspect_guidance offline_planning_experiment \
  --config src/orbinspect_guidance/config/offline_planning_experiment.yaml
```

Run the independently archived paper study:

```bash
ros2 run orbinspect_guidance offline_adp_study \
  --config src/orbinspect_guidance/config/offline_planning_experiment.yaml
```

The study writes primary, exact-oracle, initial-condition, and compute cases
under one timestamped root. Use `--families primary,oracle` to run a subset or
`--quick` to reduce repeated cases.

Then render figures from the saved result directory:

```bash
ros2 run orbinspect_guidance offline_planning_plots \
  --result-dir data/results/<run-id>
```

The ROS status node publishes readiness on `/advanced_planner/status`. It does
not replace `/chaser/reference` or `/chaser/safe_control_command`; online
closed-loop activation remains a separate integration step after offline
validation.
