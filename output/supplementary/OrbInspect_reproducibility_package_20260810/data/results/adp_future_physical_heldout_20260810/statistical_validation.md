# Statistical validation

- Primary claim supported: True
- Confidence: CAUTION
- Fallacy scan: 11/11

| Split | Baseline | n | Success (ADP/base) | Mean difference [95% CI] | Reduction | W/T/L | Sign p |
|---|---|---:|---:|---:|---:|---:|---:|
| ood | local_search | 20 | 1.000/1.000 | -8.390 [-11.677, -5.223] | 8.4% | 17/1/2 | 0.000729 |
| ood | incumbent | 20 | 1.000/1.000 | -15.790 [-20.430, -11.687] | 14.6% | 20/0/0 | 1.91e-06 |
| ood | rollout | 20 | 1.000/1.000 | -6.719 [-9.605, -4.022] | 6.8% | 17/0/3 | 0.00258 |
| ood | search_only | 20 | 1.000/0.650 | -170.678 [-242.202, -107.119] | 65.0% | 20/0/0 | 1.91e-06 |
| ood | frozen_adp | 20 | 1.000/0.550 | -187.125 [-260.804, -119.849] | 67.0% | 20/0/0 | 1.91e-06 |
| test | local_search | 30 | 1.000/1.000 | -14.016 [-18.265, -10.451] | 13.1% | 28/2/0 | 7.45e-09 |
| test | incumbent | 30 | 1.000/1.000 | -19.135 [-23.907, -14.583] | 17.1% | 30/0/0 | 1.86e-09 |
| test | rollout | 30 | 1.000/1.000 | -10.497 [-13.802, -7.401] | 10.2% | 28/2/0 | 7.45e-09 |
| test | search_only | 30 | 1.000/0.833 | -105.800 [-154.357, -66.245] | 53.3% | 30/0/0 | 1.86e-09 |
| test | frozen_adp | 30 | 1.000/0.600 | -180.622 [-233.456, -132.209] | 66.1% | 30/0/0 | 1.86e-09 |

The paired simulation evidence is internally strong, but accepted scenarios are conditioned on incumbent feasibility and the result does not establish hardware or unmodeled-dynamics performance.
