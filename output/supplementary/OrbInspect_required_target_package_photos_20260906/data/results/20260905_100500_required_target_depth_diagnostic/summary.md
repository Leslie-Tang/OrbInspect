# Required-target depth-one-to-six diagnostic

Post-selection, user-requested validation diagnostic. Exact twelve confirmation scenarios and nine required IDs are unchanged. Every depth is recomputed sequentially; primary test results are not changed.

| Depth | Complete | Common | Mean common J | Change vs d3 (%) | Median time (s) | Time / d3 | Mean ADP screens |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 9/12 | 9 | 135.714329 | 14.507 | 0.027213 | 0.027 | 7131.833 |
| 2 | 9/12 | 9 | 133.449700 | 12.596 | 0.220704 | 0.219 | 65928.250 |
| 3 | 9/12 | 9 | 118.520436 | 0.000 | 1.009366 | 1.000 | 322349.000 |
| 4 | 9/12 | 9 | 115.271611 | -2.741 | 4.675955 | 4.633 | 1527408.167 |
| 5 | 9/12 | 9 | 115.271611 | -2.741 | 17.660148 | 17.496 | 5757081.000 |
| 6 | 9/12 | 9 | 115.271611 | -2.741 | 53.013305 | 52.521 | 17454611.083 |

online_time_s includes standalone greedy-base construction plus ADP planning; graph loading and result serialization are excluded.
safe_action_evaluations counts ADP screens only and excludes the separate preliminary greedy-base call.
Observations are presumed stabilized with exposure completed a priori; mission_duration_s is transfer-only and adds no modeled exposure duration.

- Post-selection validation diagnostic; cannot retroactively select the tested depth.
- Single sequential measurement per scenario-depth on a shared desktop host.
- Cost means condition on the common completed cohort; unconditional success and penalties remain visible.
- Realized policy cost need not vary monotonically with depth; no universal optimum or real-time guarantee is implied.
