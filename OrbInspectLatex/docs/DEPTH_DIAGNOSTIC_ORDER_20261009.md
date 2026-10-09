# Depth diagnostic presentation, 9 October 2026

The main manuscript now presents the validation depth study first in Results,
as Section VI-A, “Rollout Depth and Computational Cost.” The depth figure moves
with the subsection; its artwork, inclusion dimensions, fonts, and panel layout
are unchanged. LaTeX automatically numbers it Figure 3, ahead of the paired
comparison (Figure 4) and representative route (Figure 5).

The protocol distinguishes the earlier fixed-library confirmation, for which
depth three was already frozen, from the later independently certified
all-solvable benchmark. The six-depth diagnostic followed the confirmation and
supported retaining depth three for the subsequent benchmark. The supplement
uses the same explanation. This does not claim prospective depth selection for
the earlier confirmation or a universally optimal depth.

The repeated development-history paragraph was removed from the main Results;
its outcomes remain in Supplementary Table S3 and the protocol still identifies
its role in motivating the fresh comparator. No experiment was rerun.

## Validation

- `make all`, `make check`, and `git diff --check` passed.
- Main manuscript: 13 pages. Supplement: 2 pages.
- All 68 approved figure files passed the recorded integrity hashes.
- All main-article tables and displayed equations match the pre-edit source.
- Figure inclusions, including sizes, match the pre-edit source irrespective of
  their order. Only the depth figure's caption wording changed.
- No overflow, unresolved reference, missing citation, or oversized float was
  reported. Existing underfull typesetting warnings remain.
- Rendered all article and supplement pages and inspected the Results page in
  detail. No clipping, overlap, or stranded subsection heading was observed.
- Root-level PDFs and existing auxiliary files were refreshed from `build/`.
