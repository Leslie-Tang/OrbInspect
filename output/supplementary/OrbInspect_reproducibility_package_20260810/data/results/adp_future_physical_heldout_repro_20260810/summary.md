# Safety-shielded rollout ADP held-out superiority study

- Nodes: 24
- Targets: 41
- Training time: 0.319 s
- Superiority demonstrated: True

| Split | Method | n | Success | Penalized cost | Median online time (s) |
|---|---|---:|---:|---:|---:|
| test | adaptive_rollout_adp | 30 | 1.000 | 92.789 | 1.380543 |
| test | frozen_adp | 30 | 0.600 | 273.410 | 0.388545 |
| test | search_only | 30 | 0.833 | 198.588 | 0.362846 |
| test | incumbent | 30 | 1.000 | 111.924 | 0.000215 |
| test | rollout | 30 | 1.000 | 103.286 | 0.009298 |
| test | local_search | 30 | 1.000 | 106.804 | 0.005724 |
| test | frozen_adp_safeguard | 30 | 1.000 | 111.924 | 0.381976 |
| ood | adaptive_rollout_adp | 20 | 1.000 | 92.063 | 0.598358 |
| ood | frozen_adp | 20 | 0.550 | 279.188 | 0.294183 |
| ood | search_only | 20 | 0.650 | 262.741 | 0.244156 |
| ood | incumbent | 20 | 1.000 | 107.853 | 0.000180 |
| ood | rollout | 20 | 1.000 | 98.782 | 0.006829 |
| ood | local_search | 20 | 1.000 | 100.453 | 0.003590 |
| ood | frozen_adp_safeguard | 20 | 1.000 | 107.361 | 0.310130 |
