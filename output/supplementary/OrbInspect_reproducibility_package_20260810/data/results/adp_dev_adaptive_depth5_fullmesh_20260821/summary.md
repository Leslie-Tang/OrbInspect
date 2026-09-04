# Safety-shielded rollout ADP held-out superiority study

- Nodes: 24
- Targets: 41
- Training time: 0.273 s
- Superiority demonstrated: False

| Split | Method | n | Success | Penalized cost | Median online time (s) |
|---|---|---:|---:|---:|---:|
| validation | adaptive_rollout_adp | 12 | 1.000 | 92.369 | 14.966280 |
| validation | frozen_adp | 12 | 0.750 | 233.764 | 0.277353 |
| validation | search_only | 12 | 0.917 | 169.153 | 0.248111 |
| validation | incumbent | 12 | 1.000 | 116.256 | 0.000177 |
| validation | rollout | 12 | 1.000 | 106.439 | 0.006966 |
| validation | local_search | 12 | 1.000 | 109.299 | 0.003516 |
| validation | frozen_adp_safeguard | 12 | 1.000 | 116.256 | 0.250894 |
