# Safety-shielded rollout ADP held-out superiority study

- Nodes: 24
- Targets: 41
- Training time: 0.148 s
- Superiority demonstrated: False

| Split | Method | n | Success | Penalized cost | Median online time (s) |
|---|---|---:|---:|---:|---:|
| validation | adaptive_rollout_adp | 12 | 1.000 | 101.211 | 1.458689 |
| validation | frozen_adp | 12 | 0.750 | 248.949 | 0.113373 |
| validation | search_only | 12 | 0.083 | 393.464 | 0.134198 |
| validation | incumbent | 12 | 1.000 | 113.781 | 0.000106 |
| validation | rollout | 12 | 1.000 | 107.074 | 0.003581 |
| validation | local_search | 12 | 1.000 | 109.343 | 0.001736 |
| validation | frozen_adp_safeguard | 12 | 1.000 | 113.781 | 0.120447 |
