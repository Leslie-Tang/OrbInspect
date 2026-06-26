# Offline Planning Experiment Summary

| Method | Raw coverage | Inspectable coverage | Delta-v | Peak input | Clipped steps | CW dynamic cost | Min clearance | Feasible |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| set_cover_cw_tour | 0.983 | 0.983 | 21.592 | 0.039 | 0 | 177.784 | 9.911 | True |
| proposed_safe_cw_nbv | 0.978 | 0.978 | 32.070 | 0.058 | 0 | 264.106 | 5.090 | True |
| coverage_greedy | 0.983 | 0.983 | 49.746 | 0.085 | 85 | 842.386 | -1.895 | False |
| safe_coverage_greedy | 0.983 | 0.983 | 45.367 | 0.058 | 0 | 373.659 | 0.887 | True |
| distance_greedy | 0.983 | 0.983 | 28.077 | 0.053 | 0 | 423.900 | -1.606 | False |
| fuel_greedy | 0.967 | 0.967 | 24.288 | 0.037 | 0 | 199.958 | 0.143 | True |
| random_safe | 0.983 | 0.983 | 62.604 | 0.059 | 0 | 515.532 | 1.010 | True |
