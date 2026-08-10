# Safety-shielded rollout ADP held-out superiority study

- Nodes: 24
- Targets: 41
- Training time: 0.428 s
- Superiority demonstrated: True

| Split | Method | n | Success | Penalized cost | Median online time (s) |
|---|---|---:|---:|---:|---:|
| test | adaptive_rollout_adp | 30 | 1.000 | 92.789 | 1.643444 |
| test | frozen_adp | 30 | 0.600 | 273.410 | 0.476281 |
| test | search_only | 30 | 0.833 | 198.588 | 0.425210 |
| test | incumbent | 30 | 1.000 | 111.924 | 0.000284 |
| test | rollout | 30 | 1.000 | 103.286 | 0.011812 |
| test | local_search | 30 | 1.000 | 106.804 | 0.007603 |
| test | frozen_adp_safeguard | 30 | 1.000 | 111.924 | 0.477653 |
| ood | adaptive_rollout_adp | 20 | 1.000 | 92.063 | 0.733225 |
| ood | frozen_adp | 20 | 0.550 | 279.188 | 0.340827 |
| ood | search_only | 20 | 0.650 | 262.741 | 0.306429 |
| ood | incumbent | 20 | 1.000 | 107.853 | 0.000241 |
| ood | rollout | 20 | 1.000 | 98.782 | 0.008826 |
| ood | local_search | 20 | 1.000 | 100.453 | 0.004344 |
| ood | frozen_adp_safeguard | 20 | 1.000 | 107.361 | 0.339969 |
