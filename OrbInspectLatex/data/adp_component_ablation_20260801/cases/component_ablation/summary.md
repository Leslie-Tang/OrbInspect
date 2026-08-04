# Offline Planning Experiment Summary

| Method | Raw coverage | Inspectable coverage | Delta-v | Peak input | Clipped steps | CW dynamic cost | Min clearance | Feasible | Certificate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| set_cover_cw_tour | 0.983 | 0.983 | 21.592 | 0.039 | 0 | 177.784 | 9.911 | True |  |
| safe_graph_adp_critic_only | 0.983 | 0.983 | 42.861 | 0.060 | 0 | 352.955 | 1.345 | True |  |
| safe_graph_adp_critic_safeguard | 0.983 | 0.983 | 21.592 | 0.039 | 0 | 177.784 | 9.911 | True |  |
| safe_graph_adp_rollout | 0.983 | 0.983 | 20.924 | 0.037 | 0 | 172.315 | 9.911 | True |  |
| safe_graph_adp_local_search | 0.983 | 0.983 | 19.465 | 0.038 | 0 | 160.281 | 9.911 | True |  |
| safe_graph_adp_no_local | 0.983 | 0.983 | 20.924 | 0.037 | 0 | 172.315 | 9.911 | True |  |
| safe_graph_adp | 0.983 | 0.983 | 19.465 | 0.038 | 0 | 160.281 | 9.911 | True |  |
