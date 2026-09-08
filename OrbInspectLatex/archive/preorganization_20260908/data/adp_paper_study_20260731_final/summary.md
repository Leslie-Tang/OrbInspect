# Safety-Shielded Graph ADP Study

| Case | Method | Coverage | Delta-v | Clearance | Feasible | Plan time | Exact gap |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: |
| primary | safe_graph_adp | 0.9833 | 19.465 | 9.911 | True | 340.293 |  |
| primary | set_cover_cw_tour | 0.9833 | 21.592 | 9.911 | True | 6.045 |  |
| primary | safe_coverage_greedy | 0.9833 | 45.367 | 0.887 | False | 6.039 |  |
| primary | fuel_greedy | 0.9667 | 24.288 | 0.143 | False | 10.849 |  |
| primary | coverage_greedy | 0.9833 | 49.746 | -1.895 | False | 5.353 |  |
| oracle_n8_seed3 | safe_graph_adp | 0.4250 | 5.320 | 17.836 | True | 8.345 | 0.0000 |
| oracle_n8_seed7 | safe_graph_adp | 0.4250 | 5.320 | 17.836 | True | 8.416 | 0.0000 |
| oracle_n8_seed11 | safe_graph_adp | 0.4250 | 5.320 | 17.836 | True | 8.485 | 0.0000 |
| oracle_n10_seed3 | safe_graph_adp | 0.4250 | 5.320 | 17.836 | True | 13.794 | 0.0000 |
| oracle_n10_seed7 | safe_graph_adp | 0.4250 | 5.320 | 17.836 | True | 13.686 | 0.0000 |
| oracle_n10_seed11 | safe_graph_adp | 0.4250 | 5.320 | 17.836 | True | 14.008 | 0.0000 |
| oracle_n12_seed3 | safe_graph_adp | 0.4250 | 5.320 | 17.836 | True | 19.604 | 0.0000 |
| oracle_n12_seed7 | safe_graph_adp | 0.4250 | 5.320 | 17.836 | True | 19.631 | 0.0000 |
| oracle_n12_seed11 | safe_graph_adp | 0.4250 | 5.320 | 17.836 | True | 19.790 | 0.0000 |
| robustness_ic0 | safe_graph_adp | 0.9833 | 19.465 | 9.911 | True | 273.458 |  |
| robustness_ic0 | set_cover_cw_tour | 0.9833 | 21.592 | 9.911 | True | 6.098 |  |
| robustness_ic1 | safe_graph_adp | 0.9833 | 37.124 | 4.125 | True | 196.450 |  |
| robustness_ic1 | set_cover_cw_tour | 0.9833 | 23.088 | 0.808 | False | 6.482 |  |
| robustness_ic2 | safe_graph_adp | 0.9833 | 20.099 | 6.863 | True | 239.292 |  |
| robustness_ic2 | set_cover_cw_tour | 0.9833 | 20.193 | 6.863 | True | 5.459 |  |
| compute_critic_free | safe_graph_adp | 0.9551 | 32.231 | 10.900 | True | 60.772 |  |
| compute_short_training | safe_graph_adp | 0.9663 | 30.195 | 9.522 | True | 83.984 |  |
| compute_primary_compute | safe_graph_adp | 0.9326 | 26.949 | 14.427 | True | 91.227 |  |
| compute_deeper_lookahead | safe_graph_adp | 0.9438 | 29.737 | 5.742 | True | 103.246 |  |
