# Folder organization, 2026-09-08

The current paper is separated from historical assets and repository-dependent
analysis tools. `main.tex` remains the entry point. Only file references were
changed in the manuscript; wording, equations, numeric table contents and all
figure files were preserved. Concurrent author edits to figure widths were
retained rather than replaced with the earlier saved source.

## Preservation and scope

The complete previous LaTeX folder was moved into
`archive/preorganization_20260908/`. The latest source saved by the editor during
organization is also preserved under its `concurrent_editor/` subfolder.
`organization_manifest.json` maps original files and hashes, figure path
replacements, and copied local evidence. No earlier data or figure options
were deleted. The two previous Figure 2 alternatives are also retained in
`archive/figure2_alternatives/`.

`tools/paper/` in the repository contains the working copies of the former
repository-dependent scripts. Their original bytes remain in the archive.
The standalone paper needs none of these scripts or the archive to compile.
Existing full-repository reproducibility packages remain unchanged.

## Build policy

The included `.latexmkrc` sends the PDF and intermediate files to `build/`.
The Makefile always invokes latexmk, so changes to included tables and figures
are detected. `make clean` targets only intermediate build files, not source
or figure PDFs. The source ZIP is assembled from an explicit allow-list and
does not include historical files or generated build debris.

Standard TeX packages are external software dependencies, not manuscript assets.
The nonstandard journal class and IEEE bibliography style are included locally.
The source package contains no project-external include paths or symlinks.

## Verification

Run `make check` to resolve every active input, validate the numbered figure
inventory and hashes, and verify that draw.io/SVG image resources are embedded.
Run `python3 scripts/check_project.py --verify-archive` in the complete working
folder to verify the preservation inventory. The archive option is intentionally
not applicable to the lightweight source ZIP.

The source ZIP was extracted outside the repository and compiled with no
repository-specific search paths. Its 12-page PDF has identical page text
and identical 120-dpi page renders to both the organized working build and
a fresh build of the latest author source using its original input paths.
The render comparison isolates the folder change from concurrent author edits.
All seven figure groups (52 files), 32 local compilation inputs and 756
inventoried archival files pass integrity checks. The 19 relevant repository
regression tests pass. No overfull boxes, unresolved references or oversized
float warnings remain; existing underfull spacing diagnostics are unchanged.
The page contact sheet and full Figure 2 page were visually inspected.

The earlier figures and manuscript versions remain available, and no raw
experimental source outside the LaTeX folder was modified. Copied evidence
snapshots retain the original bytes and provenance records.
