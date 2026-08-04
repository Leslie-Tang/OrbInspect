# Offline Planning Experiment Summary

| Method | Raw coverage | Inspectable coverage | Delta-v | Peak input | Clipped steps | CW dynamic cost | Min clearance | Feasible | Certificate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| safe_graph_adp | 0.983 | 0.983 | 19.465 | 0.038 | 0 | 160.281 | 9.911 | True |  |
| set_cover_cw_tour | 0.983 | 0.983 | 21.592 | 0.039 | 0 | 177.784 | 9.911 | True |  |
| safe_coverage_greedy | 0.983 | 0.983 | 45.367 | 0.058 | 0 | 373.659 | 0.887 | False |  |
| fuel_greedy | 0.967 | 0.967 | 24.288 | 0.037 | 0 | 199.958 | 0.143 | False |  |
| coverage_greedy | 0.983 | 0.983 | 49.746 | 0.085 | 85 | 842.386 | -1.895 | False |  |
