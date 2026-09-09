# Fresh required-nine ADP confirmation

The original nine required IDs are unchanged. Fresh scenarios and the one-step-ADP-seeded local comparator were frozen before evaluation.
No scenario is rejected. ADP3 has no one-step fallback. All base diagnostics refer to the original greedy policy.

| Split | Method | Complete | N | Successful mean cost | Median time (s) |
|---|---|---:|---:|---:|---:|
| ood | incumbent | 0 | 30 | nan | 0.0003 |
| ood | one_step_adp | 8 | 30 | 140.102 | 0.0037 |
| ood | seeded_local_search | 8 | 30 | 130.841 | 0.0037 |
| ood | adaptive_rollout_adp | 9 | 30 | 120.751 | 0.1747 |
| ood | coverage_only80 | 0 | 30 | nan | 0.1770 |
| test | incumbent | 0 | 50 | nan | 0.0004 |
| test | one_step_adp | 43 | 50 | 135.945 | 0.0240 |
| test | seeded_local_search | 43 | 50 | 129.892 | 0.0247 |
| test | adaptive_rollout_adp | 43 | 50 | 115.641 | 1.0269 |
| test | coverage_only80 | 1 | 50 | 136.614 | 0.5159 |

- Comparator includes depth-one ADP; effects are empirical and not guaranteed against local search.
- Same corrected graph and unchanged synthetic nine-item requirement; fresh perturbations are not independent geometries.
- All greedy-base failures are retained; base-cost bound is conditional on successful greedy completion.
- No new ROS execution or DRL-trained policy is represented by this campaign.

Frozen inputs, target identities and per-scenario routes are retained under raw/ and config_snapshot/. ROS bags and videos are not generated.
