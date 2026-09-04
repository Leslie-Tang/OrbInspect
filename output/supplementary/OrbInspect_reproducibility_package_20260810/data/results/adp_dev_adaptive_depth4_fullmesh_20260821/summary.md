# Safety-shielded rollout ADP held-out superiority study

- Nodes: 24
- Targets: 41
- Training time: 0.256 s
- Superiority demonstrated: False

| Split | Method | n | Success | Penalized cost | Median online time (s) |
|---|---|---:|---:|---:|---:|
| validation | adaptive_rollout_adp | 12 | 1.000 | 92.431 | 3.847184 |
| validation | frozen_adp | 12 | 0.750 | 233.764 | 0.241499 |
| validation | search_only | 12 | 0.917 | 169.153 | 0.250001 |
| validation | incumbent | 12 | 1.000 | 116.256 | 0.000170 |
| validation | rollout | 12 | 1.000 | 106.439 | 0.006829 |
| validation | local_search | 12 | 1.000 | 109.299 | 0.003349 |
| validation | frozen_adp_safeguard | 12 | 1.000 | 116.256 | 0.239861 |
