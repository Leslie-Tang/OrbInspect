# High-coverage and mandatory-target stress test

The original frozen scenarios are retained. Structural infeasibility means the available candidate nodes cannot meet the requested weighted coverage even before dynamics-aware route search.

The stopping goal is weighted over the 41 candidate-observable targets, not all 90 mesh samples. Whole-surface coverage is reported separately.

## Selected spatial sentinels

The six sentinels are robust coordinate extremes that remain observable in every frozen test and OOD scenario. They are spatial proxies because the mesh targets do not carry semantic ISS component labels.

| Criterion | Target | Position (m) | Visible graph nodes |
|---|---|---:|---:|
| min_x | mesh_00010 | (-19.535, 9.277, 16.243) | 3 |
| max_x | mesh_00015 | (24.665, -27.133, 39.758) | 5 |
| min_y | mesh_00059 | (23.283, -27.648, -39.758) | 2 |
| max_y | mesh_00019 | (-13.489, 36.043, 39.758) | 3 |
| min_z | mesh_00053 | (-7.872, 29.219, -57.909) | 2 |
| max_z | mesh_00028 | (-8.417, 27.255, 57.909) | 4 |

## Results

| Goal | Requirement | Structural | Success (all) | Success (structural) | All sentinels | Weighted inspectable | Unweighted inspectable | Whole mesh | Mean SOOAs | Mean delta-v (m/s) |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 95% | coverage_only | 27/30 | 23/30 | 85.2% | 23/23 | 95.96% | 95.12% | 43.33% | 13.04 | 17.264 |
| 95% | six_spatial_sentinels | 27/30 | 23/30 | 85.2% | 23/23 | 95.96% | 95.12% | 43.33% | 13.04 | 17.264 |
| 98% | coverage_only | 19/30 | 10/30 | 52.6% | 10/10 | 98.05% | 97.56% | 44.44% | 13.60 | 19.506 |
| 98% | six_spatial_sentinels | 19/30 | 10/30 | 52.6% | 10/10 | 98.05% | 97.56% | 44.44% | 13.60 | 19.506 |
