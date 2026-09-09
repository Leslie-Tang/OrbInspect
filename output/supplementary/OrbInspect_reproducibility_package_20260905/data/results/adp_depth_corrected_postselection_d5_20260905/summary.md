# Safety-shielded rollout ADP held-out superiority study

- Nodes: 24
- Targets: 41
- Training time: 0.163 s
- Superiority demonstrated: False

| Split | Method | n | Success | Penalized cost | Median online time (s) |
|---|---|---:|---:|---:|---:|
| validation | adaptive_rollout_adp | 12 | 1.000 | 100.870 | 4.582243 |
| validation | frozen_adp | 12 | 0.750 | 248.949 | 0.119302 |
| validation | search_only | 12 | 0.083 | 393.464 | 0.128446 |
| validation | incumbent | 12 | 1.000 | 113.781 | 0.000105 |
| validation | rollout | 12 | 1.000 | 107.074 | 0.003633 |
| validation | local_search | 12 | 1.000 | 109.343 | 0.001759 |
| validation | frozen_adp_safeguard | 12 | 1.000 | 113.781 | 0.118708 |
