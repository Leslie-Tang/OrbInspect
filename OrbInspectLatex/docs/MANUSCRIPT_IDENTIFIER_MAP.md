# Manuscript terminology and experiment identifiers

Internal experiment identifiers remain unchanged in the frozen data and code.
The manuscript uses descriptive labels so implementation details do not
interrupt the scientific argument.

| Internal identifier | Manuscript wording | Location |
|---|---|---|
| `required06` | 6-target profile | Tables II and IV |
| `required09` | 9-target profile | Tables II and IV; primary profile |
| `required12` | 12-target profile | Tables II and IV |
| `required09_test_000` | Representative test case | Section VI-D and Figure 6 |
| `validation_002` | Historical ROS 2 validation run | Figure 7 caption |
| `coverage_only80` | Coverage-only (80%) | Table VII |

The representative case is selected from jointly completed test missions by
proximity to the median ADP-minus-local graph-cost difference. Scenario IDs
break ties deterministically; the original selection rule is unchanged.

The historical ROS 2 run uses the earlier 80% survey objective. It is separate
from the current nine-target offline study; the terminology revision does not
turn it into a required-target ROS experiment.

Table II retains the explicit required-sample IDs because those identify the
fixed geometric targets. They serve reproducibility rather than narrative
labeling. No recorded data, selected scenario, target identity, numerical
result, figure artwork or scientific claim changes in this revision.

Repository-dependent table/detail generators use `publication_labels.py` to
keep these publication labels separate from immutable experiment keys.

Verification on 8 September 2026: all 38 relevant regression tests pass. The
compiled manuscript remains 12 pages, with no overfull boxes, oversized floats
or unresolved references. The full-page overview and changed pages 7, 9, 10
and 11 were visually checked. All figure-file integrity checks pass unchanged.
