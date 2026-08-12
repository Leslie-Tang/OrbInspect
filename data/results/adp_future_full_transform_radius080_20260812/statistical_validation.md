# Statistical validation

- Primary claim supported: True
- Confidence: CAUTION
- Fallacy scan: 11/11

| Split | Baseline | n | Success (ADP/base) | Mean difference [95% CI] | Reduction | W/T/L | Sign p |
|---|---|---:|---:|---:|---:|---:|---:|
| ood | local_search | 20 | 1.000/1.000 | -6.608 [-11.819, -1.706] | 6.7% | 14/1/5 | 0.0636 |
| ood | incumbent | 20 | 1.000/1.000 | -19.732 [-25.719, -14.356] | 17.7% | 20/0/0 | 1.91e-06 |
| ood | rollout | 20 | 1.000/1.000 | -10.775 [-15.043, -6.634] | 10.5% | 16/2/2 | 0.00131 |
| ood | search_only | 20 | 1.000/0.450 | -204.202 [-265.994, -143.051] | 69.0% | 20/0/0 | 1.91e-06 |
| ood | frozen_adp | 20 | 1.000/0.450 | -226.276 [-287.789, -163.526] | 71.1% | 20/0/0 | 1.91e-06 |
| test | local_search | 30 | 1.000/1.000 | -4.093 [-7.028, -1.143] | 4.0% | 21/4/5 | 0.00249 |
| test | incumbent | 30 | 1.000/1.000 | -13.921 [-17.281, -10.642] | 12.3% | 28/2/0 | 7.45e-09 |
| test | rollout | 30 | 1.000/1.000 | -7.136 [-10.226, -4.454] | 6.7% | 24/4/2 | 1.05e-05 |
| test | search_only | 30 | 1.000/0.533 | -165.528 [-214.957, -117.616] | 62.5% | 30/0/0 | 1.86e-09 |
| test | frozen_adp | 30 | 1.000/0.833 | -116.352 [-158.553, -81.047] | 53.9% | 30/0/0 | 1.86e-09 |

The paired simulation evidence is internally strong, but accepted scenarios are conditioned on incumbent feasibility and the result does not establish hardware or unmodeled-dynamics performance.
