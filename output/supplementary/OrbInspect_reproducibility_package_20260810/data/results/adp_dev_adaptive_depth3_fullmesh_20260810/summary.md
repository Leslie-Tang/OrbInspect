# Frozen ADP held-out superiority study

- Nodes: 24
- Targets: 41
- Training time: 0.518 s
- Superiority demonstrated: False

| Split | Method | n | Success | Penalized cost | Median online time (s) |
|---|---|---:|---:|---:|---:|
| validation | adaptive_rollout_adp | 12 | 1.000 | 93.586 | 1.684590 |
| validation | frozen_adp | 12 | 0.750 | 233.764 | 0.516701 |
| validation | search_only | 12 | 0.917 | 169.153 | 0.495762 |
| validation | incumbent | 12 | 1.000 | 116.256 | 0.000328 |
| validation | rollout | 12 | 1.000 | 106.439 | 0.012990 |
| validation | local_search | 12 | 1.000 | 109.299 | 0.006628 |
| validation | frozen_adp_safeguard | 12 | 1.000 | 116.256 | 0.500080 |
