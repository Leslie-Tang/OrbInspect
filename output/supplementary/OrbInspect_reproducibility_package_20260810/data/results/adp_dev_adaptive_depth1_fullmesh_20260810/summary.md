# Frozen ADP held-out superiority study

- Nodes: 24
- Targets: 41
- Training time: 0.492 s
- Superiority demonstrated: False

| Split | Method | n | Success | Penalized cost | Median online time (s) |
|---|---|---:|---:|---:|---:|
| validation | adaptive_rollout_adp | 12 | 1.000 | 101.424 | 0.039874 |
| validation | frozen_adp | 12 | 0.750 | 233.764 | 0.505945 |
| validation | search_only | 12 | 0.917 | 169.153 | 0.502811 |
| validation | incumbent | 12 | 1.000 | 116.256 | 0.000317 |
| validation | rollout | 12 | 1.000 | 106.439 | 0.013041 |
| validation | local_search | 12 | 1.000 | 109.299 | 0.007334 |
| validation | frozen_adp_safeguard | 12 | 1.000 | 116.256 | 0.490639 |
