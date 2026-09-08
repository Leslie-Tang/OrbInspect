# Table layout revision — 8 September 2026

This revision follows the self-contained-folder organization. It changes table
geometry only; it does not revise the manuscript's scientific content.

## Layout choices

| Table | Change | Reason |
|---|---|---|
| I | Unchanged, two columns | The modeling-assumption descriptions need the width. |
| II | One column; target IDs wrap; two-line slab-count header | Removes a wide float used mainly for long ID lists. |
| III | Retained two columns; columns distributed across the text width | Eight columns remain readable without shrinking text. |
| IV | One column; stacked headers | The short development-results table fits comfortably. |
| V | Retained two columns; columns distributed across the text width | Seven columns include method names and resource metrics. |
| VI | Retained two columns; columns distributed across the text width | Seven columns include confidence intervals and sign-test results. |
| VII | Unchanged, one column | Already uses an appropriate compact layout. |

Captions, table numbers, row order, all data cells, manuscript prose and figure
artwork are unchanged. Header wording is preserved, with line breaks added
only where needed. No table is scaled or given a smaller font.

## Verification

- The rebuilt paper remains 12 pages.
- The full-paper page overview and table pages 7, 9 and 10 were visually checked.
- Table text remains 8.2192 PDF points, matching the preceding version.
- All nine included table/numerical fragments were checked against the
  pre-revision files: data blocks and captions are unchanged, and only the
  intended layout transformations differ.
- `main.tex` is byte-identical to the pre-revision source.
- The local dependency check passes: 32 compile inputs, zero external project
  inputs, seven figure groups and 52 unchanged figure files.
- The build has no overfull boxes, oversized floats or unresolved references.
- All 23 relevant regression tests pass, including four table-layout tests.

The repository-side table writer applies these rules through
`tools/paper/table_layout.py`, so regenerating a table retains its layout.
The portable LaTeX package includes the formatted TeX fragments and does not
need the repository-side generator to compile.
