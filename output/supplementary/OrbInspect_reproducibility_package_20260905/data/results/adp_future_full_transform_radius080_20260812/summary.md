# Safety-shielded rollout ADP held-out superiority study

- Nodes: 24
- Targets: 41
- Training time: 0.222 s
- Superiority demonstrated: True

| Split | Method | n | Success | Penalized cost | Median online time (s) |
|---|---|---:|---:|---:|---:|
| test | adaptive_rollout_adp | 30 | 1.000 | 99.397 | 0.709329 |
| test | frozen_adp | 30 | 0.833 | 215.749 | 0.201360 |
| test | search_only | 30 | 0.533 | 264.925 | 0.212677 |
| test | incumbent | 30 | 1.000 | 113.318 | 0.000158 |
| test | rollout | 30 | 1.000 | 106.534 | 0.005910 |
| test | local_search | 30 | 1.000 | 103.491 | 0.004916 |
| test | frozen_adp_safeguard | 30 | 1.000 | 113.318 | 0.198372 |
| ood | adaptive_rollout_adp | 20 | 1.000 | 91.867 | 0.345922 |
| ood | frozen_adp | 20 | 0.450 | 318.143 | 0.142563 |
| ood | search_only | 20 | 0.450 | 296.070 | 0.158560 |
| ood | incumbent | 20 | 1.000 | 111.600 | 0.000145 |
| ood | rollout | 20 | 1.000 | 102.643 | 0.004707 |
| ood | local_search | 20 | 1.000 | 98.475 | 0.003654 |
| ood | frozen_adp_safeguard | 20 | 1.000 | 111.600 | 0.142953 |
