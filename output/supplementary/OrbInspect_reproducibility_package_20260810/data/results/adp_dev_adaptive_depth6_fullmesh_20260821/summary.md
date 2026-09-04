# Safety-shielded rollout ADP held-out superiority study

- Nodes: 24
- Targets: 41
- Training time: 0.421 s
- Superiority demonstrated: False

| Split | Method | n | Success | Penalized cost | Median online time (s) |
|---|---|---:|---:|---:|---:|
| validation | adaptive_rollout_adp | 12 | 1.000 | 91.564 | 38.420876 |
| validation | frozen_adp | 12 | 0.750 | 233.764 | 0.243506 |
| validation | search_only | 12 | 0.917 | 169.153 | 0.246731 |
| validation | incumbent | 12 | 1.000 | 116.256 | 0.000174 |
| validation | rollout | 12 | 1.000 | 106.439 | 0.006631 |
| validation | local_search | 12 | 1.000 | 109.299 | 0.003466 |
| validation | frozen_adp_safeguard | 12 | 1.000 | 116.256 | 0.247198 |
